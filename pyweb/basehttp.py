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

DEFAULT_PAGES = {
    100:('Continue', 'Request received, please continue'),
    101:('Switching Protocols',
          'Switching to new protocol; obey Upgrade header'),

    200:('OK', ''),
    201:('Created', 'Document created, URL follows'),
    202:('Accepted', 'Request accepted, processing continues off-line'),
    203:('Non-Authoritative Information', 'Request fulfilled from cache'),
    204:('No Content', 'Request fulfilled, nothing follows'),
    205:('Reset Content', 'Clear input form for further input.'),
    206:('Partial Content', 'Partial content follows.'),

    300:('Multiple Choices', 'Object has several resources -- see URI list'),
    301:('Moved Permanently', 'Object moved permanently -- see URI list'),
    302:('Found', 'Object moved temporarily -- see URI list'),
    303:('See Other', 'Object moved -- see Method and URL list'),
    304:('Not Modified', 'Document has not changed since given time'),
    305:('Use Proxy',
          'You must use proxy specified in Location to access this resource.'),
    307:('Temporary Redirect', 'Object moved temporarily -- see URI list'),

    400:('Bad Request', 'Bad request syntax or unsupported method'),
    401:('Unauthorized', 'No permission -- see authorization schemes'),
    402:('Payment Required', 'No payment -- see charging schemes'),
    403:('Forbidden', 'Request forbidden -- authorization will not help'),
    404:('Not Found', 'Nothing matches the given URI'),
    405:('Method Not Allowed', 'Specified method is invalid for this server.'),
    406:('Not Acceptable', 'URI not available in preferred format.'),
    407:('Proxy Authentication Required',
          'You must authenticate with this proxy before proceeding.'),
    408:('Request Timeout', 'Request timed out; try again later.'),
    409:('Conflict', 'Request conflict.'),
    410:('Gone', 'URI no longer exists and has been permanently removed.'),
    411:('Length Required', 'Client must specify Content-Length.'),
    412:('Precondition Failed', 'Precondition in headers is false.'),
    413:('Request Entity Too Large', 'Entity is too large.'),
    414:('Request-URI Too Long', 'URI is too long.'),
    415:('Unsupported Media Type', 'Entity body in unsupported format.'),
    416:('Requested Range Not Satisfiable', 'Cannot satisfy request range.'),
    417:('Expectation Failed', 'Expect condition could not be satisfied.'),

    500:('Internal Server Error', 'Server got itself in trouble'),
    501:('Not Implemented', 'Server does not support this operation'),
    502:('Bad Gateway', 'Invalid responses from another server/proxy.'),
    503:('Service Unavailable',
          'The server cannot process the request due to a high load'),
    504:('Gateway Timeout',
          'The gateway server did not receive a timely response'),
    505:('HTTP Version Not Supported', 'Cannot fulfill request.'),
}

MIME = {
    '.htm':"text/html", '.html':"text/html", ".txt":"text/plain",
    ".xhtm":"application/xhtml+xml", ".xhtml":"application/xhtml+xml",
    ".xsit":"text/xml", ".xsl":"text/xml", ".xml":"text/xml",
    ".gif":"image/gif", ".jpg":"image/jpeg", ".jpeg":"image/jpeg",
    ".png":"image/png", ".tif":"image/tiff", ".tiff":"image/tiff",
    ".wav":"audio/x-wav",
    ".gz":"application/x-gzip", ".bz2":"application/x-bzip2",
    ".tar":"application/x-tar", ".zip":"application/zip"
}

class HttpMessage(object):
    ''' Http消息处理基类
    @ivar header: 消息头 '''

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
        if isinstance(v, list): return l[0]
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
            k = '-'.join([t.capitalize() for t in k.split('-')])
            if hasattr(l, '__iter__'):
                for v in l: lines.append("%s: %s" %(k, v))
            else: lines.append("%s: %s" %(k, l))
        return "\r\n".join(lines) + "\r\n\r\n"

    def body_len(self): return sum([len(i) for i in self.content])
    def append_body(self, data): self.content.append(data)
    def end_body(self): self.body_recved = True
    def send_body(self, data):
        ''' 发送一个数据片段 '''
        if isinstance(data, unicode): data = data.encode('utf-8')
        if not isinstance(data, str): data = str(data)
        if not self.chunk_mode: self.sock.sendall(data)
        else: self.sock.sendall('%x\r\n%s\r\n' %(len(data), data))
    def get_body(self): return ''.join(self.content)

    def recv_body(self, hasbody = False):
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
            for data in self.sock.datas():
                self.append_body(data)
                length -= len(data)
                if length <= 0: break
        elif hasbody:
            try:
                for d in self.sock.datas(): self.append_body(d)
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
