#!/usr/bin/python
# -*- coding: utf-8 -*-
'''
@date: 2010-09-27
@author: shell.xu
'''
from __future__ import with_statement
import os
import stat
import urllib
import logging
from os import path
from datetime import datetime
import basehttp
import template
import apps

def get_stat_str(mode):
    stat_list = []
    if stat.S_ISDIR(mode): stat_list.append("d")
    if stat.S_ISREG(mode): stat_list.append("f")
    if stat.S_ISLNK(mode): stat_list.append("l")
    if stat.S_ISSOCK(mode): stat_list.append("s")
    return ''.join(stat_list)

def calc_path(filepath, base_dir):
    url_path = urllib.unquote(filepath)
    real_path = path.join(base_dir, url_path.lstrip('/'))
    real_path = path.abspath(path.realpath(real_path))
    if not real_path.startswith(base_dir): raise basehttp.HttpException(403)
    return url_path, real_path

class StaticFile(object):
    ''' 静态文件的处理类 '''
    MIME = basehttp.MIME
    PIPE_LENGTH = 512 * 1024
    DEFAULT_INDEX_SET = ['index.htm', 'index.html']

    def __init__(self, base_dir, show_directory = True, index_set = None):
        '''
        @param base_dir: 指定根路径
        @param show_directory: 如果为True，则当请求一个目录的时候，列出目录
        @param index_set: 默认index文件名
        '''
        base_dir = path.expanduser(base_dir)
        self.base_dir = path.abspath(path.realpath(base_dir))
        self.show_directory = show_directory
        if index_set: self.index_set = index_set
        else: self.index_set = self.DEFAULT_INDEX_SET

    def __call__(self, request):
        url_path, real_path = calc_path(request.url_match['filepath'], self.base_dir)
        logging.debug("StaticFile: %s requested and %s hit." % \
                          (request.urls.path, real_path))
        if path.isdir(real_path):
            return self.dir_app(request, url_path, real_path)
        else: return self.file_app(request, real_path)

    def file_app(self, request, real_path):
        if not os.access(real_path, os.R_OK):
            raise basehttp.NotFoundError(real_path)
        file_stat = os.lstat(real_path)
        modify = request.get_header("if-modified-since")
        if modify:
            modify = basehttp.get_http_date(modify)
            if modify <= datetime.fromtimestamp(file_stat.st_mtime):
                raise basehttp.HttpException(304)
        response = request.make_response()
        content_type = self.MIME.get(path.splitext(real_path)[1], "text/html")
        response.set_header("content-type", content_type)
        modify = basehttp.make_http_date(datetime.fromtimestamp(file_stat.st_mtime))
        response.set_header("last-modified", modify)
        if file_stat.st_size < self.PIPE_LENGTH:
            with open(real_path, "rb") as datafile:
                response.append_body(datafile.read())
            response.cache = 300
        else:
            response.set_header("content-length", os.stat(real_path)[6])
            response.send_header()
            with open(real_path, "rb") as datafile:
                while True:
                    data = datafile.read(4096)
                    if len(data) == 0: break
                    response.send_body(data)
            response.body_sended = True
        response.connection = False
        return response

    tpl = template.Template(template = '{%import os%}{%from os import path%}<html><head><meta http-equiv="Content-Type" content="text/html; charset=utf-8"/></head><body><table><thead><tr><td>file name</td><td>file mode</td><td>file size</td></tr></thead><tbody>{%for name in namelist:%}{%name=name.decode("utf-8")%}{%stat_info = os.lstat(path.join(real_path, name))%}<tr><td><a href="{%=path.join(url_path, name).replace(os.sep, "/")%}">{%=name%}</a></td><td>{%=get_stat_str(stat_info.st_mode)%}</td><td>{%=stat_info.st_size%}</td></tr>{%end%}</tbody></table></body>')
    def dir_app(self, request, url_path, real_path):
        for index_file in self.index_set:
            test_path = path.join(real_path, index_file)
            if os.access(test_path, os.R_OK):
                return self.file_app(request, test_path)
        if not self.show_directory: raise basehttp.NotFoundError(real_path)
        if not os.access(real_path, os.X_OK): raise basehttp.NotFoundError(real_path)
        response = request.make_response()
        namelist = os.listdir(real_path)
        namelist.sort()
        info = {'namelist': namelist, 'get_stat_str': get_stat_str,
                'real_path': real_path, 'url_path': url_path}
        response.append_body(self.tpl.render(info))
        response.connection = False
        response.cache = 300
        return response

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
        url_path, real_path = calc_path(request.url_match['filepath'], self.base_dir)
        if not path.isfile(real_path): raise basehttp.HttpException(403)
        if real_path not in self.cache:
            self.cache[real_path] = template.Template(filepath = real_path)
        else: self.cache[real_path].reload(real_path)
        tplfile = self.cache[real_path]

        query_info = basehttp.get_params_dict(request.urls.query)
        funcname = query_info.get('func', None)
        if funcname:
            funcobj = tplfile.defcodes.get(funcname, None)
            if not funcobj: raise basehttp.NotFoundError()
            response = apps.J(request, funcobj, *param)
        else:
            response = request.make_response()
            info = {'request': request, 'response': response, 'param': param}
            response.append_body(tplfile.render(info))
        return response
