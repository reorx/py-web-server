#!/usr/bin/python
# -*- coding: utf-8 -*-
'''
@date: 2010-06-04
@author: shell.xu
'''
import sys
import logging
import traceback
import random
import pyweb

def test_json(request, post):
    if 'count' not in request.session: request.session['count'] = 0
    else: request.session['count'] += 1
    li = [request.session['count'],]
    for i in xrange(1, 100): li.append(random.randint(0, 100))
    return li

def test_post(request):
    request.recv_body()
    print 'client send:', request.get_body()
    response = request.make_response()
    response.append_body('client send: %s' % request.get_body())
    return response

mc = pyweb.Memcache()
mc.add_server('localhost')
sess = pyweb.MemcacheSession(mc, 300)

dis = pyweb.Dispatch([
        ['^/pyweb/files/(?P<filepath>.*)', pyweb.StaticFile('~/')],
        ['^/pyweb/tpl/(?P<filepath>.*)', pyweb.TemplateFile('.')],
        ['^/pyweb/post.*', test_post],
        ['^/pyweb/.*', sess, pyweb.J, test_json],
        ])
# dis = pyweb.MemcacheCache(mc, dis)
dis = pyweb.MemoryCache(20, dis)

def main(fastcgi = False, unix_sock = False, daemon = True):
    pyweb.set_log()
    if fastcgi: serve = pyweb.FastCGIServer(dis)
    else: serve = pyweb.HttpServer(dis)
    if daemon:
        daemon = pyweb.Daemon(serve)
        daemon.lock_pidfile('test.pid')
        try:
            if unix_sock: serve.listen_unix('test.sock', reuse = True)
            else: serve.listen(reuse = True)
            try: daemon.run()
            except KeyboardInterrupt: print 'exit.'
        finally: daemon.free_pidfile()
    else:
        if unix_sock: serve.listen_unix('test.sock', reuse = True)
        else: serve.listen(reuse = True)
        try: serve.run()
        except KeyboardInterrupt: print 'exit.'

if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] == 'fastcgi': fastcgi = True
    else: fastcgi = False
    main(fastcgi, daemon = False)
