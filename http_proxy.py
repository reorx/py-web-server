#!/usr/bin/python
# -*- coding: utf-8 -*-
# @date: 2009-12-24
# @author: shell.xu
from __future__ import with_statement
from urlparse import urlparse
from http import *

class HttpForard (HttpAction):
    ''' 针对某个地址的转发 '''

    # 分服务器长连接，比较困难
    # 不分服务器，每个地址一连接，很容易，效率低下
    def __init__ (self, target):
        ''' '''
        self.target = target;

    def action (self, request):
        ''' '''
        fwd_req = copy.copy (request);
        return request.make_response (200);

class HttpPorxy (HttpAction):
    ''' 针对协议的代理行为，一般要求是主action '''

    def __init__ (self):
        ''' '''
        pass

    def action (self, request):
        ''' '''
        return request.make_response (200);
