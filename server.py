#!/usr/bin/python
# -*- coding: utf-8 -*-
# @date: 20090921
# @author: shell.xu
from __future__ import with_statement
from http import *

class TcpPreworkServer (TcpServerBase):
    """ """

    def do_loop (self):
        """ 主进程，监听并创立连接 """
        conn, addr = self.sock.accept ();
	while True:
	    try: pid = os.fork (); break;
	    except: time.sleep (1);
        if pid != 0: conn.close ();
        else:
            self.sock.close ();
            self.sock = conn;
            self.from_addr = addr;
            self.run (self.do_sub_loop);
            sys.exit (0);
        return True;

    def do_sub_loop (self):
        """ 子进程函数，处理连接数据 """
        data = self.sock.recv (TcpServerBase.buffer_size);
        if len (data) == 0: return False;
        return self.do_process (data);

class TcpThreadServer (TcpServerBase, threading.Thread):
    """ """

    def __init__ (self, *params, **kargs):
        """ """
        super (TcpThreadServer, self).__init__ (*params, **kargs);
        threading.Thread.__init__ (self);
        self.main = True;
        with open ("/proc/cpuinfo", "r") as cpu_file:
            cpu_num = len (filter (lambda x: x.startswith ("processor"),
                                   cpu_file.readlines ()));
        for i in xrange (0, cpu_num - 1):
            if os.fork () == 0: break;

    def do_loop (self):
        """ 主进程，监听并创立连接 """
        if not self.main:
            data = self.sock.recv (TcpServerBase.buffer_size);
            if len (data) == 0: return False
            return self.do_process (data);
        else:
            new_server = copy.copy (self);
            new_server.main = False;
            new_server.sock, new_server.from_addr = self.sock.accept ();
            new_server.start ();
            return True;

class TcpEpollServer (TcpServerBase):
    """ """

    def __init__ (self, *params, **kargs):
        """ """
        super (TcpEpollServer, self).__init__ (self, *params, **kargs);
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

    def recv (self, size):
        """ """
        raise Exception ();

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
