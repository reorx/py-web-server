#!/usr/bin/python
# -*- coding: utf-8 -*-
# @date: 20090921
# @author: shell.xu
from __future__ import with_statement
import os
import sys
import stat
import datetime
from os import path
from http import *

class HttpFileAction (HttpAction):
    """ """
    from default_setting import MIME

    def __init__ (self, base_dir, show_directory = True,
                  index_set = ['index.htm', 'index.html']):
        """ """
        super (HttpFileAction, self).__init__ ();
        base_dir = path.expanduser (base_dir);
        self.base_dir = path.abspath (path.realpath (base_dir));
        self.show_directory = show_directory;
        self.index_set = index_set;

    def action (self, request):
        """ """
        real_path = path.join (self.base_dir, request.url_path.lstrip ("/"));
        real_path = path.abspath (path.realpath (real_path));
        if not real_path.startswith (self.base_dir):
            return request.make_response (403);
        if path.isdir (real_path):
            for index_file in self.index_set:
                test_path = path.join (real_path, index_file);
                if not os.access (test_path, os.R_OK): continue;
                real_path = test_path;
                break;
        if not os.access (real_path, os.R_OK): return request.make_response (404);
        if path.isdir (real_path): return self.dir_action (request, real_path);
        else: return self.file_action (request, real_path);

    def file_action (self, request, real_path):
        """ """
        file_stat = os.lstat (real_path);
        if "If-Modified-Since" in request:
            modify = request.get_http_date (request["If-Modified-Since"]);
            print modify;
            if modify <= file_stat.st_mtime:
                return request.make_response (304);
        response = request.make_response (200);
        response["Content-Length"] = os.stat (real_path)[6];
        response["Content-Type"] = HttpFileAction.MIME.get (
            path.splitext (real_path)[1], "text/html");
        response["Last-Modified"] = request.make_http_date (
            datetime.datetime.fromtimestamp (file_stat.st_mtime));
        response.response_message ();
        with open (real_path, "rb") as datafile:
            while True:
                data = datafile.read (4096);
                if len (data) == 0: break;
                response.append_content (data);
        return response;

    def get_stat_str (self, mode):
        """ """
        stat_str = "";
        if stat.S_ISDIR (mode): stat_str += "d";
        if stat.S_ISREG (mode): stat_str += "f";
        if stat.S_ISLNK (mode): stat_str += "l";
        if stat.S_ISSOCK (mode): stat_str += "s";
        return stat_str;

    header = '<html><head></head><body><table><thead>%s</thead><tbody>';
    title = '<tr><td>file name</td><td>file mode</td><td>file size</td></tr>';
    item = '<tr><td><a href="%s">%s</a></td><td>%s</td><td>%s</td></tr>';
    tail = "</tbody></table></body>";
    def dir_action (self, request, real_path):
        """ """
        if not self.show_directory: return request.make_response (404);
        response = request.make_response (200);
        response.append_content (HttpFileAction.header % HttpFileAction.title);
        for name in os.listdir (real_path):
            stat = os.lstat (path.join (real_path, name));
            response.append_content (
                HttpFileAction.item % 
                (path.join (request.url_path, name).replace (os.sep, "/"),
                 name, self.get_stat_str (stat.st_mode), stat.st_size));
        response.append_content (HttpFileAction.tail);
        return response;
