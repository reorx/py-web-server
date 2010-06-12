#!/usr/bin/python
# -*- coding: utf-8 -*-
# @date: 2010-06-04
# @author: shell.xu
import socket
import eventlet
import base
from http import HttpAction, HttpResponse
from server import TcpEventletClient
socks = eventlet.import_patched ('socks')

class TcpSocksClient (TcpEventletClient):

    def connect (self, hostname, **kargs):
        '''
        proxytype - The type of the proxy to be used. Three types
                    are supported: PROXY_TYPE_SOCKS4 (including socks4a),
                    PROXY_TYPE_SOCKS5 and PROXY_TYPE_HTTP
        addr      - The address of the server (IP or DNS).
        port      - The port of the server. Defaults to 1080 for SOCKS
                    servers and 8080 for HTTP proxy servers.
        rdns      - Should DNS queries be preformed on the remote side
                    (rather than the local side). The default is True.
                    Note: This has no effect with SOCKS4 servers.
        username  - Username to authenticate with to the server.
                    The default is no authentication.
        password  - Password to authenticate with to the server.
                    Only relevant when username is also provided.
        '''
        self.sock = socks.socksocket (socket.AF_INET, socket.SOCK_STREAM)
        hostinfo = hostname.partition (':')
        port = int (hostinfo[2]) if len (hostinfo[1]) != 0 else 80
        self.sock.setproxy (**kargs)
        self.sock.connect ((hostinfo[0], port))

class HttpProxyResponse (HttpResponse):
    MAX_CACHE = 16 * 1024

    def load_header (self):
        try: info = self.recv_headers ()
        except base.BadRequestError, err: raise base.BadGatewayError (err.args[1:])
        if len (info) < 2: raise base.BadGatewayError (info)
        self.version, self.code = info[0], int (info[1])
        if len (info) >= 3: self.phrase = " ".join (info[2:])
        else: self.phrase = self.DEFAULT_PAGES[self.code][0]
        if int (self.get ('Content-Length', '1')) < self.MAX_CACHE:
            self.cache = True

    def check_hasbody (self):
        if self.request.verb == 'HEAD': return False
        if self.code in [100, 101, 204, 304]: return False
        # it has body, so real server close connection to end body
        # and we also need to close connection to let client know
        self.connection = False
        return True

    def append_body (self, data):
        if self.chunk_mode:
            self.socks[1].sendall ('%x\r\n%s\r\n' % (len (data), data))
        else: self.socks[1].sendall (data)
        self.request.proxy_count[1] += len (data)
        if self.cache: super (HttpProxyResponse, self).append_body (data)

    def end_body (self):
        super (HttpProxyResponse, self).end_body ()
        if self.chunk_mode: self.socks[1].sendall ('0\r\n\r\n')
        self.body_sended = True

class HttpProxyAction (HttpAction):
    name = 'proxy'
    DEBUG = False

    def __init__ (self, shared_pool):
        super (HttpProxyAction, self).__init__ ()
        self.shared_pool = shared_pool
    
    def get_hostname (self, request): return request.hostname

    def send_request (self, request):
        if not request.hostname: raise base.NotAcceptableError (request.url)
        rest = request.url.partition (request.hostname)
        if not rest[2]: raise base.NotAcceptableError (request.url)
        req_info = request.make_headers ([request.verb, rest[2], request.version])
        if self.DEBUG: print req_info
        request.socks[1].sendall (req_info + "".join (request.content))

    def get_response (self, request):
        response = request.make_response (200, HttpProxyResponse)
        response.socks.reverse ()
        try: response.load_header ()
        finally: response.socks.reverse ()
        response.send_header ()
        if self.DEBUG: print response.make_header ()

        if hasattr (request, 'timeout'): request.timeout.cancel ()
        response.socks.reverse ()
        try: response.recv_body ()
        finally: response.socks.reverse ()
        return response, response.get ('Connection', 'close').lower () == 'close'

    def action_connect (self, request):
        if self.DEBUG: print request.make_header ()
        response = request.make_response ()
        response.send_header ()
        if self.DEBUG: print response.make_header ()
        return response, True

    def action (self, request):
        force, request.proxy_count = True, [0, 0] # send, recv
        try:
            request.recv_body ()
            try: sock = self.shared_pool.acquire (self.get_hostname (request))
            except (EOFError, socket.error): raise base.BadGatewayError ()
            if sock is None: raise base.BadGatewayError ()
            request.socks.append (sock)
            try:
                if request.verb == 'CONNECT':
                    response, force = self.action_connect (request)
                    if hasattr (request, 'timeout'): request.timeout.cancel ()
                    s = request.socks
                    s[0].pump ([[s[0], s[1], 0], [s[1], s[0], 1],],
                               request, request.proxy_count)
                    response.connection, response.body_sended = False, True
                else:
                    self.send_request (request)
                    response, force = self.get_response (request)
            finally:
                request.socks.remove (sock)
                self.shared_pool.release (sock, force)
        except base.TimeoutError, err: raise base.HttpException (504, err.args[1:])
        return response

class HttpProxyForwardAction (HttpProxyAction):
    name = 'forward'

    def __init__ (self, shared_pool, hostname):
        super (HttpProxyForwardAction, self).__init__ (shared_pool)
        self.hostname = hostname

    def get_hostname (self, request): return self.hostname

    def send_request (self, request):
        req_info = request.make_header ()
        if self.DEBUG: print req_info
        request.socks[1].sendall (req_info + "".join (request.content))

    def action_connect (self, request):
        if self.DEBUG: print request.make_header ()
        request.socks[1].sendall (request.make_header () + "".join (request.content))
        response = request.make_response ()
        res_header = request.socks[1].recv_until ()
        if self.DEBUG: print res_header
        response.socks[0].sendall (res_header + '\r\n\r\n')
        response.header_sended = True
        return response, True
