#!/usr/bin/python
# -*- coding: utf-8 -*-
# @date: 20090927
# @author: shell.xu
from __future__ import with_statement
import epoll
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

    def set_socket (self):
        """ """
        self.fileno_mapping[self.sock.fileno ()] = self;
        self.epoll.register (self.sock.fileno (), epoll.POLLIN);
        self.sock.setblocking (0);

    def final (self):
        """ """
        fileno = self.sock.fileno ();
        self.epoll.unregister (fileno);
        del self.fileno_mapping[fileno];
        super (TcpEpollServer, self).final ();

    def do_loop (self):
        """ """
        events = self.epoll.poll (1);
        for fileno, event in events:
            try:
                server = self.fileno_mapping[fileno];
                if server == self:
                    new_server = copy.copy (self);
                    new_server.sock, new_server.from_addr = self.sock.accept ();
                    new_server.set_socket ();
                elif event & epoll.POLLIN:
                    data = server.sock.recv (TcpServerBase.buffer_size);
                    if not server.do_process (data): server.final ();
                elif event & epoll.POLLHUP: server.final ();
            except socket.error, e: server.final ();
        return True;

    def recv (self, size):
        """ """
        raise Exception ();
