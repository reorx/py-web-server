#!/usr/bin/python
# -*- coding: utf-8 -*-
# @date: 2009-09-24
# @author: shell.xu
from __future__ import with_statement
import sys
import socket
import logging
import datetime
from os import path

class TcpServerBase (object):
    """ Tcp Server的基类，实现常用抽象操作 """
    buffer_size = 4096

    def __init__ (self, address = '', port = 8000):
        """ 传入需要监听的地址和端口 """
        self.sock = socket.socket (socket.AF_INET, socket.SOCK_STREAM)
        self.sock.bind ((address, port))
        self.sock.listen (5)
        self.loop_func = self.do_loop

    @staticmethod
    def get_cpu_num ():
        """ 获得当前CPU的个数 """
        with open ("/proc/cpuinfo", "r") as cpu_file:
            return len (filter (lambda x: x.startswith ("processor"),
                                cpu_file.readlines ()))

    def run (self):
        """ 执行过程的抽象 """
        try:
            while self.loop_func ():
                pass
        finally: self.final ()

    def final (self):
        """ 对象关闭调用 """
        self.sock.close ()

    def do_loop (self):
        pass

    def do_process (self, request_data):
        """ """
        sys.stdout.write (request_data)
        return True

    def send (self, data):
        """ 发送数据的默认函数 """
        return self.sock.sendall (data)

    def recv (self, size):
        """ 接收数据的默认函数 """
        return self.sock.recv (size)

class HttpMessage (object):
    """ """

    def __init__ (self):
        """ """
        self.header = {}

    def __setitem__ (self, k, val):
        """ """
        self.header[str (k)] = str (val)

    def __contains__ (self, k):
        """ """
        return k in self.header

    def get_header (self, k, default = ""):
        """ """
        return self.header.get (k, default)

    def __getitem__ (self, k):
        """ """
        return self.get_header (k)

class DummyStdoutput (object):
    """ """

    def __init__ (self, func):
        """ """
        self.func = func

    def write (self, data):
        """ """
        self.func (data)

class Logging (object):
    """ """
    format = "[%(asctime)s]%(name)s:%(levelname)s:%(message)s"
    datefmt = "%Y%m%d %H:%M:%S"

    def __init__ (self, access_path, error_path, level = logging.INFO):
        """ """
        Logging._instance = self
        self.access_path = path.expanduser (access_path)
        self.error_path = path.expanduser (error_path)
        self.access_file = open (self.access_path, "a")
        logging.basicConfig (level = level,
                             format = Logging.format,
                             datefmt = Logging.datefmt,
                             filename = self.error_path)
        self.stderr = None
        self.stderr_hook = DummyStdoutput (self.stderr_write)
        self.stdout = None
        self.stdout_hook = DummyStdoutput (self.stdout_write)
        self.hook_std ()

    def hook_std (self):
        """ """
        self.stderr = sys.stderr
        sys.stderr = self.stderr_hook
        self.stdout = sys.stdout
        sys.stdout = self.stdout_hook

    def unhook_std (self):
        """ """
        sys.stderr = self.stderr
        sys.stdout = self.stdout

    @staticmethod
    def get_time ():
        """ """
        return datetime.datetime.now ().strftime (Logging.datefmt)

    def request (self, request, response):
        """ """
        output = '%s - %s [%s] "%s %s %s" %d %s "-" "%s"\r\n' % \
            (request.from_addr[0], "-", self.get_time (),
             request.verb, request.url, request.version,
             response.response_code,
             response.get_header ("Content-Length", default = "0"),
             response.response_phrase)
        self.access_file.write (output)
        self.access_file.flush ()
        logging.debug (request.message_header ())
        logging.debug (response.message_header ())

    @staticmethod
    def stderr_write (data):
        """ """
        logging.error (data.rstrip ("\r\n"))

    @staticmethod
    def stdout_write (data):
        """ """
        logging.info (data.rstrip ("\r\n"))
