#!/usr/bin/python
# -*- coding: utf-8 -*-
# @date: 2009-09-24
# @author: shell.xu
from __future__ import with_statement
import sys
import socket
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
