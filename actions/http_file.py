#!/usr/bin/python
# -*- coding: utf-8 -*-
# @date: 20090921
# @author: shell.xu
from __future__ import with_statement
import os
import logging
import datetime
from os import path
import webserver

class HttpFileAction (webserver.HttpAction):
    """ """
    MIME = webserver.default_setting.MIME
    PIPE_LENGTH = 512 * 1024

    def __init__ (self, base_dir):
        """ """
        super (HttpFileAction, self).__init__ ()
        base_dir = path.expanduser (base_dir)
        self.base_dir = path.abspath (path.realpath (base_dir))

    def action (self, request):
        """ """
        real_path = path.join (self.base_dir,
                               request.url_unquoted_path.lstrip ("/"))
        real_path = path.abspath (path.realpath (real_path))
        if not real_path.startswith (self.base_dir):
            return request.make_response (403)
        logging.debug ("%s requested and %s %s hit." %\
                           (request.url_path, type (self), real_path))        
        return self.file_action (request, real_path)

    def file_action (self, request, real_path):
        ''' '''
        if not os.access (real_path, os.R_OK):
            return request.make_response (404)
        file_stat = os.lstat (real_path)
        if "If-Modified-Since" in request:
            modify = request.get_http_date (request["If-Modified-Since"])
            if modify <= datetime.datetime.fromtimestamp (file_stat.st_mtime):
                return request.make_response (304)
        response = request.make_response (200)
        response["Content-Type"] = self.MIME.get (
            path.splitext (real_path)[1], "text/html")
        response["Last-Modified"] = request.make_http_date (
            datetime.datetime.fromtimestamp (file_stat.st_mtime))
        if file_stat.st_size < self.PIPE_LENGTH:
            response.cache = 300
            with open (real_path, "rb") as datafile:
                response.set_content (datafile.read ())
        else:
            self.do_file_pipe (request, real_path, response)
        return response

    def do_file_pipe (self, request, real_path, response):
        ''' '''
        response["Content-Length"] = os.stat (real_path)[6]
        response.send_response (generate_header = False)
        response.connection = False
        with open (real_path, "rb") as datafile:
            while True:
                data = datafile.read (4096)
                if len (data) == 0:
                    break
                response.append_content (data)
