#!/usr/bin/python
# -*- coding: utf-8 -*-
'''
@date: 2010-11-12
@author: shell.xu
'''
import time
import heapq
from greenlet import greenlet
from contextlib import contextmanager

try: import epoll
except ImportError: import select as epoll

class TimeOutException(Exception): pass

class EpollBus(object):

    class __node(object):
        def __init__(self, t, gr, e): self.t, self.gr, self.e = t, gr, e
        def __cmp__(self, o): return self.t > o.t

    def __init__(self):
        self.poll = epoll.poll()
        self.fdmap, self.queue = {}, []
        self.timeline, self.tlmap = [], {}

    def register(self, fd, ev):
        gr = greenlet.getcurrent()
        self.poll.register(fd, ev)
        if fd not in self.fdmap: self.fdmap[fd] = gr
        else: assert(self.fdmap[fd] == gr)

    def unregister(self, fd):
        self.unset_timeout()
        del self.fdmap[fd]
        self.poll.unregister(fd)

    def set_timeout(self, timeout, exp = TimeOutException):
        gr = greenlet.getcurrent()
        if gr in self.tlmap:
            n = self.tlmap[gr]
            n.timeout, n.exp = time.time() + timeout, exp
            heapq.heapify(self.timeline)
        else:
            n = self.__node(time.time() + timeout, gr, exp)
            heapq.heappush(self.timeline, n)
            self.tlmap[gr] = n

    def unset_timeout(self):
        gr = greenlet.getcurrent()
        try: n = self.tlmap.pop(gr)
        except KeyError: return
        self.timeline.remove(n)
        heapq.heapify(self.timeline)

    def next_job(self, gr): self.queue.append(gr)

    def _wait_ev(self):
        if not self.timeline: timeout = -1
        else: timeout = (self.timeline[0].t - time.time()) * 1000
        for fd, ev in self.poll.poll(timeout): self.next_job(self.fdmap[fd])

    def _fire_timeout(self):
        while self.timeline and time.time() > self.timeline[0].t:
            del self.tlmap[self.timeline[0].gr]
            next = heapq.heappop(self.timeline)
            next.gr.throw(next.e)

    def _switch_queue(self):
        gr = greenlet.getcurrent()
        if not self.queue: return False
        while self.queue[0] != gr:
            # print 'switch from %s to %s' % (gr, self.queue[0])
            self.queue[0].switch()
        del self.queue[0]
        return True

    def switch(self):
        while not self._switch_queue():
            self._wait_ev()
            self._fire_timeout()

bus = EpollBus()

class TokenPool(object):

    def __init__(self, min_item, max_item):
        self.min_item, self.max_item = min_item, max_item
        self.token, self.gr_wait = min_item, []

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
                self.gr_wait.pop(0).switch()

class ObjPool(object):

    def __init__(self, min_item, max_item):
        self.min_item, self.max_item = min_item, max_item
        self.pool, self.count, self.gr_wait = [], 0, []

    @contextmanager
    def item(self):
        gr = greenlet.getcurrent()
        while self.count >= self.max_item:
            if gr not in self.gr_wait: self.gr_wait.append(gr)
            bus.switch()
        if not len(self.pool): self.pool.append(self.create())
        self.count += 1
        obj = self.pool.pop()
        try: yield obj
        finally:
            self.pool.append(obj)
            self.count -= 1
            if self.count == self.max_item - 1:
                bus.next_job(greenlet.getcurrent())
                self.gr_wait.pop(0).switch()
            elif self.count > self.min_item and hasattr(self, 'free'):
                while self.pool: self.free(self.pool.pop())
