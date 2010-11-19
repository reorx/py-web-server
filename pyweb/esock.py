#!/usr/bin/python
# -*- coding: utf-8 -*-
'''
@date: 2010-06-04
@author: shell.xu
'''
import os
import errno
import socket
import logging
import traceback
from greenlet import greenlet
import ebus

class SockBase(object):
    buffer_size = 65536

    def __init__(self, sock = None, socktype = socket.AF_INET, reuse = True):
        if sock: self.sock = sock
        else: self.sock = socket.socket(socktype, socket.SOCK_STREAM)
        if reuse:
            self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        if hasattr(self, 'setsock'): self.setsock()
        self.recv_rest = ""
    def fileno(self): return self.sock.fileno()

    def listen(self, addr = '', port = 8080, listen_queue = 50, **kargs):
        self.sockaddr = (addr, port)
        self.sock.bind(self.sockaddr)
        self.sock.listen(listen_queue)

    def listen_unix(self, sockpath = '', listen_queue = 50, **kargs):
        self.sockaddr = sockpath
        try: os.remove(sockpath)
        except OSError: pass
        self.sock.bind(self.sockaddr)
        self.sock.listen(listen_queue)

    def connect(self, hostaddr, port):
        self.sockaddr = (hostaddr, port)
        self.sock.connect(self.sockaddr)

    def close(self): self.sock.close()

    def sendall(self, data):
        return self.sock.sendall(data)

    def recv(self, size):
        data = self.sock.recv(size)
        if len(data) == 0: raise EOFError
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
    def setsock(self): self.sock.setblocking(0)

    conn_errset = set((errno.EINPROGRESS, errno.EALREADY, errno.EWOULDBLOCK))
    def connect(self, hostaddr, port, timeout = 60):
        self.sockaddr = (hostaddr, port)
        ton = ebus.bus.set_timeout(timeout)
        try:
            while True:
                err = self.sock.connect_ex(self.sockaddr)
                if not err: return
                elif err in self.conn_errset:
                    ebus.bus.wait_for_write(self.sock.fileno())
                else: raise socket.error(err, errno.errorcode[err])
        finally: ebus.bus.unset_timeout(ton)

    def close(self):
        ebus.bus.unreg(self.sock.fileno())
        super(EpollSocket, self).close()

    def send(self, data, flags = 0):
        while True:
            try: return self.sock.send(data, flags)
            except socket.error, err:
                if err.args[0] != errno.EAGAIN: raise
                ebus.bus.wait_for_write()

    def sendall(self, data, flags = 0):
        tail, len_data = self.send(data, flags), len(data)
        while tail < len_data: tail += self.send(data[tail:], flags)

    def recv(self, size):
        while True:
            try:
                data = self.sock.recv(size)
                if len(data) == 0: raise EOFError
                return data
            except socket.error, err:
                if err.args[0] != errno.EAGAIN: raise
                ebus.bus.wait_for_read(self.sock.fileno())

    def datas(self):
        if self.recv_rest:
            data, self.recv_rest = self.recv_rest, ''
            yield data
        while True:
            try:
                data = self.sock.recv(self.buffer_size)
                if len(data) == 0: raise StopIteration
                yield data
            except socket.error, err:
                if err.args[0] != errno.EAGAIN: raise
                ebus.bus.wait_for_read()

    def accept(self):
        while True:
            try: return self.sock.accept()
            except socket.error, err:
                if err.args[0] != errno.EAGAIN: raise
                ebus.bus.wait_for_read(self.sock.fileno())

    def run(self):
        ebus.bus.init_poll()
        self.gr = greenlet.getcurrent()
        try:
            while True:
                s, addr = self.accept()
                ebus.bus.next_job(greenlet(self.on_accept), s, addr)
                ebus.bus.wait_for_read(self.sock.fileno())
        finally: ebus.bus.unreg(self.sock.fileno())

    def on_accept(self, s, addr):
        try:
            sock = EpollSocket(s)
            try:
                sock.from_addr, sock.server = addr, self
                sock.gr = greenlet.getcurrent()
                self.handler(sock)
            finally: sock.close()
        except KeyboardInterrupt: raise
        except: logging.error(traceback.format_exc())

class EpollSocketPool(ebus.ObjPool):

    def __init__(self, host, port, max_size):
        super(EpollSocketPool, self).__init__(max_size)
        self.sockaddr = (host, port)

    def create(self):
        sock = EpollSocket()
        sock.connect(self.sockaddr[0], self.sockaddr[1])
        return sock
    def unbind(self, sock): ebus.bus.unreg(sock.fileno())
