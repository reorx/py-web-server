#!/usr/bin/python
# -*- coding: utf-8 -*-
'''
@date: 2010-09-27
@author: shell.xu
'''
from __future__ import with_statement
import os
import re
import logging
import traceback
import simplejson as json
import base

def J(request, func, *params):
    ''' JSON对象的包装，将请求解析为一个JSON对象，调用被包装函数
    将返回生成JSON，并填写到响应对象中。
    配置例子：['^/def.*', pyweb.J, test_json]
    代码：
    def test_json(request, json):
        li = []
        for i in xrange(1, 100): li.append(random.randint(0, 100))
        return li
    '''
    try:
        post = request.post_params()
        obj = func(request, post, *params)
        if obj is None: code, content = 500, 'function return None'
        else: code, content = 200, json.dumps(obj)
    except Exception, err:
        logging.error(''.join(traceback.format_exc()))
        code, content = 500, str(err)
    response = request.make_response(code)
    response.append_body(content)
    return response

def redirect(request, url, *params):
    ''' 重定向函数
    配置例子：['^/def.*', pyweb.redirect, '/abc']'''
    return request.make_redirect(url)

class Dispatch(object):
    ''' 分派器对象，根据正则，找到合适的处理程序对客户请求进行处理。
    例子：dispatch = pyweb.Dispatch([
        ['^/json/list_money.*', pyweb.J, list_money],
        ['^/json/add_money.*', pyweb.J, add_money],
        ['.*', hello_kitty],
        ]) '''

    def __init__(self, urlmap = None):
        '''
        @param urlmap: 一个多个映射关系组成的列表，以从前向后的次序进行匹配，每项规则包括多个内容。
        	第一项是url正则规则，如果是字符串会自动进行re编译。
                第二项是处理程序，如果有action成员自动调用action成员（调用传递），如果没有action成员，则直接调用。
                其余项目会作为处理程序的参数传入，re匹配的groupdict会作为字典参数传入。
        '''
        self.urlmap = []
        if urlmap: self.urlmap = map(self.re_url_obj, urlmap)

    def re_url_obj(self, obj):
        if isinstance(obj[0], (str, unicode)): obj[0] = re.compile(obj[0])
        return obj
    
    def func_wrapper(self, url, *args):
        def get_func(func):
            self.urlmap.append([re.compile(url), func] + args)
            return func
        return get_func

    def json_wrapper(self, url, *args):
        def get_func(func):
            self.urlmap.append([re.compile(url), J, func] + args)
            return func
        return get_func

    def __call__(self, request):
        for obj in self.urlmap:
            m = obj[0].match(request.urls.path)
            if not m: continue
            request.url_match = m.groupdict()
            return obj[1](request, *obj[2:])
        raise base.NotFoundError()

class Cache(object):

    def __init__(self, action = None): self.action = action
    def __call__(self, request, *params):
        pd = self.get_data(request.urls.path)
        if pd:
            response = request.make_response()
            response.unpack(pd)
            return response
        if self.action: response = self.action(request, *params)
        else: response = params[0](request, *params[1:])
        if response and response.cache is not None:
            pd = response.pack()
            self.set_data(request.urls.path, pd, response.cache)
        return response

class MemcacheCache(Cache):

    def __init__(self, mc, action = None):
        super(MemcacheCache, self).__init__(action)
        self.mc = mc
    def get_data(self, k):
        f, data = self.mc.get('cache:' + k)
        return data
    def set_data(self, k, v, exp): self.mc.set('cache:' + k, v, exp = exp)
