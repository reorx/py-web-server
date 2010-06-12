#!/usr/bin/python
# -*- coding: utf-8 -*-
# @date: 2010-06-04
# @author: shell.xu
import socket
import datetime
from urlparse import urlparse
import base

class HttpMessage (object):

    def __init__ (self, socks):
        self.socks, self.from_addr = socks, socks[0].from_addr
        self.header, self.content = {}, []
        self.chunk_mode, self.body_recved = False, False

    def __setitem__ (self, k, val): self.header[str (k)] = str (val)
    def __contains__ (self, k): return k in self.header
    def __getitem__ (self, k): return self.header[k]
    def get (self, k, default): return self.header.get (k, default)

    def recv_headers (self):
        lines = self.socks[0].recv_until ().splitlines ()
        for line in lines[1:]:
            part = line.partition (":")
            if len (part[1]) != 0: self[part[0]] = part[2].strip ()
            else: raise base.BadRequestError (line)
        return lines[0].split ()

    def make_headers (self, start_line_info):
        lines = [" ".join (start_line_info)]
        for k, v in self.header.items (): lines.append ("%s: %s" % (k, v))
        return "\r\n".join (lines) + "\r\n\r\n"

    def recv_body (self, hasbody = True):
        if self.body_recved: return
        if self.get ('Transfer-Encoding', 'identity') != 'identity':
            chunk_size = 1
            while chunk_size != 0:
                chunk = self.socks[0].recv_until ('\r\n').split (';')
                chunk_size = int (chunk[0], 16)
                self.append_body (self.socks[0].recv_length (chunk_size + 2)[:-2])
        elif 'Content-Length' in self:
            length = int (self['Content-Length'])
            while length > 0:
                data = self.socks[0].recv_once (length)
                self.append_body (data)
                length -= len (data)
        elif hasbody and self.check_hasbody ():
            try:
                while True: self.append_body (self.socks[0].recv_once ())
            except (EOFError, socket.error): pass
        self.end_body ()

    def check_hasbody (self): return True
    def body_len (self): return sum ([len (i) for i in self.content])
    def append_body (self, data): self.content.append (data)
    def end_body (self): self.body_recved = True

    http_date_fmts = ["%a %d %b %Y %H:%M:%S"]
    @staticmethod
    def get_http_date (date_str):
        for fmt in HttpMessage.http_date_fmts:
            try: return datetime.datetime.strptime (date_str, fmt)
            except ValueError: pass

    @staticmethod
    def make_http_date (date_obj):
        return date_obj.strftime (HttpRequest.http_date_fmts[0])

class HttpRequest (HttpMessage):
    VERBS = ['OPTIONS', 'GET', 'HEAD', 'POST', 'PUT', 'DELETE', 'TRACE', 'CONNECT']
    VERSIONS = ['HTTP/1.0', 'HTTP/1.1']

    def __init__ (self, socks):
        super (HttpRequest, self).__init__ (socks)
        self.threads = [socks[0].gthread,]
        self.urls = {}

    def load_header (self):
        info = self.recv_headers ()
        if len (info) < 3: raise base.BadRequestError (info)
        self.verb, self.url, self.version =\
            info[0].upper (), info[1], info[2].upper ()
        if self.verb not in self.VERBS:
            raise base.MethodNotAllowedError (self.verb)
        if self.version not in self.VERSIONS:
            raise base.HttpException (505, self.version)
        if self.url.startswith ('/') or self.url.lower ().find ('://') != -1:
            self.urls['scheme'], self.urls['netloc'], self.urls['path'],\
                self.urls['params'], self.urls['query'],\
                self.urls['fragment'] = urlparse (self.url)
            self.hostname = self.urls['netloc']
        else: self.hostname = self.url

    def get_params_dict (self, data):
        if not data: return {}
        rslt = {}
        for p in data.split ('&'):
            i = p.partition ('=')
            rslt[i[0]] = i[2]
        return rslt

    def make_header (self):
        return self.make_headers ([self.verb, self.url, self.version])

    def check_hasbody (self): return False

    def make_response (self, code = 200, res_type = None):
        if res_type is None: res_type = HttpResponse
        response = res_type (self, code)
        self.response = response
        if hasattr (self, 'version'): response.version = self.version
        if code >= 500: response.connection = False
        if self.get ('Connection', '').lower () == 'close':
            response.connection = False
        return response

    def make_redirect (self, url, code = 303):
        response = self.make_response (code)
        response['Location'] = url
        return response
    
    def term (self):
        # use with EventletConnPool may leak counter
        for s in self.socks: s.final ()
        for t in self.threads: t.cancel ()

class HttpResponse (HttpMessage):
    from default_setting import DEFAULT_PAGES

    def __init__ (self, request, code):
        super (HttpResponse, self).__init__ (request.socks)
        self.request, self.connection = request, True
        self.header_sended, self.body_sended = False, False
        self.code, self.version, self.cache = code, "HTTP/1.1", None
        self.phrase = HttpResponse.DEFAULT_PAGES[code][0]

    def make_header (self):
        return self.make_headers ([self.version, str (self.code), self.phrase,])

    def send_header (self, auto = False):
        if self.header_sended: return
        if auto and 'Content-Length' not in self:
            self["Content-Length"] = self.body_len ()
        self.socks[0].sendall (self.make_header ())
        self.header_sended = True

    def send_one_body (self, data):
        if self.body_sended: return
        if not self.chunk_mode: self.socks[0].sendall (data)
        else: self.socks[0].sendall ('%x\r\n%s\r\n' % (len (data), data))

    def finish (self):
        if not self.header_sended: self.send_header (True)
        if not self.body_sended and self.content:
            for data in self.content: self.send_one_body (data)
            self.body_sended = True

class HttpAction (object):
    def action (self, request): return request.make_response ()
