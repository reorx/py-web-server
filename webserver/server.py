#!/usr/bin/python
# -*- coding: utf-8 -*-
# @date: 2010-06-04
# @author: shell.xu
from __future__ import with_statement
import os
import copy
import socket
import eventlet
import traceback
from eventlet.timeout import Timeout as eTimeout
import base
import log
import http

class TcpEventletServer (base.TcpServer):

    def fork_server (self):
        with open ("/proc/cpuinfo", "r") as cpu_file:
            cpuinfo = cpu_file.readlines ()
        cpunum = len (filter (lambda x: x.startswith ("processor"), cpuinfo))
        for i in xrange (0, cpunum - 1):
            if os.fork () == 0: break

    def listen (self, addr = '0.0.0.0', port = 8000, poolsize = 1000, **kargs):
        self.laddr = (addr, port)
        self.sock = eventlet.listen(self.laddr)
        if kargs.get ('reuse', True):
            self.sock.setsockopt (socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.pool = eventlet.GreenPool (poolsize)

    def do_loop (self):
        new_server = copy.copy (self)
        new_server.loop_func = new_server.do_process
        new_server.sock, new_server.from_addr = self.sock.accept ()
        new_server.gthread = self.pool.spawn (new_server.run)
        return True

    @staticmethod
    def pump_one (s, t, counter, n):
        try:
            while True:
                d = s.recv_once ()
                if counter: counter[n] += len (d)
                t.sendall (d)
        except (EOFError, socket.error): pass

    def pump (self, flows, threads, counter):
        if len (flows) == 0: return
        tmpth, spawn = [], eventlet.greenthread.spawn
        for s, t, n in flows[:-1]:
            th = spawn (self.pump_one, s, t, counter, n)
            tmpth.append (th)
            threads.append (th)
        self.pump_one (flows[-1][0], flows[-1][1], counter, flows[-1][2])
        for th in tmpth:
            th.wait ()
            threads.remove (th)

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
        try: response.finish ()
        except (EOFError, socket.error): return False
        except Exception:
            print traceback.format_exc ()
            return False
        try:
            log.log.action (request, response)
            if self.DEBUG: print response.make_header ()
        except: pass
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
