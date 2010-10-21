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
import datetime
from os import path
import base
import template

def get_stat_str(mode):
    stat_list = []
    if stat.S_ISDIR(mode): stat_list.append("d")
    if stat.S_ISREG(mode): stat_list.append("f")
    if stat.S_ISLNK(mode): stat_list.append("l")
    if stat.S_ISSOCK(mode): stat_list.append("s")
    return ''.join(stat_list)

class StaticFile(object):
    ''' 静态文件的处理类 '''
    DEBUG = False
    from default_setting import MIME
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

    def action(self, request):
        url_path = urllib.unquote(request.url_match['filepath'])
        real_path = path.join(self.base_dir, url_path.lstrip('/'))
        real_path = path.abspath(path.realpath(real_path))
        if not real_path.startswith(self.base_dir): raise base.HttpException(403)
        if self.DEBUG:
            print "StaticFile: %s requested and %s hit." % \
                (request.urls.path, real_path)
        if path.isdir(real_path):
            return self.dir_action(request, url_path, real_path)
        else: return self.file_action(request, real_path)

    def file_action(self, request, real_path):
        if not os.access(real_path, os.R_OK):
            raise base.NotFoundError(real_path)
        file_stat = os.lstat(real_path)
        if "If-Modified-Since" in request:
            modify = request.get_http_date(request["If-Modified-Since"])
            if modify <= datetime.datetime.fromtimestamp(file_stat.st_mtime):
                raise base.HttpException(304)
        response = request.make_response()
        response["Content-Type"] = self.MIME.get(
            path.splitext(real_path)[1], "text/html")
        response["Last-Modified"] = request.make_http_date(
            datetime.datetime.fromtimestamp(file_stat.st_mtime))
        if file_stat.st_size < self.PIPE_LENGTH:
            with open(real_path, "rb") as datafile:
                response.append_body(datafile.read())
        else:
            response["Content-Length"] = os.stat(real_path)[6]
            response.send_header()
            with open(real_path, "rb") as datafile:
                while True:
                    data = datafile.read(4096)
                    if len(data) == 0: break
                    response.send_one_body(data)
            response.body_sended = True
        response.connection = False
        return response

    tpl = template.Template(template = '{%import os%}{%from os import path%}<html><head></head><body><table><thead><tr><td>file name</td><td>file mode</td><td>file size</td></tr></thead><tbody>{%for name in namelist:%}{%stat_info = os.lstat(path.join(real_path, name))%}<tr><td><a href="{%=path.join(url_path, name).replace(os.sep, "/")%}">{%=name%}</a></td><td>{%=get_stat_str(stat_info.st_mode)%}</td><td>{%=stat_info.st_size%}</td></tr>{%end%}</tbody></table></body>')
    def dir_action(self, request, url_path, real_path):
        for index_file in self.index_set:
            test_path = path.join(real_path, index_file)
            if os.access(test_path, os.R_OK):
                return self.file_action(request, test_path)
        if not self.show_directory: raise base.NotFoundError(real_path)
        if not os.access(real_path, os.X_OK): raise base.NotFoundError(real_path)
        response = request.make_response()
        namelist = os.listdir(real_path)
        namelist.sort()
        info = {'namelist': namelist, 'get_stat_str': get_stat_str,
                'real_path': real_path, 'url_path': url_path}
        self.tpl.render_res(response, info)
        response.connection = False
        # TODO: response.cache = 300
        return response
