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

class EpollBus(object):

    class __TimeoutNode(object):
        def __init__(self, timeout, gr, exp):
            self.timeout, self.gr, self.exp = timeout, gr, exp
        def __cmp__(self, o): return self.timeout > o.timeout

    def __init__(self):
        self.fdrmap, self.fdwmap = {}, {}
        self.queue, self.timeline = [], []

    def init_poll(self):
        self.poll = epoll_factory()
        if not python_epoll: self._epoll_modify = self.poll.modify
        else: self._epoll_modify = self.poll.register

    def _sync_register(self, fd):
        ev = epoll.POLLHUP
        if fd in self.fdrmap: ev |= epoll.POLLIN
        if fd in self.fdwmap: ev |= epoll.POLLOUT
        self._epoll_modify(fd, ev)
        # if new_reg: self.poll.register(fd, ev)

    def register(self, fd, ev):
        # print 'register', fd, ev
        if ev not in (epoll.POLLIN, epoll.POLLOUT): return
        if ev == epoll.POLLIN: self.fdrmap[fd] = greenlet.getcurrent()
        elif ev == epoll.POLLOUT: self.fdwmap[fd] = greenlet.getcurrent()
        self._sync_register(fd)

    def unregister(self, fd, ev = None):
        # print 'unregister', fd, ev
        if fd == -1: return
        if ev is None or ev & epoll.POLLOUT:
            try: del self.fdwmap[fd]
            except KeyError: pass
        if ev is None or ev & epoll.POLLIN:
            try: del self.fdrmap[fd]
            except KeyError: pass
        if ev is None: self.poll.unregister(fd)
        else: self._sync_register(fd)

    def set_timeout(self, timeout, exp = TimeOutException):
        ton = self.__TimeoutNode(time.time() + timeout,
                                 greenlet.getcurrent(), exp)
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

    def switch_queue(self):
        gr = greenlet.getcurrent()
        while self.queue:
            q = self.queue[-1]
            if q[0].dead: self.queue.pop()
            elif q[0] == gr: return self.queue.pop()
            else: q[0].switch(*q[1])

    def load_poll(self):
        if not self.timeline: timeout = -1
        else:
            timeout = self.timeline[0].timeout - time.time()
            timeout *= timout_factor
        for fd, ev in self.poll.poll(timeout):
            # print 'event come', fd, ev
            if ev & epoll.POLLHUP:
                gr = self.fdwmap.get(fd, None)
                if gr: gr.throw(EOFError)
                gr = self.fdrmap.get(fd, None)
                if gr: gr.throw(EOFError)
                self.unregister(fd)
            elif ev & epoll.POLLIN and fd in self.fdrmap:
                if self.next_job(self.fdrmap[fd]): break
            elif ev & epoll.POLLOUT and fd in self.fdwmap:
                if self.next_job(self.fdwmap[fd]): break
            else: self._sync_register(fd)
        # print len(self.queue), len(self.fdrmap), len(self.fdwmap)
        # print ''.join(traceback.format_stack())
        while self.timeline and time.time() > self.timeline[0].timeout:
            next = heapq.heappop(self.timeline)
            if next: next.gr.throw(next.exp)
        return bool(self.queue)

    def switch(self):
        while not self.switch_queue(): self.load_poll()

bus = EpollBus()

class TokenPool(object):

    def __init__(self, max_item): self.token, self.gr_wait = max_item, []
    @contextmanager
    def item(self):
        gr = greenlet.getcurrent()
        while self.token == 0:
            if gr not in self.gr_wait: self.gr_wait.append(gr)
            bus.switch()
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
            bus.switch()
        if not self.pool: self.pool.append(self.create())
        self.count += 1
        obj = self.pool.pop()
        try: yield obj
        finally:
            self.free(obj)
            self.pool.append(obj)
            self.count -= 1
            if self.count == self.max_item - 1:
                bus.next_job(greenlet.getcurrent())
                self.gr_wait.pop().switch()
