#!/usr/bin/python
# -*- coding: utf-8 -*-
'''
@date: 2010-06-04
@author: shell.xu
'''
import os
import socket

class HttpException(Exception): pass
class BadRequestError(HttpException):
    def __init__(self, *params): HttpException.__init__(self, 400, *params)
class NotFoundError(HttpException):
    def __init__(self, *params): HttpException.__init__(self, 404, *params)
class MethodNotAllowedError(HttpException):
    def __init__(self, *params): HttpException.__init__(self, 405, *params)
class NotAcceptableError(HttpException):
    def __init__(self, *params): HttpException.__init__(self, 406, *params)
class TimeoutError(HttpException):
    def __init__(self, *params): HttpException.__init__(self, 408, *params)
class BadGatewayError(HttpException):
    def __init__(self, *params): HttpException.__init__(self, 502, *params)

class SockBase(object):
    buffer_size = 2096

    def __init__(self): self.recv_rest = ""
    def setsock(self, sock): self.sock = sock
    def fileno(self): return self.sock.fileno()
    def close(self): self.sock.close()
    def sendall(self, data): return self.sock.sendall(data)

    def recv(self, size):
        data = self.sock.recv(size)
        if len(data) == 0: raise EOFError(self)
        return data

    def recv_into(self, buf, size):
        s = self.sock.recv_into(buf, size)
        if s == 0: raise EOFError(self)
        return s

    def recv_once(self, size = 0):
        if size == 0: size = self.buffer_size
        if not self.recv_rest: return self.recv(size)
        self.recv_rest, data = "", self.recv_rest
        return data

    def recv_until(self, break_str = "\r\n\r\n"):
        while self.recv_rest.find(break_str) == -1:
            self.recv_rest += self.recv(self.buffer_size)
        data, part, self.recv_rest = self.recv_rest.partition(break_str)
        return data

    def recv_length(self, length):
        while len(self.recv_rest) < length:
            self.recv_rest += self.recv(length - len(self.recv_rest))
        data, self.recv_rest = self.recv_rest, ''
        return data

    def run(self):
        try:
            while self.do_loop(): pass
        finally: self.close()

class TcpServer(SockBase):

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

    def do_loop(self):
        # This can't work at all.
        sock = SockBase()
        s, sock.from_addr = self.sock.accept()
        sock.setsock(s)
        sock.run()
        return sock
    
class TcpClient(SockBase):

    def connect(self, hostaddr, port):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sockaddr = (hostaddr, port)
        self.sock.connect(self.sockaddr)
