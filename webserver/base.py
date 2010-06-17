#!/usr/bin/python
# -*- coding: utf-8 -*-
# @date: 2010-06-04
# @author: shell.xu
import socket

class HttpException (Exception): pass
class BadRequestError (HttpException):
    def __init__ (self, *params): HttpException.__init__ (self, 400, *params)
class NotFoundError (HttpException):
    def __init__ (self, *params): HttpException.__init__ (self, 404, *params)
class MethodNotAllowedError (HttpException):
    def __init__ (self, *params): HttpException.__init__ (self, 405, *params)
class NotAcceptableError (HttpException):
    def __init__ (self, *params): HttpException.__init__ (self, 406, *params)
class TimeoutError (HttpException):
    def __init__ (self, *params): HttpException.__init__ (self, 408, *params)
class BadGatewayError (HttpException):
    def __init__ (self, *params): HttpException.__init__ (self, 502, *params)

class SockBase (object):
    buffer_size = 2096

    def __init__ (self): self.recv_rest = ""
    def fileno (self): return self.sock.fileno ()
    def close (self): self.sock.close ()
    def sendall (self, data): return self.sock.sendall (data)

    def recv (self, size):
        data = self.sock.recv (size)
        if len (data) == 0: raise EOFError (self)
        return data

    def recv_once (self, size = 0):
        if size == 0: size = self.buffer_size
        if not self.recv_rest: return self.recv (size)
        self.recv_rest, data = "", self.recv_rest
        return data

    def recv_until (self, break_str = "\r\n\r\n"):
        while self.recv_rest.find (break_str) == -1:
            self.recv_rest += self.recv (self.buffer_size)
        data, part, self.recv_rest = self.recv_rest.partition (break_str)
        return data

    def recv_length (self, length):
        while len (self.recv_rest) < length:
            self.recv_rest += self.recv (self.buffer_size)
        data, self.recv_rest = self.recv_rest[:length], self.recv_rest[length:]
        return data

class TcpServer (SockBase):

    def __init__ (self):
        super (TcpServer, self).__init__ ()
        self.loop_func = self.do_loop

    def listen (self, addr = '', port = 8000, **kargs):
        self.laddr = (addr, port)
        self.sock = socket.socket (socket.AF_INET, socket.SOCK_STREAM)
        if kargs.get ('reuse', True):
            self.sock.setsockopt (socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.bind (self.laddr)
        self.sock.listen (kargs.get ('listen', 5))

    def run (self):
        try:
            while self.loop_func (): pass
        finally: self.close ()
    
class TcpClient (SockBase):

    def connect (self, hostname, **kargs):
        self.sock = socket.socket (socket.AF_INET, socket.SOCK_STREAM)
        hostinfo = hostname.partition (':')
        if len (hostinfo[1]) == 0: port = 80
        else: port = int (hostinfo[2])
        self.caddr = (hostinfo[0], port)
        self.sock.connect (self.caddr)

class DummyConnPool (object):

    def __init__ (self, **kargs):
        self.factory = kargs.get ('factory', TcpClient)
        self.kargs = kargs.get ('kargs', {})

    def acquire (self, hostname):
        conn = self.factory ()
        conn.connect (hostname, **self.kargs)
        return conn

    def release (self, sock, force): sock.close ()
