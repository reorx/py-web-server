#!/usr/bin/python
# -*- coding: utf-8 -*-
# @date: 2010-06-04
# @author: shell.xu
from __future__ import with_statement
import copy
import socket
import eventlet
import traceback
from eventlet.timeout import Timeout as eTimeout
import base
import log
import http

class TcpEventletServer (base.TcpServer):

    # FIXME: 代码还不正确
    @staticmethod
    def fork_server (fork_param = None):
        if fork_param == None:
            fork_param = TcpServerBase.get_cpu_num
        if callable (fork_param):
            fork_param = fork_param ()
        for i in xrange (0, fork_param - 1):
            if os.fork () == 0:
                break

    @staticmethod
    def get_cpu_num ():
        with open ("/proc/cpuinfo", "r") as cpu_file:
            return len (filter (lambda x: x.startswith ("processor"),
                                cpu_file.readlines ()))

    def listen (self, addr = '0.0.0.0', port = 8000):
        self.laddr = (addr, port)
        self.sock = eventlet.listen((addr, port))
        self.sock.setsockopt (socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.pool = eventlet.GreenPool (1000)

    def do_loop (self):
        new_server = copy.copy (self)
        new_server.loop_func = new_server.do_process
        new_server.sock, new_server.from_addr = self.sock.accept ()
        new_server.gthread = self.pool.spawn (new_server.run)
        return True

    @staticmethod
    def pump_one (s, t, obj, n):
        try:
            while True:
                d = s.recv_once ()
                if obj: obj[n] += len (d)
                t.sendall (d)
        except (EOFError, socket.error): pass

    @staticmethod
    def pump (flows, req, obj):
        threads, spawn = [], eventlet.greenthread.spawn
        for s, t, n in flows:
            th = spawn (TcpEventletServer.pump_one, s, t, obj, n)
            threads.append (th)
            req.threads.append (th)
        for th in threads:
            th.wait ()
            req.threads.remove (th)

class TcpEventletClient (base.TcpClient):

    def connect (self, hostname, **kargs):
        hostinfo = hostname.partition (':')
        port = int (hostinfo[2]) if len (hostinfo[1]) != 0 else 80
        self.sock = eventlet.connect ((hostinfo[0], port))

class EventletConnPool (object):

    def __init__ (self, factory = TcpEventletClient, kargs = None,
                  max_conn = 100, max_keep = 10, keep_time = 60):
        self.factory, self.kargs = factory, kargs
        if self.kargs is None: self.kargs = {}
        self.max_conn, self.max_keep = max_conn, max_keep
        self.keep_time, self.timer, self.keep = keep_time, None, []
        self.counter = eventlet.semaphore.Semaphore (self.max_conn)

    def acquire (self, hostname):
        self.counter.acquire ()
        if len (self.keep) != 0: conn = self.keep.pop (0)
        else:
            conn = self.factory ()
            conn.connect (hostname, **self.kargs)
        return conn

    def release (self, sock, force):
        if len (self.keep) >= self.max_keep or force: sock.final ()
        else: self.keep.append (sock)
        self.counter.release ()

class HttpServer (TcpEventletServer):
    DEBUG, RESPONSE_DEBUG = False, True

    def __init__ (self, action, **kargs):
        super (HttpServer, self).__init__ (**kargs)
        self.action = action
        self.timeout = 60

    def do_process (self):
        request = http.HttpRequest ([self,])
        try:
            with eTimeout (self.timeout, base.TimeoutError) as timeout:
                request.timeout = timeout
                request.load_header ()
                if self.DEBUG: print request.make_header ()
                response = self.action.action (request)
                if response == None: response = request.make_response (500)
        except (EOFError, socket.error): return False
        except base.HttpException, err:
            response = self.err_handler (request, err, err.args[0])
            if response is None: return False
        except Exception, err:
            response = self.err_handler (request, err)
            if response is None: return False
            print traceback.format_exc ()
        try:
            log.log.action (request, response)
            if self.DEBUG: print response.make_header ()
        except: pass
        try: response.finish ()
        except (EOFError, socket.error): return False
        except Exception:
            print traceback.format_exc ()
            return False
        return response.connection
    
    def err_handler (self, request, err, code = 500):
        if hasattr (request, 'response') and\
                request.response.header_sended:
            return None
        else: response = request.make_response (code)
        info = (response.phrase, code, response.phrase,
                http.HttpResponse.DEFAULT_PAGES[code][1])
        response.append_body ('<html><head><title>%s</title></head>\
<body><h1>%d %s</h1><h3>%s</h3>' % info)
        if self.RESPONSE_DEBUG:
            response.append_body ('<br/>Debug Info:<br/>')
            if len (err.args) > 1:
                response.append_body ('%s<br/>' % str (err.args[1:]))
            debug_info = ''.join (traceback.format_exc ())
            response.append_body ('<pre>%s</pre>' % debug_info)
        response.append_body ('</body></html>')
        return response
