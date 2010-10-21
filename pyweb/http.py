#!/usr/bin/python
# -*- coding: utf-8 -*-
# @date: 2010-06-04
# @author: shell.xu
import socket
import datetime
from urlparse import urlparse
import base

class HttpMessage(object):
    ''' Http消息处理基类 '''
    DEFAULT_HASBODY = False

    def __init__(self, sock):
        ''' Http消息基础构造
        @var header: 消息头 '''
        self.sock, self.header, self.content = sock, {}, []
        self.chunk_mode, self.body_recved = False, False

    def recv_headers(self):
        ''' 抽象的读取Http头部 '''
        lines = self.sock.recv_until().splitlines()
        for line in lines[1:]:
            part = line.partition(":")
            if part[1]: self.header[part[0]] = part[2].strip()
            else: raise base.BadRequestError(line)
        return lines[0].split()

    def make_headers(self, start_line_info):
        ''' 抽象的头部生成过程 '''
        lines = [" ".join(start_line_info)]
        for k, v in self.header.items(): lines.append("%s: %s" %(k, v))
        return "\r\n".join(lines) + "\r\n\r\n"

    def body_len(self): return sum([len(i) for i in self.content])
    def append_body(self, data): self.content.append(data)
    def end_body(self): self.body_recved = True
    def get_body(self): return ''.join(self.content)

    def recv_body(self, hasbody = True):
        ''' 进行body接收过程，数据会写入本对象的append_body函数中 '''
        if self.body_recved: return
        if self.header.get('Transfer-Encoding', 'identity') != 'identity':
            chunk_size = 1
            while chunk_size != 0:
                chunk = self.sock.recv_until('\r\n').split(';')
                chunk_size = int(chunk[0], 16)
                self.append_body(self.sock.recv_length(chunk_size + 2)[:-2])
        elif 'Content-Length' in self.header:
            length = int(self.header['Content-Length'])
            while length > 0:
                data = self.sock.recv_once(length)
                self.append_body(data)
                length -= len(data)
        elif hasbody and self.DEFAULT_HASBODY:
            try:
                while True: self.append_body(self.sock.recv_once())
            except (EOFError, socket.error): pass
        self.end_body()

class HttpRequest(HttpMessage):
    ''' @var timeout: Server所附加的超时对象
    @var responsed: Response附加，当开始应答后增加标志，阻止下一个应答 '''
    VERBS = ['OPTIONS', 'GET', 'HEAD', 'POST', 'PUT', 'DELETE', 'TRACE', 'CONNECT']
    VERSIONS = ['HTTP/1.0', 'HTTP/1.1']

    def load_header(self):
        ''' 读取请求头，一般不由客户调用
        @var verb: 用户请求动作
        @var url: 用户请求原始路径
        @var version: 用户请求版本 '''
        info = self.recv_headers()
        if len(info) < 3: raise base.BadRequestError(info)
        self.verb, self.url, self.version = \
            info[0].upper(), info[1], info[2].upper()
        self.proc_header()

    def proc_header(self):
        ''' 处理请求头，一般不由客户调用
        @var hostname: 主机名
        @var urls: 通常应当存在，为url的解析结果 '''
        if self.url.startswith('/') or self.url.lower().find('://') != -1:
            self.urls = urlparse(self.url)
            self.hostname = self.urls.netloc
        else: self.hostname, self.urls = self.url, {}
        if self.verb not in self.VERBS: raise base.MethodNotAllowedError(self.verb)
        if self.version not in self.VERSIONS:
            raise base.HttpException(505, self.version)

    def get_params(self): return get_params_dict(self.urls.query)
    def post_params(self):
        self.recv_body()
        return get_params_dict(self.get_body())

    def make_header(self):
        ''' 生成请求头 '''
        return self.make_headers([self.verb, self.url, self.version])

    def make_response(self, code = 200):
        ''' 生成响应对象
        @param code: 响应对象的代码，默认200
        @param res_type: 响应对象的类别，默认是HttpResponse '''
        response = HttpResponse(self, code)
        if hasattr(self, 'version'): response.version = self.version
        if self.header.get('Connection', '').lower() == 'close':
            response.connection = False
        return response

    def make_redirect(self, url, code = 302):
        ''' 生成重定向响应 '''
        response = self.make_response(code)
        response.header['Location'] = url
        return response

class HttpResponse(HttpMessage):
    from default_setting import DEFAULT_PAGES

    def __init__(self, request, code):
        ''' 生成响应对象
        @var request: 请求对象
        @var connection: 是否保持连接，默认为保持
        @var code: 返回码
        @var cache: 缓存，目前未使用 '''
        super(HttpResponse, self).__init__(request.sock)
        self.request, self.connection = request, True
        self.header_sended, self.body_sended = False, False
        self.code, self.version, self.cache = code, "HTTP/1.1", None
        self.phrase = HttpResponse.DEFAULT_PAGES[code][0]
        if code >= 500: self.connection = False

    def make_header(self):
        return self.make_headers([self.version, str(self.code), self.phrase,])

    def send_header(self, auto = False):
        ''' 发送响应头 '''
        if self.header_sended: return
        self.request.responsed = True
        if auto and 'Content-Length' not in self.header:
            self.header["Content-Length"] = self.body_len()
        self.sock.sendall(self.make_header())
        self.header_sended = True

    def append_body(self, data):
        ''' 保存响应数据 '''
        if isinstance(data, unicode): data = data.encode('utf-8', 'ignore')
        if not isinstance(data, str): data = str(data)
        self.content.append(data)

    def send_body(self, data):
        ''' 发送一个数据片段 '''
        if self.body_sended: return
        if isinstance(data, unicode): data = data.encode('utf-8')
        if not isinstance(data, str): data = str(data)
        if not self.chunk_mode: self.sock.sendall(data)
        else: self.sock.sendall('%x\r\n%s\r\n' %(len(data), data))

    def finish(self):
        ''' 结束响应发送过程，此后整个请求不能发送和追加任何数据 '''
        if not self.header_sended: self.send_header(True)
        if not self.body_sended and self.content:
            for data in self.content: self.send_body(data)
            self.body_sended = True

HTTP_DATE_FMTS = ["%a %d %b %Y %H:%M:%S"]
def get_http_date(date_str):
    for fmt in HTTP_DATE_FMTS:
        try: return datetime.datetime.strptime(date_str, fmt)
        except ValueError: pass

def make_http_date(date_obj):
    return date_obj.strftime(HTTP_DATE_FMTS[0])

def get_params_dict(data):
    ''' 将请求参数切分成词典 '''
    if not data: return {}
    rslt = {}
    for p in data.split('&'):
        i = p.partition('=')
        rslt[i[0]] = i[2]
    return rslt
