#!/usr/bin/python
# -*- coding: utf-8 -*-
# @date: 2009-09-21
# @author: shell.xu
from __future__ import with_statement
import os
import stat
import urllib
import datetime
from os import path
import webserver

class HttpFileAction (webserver.HttpAction):
    DEBUG = False
    MIME = webserver.default_setting.MIME
    PIPE_LENGTH = 512 * 1024

    def __init__ (self, base_dir):
        super (HttpFileAction, self).__init__ ()
        base_dir = path.expanduser (base_dir)
        self.base_dir = path.abspath (path.realpath (base_dir))

    def action (self, request):
        url_path = urllib.unquote (request.urls['path'])
        real_path = path.join (self.base_dir, url_path.lstrip ('/'))
        real_path = path.abspath (path.realpath (real_path))
        if not real_path.startswith (self.base_dir):
            raise webserver.HttpException (403)
        if self.DEBUG: print "%s requested and %s %s hit." %\
                (request.urls['path'], type (self), real_path)
        if not path.isdir (real_path): return self.file_action (request, real_path)
        if hasattr (self, 'dir_action'): return self.dir_action (request, real_path)
        raise webserver.NotAcceptableError (real_path)

    def file_action (self, request, real_path):
        if not os.access (real_path, os.R_OK):
            raise webserver.NotFoundError (real_path)
        file_stat = os.lstat (real_path)
        if "If-Modified-Since" in request:
            modify = request.get_http_date (request["If-Modified-Since"])
            if modify <= datetime.datetime.fromtimestamp (file_stat.st_mtime):
                raise webserver.HttpException (304)
        response = request.make_response ()
        response["Content-Type"] = self.MIME.get (
            path.splitext (real_path)[1], "text/html")
        response["Last-Modified"] = request.make_http_date (
            datetime.datetime.fromtimestamp (file_stat.st_mtime))
        if file_stat.st_size < self.PIPE_LENGTH:
            # TODO: response.cache = 300
            with open (real_path, "rb") as datafile:
                response.append_body (datafile.read ())
        else:
            response["Content-Length"] = os.stat (real_path)[6]
            response.send_header ()
            with open (real_path, "rb") as datafile:
                while True:
                    data = datafile.read (4096)
                    if len (data) == 0: break
                    response.send_one_body (data)
            response.body_sended = True
        response.connection = False
        return response

class HttpDirectoryAction (HttpFileAction):
    DEFAULT_INDEX_SET = ['index.htm', 'index.html']

    def __init__ (self, base_dir, show_directory = True, index_set = None):
        super (HttpDirectoryAction, self).__init__ (base_dir)
        self.show_directory = show_directory
        if index_set is not None: self.index_set = index_set
        else: self.index_set = self.DEFAULT_INDEX_SET

    @staticmethod
    def get_stat_str (mode):
        stat_list = []
        if stat.S_ISDIR (mode): stat_list.append ("d")
        if stat.S_ISREG (mode): stat_list.append ("f")
        if stat.S_ISLNK (mode): stat_list.append ("l")
        if stat.S_ISSOCK (mode): stat_list.append ("s")
        return ''.join (stat_list)

    header = '<html><head></head><body><table><thead>%s</thead><tbody>'
    title = '<tr><td>file name</td><td>file mode</td><td>file size</td></tr>'
    item = '<tr><td><a href="%s">%s</a></td><td>%s</td><td>%s</td></tr>'
    tail = '</tbody></table></body>'
    def dir_action (self, request, real_path):
        if not path.isdir (real_path): return self.file_action (request, real_path)
        for index_file in self.index_set:
            test_path = path.join (real_path, index_file)
            if os.access (test_path, os.R_OK):
                return self.file_action (request, test_path)
        if not self.show_directory: raise webserver.NotFoundError (real_path)
        if not os.access (real_path, os.X_OK):
            raise webserver.NotFoundError (real_path)
        response = request.make_response ()
        response.append_body (self.header % self.title)
        namelist = os.listdir (real_path)
        namelist.sort ()
        for name in namelist:
            stat_info = os.lstat (path.join (real_path, name))
            response.append_body (self.item % (
                    path.join (request.urls['path'], name).replace (os.sep, "/"),
                    name, self.get_stat_str (stat_info.st_mode), stat_info.st_size))
        response.append_body (self.tail)
        response.connection = False
        # TODO: response.cache = 300
        return response
