#!/usr/bin/python
# -*- coding: utf-8 -*-
# @date: 20090921
# @author: shell.xu
from __future__ import with_statement
import os
import sys
import copy
import socket
import select
import datetime
import traceback
import threading
from http import *

class TcpServerBase (object):
    """ """
    buffer_size = 4096;

    def __init__ (self, address = '', port = 8000, *params, **kargs):
        """ """
        self.sock = socket.socket (socket.AF_INET, socket.SOCK_STREAM);
        self.sock.bind ((address, port));
        self.sock.listen (5);

    def run (self, loop_func = None):
        """ """
        if loop_func == None: loop_func = self.do_loop;
        try:
            while loop_func (): pass
        finally: self.final ();

    def final (self):
        """ """
        self.sock.close ();

    def do_process (self, request_data):
        """ """
        sys.stdout.write (request_data);
        return True;

    def send (self, data):
        """ """
        return self.sock.send (data);

    def recv (self, size):
        """ """
        return self.sock.recv (data);

class TcpPreworkServer (TcpServerBase):
    """ """

    def do_loop (self):
        """ 主进程，监听并创立连接 """
        conn, addr = self.sock.accept ();
        if os.fork () == 0:
            self.sock.close ();
            self.sock = conn;
            self.from_addr = addr;
            self.run (self.do_sub_loop);
            sys.exit (0);
        else: conn.close ();
        return True;

    def do_sub_loop (self):
        """ 子进程函数，处理连接数据 """
        data = self.sock.recv (TcpServerBase.buffer_size);
        if len (data) == 0: return False;
        return self.do_process (data);

class TcpThreadServer (TcpServerBase, threading.Thread):
    """ """

    def __init__ (self, address = '', port = 8000, *params, **kargs):
        """ """
        super (TcpThreadServer, self).__init__ (address, port, *params, **kargs);
        threading.Thread.__init__ (self);
        self.worker = False;

    def do_loop (self):
        """ 主进程，监听并创立连接 """
        if self.worker == True:
            data = self.sock.recv (TcpServerBase.buffer_size);
            if len (data) == 0: return False
            return self.do_process (data);
        else:
            conn, addr = self.sock.accept ();
            new_server = copy.copy (self);
            new_server.sock = conn;
            new_server.from_addr = addr;
            new_server.worker = True;
            new_server.start ();
            return True;

class TcpEpollServer (TcpServerBase):
    """ """

    def __init__ (self, address = '', port = 8000, *params, **kargs):
        """ """
        super (TcpEpollServer, self).__init__ (self, address = '', port = 8000, *params, **kargs);
        self.sock.setblocking (0);
        self.epoll = select.epoll();
        self.epoll.register (self.sock.fileno (), select.EPOLLIN);

    def final (self):
        """ """
        self.epoll.unregister (self.sock.fileno ());
        self.epoll.close ();
        super (TcpEpollServer, self).final ();

    def do_loop (self):
        """ """
        pass

class HttpServer (TcpThreadServer):
    """ """

    def __init__ (self, dispatcher, *params, **kargs):
        """ """
        super (HttpServer, self).__init__ (*params, **kargs);
        self.dispatcher = dispatcher;
        self.request_data = "";
        self.request_content = None;

    def do_process (self, request_data):
        """ 接收数据到完成头部，内容读入在HttpRequest中做 """
        self.request_data += request_data;
        idx = self.request_data.find ("\r\n\r\n");
        if idx == -1: idx = self.request_data.find ("\r\r");
        if idx == -1: idx = self.request_data.find ("\n\n");
        if idx == -1: return True;
        try:
            request = HttpRequest (self, self.request_data[:idx].splitlines ());
            request.request_content = self.request_data[idx:];
            self.request_data = "";
            try: response = self.dispatcher.action (request);
            except Exception, e: response = self.exception_response (request, e);
        except Exception, e: response = self.exception_response (request, e);
        response.response_message ();
        Logging._instance.request (request, response);
        return not response or response.connection;

    def exception_response (self, request, e):
        """ """
        if isinstance (e, HttpException):
            response = request.make_response (e.response_code);
        else: response = request.make_response (500);
        response.set_content ("".join (traceback.format_exc ()));
        response.connection = False;
        return response;
