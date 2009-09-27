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
            self.loop_func = self.work_loop;
            self.run ();
            sys.exit (0);
        return True;

    def do_work_loop (self):
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
        for i in xrange (0, self.get_cpu_num() - 1):
            if os.fork () == 0: break;

    def do_loop (self):
        """ 主进程，监听并创立连接 """
        new_server = copy.copy (self);
        new_server.loop_func = new_server.do_work_loop;
        new_server.sock, new_server.from_addr = self.sock.accept ();
        new_server.setDaemon (True); new_server.start ();
        return True;

    def do_work_loop (self):
        """ 子进程函数，处理连接数据 """
        data = self.sock.recv (TcpServerBase.buffer_size);
        if len (data) == 0: return False;
        return self.do_process (data);

import epoll
class TcpEpollServer (TcpServerBase):
    """ """

    def __init__ (self, *params, **kargs):
        """ """
        super (TcpEpollServer, self).__init__ (*params, **kargs);
        # self.send_buffer = "";
        self.fileno_mapping = {};
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
        if len (events) == 0: time.sleep (0.1); return True;
        for fileno, event in events:
            server = self.fileno_mapping[fileno];
            if server == self:
                new_server = copy.copy (self);
                new_server.sock, new_server.from_addr = self.sock.accept ();
                new_server.set_socket ();
            elif event & epoll.POLLIN:
                data = server.sock.recv (TcpServerBase.buffer_size);
                server.do_process (data);
                server.final ();
            elif event & epoll.POLLOUT: server.do_send ();
            elif event & epoll.POLLHUP: server.final ();
        return True;

    def recv (self, size):
        """ """
        raise Exception ();

    # def send (self, data):
    #     """ """
    #     self.send_buffer += data;
    #     self.epoll.modify (self.sock.fileno (), epoll.POLLOUT);

    # def do_send (self):
    #     """ """
    #     self.sock.send (self.send_buffer);
    #     self.send_buffer = "";

class HttpServer (TcpThreadServer):
    """ """

    def __init__ (self, dispatcher, *params, **kargs):
        """ """
        super (HttpServer, self).__init__ (*params, **kargs);
        self.dispatcher = dispatcher;
        self.request_data = StringIO.StringIO ();
        self.request_content = None;

    def do_process (self, request_data):
        """ 接收数据到完成头部，内容读入在HttpRequest中做 """
        self.request_data.write (request_data);
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
