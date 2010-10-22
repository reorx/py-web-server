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

def test_json(request, json):
    if 'count' not in request.session: request.session['count'] = 0
    else: request.session['count'] += 1
    li = [request.session['count'],]
    for i in xrange(1, 100): li.append(random.randint(0, 100))
    return li

mc = pyweb.Memcache()
mc.add_server('localhost')
sess = pyweb.MemcacheSession(mc, 300)

dis = pyweb.Dispatch([
        ['^/pyweb/files/(?P<filepath>.*)', pyweb.StaticFile('~/')],
        ['^/pyweb/tpl/(?P<filepath>.*)', pyweb.TemplateFile('.')],
        ['^/pyweb/.*', sess, pyweb.J, test_json],
        ])

def main():
    logging.basicConfig(level = logging.DEBUG)
    if len(sys.argv) > 1 and sys.argv[1] == 'fastcgi':
        serve = pyweb.FastCGIServer(dis)
        # serve.listen_unix('test.sock', reuse = True)
        serve.listen(reuse = True)
    else:
        serve = pyweb.HttpServer(dis)
        serve.listen(reuse = True)
    try: serve.run()
    except KeyboardInterrupt: print 'exit.'

if __name__ == '__main__': main()
