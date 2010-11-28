#!/usr/bin/python
# -*- coding: utf-8 -*-
'''
@date: 2010-11-12
@author: shell.xu
'''
import sys
import time
import heapq
from greenlet import greenlet
from contextlib import contextmanager

import traceback

try:
    import epoll
    epoll_factory = epoll.poll
    timout_factor = 1000
    python_epoll = True
except ImportError:
    import select as epoll
    epoll_factory = epoll.epoll
    timout_factor = 1.0
    python_epoll = False

class TimeOutException(Exception): pass

class TimeoutObject(object):
    ''' 超时对象 '''
    def __init__(self, timeout, gr, exp):
        self.timeout, self.gr, self.exp = timeout, gr, exp
    def __cmp__(self, o): return self.timeout > o.timeout
    def cancel(self):
        ''' 取消超时对象的作用 '''
        bus.unset_timeout(self)

class EpollBus(object):

    def __init__(self):
        self.fdrmap, self.fdwmap = {}, {}
        self.queue, self.timeline = [], []
        self.init_poll()

    def init_poll(self):
        ''' 初始化poll对象，必须在fork后使用。 '''
        self.poll = epoll_factory()
        if not python_epoll: self._epoll_modify = self.poll.modify
        else: self._epoll_modify = self.poll.register

    def _setpoll(self, fd):
        ''' 同步某fd的fdmap和poll注册 '''
        ev = epoll.POLLHUP
        if fd in self.fdrmap: ev |= epoll.POLLIN
        if fd in self.fdwmap: ev |= epoll.POLLOUT
        try: self._epoll_modify(fd, ev)
        except IOError: self.poll.register(fd, ev)

    def wait_for_read(self, fd):
        ''' 等待，直到某fd可以读 '''
        self.fdrmap[fd] = greenlet.getcurrent()
        self._setpoll(fd)
        self.schedule()
        try: del self.fdrmap[fd]
        except KeyError: pass
        self._setpoll(fd)

    def wait_for_write(self, fd):
        ''' 等待，直到某fd可以写 '''
        self.fdwmap[fd] = greenlet.getcurrent()
        self._setpoll(fd)
        self.schedule()
        try: del self.fdwmap[fd]
        except KeyError: pass
        self._setpoll(fd)

    def unreg(self, fd):
        ''' 反注册某fd，不再发生任何事件 '''
        try: del self.fdwmap[fd]
        except KeyError: pass
        try: del self.fdrmap[fd]
        except KeyError: pass
        try: self.poll.unregister(fd)
        except (IOError, KeyError): pass

    def set_timeout(self, timeout, exp = TimeOutException):
        ''' 注册某个greenlet的超时，返回超时对象 '''
        gr = greenlet.getcurrent()
        ton = TimeoutObject(time.time() + timeout, gr, exp)
        ton.stack = traceback.format_stack()
        heapq.heappush(self.timeline, ton)
        return ton

    def unset_timeout(self, ton):
        ''' 取消某greenlet的超时
        @param ton: 超时对象 '''
        try:
            self.timeline.remove(ton)
            heapq.heapify(self.timeline)
        except ValueError: pass

    def next_job(self, gr, *args):
        ''' 加入调度队列
        @param gr: 需要被调度的greenlet对象
        @param args: 调度greenlet对象的参数 '''
        self.queue.append((gr, args))
        return len(self.queue) > 50

    def _switch_queue(self):
        ''' 调度队列，直到列队空或者当前gr被队列调度。
        @return: 如果队列空，返回None，如果当前gr被调度，返回被调度的gr对象和参数。 '''
        gr = greenlet.getcurrent()
        while self.queue:
            q = self.queue[-1]
            if q[0].dead: self.queue.pop()
            elif q[0] == gr: return self.queue.pop()
            else: q[0].switch(*q[1])

    def _fire_timeout(self):
        ''' 检测timeout的发生。
        @return: 发生所有timeout后，返回下一个timeout发生的interval。 '''
        t = time.time()
        while self.timeline and t > self.timeline[0].timeout:
            next = heapq.heappop(self.timeline)
            if next.gr:
                # print 'fire_timeout', id(next.gr)
                # print ''.join(next.stack)
                self._gr_exp(next.gr, next.exp)
        if not self.timeline: return -1
        return (self.timeline[0].timeout - t) * timout_factor

    def _gr_exp(self, gr, exp):
        if not gr: return
        self.next_job(greenlet.getcurrent())
        gr.throw(exp)

    def _load_poll(self, timeout = -1):
        ''' 读取poll对象，并且将发生事件的fd所注册的gr加入队列。
        @param timeout: 下一次超时的interval。 '''
        for fd, ev in self.poll.poll(timeout):
            # print 'event come', fd, ev
            if ev & epoll.POLLHUP:
                self._gr_exp(self.fdwmap.get(fd, None), EOFError)
                self._gr_exp(self.fdrmap.get(fd, None), EOFError)
                self.unreg(fd)
                # TODO: close here
            elif ev & epoll.POLLIN and fd in self.fdrmap:
                if self.next_job(self.fdrmap[fd]): break
            elif ev & epoll.POLLOUT and fd in self.fdwmap:
                if self.next_job(self.fdwmap[fd]): break
            else: self._setpoll(fd)
        # print len(self.queue), len(self.fdrmap), len(self.fdwmap)

    def schedule(self):
        ''' 调度 '''
        while not self._switch_queue():
            self._load_poll(self._fire_timeout())

bus = EpollBus()

class TokenPool(object):
    ''' 令牌池，程序可以从中获得一块令牌。当令牌耗尽时，阻塞直到有程序释放令牌为止。
    用法：
    token = TokenPool(10)
    with token.item():
        do things...
    '''

    def __init__(self, max_item): self.token, self.gr_wait = max_item, []
    @contextmanager
    def item(self):
        gr = greenlet.getcurrent()
        while self.token == 0:
            if gr not in self.gr_wait: self.gr_wait.append(gr)
            bus.schedule()
        self.token -= 1
        try: yield
        finally:
            self.token += 1
            if self.token == 1:
                bus.next_job(greenlet.getcurrent())
                self.gr_wait.pop().switch()

class ObjPool(object):
    ''' 对象池，程序可以从中获得一个对象。当对象耗尽时，阻塞直到有程序释放对象为止。
    具体实现必须重载create函数和unbind函数。
    用法：
    objpool = ObjPool(10)
    with token.item() as obj:
        do things with obj...
    '''

    def __init__(self, max_item):
        self.max_item = max_item
        self.pool, self.count, self.gr_wait = [], 0, []

    @contextmanager
    def item(self):
        gr = greenlet.getcurrent()
        while self.count >= self.max_item:
            if gr not in self.gr_wait: self.gr_wait.append(gr)
            bus.schedule()
        if not self.pool: self.pool.append(self.create())
        self.count += 1
        obj = self.pool.pop()
        try: yield obj
        finally:
            self.unbind(obj)
            self.pool.append(obj)
            self.count -= 1
            if self.count == self.max_item - 1:
                bus.next_job(greenlet.getcurrent())
                self.gr_wait.pop().switch()

    def create(self):
        ''' 返回一个对象，用于对象创建 '''
        pass

    def unbind(self):
        ''' 将对象和当前gr分离，常用于socket对象的unreg。 '''
        pass
        
