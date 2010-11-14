#!/usr/bin/python
# -*- coding: utf-8 -*-
'''
@date: 2010-11-12
@author: shell.xu
'''
from __future__ import with_statement
import os
import time
import errno
import heapq
import socket
import logging
import traceback
import basesock
from greenlet import greenlet

try: import epoll
except ImportError: import select as epoll

class TimeOutException(Exception): pass

class EpollSocket(basesock.SockBase):

    def setsock(self, sock):
        self.sock = sock
        self.sock.setblocking(0)

    def close(self):
        if self.sock: bus.unregister(self.sock.fileno())
        super(EpollSocket, self).close()

    def send(self, data, flags = 0):
        bus.register(self.sock.fileno(), epoll.POLLOUT)
        while True:
            try: return self.sock.send(data, flags)
            except socket.error, err:
                # print 'send not hit'
                if err.args[0] == errno.EAGAIN: bus.switch()
                else: raise

    def sendall(self, data, flags = 0):
        tail = self.send(data, flags)
        len_data = len(data)
        while tail < len_data: tail += self.send(data[tail:], flags)

    def recv(self, size):
        # print 'begin recv'
        bus.register(self.sock.fileno(), epoll.POLLIN)
        while True:
            try:
                # print 'once recv'
                data = self.sock.recv(size)
                if len(data) == 0: raise EOFError(self)
                return data
            except socket.error, err:
                # print 'recv not hit'
                if err.args[0] == errno.EAGAIN: bus.switch()
                else: raise

    def datas(self):
        if self.recv_rest:
            data, self.recv_rest = self.recv_rest, ''
            yield data
        bus.register(self.sock.fileno(), epoll.POLLIN)
        while True:
            try:
                data = self.sock.recv(self.buffer_size)
                if len(data) == 0: raise StopIteration
                yield data
            except socket.error, err:
                if err.args[0] == errno.EAGAIN: bus.switch()
                else: raise

    def accept(self):
        bus.register(self.sock.fileno(), epoll.POLLIN)
        while True:
            try: return self.sock.accept()
            except socket.error, err:
                # print 'accept not hit'
                if err.args[0] == errno.EAGAIN: bus.switch()
                else: raise

    def run(self):
        self.gr = greenlet.getcurrent()
        while True:
            s, addr = self.accept()
            # print 'accept new'
            greenlet(self.on_accept).switch(s, addr)

    def on_accept(self, s, addr):
        try:
            try:
                sock = EpollSocket()
                sock.setsock(s)
                sock.from_addr, sock.server = addr, self
                sock.gr = greenlet.getcurrent()
                self.handler(sock)
            finally: sock.close()
        except: logging.error(traceback.format_exc())
        
    def handler(self, sock):
        while True:
            d = sock.recv(1024)
            # bus.unset_timeout()
            sock.sendall(d)
            # bus.set_timeout(2)

class TakonPool(object):

    def __init__(self, min_item, max_item):
        self.min_item, self.max_item = min_item, max_item
        self.token, self.gr_wait = min_item, []

    def __enter__(self):
        gr = greenlet.getcurrent()
        while self.token == 0:
            if gr not in self.gr_wait: self.gr_wait.append(gr)
            bus.switch()
        self.token -= 1

    def __exit__(self, *args):
        self.token += 1
        if self.token == 1:
            bus.next_job(greenlet.getcurrent())
            self.gr_wait.pop(0).switch()

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
        # print 'event come'

    def _fire_timeout(self):
        while self.timeline and time.time() > self.timeline[0].t:
            # print 'fire timeout'
            del self.tlmap[self.timeline[0].gr]
            next = heapq.heappop(self.timeline)
            next.gr.throw(next.e)

    def _switch_queue(self):
        gr = greenlet.getcurrent()
        if not self.queue: return False
        while self.queue[0] != gr:
            print 'switch from %s to %s' % (gr, self.queue[0])
            self.queue[0].switch()
        del self.queue[0]
        return True

    def switch(self):
        while not self._switch_queue():
            self._wait_ev()
            self._fire_timeout()

bus = EpollBus()

if __name__ == '__main__':
    serve = EpollSocket()
    serve.listen(port = 1200, reuse = True)
    serve.run()
