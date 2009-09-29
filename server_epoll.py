#!/usr/bin/python
# -*- coding: utf-8 -*-
# @date: 20090927
# @author: shell.xu
from __future__ import with_statement
import epoll
from py.magic import greenlet
from http import *

class TcpEpollServer (TcpServerBase):
    """ """

    def __init__ (self, *params, **kargs):
        """ """
        super (TcpEpollServer, self).__init__ (*params, **kargs);
        # self.send_buffer = "";
        self.fileno_mapping = {};
        if "multi_proc" in kargs and kargs["multi_proc"]:
            for i in xrange (0, self.get_cpu_num() - 1):
                if os.fork () == 0: break;
        self.epoll = epoll.poll();
        self.set_socket ();
        self.gr = greenlet.getcurrent ();

    def set_socket (self):
        """ """
        self.fileno_mapping[self.sock.fileno ()] = self;
        self.epoll.register (self.sock.fileno (), epoll.POLLIN);
        self.sock.setblocking (0);

    def final (self):
        """ """
        try:
            fileno = self.sock.fileno ();
            self.epoll.unregister (fileno);
            del self.fileno_mapping[fileno];
            super (TcpEpollServer, self).final ();
        except: pass

    def run (self):
        """ """
        while True:
            events = self.epoll.poll (30); 
            for fileno, event in events:
                server = self.fileno_mapping[fileno];
                try: self.do_loop (server, event);
                except socket.error, e:
                    if server != self: server.final ();

    def do_loop (self, server, event):
        """ """
        if server == self:
            new_server = copy.copy (self);
            new_server.sock, new_server.from_addr = self.sock.accept ();
            new_server.set_socket ();
            new_server.gr = greenlet (new_server.do_work_loop);
        elif event & epoll.POLLIN: server.gr.switch ();
        elif event & epoll.POLLHUP: server.final ();

    def do_work_loop (self):
        """ """
        data = self.sock.recv (TcpServerBase.buffer_size);
        if not self.do_process (data): self.final ();

    def recv (self, size):
        """ """
        self.gr.parent.switch ();
        return super (TcpEpollServer, self).recv ();
