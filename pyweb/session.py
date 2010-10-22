#!/usr/bin/python
# -*- coding: utf-8 -*-
'''
@date: 2010-10-21
@author: shell.xu
'''
from __future__ import with_statement
import urllib
import random
import cPickle
from os import path
import basehttp

random.seed()
alpha = '0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ+/'
def get_rnd_sess(): return ''.join(random.sample(alpha, 32))

class Cookie(object):

    def __init__(self, cookie):
        ''' 解析数据，建立cookie '''
        if not cookie: self.v = {}
        else: self.v = basehttp.get_params_dict(cookie, ';')
        self.m = set()

    def get(self, k, d): return self.v.get(k, d)
    def __contains__(self, k): return k in self.v
    def __getitem__(self, k): return self.v[k]
    def __delitem__(self, k):
        self.m.add(k)
        del self.v[k]
    def __setitem__(self, k, v):
        self.m.add(k)
        self.v[k] = v

    def set_cookie(self):
        ''' 生成适合http多重头部格式的cookie数据 '''
        rslt = []
        for k in self.m: rslt.append('%s=%s' % (k, urllib.quote(self.v[k])))
        return rslt

class Session(object):

    def __init__(self, timeout, action = None):
        self.action, self.exp = action, timeout

    def __call__(self, request, *params):
        request.cookie = Cookie(request.header.get('cookie', None))
        sessionid = request.cookie.get('sessionid', '')
        if not sessionid:
            sessionid = get_rnd_sess()
            request.cookie['sessionid'] = sessionid
            data = None
        else: data = self.get_data(sessionid)
        if not data: request.session = {}
        else: request.session = cPickle.loads(data)
        if self.action: response = self.action(request, *params)
        else: response = params[0](request, *params[1:])
        self.set_data(sessionid, cPickle.dumps(request.session, 2))
        set_cookie = request.cookie.set_cookie()
        if set_cookie: response.header['Set-Cookie'] = set_cookie
        return response

class MemcacheSession(Session):
    ''' Session的Memcache实现，根据cookie内的sessionid来读写memcache内数据
    可以作为action使用，或者作为映射包装器。action首先作用。
    例子：
        mc = pyweb.Memcache()
        mc.add_server('localhost')
    action例子：
        dispatch = pyweb.Dispatch(...)
        action = pyweb.MemcacheSession(mc, 300, dispatch)
    映射包装器例子：
        sess = pyweb.MemcacheSession(mc, 300)
        dispatch = pyweb.Dispatch([ ['.*', sess, hello_kitty], ]) '''

    def __init__(self, mc, timeout, action = None):
        super(MemcacheSession, self).__init__(timeout, action)
        self.mc = mc

    def get_data(self, sessionid):
        f, data = self.mc.get('sess:%s' % sessionid)
        return data

    def set_data(self, sessionid, data):
        self.mc.set('sess:%s' % sessionid, data, exp = self.exp)

class MongoSession(Session):

    def __init__(self, conn, timeout, action = None):
        super(MemcacheSession, self).__init__(timeout, action)
        self.conn = conn

    # TODO: Monge未实现
    def get_data(self, sessionid):
        f, data = self.mc.get('sess:%s' % sessionid)
        return data

    def set_data(self, sessionid, data):
        self.mc.set('sess:%s' % sessionid, data, exp = self.exp)
