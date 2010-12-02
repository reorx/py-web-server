#!/usr/bin/python
# -*- coding: utf-8 -*-
'''
@date: 2010-11-12
@author: shell.xu
'''
import sys
import time
import heapq
import logging
from greenlet import greenlet
from contextlib import contextmanager

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
        self.t, self.gr, self.exp = timeout, gr, exp
    def __eq__(self, o): return self is o
    def __cmp__(self, o): return self.t > o.t
    def cancel(self):
        ''' 取消超时对象的作用 '''
        bus.unset_timeout(self)

class EpollBus(object):

    def __init__(self):
        self.fdrmap, self.fdwmap = {}, {}
        self.queue, self.wait_for_end = [], {}
        self.tol, self.ftol = [], []
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
        self.ftol.append(ton)
        return ton

    def unset_timeout(self, ton):
        ''' 取消某greenlet的超时
        @param ton: 超时对象 '''
        if ton in self.ftol: self.ftol.remove(ton)
        elif ton in self.tol:
            try:
                self.tol.remove(ton)
                heapq.heapify(self.tol)
            except ValueError: pass

    def _pre_switch(self):
        while self.ftol: heapq.heappush(self.tol, self.ftol.pop())

    def add_queue(self, gr, *args):
        ''' 加入调度队列
        @param gr: 需要被调度的greenlet对象
        @param args: 调度greenlet对象的参数 '''
        self.queue.append((gr, args))
        return len(self.queue) > 50

    def fork_gr(self, func, *args):
        ''' 建立新的gr，并加入调度队列。
        @param func: 主函数
        @param args: 参数 '''
        gr = greenlet(self._gr_root)
        self.add_queue(gr, func, *args)
        return gr

    def _gr_root(self, func, *args):
        try:
            curgr = greenlet.getcurrent()
            rslt = func(*args)
            gr_waits = self.wait_for_end.pop(curgr, None)
            if gr_waits is not None:
                for gr in gr_waits: self.add_queue(gr)
            return rslt
        except KeyboardInterrupt: raise
        except: logging.exception('unknown error')

    def switch_out(self, gr, *args):
        ''' 人工调出，执行gr所指定的上下文，最终可能切回。
        @param gr: greenlet，需要被切入的上下文
        @param args: 切入的参数 '''
        if not gr: return
        self.add_queue(greenlet.getcurrent())
        self._pre_switch()
        gr.switch(*args)

    def wait_for_gr(self, gr):
        ''' 等待一个gr结束。注意被等待的gr必须是使用fork_gr建立的。 '''
        curgr = greenlet.getcurrent()
        if gr.dead: return
        if gr not in self.wait_for_end: self.wait_for_end[gr] = []
        if curgr not in self.wait_for_end[gr]:
            self.wait_for_end[gr].append(curgr)
        while not gr.dead: self.schedule()

    def _switch_queue(self):
        ''' 调度队列，直到列队空或者当前gr被队列调度。
        除非预先设定监听fd事件，否则当前上下文不会自动被切回。
        @return: 如果队列空，返回None，如果当前gr被调度，返回被调度的gr对象和参数。 '''
        gr = greenlet.getcurrent()
        while self.queue:
            q = self.queue[-1]
            if q[0].dead: self.queue.pop()
            elif q[0] == gr: return self.queue.pop()
            else:
                self._pre_switch()
                q[0].switch(*q[1])

    def _fire_timeout(self):
        ''' 检测timeout的发生。
        @return: 发生所有timeout后，返回下一个timeout发生的interval。 '''
        t = time.time()
        while self.tol and t > self.tol[0].t:
            next = heapq.heappop(self.tol)
            self.throw_gr_exp(next.gr, next.exp)
        if not self.tol: return -1
        return (self.tol[0].t - t) * timout_factor

    def throw_gr_exp(self, gr, exp):
        ''' 向某个gr抛出异常，会切回当前gr。 '''
        if not gr: return
        self.add_queue(greenlet.getcurrent())
        gr.throw(exp)

    def _load_poll(self, timeout = -1):
        ''' 读取poll对象，并且将发生事件的fd所注册的gr加入队列。
        @param timeout: 下一次超时的interval。 '''
        for fd, ev in self.poll.poll(timeout):
            # print 'event come', fd, ev
            if ev & epoll.POLLHUP:
                self.throw_gr_exp(self.fdwmap.get(fd, None), EOFError)
                self.throw_gr_exp(self.fdrmap.get(fd, None), EOFError)
                self.unreg(fd)
                # TODO: close here
            elif ev & epoll.POLLIN and fd in self.fdrmap:
                if self.add_queue(self.fdrmap[fd]): break
            elif ev & epoll.POLLOUT and fd in self.fdwmap:
                if self.add_queue(self.fdwmap[fd]): break
            else: self._setpoll(fd)

    def schedule(self):
        ''' 调度，进入调度后不会自动被切回。 '''
        while not self._switch_queue():
            self._load_poll(self._fire_timeout())

bus = EpollBus()

class TokenPool(object):
    ''' 令牌池，程序可以从中获得一块令牌。当令牌耗尽时，阻塞直到有程序释放令牌为止。
    用法：
    token = TokenPool(10)
    with token.item():
        do things... '''

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
            if self.token == 1 and self.gr_wait:
                bus.switch_out(self.gr_wait.pop())
