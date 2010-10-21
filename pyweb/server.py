#!/usr/bin/python
# -*- coding: utf-8 -*-
'''
@date: 2010-06-04
@author: shell.xu
'''
from __future__ import with_statement
import os
import socket
import logging
import eventlet
import traceback
from eventlet import tpool
from eventlet.timeout import Timeout as eventTimeout
import log
import base
import http
import template

def fork_server():
    with open("/proc/cpuinfo", "r") as cpu_file:
        cpuinfo = cpu_file.readlines()
    cpunum = len(filter(lambda x: x.startswith("processor"), cpuinfo))
    for i in xrange(0, cpunum - 1):
        if os.fork() == 0: break

class EventletServer(base.TcpServer):

    def listen(self, addr = '', port = 8080,
               poolsize = 10000, reuse = False, **kargs):
        ''' 监听指定端口
        @param addr: 监听地址，默认是所有地址
        @param port: 监听端口
        @param poolsize: eventlet的调度池最大容量
        @param reuse: 指定为True则使用reuse方式打开端口，避免CLOSE_WAIT的影响 '''
        self.sockaddr = (addr, port)
        self.setsock(eventlet.listen(self.sockaddr))
        if reuse: self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.pool = eventlet.GreenPool(poolsize)

    def listen_unix(self, sockpath = '', poolsize = 10000, reuse = False, **kargs):
        ''' 监听unix socket
        @param sockpath: unix socket路径
        @param poolsize: eventlet的调度池最大容量
        @param reuse: 指定为True则使用reuse方式打开端口，避免CLOSE_WAIT的影响 '''
        self.sockaddr = sockpath
        try: os.remove(sockpath)
        except OSError: pass
        self.setsock(eventlet.listen(self.sockaddr, socket.AF_UNIX))
        if reuse: self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.pool = eventlet.GreenPool(poolsize)

    def do_loop(self):
        sock = base.SockBase()
        s, sock.from_addr = self.sock.accept()
        sock.setsock(s)
        self.pool.spawn_n(self.handler, sock)
        return True

class EventletClient(base.TcpClient):

    def connect(self, hostaddr, port):
        self.setsock(tpool.execute(eventlet.connect, (hostaddr, port)))

class HttpServer(EventletServer):
    BREAK_CONN, RESPONSE_DEBUG = False, True
    RequestCls = http.HttpRequest

    def __init__(self, action):
        super(HttpServer, self).__init__()
        self.action, self.timeout = action, 60

    def handler(self, sock):
        try:
            while True:
                request = self.RequestCls(sock)
                request.load_header()
                logging.debug(request.make_header())
                response = self.process_request(request)
                if response is None: break
                try:
                    if log.weblog: log.weblog.log_req(request, response)
                except: pass
                logging.debug(response.make_header())
                if not response.connection or self.BREAK_CONN: break
        finally: sock.close()

    def process_request(self, request):
        try:
            request.timeout = eventTimeout(self.timeout, base.TimeoutError)
            try: response = self.action(request)
            finally: request.timeout.cancel()
            if not response: response = request.make_response(500)
        except(EOFError, socket.error): return None
        except base.HttpException, err:
            response = self.err_handler(request, err, err.args[0])
        except Exception, err:
            response = self.err_handler(request, err)
        if not response: return None
        try: response.finish()
        except: return None
        return response

    tpl = template.Template(template = '<html><head><title>{%=res.phrase%}</title></head><body><h1>{%=code%} {%=res.phrase%}</h1><h3>{%=default_pages[code][1]%}</h3>{%if res_dbg:%}<br/>Debug Info:<br/>{%if len(err.args) > 1:%}{%="%s<br/>" % str(err.args[1:])%}{%end%}{%="<pre>%s</pre>" % debug_info%}{%end%}</body></html>')
    def err_handler(self, request, err, code = 500):
        if hasattr(request, 'responsed'): return None
        response = request.make_response(code)
        info = {'res': response, 'code': code, 'res_dbg': self.RESPONSE_DEBUG,
                'err': err, 'debug_info': ''.join(traceback.format_exc()),
                'default_pages': http.HttpResponse.DEFAULT_PAGES}
        self.tpl.render_res(response, info)
        return response
        
