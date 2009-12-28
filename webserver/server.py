#!/usr/bin/python
# -*- coding: utf-8 -*-
# @date: 20090921
# @author: shell.xu
'''Prefork和Thread服务器，以及Http服务器'''
import os
import sys
import time
import copy
import threading
import traceback
import base
import log
import http

class TcpPreforkServer (base.TcpServerBase):
    """ 每进程模式服务器 """

    def __init__ (self):
        """ 根据参数，生成每进程模式服务器 """
        super (TcpPreforkServer, self).__init__ ()
        self.from_addr = None

    def do_loop (self):
        """ 主进程，监听并创立连接 """
        conn, addr = self.sock.accept ()
        while True:
            try:
                pid = os.fork ()
                break
            except:
                time.sleep (1)
        if pid != 0:
            conn.close ()
        else:
            self.sock.close ()
            self.sock = conn
            self.from_addr = addr
            self.loop_func = self.do_work_loop
            self.run ()
            sys.exit (0)
        return True

    def do_work_loop (self):
        """ 子进程函数，处理连接数据 """
        data = self.sock.recv (base.TcpServerBase.buffer_size)
        if len (data) == 0:
            return False
        return self.do_process (data)

class TcpThreadServer (base.TcpServerBase, threading.Thread):
    """ 每线程模式服务器 """

    def __init__ (self, **kargs):
        """ 根据参数，生成每线程模式服务器 """
        super (TcpThreadServer, self).__init__ ()
        threading.Thread.__init__ (self)
        if "multi_proc" in kargs and kargs["multi_proc"]:
            for i in xrange (0, self.get_cpu_num() - 1):
                if os.fork () == 0:
                    break

    def do_loop (self):
        """ 主进程，监听并创立连接 """
        new_server = copy.copy (self)
        new_server.loop_func = new_server.do_work_loop
        new_server.sock, new_server.from_addr = self.sock.accept ()
        new_server.setDaemon (True)
        new_server.start ()
        return True

    def do_work_loop (self):
        """ 子进程函数，处理连接数据 """
        data = self.sock.recv (base.TcpServerBase.buffer_size)
        if len (data) == 0:
            return False
        return self.do_process (data)

class HttpServer (TcpThreadServer):
    """ Http服务器，继承某种Tcp服务器 """

    def __init__ (self, action, **kargs):
        """ 生成Http服务器实例 """
        super (HttpServer, self).__init__ (**kargs)
        self.action = action
        self.request_data = ""
        self.request_content = None

    def do_process (self, request_data):
        """ 接收数据到完成头部，内容读入在HttpRequest中做 """
        self.request_data += request_data
        idx = self.request_data.find ("\r\n\r\n")
        if idx == -1:
            idx = self.request_data.find ("\r\r")
        if idx == -1:
            idx = self.request_data.find ("\n\n")
        if idx == -1:
            return True
        request = None
        try:
            req_lines = self.request_data[:idx].splitlines ()
            request = http.HttpRequest (self, req_lines)
            request.request_content = self.request_data[idx:]
            self.request_data = ""
            response = self.action.action (request)
        except Exception, err:
            response = self.exception_response (request, err)
        if response != None:
            response.send_response ()
        log.Logging.request (request, response)
        return not response or response.connection

    @staticmethod
    def exception_response (request, err):
        """ 将某个异常变成网页返回 """
        if isinstance (err, http.HttpException):
            response = http.HttpResponse (err.response_code)
        else: response = http.HttpResponse (500, request)
        response.set_content ("".join (traceback.format_exc ()))
        response.connection = False
        return response
