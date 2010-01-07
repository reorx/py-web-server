#!/usr/bin/python
# -*- coding: utf-8 -*-
# @date: 2010-01-03
# @author: shell.xu
from __future__ import with_statement
import os
import sys
import stat
import webserver
import http_file
from os import path

class HttpDirectoryAction (http_file.HttpFileAction):
    """ """
    DEFAULT_INDEX_SET = ['index.htm', 'index.html']

    def __init__ (self, base_dir, show_directory = True, index_set = None):
        """ """
        super (HttpDirectoryAction, self).__init__ (base_dir)
        self.show_directory = show_directory
        if index_set == None:
            index_set = self.DEFAULT_INDEX_SET
        self.index_set = index_set

    @staticmethod
    def get_stat_str (mode):
        """ """
        stat_str = ""
        if stat.S_ISDIR (mode):
            stat_str += "d"
        if stat.S_ISREG (mode):
            stat_str += "f"
        if stat.S_ISLNK (mode):
            stat_str += "l"
        if stat.S_ISSOCK (mode):
            stat_str += "s"
        return stat_str

    header = '<html><head></head><body><table><thead>%s</thead><tbody>'
    title = '<tr><td>file name</td><td>file mode</td><td>file size</td></tr>'
    item = '<tr><td><a href="%s">%s</a></td><td>%s</td><td>%s</td></tr>'
    tail = "</tbody></table></body>"
    def file_action (self, request, real_path):
        """ """
        parent_action = super (HttpDirectoryAction, self).file_action
        if not path.isdir (real_path):
            return parent_action (request, real_path)
        for index_file in self.index_set:
            test_path = path.join (real_path, index_file)
            if os.access (test_path, os.R_OK):
                return parent_action (request, test_path)
        if not self.show_directory:
            return request.make_response (404)
        if not os.access (real_path, os.X_OK):
            return request.make_response (404)
        response = request.make_response (200)
        response.append_content (self.header % self.title)
        for name in os.listdir (real_path):
            stat_info = os.lstat (path.join (real_path, name))
            response.append_content (self.item % (
                    path.join (request.url_path, name).replace (os.sep, "/"),
                    name, self.get_stat_str (stat_info.st_mode),
                    stat_info.st_size))
        response.append_content (self.tail)
        response.connection = False
        response.cache = 300
        return response
