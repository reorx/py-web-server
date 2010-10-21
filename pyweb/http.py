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

    def __init__(self, sock):
        self.sock, self.header, self.content = sock, {}, []
        self.chunk_mode, self.body_recved = False, False

    def __setitem__(self, k, val): self.header[str(k)] = str(val)
    def __contains__(self, k): return k in self.header
    def __getitem__(self, k): return self.header[k]
    def get(self, k, default): return self.header.get(k, default)

    def recv_headers(self):
        lines = self.sock.recv_until().splitlines()
        for line in lines[1:]:
            part = line.partition(":")
            if part[1]: self[part[0]] = part[2].strip()
            else: raise base.BadRequestError(line)
        return lines[0].split()

    def make_headers(self, start_line_info):
        lines = [" ".join(start_line_info)]
        for k, v in self.header.items(): lines.append("%s: %s" %(k, v))
        return "\r\n".join(lines) + "\r\n\r\n"

    def recv_body(self, hasbody = True):
        ''' 进行body接收过程，数据会写入本对象的append_body函数中 '''
        if self.body_recved: return
        if self.get('Transfer-Encoding', 'identity') != 'identity':
            chunk_size = 1
            while chunk_size != 0:
                chunk = self.sock.recv_until('\r\n').split(';')
                chunk_size = int(chunk[0], 16)
                self.append_body(self.sock.recv_length(chunk_size + 2)[:-2])
        elif 'Content-Length' in self:
            length = int(self['Content-Length'])
            while length > 0:
                data = self.sock.recv_once(length)
                self.append_body(data)
                length -= len(data)
        elif hasbody and self.check_hasbody():
            try:
                while True: self.append_body(self.sock.recv_once())
            except (EOFError, socket.error): pass
        self.end_body()

    def body_len(self): return sum([len(i) for i in self.content])
    def append_body(self, data): self.content.append(data)
    def end_body(self): self.body_recved = True

    http_date_fmts = ["%a %d %b %Y %H:%M:%S"]
    @staticmethod
    def get_http_date(date_str):
        for fmt in HttpMessage.http_date_fmts:
            try: return datetime.datetime.strptime(date_str, fmt)
            except ValueError: pass

    @staticmethod
    def make_http_date(date_obj):
        return date_obj.strftime(HttpRequest.http_date_fmts[0])

class HttpRequest(HttpMessage):
    VERBS = ['OPTIONS', 'GET', 'HEAD', 'POST', 'PUT', 'DELETE', 'TRACE', 'CONNECT']
    VERSIONS = ['HTTP/1.0', 'HTTP/1.1']

    def load_header(self):
        ''' 读取请求头，一般不由客户调用 '''
        info = self.recv_headers()
        if len(info) < 3: raise base.BadRequestError(info)
        self.verb, self.url, self.version = \
            info[0].upper(), info[1], info[2].upper()
        self.proc_header()

    def proc_header(self):
        if self.url.startswith('/') or self.url.lower().find('://') != -1:
            self.urls = urlparse(self.url)
            self.hostname = self.urls.netloc
        else: self.hostname, self.urls = self.url, {}
        if self.verb not in self.VERBS: raise base.MethodNotAllowedError(self.verb)
        if self.version not in self.VERSIONS:
            raise base.HttpException(505, self.version)

    def get_params_dict(self, data):
        ''' 将请求参数切分成词典 '''
        if not data: return {}
        rslt = {}
        for p in data.split('&'):
            i = p.partition('=')
            rslt[i[0]] = i[2]
        return rslt

    def make_header(self):
        ''' 生成请求头 '''
        return self.make_headers([self.verb, self.url, self.version])

    def check_hasbody(self): return False

    def make_response(self, code = 200, res_type = None):
        '''
        生成响应对象
        @param code: 响应对象的代码，默认200
        @param res_type: 响应对象的类别，默认是HttpResponse
        '''
        if not res_type: res_type = HttpResponse
        response = res_type(self, code)
        if hasattr(self, 'version'): response.version = self.version
        if self.get('Connection', '').lower() == 'close':
            response.connection = False
        return response

    def make_redirect(self, url, code = 302):
        ''' 生成重定向响应 '''
        response = self.make_response(code)
        response['Location'] = url
        return response

class HttpResponse(HttpMessage):
    from default_setting import DEFAULT_PAGES

    def __init__(self, request, code):
        super(HttpResponse, self).__init__(request.sock)
        self.request, self.connection = request, True
        self.header_sended, self.body_sended = False, False
        self.code, self.version, self.cache = code, "HTTP/1.1", None
        self.phrase = HttpResponse.DEFAULT_PAGES[code][0]
        if code >= 500: self.connection = False

    def make_header(self):
        return self.make_headers([self.version, str(self.code), self.phrase, ])

    def send_header(self, auto = False):
        if self.header_sended: return
        self.request.responsed = True
        if auto and 'Content-Length' not in self:
            self["Content-Length"] = self.body_len()
        self.sock.sendall(self.make_header())
        self.header_sended = True

    def append_body(self, data):
        if isinstance(data, unicode): data = data.encode('utf-8', 'ignore')
        if not isinstance(data, str): data = str(data)
        self.content.append(data)

    def send_one_body(self, data):
        if self.body_sended: return
        if isinstance(data, unicode): data = data.encode('utf-8')
        if not self.chunk_mode: self.sock.sendall(data)
        else: self.sock.sendall('%x\r\n%s\r\n' %(len(data), data))

    def finish(self):
        ''' 结束响应发送过程，此后整个请求不能发送和追加任何数据 '''
        if not self.header_sended: self.send_header(True)
        if not self.body_sended and self.content:
            for data in self.content: self.send_one_body(data)
            self.body_sended = True
