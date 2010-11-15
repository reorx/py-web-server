#!/usr/bin/python
# -*- coding: utf-8 -*-
'''
@date: 2010-06-04
@author: shell.xu
'''
import os
import errno
import epoll
import socket
import logging
import traceback
from greenlet import greenlet
import ebus

class SockBase(object):
    buffer_size = 65536

    def __init__(self): self.recv_rest, self.sock = "", None
    def setsock(self, sock): self.sock = sock

    def listen(self, addr = '', port = 8080, reuse = False, **kargs):
        self.sockaddr = (addr, port)
        self.setsock(socket.socket(socket.AF_INET, socket.SOCK_STREAM))
        if reuse: self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.bind(self.sockaddr)
        self.sock.listen(kargs.get('listen', 5))

    def listen_unix(self, sockpath = '', reuse = False, **kargs):
        self.sockaddr = sockpath
        self.setsock(socket.socket(socket.AF_UNIX, socket.SOCK_STREAM))
        if reuse: self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try: os.remove(sockpath)
        except OSError: pass
        self.sock.bind(self.sockaddr)
        self.sock.listen(kargs.get('listen', 5))

    def connect(self, hostaddr, port):
        self.setsock(socket.socket(socket.AF_INET, socket.SOCK_STREAM))
        self.sockaddr = (hostaddr, port)
        self.sock.connect(self.sockaddr)

    def close(self):
        if self.sock: self.sock.close()

    def sendall(self, data):
        return self.sock.sendall(data)

    def recv(self, size):
        data = self.sock.recv(size)
        if len(data) == 0: raise EOFError(self)
        return data

    def datas(self):
        if self.recv_rest:
            d, self.recv_rest = self.recv_rest, ''
            yield d
        while True:
            d = self.sock.recv(self.buffer_size)
            if len(d) == 0: raise StopIteration
            yield d

    def recv_until(self, break_str = "\r\n\r\n"):
        while self.recv_rest.rfind(break_str) == -1:
            self.recv_rest += self.recv(self.buffer_size)
        data, part, self.recv_rest = self.recv_rest.partition(break_str)
        return data

    def recv_length(self, length):
        while len(self.recv_rest) < length:
            self.recv_rest += self.recv(length - len(self.recv_rest))
        if len(self.recv_rest) != length:
            data, self.recv_rest = self.recv_rest[:length], self.recv_rest[length:]
        else: data, self.recv_rest = self.recv_rest, ''
        return data

class EpollSocket(SockBase):
    connect_timeout = 60

    def setsock(self, sock):
        self.sock = sock
        self.sock.setblocking(0)

    conn_errset = set((errno.EINPROGRESS, errno.EALREADY, errno.EWOULDBLOCK))
    def connect(self, hostaddr, port):
        self.sockaddr = (hostaddr, port)
        self.setsock(socket.socket(socket.AF_INET, socket.SOCK_STREAM))
        ebus.bus.register(self.sock.fileno(), epoll.POLLOUT)
        ebus.bus.set_timeout(60)
        try:
            while True:
                err = self.sock.connect_ex(self.sockaddr)
                if not err: return
                elif err in self.conn_errset: ebus.bus.switch()
                else: raise socket.error(err, errno.errorcode[err])
        finally: ebus.bus.unset_timeout()

    def close(self):
        if self.sock: ebus.bus.unregister(self.sock.fileno())
        super(EpollSocket, self).close()

    def send(self, data, flags = 0):
        ebus.bus.register(self.sock.fileno(), epoll.POLLOUT)
        while True:
            try: return self.sock.send(data, flags)
            except socket.error, err:
                if err.args[0] == errno.EAGAIN: ebus.bus.switch()
                else: raise

    def sendall(self, data, flags = 0):
        tail = self.send(data, flags)
        len_data = len(data)
        while tail < len_data: tail += self.send(data[tail:], flags)

    def recv(self, size):
        ebus.bus.register(self.sock.fileno(), epoll.POLLIN)
        while True:
            try:
                data = self.sock.recv(size)
                if len(data) == 0: raise EOFError(self)
                return data
            except socket.error, err:
                if err.args[0] == errno.EAGAIN: ebus.bus.switch()
                else: raise

    def datas(self):
        if self.recv_rest:
            data, self.recv_rest = self.recv_rest, ''
            yield data
        ebus.bus.register(self.sock.fileno(), epoll.POLLIN)
        while True:
            try:
                data = self.sock.recv(self.buffer_size)
                if len(data) == 0: raise StopIteration
                yield data
            except socket.error, err:
                if err.args[0] == errno.EAGAIN: ebus.bus.switch()
                else: raise

    def accept(self):
        ebus.bus.register(self.sock.fileno(), epoll.POLLIN)
        while True:
            try: return self.sock.accept()
            except socket.error, err:
                if err.args[0] == errno.EAGAIN: ebus.bus.switch()
                else: raise

    def run(self):
        self.gr = greenlet.getcurrent()
        while True:
            s, addr = self.accept()
            greenlet(self.on_accept).switch(s, addr)

    def on_accept(self, s, addr):
        try:
            try:
                sock = EpollSocket()
                sock.setsock(s)
                sock.from_addr, sock.server = addr, self
                sock.gr = greenlet.getcurrent()
                self.handler(sock)
            finally:
                sock.close()
                ebus.bus.unset_timeout()
        except: logging.error(traceback.format_exc())

class EpollSocketPool(ebus.ObjPool):

    def __init__(self, host, port, max_size):
        super(EpollSocketPool, self).__init__(0, max_size)
        self.sockaddr = (host, port)

    def create(self):
        sock = EpollSocket()
        sock.connect(self.sockaddr[0], self.sockaddr[1])
        return sock
