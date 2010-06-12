#!/usr/bin/python
# -*- coding: utf-8 -*-
# @date: 2010-06-04
# @author: shell.xu
import socket

class HttpException (Exception): pass
class BadRequestError (HttpException):
    def __init__ (self, *params):
        super (BadRequestError, self).__init__ (400, *params)
class NotFoundError (HttpException):
    def __init__ (self, *params):
        super (NotFoundError, self).__init__ (404, *params)
class MethodNotAllowedError (HttpException):
    def __init__ (self, *params):
        super (MethodNotAllowedError, self).__init__ (405, *params)
class NotAcceptableError (HttpException):
    def __init__ (self, *params):
        super (NotAcceptableError, self).__init__ (406, *params)
class TimeoutError (HttpException):
    def __init__ (self, *params):
        super (TimeoutError, self).__init__ (408, *params)
class BadGatewayError (HttpException):
    def __init__ (self, *params):
        super (BadGatewayError, self).__init__ (502, *params)

class SockBase (object):
    buffer_size = 2096

    def __init__ (self): self.recv_rest = ""
    def fileno (self): return self.sock.fileno ()
    def final (self): self.sock.close ()
    def sendall (self, data): return self.sock.sendall (data)

    def recv (self, size):
        data = self.sock.recv (size)
        if len (data) == 0: raise EOFError ()
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

    def listen (self, address = '', port = 8000):
        self.sock = socket.socket (socket.AF_INET, socket.SOCK_STREAM)
        self.sock.setsockopt (socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.bind ((address, port))
        self.sock.listen (5)

    def run (self):
        try:
            while self.loop_func (): pass
        finally: self.final ()
    
class TcpClient (SockBase):

    def connect (self, hostname, **kargs):
        self.sock = socket.socket (socket.AF_INET, socket.SOCK_STREAM)
        hostinfo = hostname.partition (':')
        if len (hostinfo[1]) == 0: port = 80
        else: port = int (hostinfo[2])
        self.sock.connect ((hostinfo[0], port))

class DummyConnPool (object):

    def __init__ (self, **kargs):
        self.factory = kargs.get ('factory', TcpClient)
        self.kargs = kargs.get ('kargs', {})

    def acquire (self, hostname):
        conn = self.factory ()
        conn.connect (hostname, **self.kargs)
        return conn

    def release (self, sock, force): sock.final ()
