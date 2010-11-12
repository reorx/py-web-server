#!/usr/bin/python
# -*- coding: utf-8 -*-
'''
@date: 2010-06-04
@author: shell.xu
'''
from __future__ import with_statement
import os
import socket
import logging
import traceback
import eventlet
from eventlet import tpool
import eventlet.pools
import basesock

class EventletServer(basesock.TcpServer):

    def listen(self, addr = '', port = 8080, poolsize = 10000, **kargs):
        ''' 监听指定端口
        @param addr: 监听地址，默认是所有地址
        @param port: 监听端口
        @param poolsize: eventlet的调度池最大容量 '''
        self.sockaddr = (addr, port)
        self.setsock(eventlet.listen(self.sockaddr))
        self.poolsize = poolsize

    def listen_unix(self, sockpath = '', poolsize = 10000, **kargs):
        ''' 监听unix socket
        @param sockpath: unix socket路径
        @param poolsize: eventlet的调度池最大容量 '''
        self.sockaddr = sockpath
        try: os.remove(sockpath)
        except OSError: pass
        self.setsock(eventlet.listen(self.sockaddr, socket.AF_UNIX))
        self.poolsize = poolsize

    def run(self):
        eventlet.serve(self.sock, self.do_loop, self.poolsize)

    def do_loop(self, sock, addr):
        try:
            s = basesock.SockBase()
            s.setsock(sock)
            s.from_addr = addr
            self.handler(s)
        except: logging.error(traceback.format_exc())

class EventletClient(basesock.TcpClient):

    def connect(self, hostaddr, port):
        self.setsock(eventlet.connect((hostaddr, port)))

class EventletClientPool(eventlet.pools.Pool):

    def __init__(self, host, port, max_size):
        super(EventletClientPool, self).__init__(max_size = max_size)
        self.sockaddr = (host, port)

    def create(self):
        sock = EventletClient()
        sock.connect(self.sockaddr[0], self.sockaddr[1])
        return sock

# TODO: EventletFile
class EventletFile(object):

    def read(self, size): pass
    def write(self, d): pass
    def close(self): pass

def evlet_open(filepath, flags):
    pass
