#!/usr/bin/python
# -*- coding: utf-8 -*-
# @date: 20090921
# @author: shell.xu
from __future__ import with_statement
import os
import sys
import copy
import socket
import datetime
import traceback
import threading
from http import *

class TcpPreworkServer (object):
    """ """

    def __init__ (self, address = '', port = 8000, *params, **kargs):
        """ """
        self.sock = socket.socket (socket.AF_INET, socket.SOCK_STREAM);
        self.sock.bind ((address, port));
        self.sock.listen (5);

    def run (self):
        """ 主进程，监听并创立连接 """
        try:
            while True:
                conn, addr = self.sock.accept ();
                if os.fork () == 0:
                    self.sock.close ();
                    self.sock = conn;
                    self.from_addr = addr;
                    self.do_conn ();
                    sys.exit (0);
                else: conn.close ();
        finally: self.sock.close ();

    def do_conn (self):
        """ 子进程函数，处理连接数据 """
        try:
            while True:
                data = self.sock.recv (4096);
                if len (data) == 0: break;
                if not self.do_process (data): break;
        finally: self.sock.close ();

    def do_process (self, request_data):
        """ """
        sys.stdout.write (request_data);

class TcpThreadServer (threading.Thread):
    """ """

    def __init__ (self, address = '', port = 8000, *params, **kargs):
        """ """
        super (TcpThreadServer, self).__init__ ();
        self.sock = socket.socket (socket.AF_INET, socket.SOCK_STREAM);
        self.sock.bind ((address, port));
        self.sock.listen (5);
        self.worker = False;

    def run (self):
        """ 主进程，监听并创立连接 """
        try:
            if self.worker:
                while True:
                    data = self.sock.recv (4096);
                    if len (data) == 0: break;
                    if not self.do_process (data): break;
            else:
                while True:
                    conn, addr = self.sock.accept ();
                    new_server = copy.copy (self);
                    new_server.sock = conn;
                    new_server.from_addr = addr;
                    new_server.worker = True;
                    new_server.start ();
        finally: self.sock.close ();

    def do_process (self, request_data):
        """ """
        sys.stdout.write (request_data);

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
