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

try: import epoll
except ImportError: import select as epoll

class TimeOutException(Exception): pass

class EpollBus(object):

    class __TimeoutNode(object):
        def __init__(self, timeout, gr, exp):
            self.timeout, self.gr, self.exp = timeout, gr, exp
        def __cmp__(self, o): return self.timeout > o.timeout

    def __init__(self):
        self.poll = epoll.poll()
        self.fdmap, self.queue, self.timeline = {}, [], []

    def register(self, fd, ev):
        self.poll.register(fd, ev)
        self.fdmap[fd] = greenlet.getcurrent()

    def unregister(self, fd):
        try: del self.fdmap[fd]
        except KeyError: pass
        try: self.poll.unregister(fd)
        except KeyError: pass

    def set_timeout(self, timeout, exp = TimeOutException):
        # ton = self.__TimeoutNode(time.time() + timeout,
        #                          greenlet.getcurrent(), exp)
        # heapq.heappush(self.timeline, ton)
        # return ton
        return time.time()

    def unset_timeout(self, ton):
        # try:
        #     self.timeline.remove(ton)
        #     heapq.heapify(self.timeline)
        # except ValueError: pass
        t = time.time() - ton
        if t > 1: print t

    def next_job(self, gr): self.queue.append(gr)

    def _switch_queue(self):
        gr = greenlet.getcurrent()
        while self.queue:
            if self.queue[0].dead: self.queue.pop(0)
            elif self.queue[0] == gr:
                del self.queue[0]
                return True
            else:
                # print 'switch from %s to %s' % (gr, self.queue[0])
                self.queue[0].switch()
        return False

    def switch(self):
        while not self._switch_queue():
            if not self.timeline: timeout = -1
            else: timeout = (self.timeline[0].timeout - time.time()) * 1000
            for fd, ev in self.poll.poll(timeout):
                if fd not in self.fdmap: self.poll.unregister(fd)
                self.next_job(self.fdmap[fd])
            # while self.timeline and time.time() > self.timeline[0].timeout:
            #     next = heapq.heappop(self.timeline)
            #     next.gr.throw(next.exp)

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
