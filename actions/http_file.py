#!/usr/bin/python
# -*- coding: utf-8 -*-
# @date: 20090921
# @author: shell.xu
from __future__ import with_statement
import os
import urllib
import logging
import datetime
from os import path
import webserver

class HttpFileAction (webserver.HttpAction):
    DEBUG = True
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
        return self.file_action (request, real_path)

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
            response.body_sended, response.connection = True, False
        return response
