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
    def __init__(self, timeout, gr, exp):
        self.timeout, self.gr, self.exp = timeout, gr, exp
    def __cmp__(self, o): return self.timeout > o.timeout
    def cancel(self): bus.unset_timeout(self)

class EpollBus(object):

    def __init__(self):
        self.fdrmap, self.fdwmap = {}, {}
        self.queue, self.timeline = [], []
        self.init_poll()

    def init_poll(self):
        self.poll = epoll_factory()
        if not python_epoll: self._epoll_modify = self.poll.modify
        else: self._epoll_modify = self.poll.register

    def _setpoll(self, fd):
        ev = epoll.POLLHUP
        if fd in self.fdrmap: ev |= epoll.POLLIN
        if fd in self.fdwmap: ev |= epoll.POLLOUT
        try: self._epoll_modify(fd, ev)
        except IOError: self.poll.register(fd, ev)

    def wait_for_read(self, fd):
        self.fdrmap[fd] = greenlet.getcurrent()
        self._setpoll(fd)
        self.schedule()
        try: del self.fdrmap[fd]
        except KeyError: pass
        self._setpoll(fd)

    def wait_for_write(self, fd):
        self.fdwmap[fd] = greenlet.getcurrent()
        self._setpoll(fd)
        self.schedule()
        try: del self.fdwmap[fd]
        except KeyError: pass
        self._setpoll(fd)

    def unreg(self, fd):
        try: del self.fdwmap[fd]
        except KeyError: pass
        try: del self.fdrmap[fd]
        except KeyError: pass
        try: self.poll.unregister(fd)
        except (IOError, KeyError): pass

    def set_timeout(self, timeout, exp = TimeOutException):
        gr = greenlet.getcurrent()
        ton = TimeoutObject(time.time() + timeout, gr, exp)
        ton.stack = traceback.format_stack()
        heapq.heappush(self.timeline, ton)
        return ton

    def unset_timeout(self, ton):
        try:
            self.timeline.remove(ton)
            heapq.heapify(self.timeline)
        except ValueError: pass

    def next_job(self, gr, *args):
        self.queue.append((gr, args))
        return len(self.queue) > 50

    def _switch_queue(self):
        gr = greenlet.getcurrent()
        while self.queue:
            q = self.queue[-1]
            if q[0].dead: self.queue.pop()
            elif q[0] == gr: return self.queue.pop()
            else: q[0].switch(*q[1])

    def _fire_timeout(self):
        t = time.time()
        while self.timeline and t > self.timeline[0].timeout:
            next = heapq.heappop(self.timeline)
            if next.gr:
                # print 'fire_timeout', id(next.gr)
                # print ''.join(next.stack)
                next.gr.throw(next.exp)
        if not self.timeline: return -1
        return (self.timeline[0].timeout - t) * timout_factor

    def _load_poll(self):
        for fd, ev in self.poll.poll(self._fire_timeout()):
            # print 'event come', fd, ev
            if ev & epoll.POLLHUP:
                gr = self.fdwmap.get(fd, None)
                if gr: gr.throw(EOFError)
                gr = self.fdrmap.get(fd, None)
                if gr: gr.throw(EOFError)
                self.unreg(fd)
            elif ev & epoll.POLLIN and fd in self.fdrmap:
                if self.next_job(self.fdrmap[fd]): break
            elif ev & epoll.POLLOUT and fd in self.fdwmap:
                if self.next_job(self.fdwmap[fd]): break
            else: self._setpoll(fd)
        # print len(self.queue), len(self.fdrmap), len(self.fdwmap)

    def schedule(self):
        while not self._switch_queue(): self._load_poll()

bus = EpollBus()

class TokenPool(object):

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
