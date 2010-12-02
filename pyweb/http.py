#!/usr/bin/python
# -*- coding: utf-8 -*-
'''
@date: 2010-06-04
@author: shell.xu
'''
from __future__ import with_statement
import socket
import logging
import traceback
from contextlib import contextmanager
from urlparse import urlparse
import ebus
import esock
import daemon
import basehttp
import template

class HttpRequest(basehttp.HttpMessage):
    ''' Http请求对象
    @ivar timeout: Server所附加的超时对象
    @ivar verb: 用户请求动作
    @ivar url: 用户请求原始路径
    @ivar version: 用户请求版本
    @ivar urls: 通常应当存在，为url的解析结果
    @ivar hostname: 主机名
    @ivar responsed: Response附加，当开始应答后增加标志，阻止下一个应答
    @ivar url_match: 可能存在，Dispatch附加，当url匹配后，用于保存匹配结果
    @ivar cookie: 可能存在，Session添加，用于保存cookie信息和变更
    @ivar session: 可能存在，Session添加，用于保存session，dict，内容必须可json序列化 '''
    VERBS = ['OPTIONS', 'GET', 'HEAD', 'POST', 'PUT', 'DELETE', 'TRACE', 'CONNECT']
    VERSIONS = ['HTTP/1.0', 'HTTP/1.1']

    @classmethod
    def make_request(cls, url, self = None):
        ''' 用于非接收的情况下，根据url构造一个request。 '''
        if self is None: self = cls(None)
        urls = urlparse(url)
        if urls.port: port = int(urls.port)
        elif urls.scheme.lower() == 'https': port = 443
        else: port = 80
        self.sockaddr = [urls.hostname, port, urls.username, urls.password]
        self.verb, self.version = 'GET', 'HTTP/1.1'
        if not urls.query: self.url = urls.path
        else: self.url = '%s?%s' % (urls.path, urls.query)
        return self

    def load_header(self):
        ''' 读取请求头，一般不由客户调用 '''
        info = self.recv_headers()
        if len(info) < 3: raise basehttp.BadRequestError(info)
        self.verb, self.url, self.version = \
            info[0].upper(), info[1], info[2].upper()
        self.proc_header()

    def proc_header(self):
        ''' 处理请求头，一般不由客户调用 '''
        if self.url.startswith('/') or self.url.lower().find('://') != -1:
            self.urls = urlparse(self.url)
            self.hostname = self.urls.netloc
        else: self.hostname, self.urls = self.url, {}
        if self.verb not in self.VERBS: raise basehttp.MethodNotAllowedError(self.verb)
        if self.version not in self.VERSIONS:
            raise basehttp.HttpException(505, self.version)

    def get_params(self):
        ''' 获得get方式请求参数 '''
        return basehttp.get_params_dict(self.urls.query)
    def post_params(self):
        ''' 获得post方式请求参数 '''
        self.recv_body()
        return basehttp.get_params_dict(self.get_body())

    def make_header(self):
        ''' 生成请求头 '''
        return self.make_headers([self.verb, self.url, self.version])

    def make_response(self, code = 200):
        ''' 生成响应对象
        @param code: 响应对象的代码，默认200
        @param res_type: 响应对象的类别，默认是HttpResponse '''
        response = HttpResponse(self, code)
        if self.get_header('connection', '').lower() == 'close' or \
                code >= 500 or self.version.upper() != 'HTTP/1.1':
            response.connection = False
        return response

    def make_redirect(self, url, code = 302):
        ''' 生成重定向响应 '''
        response = self.make_response(code)
        response.set_header('location', url)
        return response

class HttpResponse(basehttp.HttpMessage):
    ''' Http应答对象
    @ivar request: 请求对象
    @ivar connection: 是否保持连接，默认为保持
    @ivar code: 返回码
    @ivar cache: 缓存，目前未使用 '''

    def __init__(self, request, code):
        ''' 生成响应对象 '''
        super(HttpResponse, self).__init__(request.sock)
        self.request, self.connection = request, True
        self.header_sended, self.body_sended = False, False
        self.code, self.version, self.cache = code, request.version, None
        self.phrase = basehttp.DEFAULT_PAGES[code][0]

    def load_header(self):
        ''' 从远程接收头信息，而不是本地构造。 '''
        info = self.recv_headers()
        self.version, self.code, self.phrase = \
            info[0].upper(), int(info[1]), ''.join(info[2:])
        trans_code = self.get_header('transfer-encoding', 'identity')
        self.chunk_mode = trans_code != 'identity'

    def make_header(self):
        return self.make_headers([self.version, str(self.code), self.phrase,])

    def send_header(self, auto = False):
        ''' 发送响应头 '''
        if self.header_sended: return
        self.request.responsed = True
        if auto and 'content-length' not in self.header:
            self.set_header('content-length', self.body_len())
        self.sock.sendall(self.make_header())
        self.header_sended = True

    def append_body(self, data):
        ''' 保存响应数据 '''
        if isinstance(data, unicode): data = data.encode('utf-8', 'ignore')
        if not isinstance(data, str): data = str(data)
        self.content.append(data)

    def finish(self):
        ''' 结束响应发送过程，此后整个请求不能发送和追加任何数据 '''
        if not self.header_sended: self.send_header(True)
        if not self.body_sended and self.content:
            for data in self.content: self.send_body(data)
            self.body_sended = True

    pack_fields = ['header', 'content', 'chunk_mode', 'body_recved',
                   'connection', 'header_sended', 'body_sended', 'code',
                   'version', 'cache', 'phrase']
    def pack(self):
        return [getattr(self, n) for n in self.pack_fields]

    def unpack(self, objs):
        for n, v in zip(self.pack_fields, objs): setattr(self, n, v)

class HttpServer(esock.EpollSocket):
    BREAK_CONN, RESPONSE_DEBUG = False, True
    RequestCls = HttpRequest

    def __init__(self, app):
        super(HttpServer, self).__init__()
        self.app, self.timeout = app, 60

    def handler(self, sock):
        while True:
            request = self.RequestCls(sock)
            response = self.process_request(request)
            if response is None: break
            if daemon.weblog: daemon.weblog.log_req(request, response)
            if not response.connection or self.BREAK_CONN: break

    def process_request(self, request):
        try: request.load_header()
        except(EOFError, socket.error): return None
        try:
            logging.debug(request.make_header()[:-4])
            request.timeout = ebus.bus.set_timeout(self.timeout,
                                                   basehttp.TimeoutError)
            try: response = self.app(request)
            finally: request.timeout.cancel()
            if not response: response = request.make_response(500)
        except(EOFError, socket.error): return None
        except basehttp.HttpException, err:
            response = self.err_handler(request, err, err.args[0])
        except Exception, err:
            response = self.err_handler(request, err)
            logging.exception('app unknown error')
        if not response: return None
        try: response.finish()
        except: return None
        logging.debug(response.make_header()[:-4])
        return response

    tpl = template.Template(template = '<html><head><title>{%=res.phrase%}</title></head><body><h1>{%=code%}&nbsp;{%=res.phrase%}</h1><h3>{%=default_pages[code][1]%}</h3>{%if res_dbg:%}<br/>Debug Info:<br/>{%if len(err.args) > 1:%}{%="%s<br/>" % str(err.args[1:])%}{%end%}{%="<pre>%s</pre>" % debug_info%}{%end%}</body></html>')
    def err_handler(self, request, err, code = 500):
        if hasattr(request, 'responsed'): return None
        response = request.make_response(code)
        info = {'res': response, 'code': code, 'res_dbg': self.RESPONSE_DEBUG,
                'err': err, 'debug_info': ''.join(traceback.format_exc()),
                'default_pages': basehttp.DEFAULT_PAGES}
        response.append_body(self.tpl.render(info))
        return response

class SockFactory(object):
    @contextmanager
    def item(self):
        sock = esock.EpollSocket()
        try: yield sock
        finally: sock.close()
    def connect(self, sock, sockaddr): sock.connect(sockaddr[0], sockaddr[1])
default_sock_factory = SockFactory()

code_has_nobody = [100, 101, 204, 304]
def http_client(request, sock_factory = default_sock_factory):
    with sock_factory.item() as request.sock:
        sock_factory.connect(request.sock, request.sockaddr)
        if request.content:
            request.set_header('content-length', str(request.body_len()))
        request.sock.sendall(request.make_header())
        for data in request.content: request.send_body(data)
        response = request.make_response()
        response.load_header()
        response.recv_body(request.verb != 'HEAD' and \
                               response.code not in code_has_nobody)
    return response
