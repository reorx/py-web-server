#!/usr/bin/python
# -*- coding: utf-8 -*-
# @date: 2009-12-25
# @author: shell.xu
'''日志系统，处理输出hook动作和访问日志'''
from __future__ import with_statement
import sys
import logging
import datetime
from os import path

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

    @staticmethod
    def request (request, response):
        """ 格式化一个请求 """
        response_code = response.response_code if response != None else ""
        if response != None:
            header_info = response.get_header ("Content-Length", default = "0")
        else: header_info = "0"
        response_phrase = response.response_phrase if response != None else ""
        output = '%s - %s [%s] "%s %s %s" %d %s "-" "%s"\r\n' % \
            (request.from_addr[0], "-", Logging._get_time (),
             request.verb, request.url, request.version,
             response_code, header_info, response_phrase)
        Logging._instance.access_file.write (output)
        Logging._instance.access_file.flush ()
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
