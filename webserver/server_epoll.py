#!/usr/bin/python
# -*- coding: utf-8 -*-
# @date: 20090927
# @author: shell.xu
'''Epoll服务器定义'''
import os
import copy
import socket
import epoll
import greenlet
import base
import http

class TcpEpollServer (base.TcpServerBase):
    """ Epoll模式服务器，使用Epoll模块作为处理系统 """

    def __init__ (self, **kargs):
        """ 构造Epoll模式服务器 """
        super (TcpEpollServer, self).__init__ ()
        # self.send_buffer = ""; sendall方式也不好
        self.fileno_mapping = {}
        if "multi_proc" in kargs and kargs["multi_proc"]:
            for i in xrange (0, self.get_cpu_num() - 1):
                if os.fork () == 0:
                    break
        self.epoll = epoll.poll()
        self.set_socket ()
        self.coroutine = greenlet.getcurrent ()

    def set_socket (self):
        """ 设定某个socket的相关初始化设定 """
        self.fileno_mapping[self.sock.fileno ()] = self
        self.epoll.register (self.sock.fileno (), epoll.POLLIN)
        self.sock.setblocking (0)

    def final (self):
        """ 关闭某个连接对象 """
        try:
            self.epoll.unregister (self.sock.fileno ())
            del self.fileno_mapping[self.sock.fileno ()]
            super (TcpEpollServer, self).final ()
        except:
            pass

    def run (self):
        """ 主循环 """
        while True:
            # will timeout in 30 seconds
            events = self.epoll.poll (30)
            for fileno, event in events:
                server = self.fileno_mapping[fileno]
                try:
                    self.do_main (server, event)
                except socket.error, err:
                    if server != self:
                        server.final ()

    def do_main (self, server, event):
        """ 主循环的每事件处理函数 """
        if server == self:
            new_server = copy.copy (self)
            new_server.sock, new_server.from_addr = self.sock.accept ()
            new_server.set_socket ()
            new_server.coroutine = greenlet.greenlet (new_server.do_work_loop)
        elif event & epoll.POLLIN:
            server.coroutine.switch ()
        elif event & epoll.POLLHUP:
            server.final ()

    def do_work_loop (self):
        """ 连接数据处理的主函数 """
        data = self.sock.recv (base.TcpServerBase.buffer_size)
        if not self.do_process (data):
            self.final ()

    def recv (self, size):
        """ 数据接收函数，在接收前切换到主线程并等待准备完成 """
        self.coroutine.parent.switch ()
        return super (TcpEpollServer, self).recv (size)
