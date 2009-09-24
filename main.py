#!/usr/bin/python
# -*- coding: utf-8 -*-
# @date: 20090921
# @author: shell.xu
from __future__ import with_statement
import os
import sys
import server
import http
import http_file

mapping = [
#    ("^.*$", http_file.HttpFileAction ("/var/www"), set (["GET"])),
("^.*$", http_file.HttpFileAction ('C:\Documents and Settings\Administrator\My Documents\current_work'), set (["GET"])),
];

if __name__ == "__main__":
    server.Logging (r'C:\Downloads\access.log', r'C:\Downloads\error.log');
    sock = server.HttpServer (http.HttpDispatcher (mapping));
    sock.run ();
