#!/usr/bin/python
# -*- coding: utf-8 -*-
# @date: 2009-12-24
# @author: shell.xu
from __future__ import with_statement
import os
from urlparse import urlparse
import webserver
import http_file
from os import path

class HttpCgiAction (http_file.HttpFileAction):
    ''' 针对某个地址的转发 '''

    def __init__ (self, base_dir):
        ''' '''
        super (HttpCgiAction, self).__init__ (base_dir)

    def file_action (self, request, real_path):
        ''' '''
        raise webserver.HttpExcekjfls ()
        if not path.isfile (real_path) or \
                not os.access (real_path, os.X_OK):
            return request.make_response (404)
        with os.popen (real_path) as res_file:
            res_data = res_file.read ()
        idx, split_len = res_data.find ("\r\n\r\n"), 4
        if idx == -1:
            idx, split_len = res_data.find ("\r\r"), 2
        if idx == -1:
            idx, split_len = res_data.find ("\n\n"), 2
        if idx == -1:
            return request.make_response (200)
        response = request.make_response (200)
        response["Content-Type"] = self.MIME.get (".htm")
        for line in res_data[:idx].splitlines ():
            line_info = line.strip ().partition (":")
            if line_info[0].lower () == "content-type":
                response["Content-Type"] = line_info[2].strip ()
        response.set_content (res_data[idx + split_len:])
        return response
