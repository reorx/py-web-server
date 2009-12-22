#!/usr/bin/python
# -*- coding: utf-8 -*-
# @date: 20090927
# @author: shell.xu
import os
import copy
import socket
import epoll
import greenlet
import base
import http

class TcpEpollServer (http.TcpServerBase):
    """ """

    def __init__ (self, **kargs):
        """ """
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
        """ """
        self.fileno_mapping[self.sock.fileno ()] = self
        self.epoll.register (self.sock.fileno (), epoll.POLLIN)
        self.sock.setblocking (0)

    def final (self):
        """ """
        try:
            self.epoll.unregister (self.sock.fileno ())
            del self.fileno_mapping[self.sock.fileno ()]
            super (TcpEpollServer, self).final ()
        except: pass

    def run (self):
        """ """
        while True:
            # will timeout in 30 seconds
            events = self.epoll.poll (30)
            for fileno, event in events:
                server = self.fileno_mapping[fileno]
                try:
                    self.do_main (server, event)
                except socket.error, e:
                    if server != self:
                        server.final ()

    def do_main (self, server, event):
        """ """
        if server == self:
            new_server = copy.copy (self)
            new_server.sock, new_server.from_addr = self.sock.accept ()
            new_server.set_socket ()
            new_server.gr = greenlet.greenlet (new_server.do_work_loop)
        elif event & epoll.POLLIN: server.gr.switch ()
        elif event & epoll.POLLHUP: server.final ()

    def do_work_loop (self):
        """ """
        data = self.sock.recv (http.TcpServerBase.buffer_size)
        if not self.do_process (data):
            self.final ()

    def recv (self, size):
        """ """
        self.coroutine.parent.switch ()
        return super (TcpEpollServer, self).recv (size)
