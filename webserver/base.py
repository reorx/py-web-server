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
        """ 处理loop过程的主函数，需要重载 """
        pass

    def do_process (self, request_data):
        """ 处理request_data的调用 """
        sys.stdout.write (request_data)
        return True

    def send (self, data):
        """ 发送数据的默认函数 """
        return self.sock.sendall (data)

    def recv (self, size):
        """ 接收数据的默认函数 """
        return self.sock.recv (size)

class HttpMessage (object):
    """ Request和Response的基类，可以存放和返回头信息 """

    def __init__ (self):
        """ 构造，初始化头信息 """
        self.header = {}

    def __setitem__ (self, k, val):
        """ 向头内添加数据 """
        self.header[str (k)] = str (val)

    def __contains__ (self, k):
        """ 判断是否有特定的头 """
        return k in self.header

    def get_header (self, k, default = ""):
        """ 获得头信息 """
        return self.header.get (k, default)

    def __getitem__ (self, k):
        """ 获得头信息，没有默认值 """
        return self.get_header (k)

class DummyStdoutput (object):
    """ 中间对象，实现了一个文件的基本操作
    但将写出数据转发到一个特定函数上 """

    def __init__ (self, func):
        """ 记录特定函数 """
        self.func = func

    def write (self, data):
        """ 转发写出动作 """
        self.func (data)

class Logging (object):
    """ 记录类，将所有屏幕输出记录到日志文件中 """
    format = "[%(asctime)s]%(name)s:%(levelname)s:%(message)s"
    datefmt = "%Y%m%d %H:%M:%S"
    _instance = None

    def __new__ (cls, *param, **kargs):
        """ 构建单例对象 """
        if Logging._instance == None:
            Logging._instance = object.__new__ (cls, *param, **kargs)
        return Logging._instance

    def __init__ (self, access_path, error_path, level = logging.INFO):
        """ 初始化日志对象 """
        self.access_path = path.expanduser (access_path)
        self.error_path = path.expanduser (error_path)
        self.access_file = open (self.access_path, "a")
        logging.basicConfig (level = level, format = Logging.format,
                             datefmt = Logging.datefmt,
                             filename = self.error_path)
        self.stderr = sys.stderr
        self.stderr_hook = DummyStdoutput (self._stderr_write)
        self.stdout = sys.stdout
        self.stdout_hook = DummyStdoutput (self._stdout_write)

    def hook_std (self):
        """ 挂钩输出 """
        sys.stderr = self.stderr_hook
        sys.stdout = self.stdout_hook

    def unhook_std (self):
        """ 反挂钩输出 """
        sys.stderr = self.stderr
        sys.stdout = self.stdout

    @staticmethod
    def write_stdout (data):
        """ 正常标准输出 """
        return Logging._instance.stdout.write (data)

    @staticmethod
    def write_stderr (data):
        """ 正常错误输出 """
        return Logging._instance.stderr.write (data)

    @staticmethod
    def _get_time ():
        """ 时间格式化函数 """
        return datetime.datetime.now ().strftime (Logging.datefmt)

    def request (self, request, response):
        """ 格式化一个请求 """
        output = '%s - %s [%s] "%s %s %s" %d %s "-" "%s"\r\n' % \
            (request.from_addr[0], "-", self._get_time (),
             request.verb, request.url, request.version,
             response.response_code,
             response.get_header ("Content-Length", default = "0"),
             response.response_phrase)
        self.access_file.write (output)
        self.access_file.flush ()
        logging.debug (request.message_header ())
        logging.debug (response.message_header ())

    @staticmethod
    def _stderr_write (data):
        """ 错误的输出函数 """
        logging.error (data.rstrip ("\r\n"))

    @staticmethod
    def _stdout_write (data):
        """ 信息的输出函数 """
        logging.info (data.rstrip ("\r\n"))
