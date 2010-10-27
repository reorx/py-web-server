#!/usr/bin/python
# -*- coding: utf-8 -*-
'''
@date: 2010-06-04
@author: shell.xu
'''
from __future__ import with_statement
import os
import socket
import eventlet
from eventlet import tpool
import basesock

class EventletServer(basesock.TcpServer):

    def listen(self, addr = '', port = 8080,
               poolsize = 10000, reuse = False, **kargs):
        ''' 监听指定端口
        @param addr: 监听地址，默认是所有地址
        @param port: 监听端口
        @param poolsize: eventlet的调度池最大容量
        @param reuse: 指定为True则使用reuse方式打开端口，避免CLOSE_WAIT的影响 '''
        self.sockaddr = (addr, port)
        self.setsock(eventlet.listen(self.sockaddr))
        if reuse: self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.pool = eventlet.GreenPool(poolsize)

    def listen_unix(self, sockpath = '', poolsize = 10000, reuse = False, **kargs):
        ''' 监听unix socket
        @param sockpath: unix socket路径
        @param poolsize: eventlet的调度池最大容量
        @param reuse: 指定为True则使用reuse方式打开端口，避免CLOSE_WAIT的影响 '''
        self.sockaddr = sockpath
        try: os.remove(sockpath)
        except OSError: pass
        self.setsock(eventlet.listen(self.sockaddr, socket.AF_UNIX))
        if reuse: self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.pool = eventlet.GreenPool(poolsize)

    def do_loop(self):
        sock = basesock.SockBase()
        s, sock.from_addr = self.sock.accept()
        sock.setsock(s)
        sock.server = self
        self.pool.spawn_n(self.handler, sock)
        return True

class EventletClient(basesock.TcpClient):

    def connect(self, hostaddr, port):
        self.setsock(tpool.execute(eventlet.connect, (hostaddr, port)))
        
# TODO: EventletFile
class EventletFile(object):

    def read(self, size): pass
    def write(self, d): pass
    def close(self): pass

def evlet_open(filepath, flags):
    pass
