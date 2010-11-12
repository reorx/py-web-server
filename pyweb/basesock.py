#!/usr/bin/python
# -*- coding: utf-8 -*-
'''
@date: 2010-06-04
@author: shell.xu
'''
import os
import socket

class SockBase(object):
    buffer_size = 2096

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
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sockaddr = (hostaddr, port)
        self.sock.connect(self.sockaddr)

    def close(self): if self.sock: self.sock.close()

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
