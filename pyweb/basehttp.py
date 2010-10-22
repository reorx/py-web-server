#!/usr/bin/python
# -*- coding: utf-8 -*-
'''
@date: 2010-06-04
@author: shell.xu
'''
import socket
import urllib
from datetime import datetime
from urlparse import urlparse

class HttpException(Exception): pass
class BadRequestError(HttpException):
    def __init__(self, *params): HttpException.__init__(self, 400, *params)
class NotFoundError(HttpException):
    def __init__(self, *params): HttpException.__init__(self, 404, *params)
class MethodNotAllowedError(HttpException):
    def __init__(self, *params): HttpException.__init__(self, 405, *params)
class NotAcceptableError(HttpException):
    def __init__(self, *params): HttpException.__init__(self, 406, *params)
class TimeoutError(HttpException):
    def __init__(self, *params): HttpException.__init__(self, 408, *params)
class BadGatewayError(HttpException):
    def __init__(self, *params): HttpException.__init__(self, 502, *params)

class HttpMessage(object):
    ''' Http消息处理基类
    @ivar header: 消息头 '''
    DEFAULT_HASBODY = False

    def __init__(self, sock):
        ''' Http消息基础构造 '''
        self.sock, self.header, self.content = sock, {}, []
        self.chunk_mode, self.body_recved = False, False

    def set_header(self, k, v):
        ''' 设定头，不论原来是什么内容 '''
        self.header[k.lower()] = v

    def add_header(self, k, v):
        ''' 添加头，如果没有这项则新建 '''
        k = k.lower()
        if k not in self.header: self.header[k] = v
        elif hasattr(self.header[k], 'append'): self.header[k].append(v)
        else: self.header[k] = [self.header[k], v]

    def get_header(self, k, v = None):
        ''' 获得头的第一个元素，如果不存在则返回v '''
        l = self.header.get(k.lower(), None)
        if l is None: return v
        if hasattr(v, '__getitem__'): return l[0]
        else: return l

    def recv_headers(self):
        ''' 抽象的读取Http头部 '''
        lines = self.sock.recv_until().splitlines()
        for line in lines[1:]:
            if not line.startswith(' ') and not line.startswith('\t'):
                part = line.partition(":")
                if not part[1]: raise BadRequestError(line)
                self.add_header(part[0], part[2].strip())
            else: self.add_header(part[0], line[1:])
        return lines[0].split()

    def make_headers(self, start_line_info):
        ''' 抽象的头部生成过程 '''
        if not start_line_info: lines = []
        else: lines = [" ".join(start_line_info)]
        for k, l in self.header.items():
            k = '_'.join([t.capitalize() for t in k.split('_')])
            if hasattr(l, '__iter__'):
                for v in l: lines.append("%s: %s" %(k, v))
            else: lines.append("%s: %s" %(k, l))
        return "\r\n".join(lines) + "\r\n\r\n"

    def body_len(self): return sum([len(i) for i in self.content])
    def append_body(self, data): self.content.append(data)
    def end_body(self): self.body_recved = True
    def get_body(self): return ''.join(self.content)

    def recv_body(self, hasbody = True):
        ''' 进行body接收过程，数据会写入本对象的append_body函数中 '''
        if self.body_recved: return
        if self.get_header('transfer-encoding', 'identity') != 'identity':
            chunk_size = 1
            while chunk_size != 0:
                chunk = self.sock.recv_until('\r\n').split(';')
                chunk_size = int(chunk[0], 16)
                self.append_body(self.sock.recv_length(chunk_size + 2)[:-2])
        elif 'content-length' in self.header:
            length = int(self.get_header('content-length'))
            while length > 0:
                data = self.sock.recv_once(length)
                self.append_body(data)
                length -= len(data)
        elif hasbody and self.DEFAULT_HASBODY:
            try:
                while True: self.append_body(self.sock.recv_once())
            except (EOFError, socket.error): pass
        self.end_body()

HTTP_DATE_FMTS = ["%a %d %b %Y %H:%M:%S"]
def get_http_date(date_str):
    for fmt in HTTP_DATE_FMTS:
        try: return datetime.strptime(date_str, fmt)
        except ValueError: pass

def make_http_date(date_obj):
    return date_obj.strftime(HTTP_DATE_FMTS[0])

def get_params_dict(data, sp = '&'):
    ''' 将请求参数切分成词典 '''
    if not data: return {}
    rslt = {}
    for p in data.split(sp):
        i = p.partition('=')
        rslt[i[0]] = urllib.unquote(i[2])
    return rslt
