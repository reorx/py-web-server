#!/usr/bin/python
# -*- coding: utf-8 -*-
'''
@date: 2010-09-27
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
import simplejson as json
from os import path
import base
import http
import template

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
        ])
    '''

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

class TemplateFile(object):
    '''
    模板自动生成系统，将指定目录下的所有文件自动进行模板泛化编译。
    例子：
        ['^/html/(?P<filepath>.*)', pyweb.TemplateFile('~/tpl/')],
    '''

    def __init__(self, base_dir):
        ''' @param base_dir: 指定根路径 '''
        base_dir = path.expanduser(base_dir)
        self.base_dir = path.abspath(path.realpath(base_dir))
        self.cache = {}

    def __call__(self, request, *param):
        url_path = urllib.unquote(request.url_match['filepath'])
        real_path = path.join(self.base_dir, url_path.lstrip('/'))
        real_path = path.abspath(path.realpath(real_path))
        if not real_path.startswith(self.base_dir) or not path.isfile(real_path):
            raise base.HttpException(403)
        if real_path not in self.cache:
            self.cache[real_path] = template.Template(filepath = real_path)
            # print self.cache[real_path].tc.get_code()

        query_info = http.get_params_dict(request.urls.query)
        funcname = query_info.get('func', None)
        if funcname:
            funcobj = self.cache[real_path].defcodes.get(funcname, None)
            if not funcobj: raise NotFoundError()
            response = J(request, funcobj, *param)
        else:
            response = request.make_response()
            info = {'request': request, 'response': response, 'param': param}
            self.cache[real_path].render_res(response, info)
        return response
