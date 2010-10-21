#!/usr/bin/python
# -*- coding: utf-8 -*-
'''
@date: 2010-10-21
@author: shell.xu
'''
from __future__ import with_statement
import os
import re
import stat
import urllib
import logging
import datetime
import traceback
from os import path
import base
import http
import template

class Cookie(object):

    def __init__(self, cookie):
        if not cookie: self.v = {}
        else: self.v = http.get_params_dict(cookie, ';')
        self.m = set()

    def get(self, k, d): return self.v.get(k, d)
    def __contains__(self, k): return k in self.v
    def __getitem__(self, k): return self.v[k]
    def __delitem__(self, k):
        self.m.add(k)
        del self.v[k]
    def __setitem__(self, k, v):
        self.m.add(k)
        return self.v[k] = v

    def set_cookie(self):
        rslt = []
        for k in self.m: rslt.append('%s=%s' % (k, urllib.quote(self.v[k])))
        return ';'.join(rslt)

class MemcacheSession(object):

    def __init__(self, mc, action = None):
        self.mc, self.action = mc, action

    def __call__(self, request, *params):
        request.cookie = Cookie(request.header.get('Cookie', ''))
        sessionid = request.cookie.get('sessionid', '')
        if sessionid:
            self.mc.get('session:%s' % sessionid)
            # load session
        else:
            request.cookie['sessionid'] = 'random id'
            # init session
        if self.action: response = self.action(request, *params)
        else: response = params[0](request, *params[1:])
        response.header['Set-Cookie'] = request.cookie.set_cookie()
