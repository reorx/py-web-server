#!/usr/bin/python
# -*- coding: utf-8 -*-
'''
@date: 2010-06-04
@author: shell.xu
'''
import struct
import logging
import http

def nvpair_data(data, b):
    if ord(data[b]) < 128: return b + 1, ord(data[b])
    else: return b + 4, struct.unpack('<L', data[b : b + 4] & 0x7fffffff)[0]

def nvpair(data, b):
    b, name_len = nvpair_data(data, b)
    b, value_len = nvpair_data(data, b)
    n, v = data[b : b + name_len], data[b + name_len : b + name_len + value_len]
    return b+name_len+value_len, n, v

def begin_request(self, reqid, content):
    self.fcgi_header, self.fcgi_reqid = {}, reqid
    role, flags = struct.unpack('>HB', content[:3])
    assert(role == 1)
    self.fcgi_keep_conn = flags & 1 == 1

def params(self, reqid, content):
    if len(content) == 0: return True
    i = 0
    while i < len(content):
        i, n, v = nvpair(content, i)
        self.fcgi_header[n] = v
        if n == 'REQUEST_METHOD': self.verb = v
        elif n == 'REQUEST_URI': self.url = v
        elif n == 'SERVER_PROTOCOL': self.version = v
        elif n.startswith('HTTP_'):
            self.add_header(n[5:].lower().replace('_', '-'), v)

def stdin(self, reqid, content):
    if len(content) == 0: self.end_body()
    else: self.append_body(content)

class FcgiRequest(http.HttpRequest):
    '''
    @ivar fcgi_header: fcgi的头部
    @ivar fcgi_reqid: fcgi的请求序列号
    @ivar fcgi_keep_conn: fcgi连接是否复用
    '''
    RECORD_FUNCS = {1:begin_request, 4:params, 5:stdin}

    def recv_record(self):
        data = self.sock.recv_length(8)
        ver, tp, reqid, cont_len, pad_len, r = struct.unpack('>BBHHBB', data)
        logging.debug('recv_record %s %s %s' % (tp, reqid, cont_len))
        content = self.sock.recv_length(cont_len)
        self.sock.recv_length(pad_len)
        return tp, reqid, content

    def load_header(self):
        while True:
            tp, reqid, content = self.recv_record()
            func = self.RECORD_FUNCS.get(tp, None)
            if not func: raise Exception('record %d %d' % (tp, reqid))
            if func(self, reqid, content): break
        while not self.body_recved:
            tp, reqid, content = self.recv_record()
            assert(tp == 5)
            stdin(self, reqid, content)
        self.proc_header()

    def make_response(self, code = 200):
        ''' 生成响应对象
        @param code: 响应对象的代码，默认200 '''
        response = FcgiResponse(self, code)
        if not self.fcgi_keep_conn or code >= 500: response.connection = False
        return response

class FcgiResponse(http.HttpResponse):

    def fcgi_record(self, tp, data):
        reqid = self.request.fcgi_reqid
        return struct.pack('>BBHHBB', 1, tp, reqid, len(data), 0, 0) + data

    def make_header(self):
        return self.fcgi_record(6, self.make_headers(None))

    def send_body(self, data):
        if self.body_sended: return
        if isinstance(data, unicode): data = data.encode('utf-8')
        if not isinstance(data, str): data = str(data)
        i = 0
        while i<<15 < len(data):
            b = i << 15
            e = 1 << 15 + b
            if e > len(data): e = len(data)
            self.sock.sendall(self.fcgi_record(6, data[b:e]))
            i += 1

    def finish(self):
        if not self.header_sended: self.send_header(True)
        if not self.body_sended and self.content:
            self.send_body(''.join(self.content))
            self.body_sended = True
        data = self.fcgi_record(6, '') + self.fcgi_record(3, '\0' * 8)
        self.sock.sendall(data)

class FcgiServer(http.HttpServer):
    RequestCls = FcgiRequest
