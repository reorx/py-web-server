#!/usr/bin/python
# -*- coding: utf-8 -*-
# @date: 20090921
# @author: shell.xu
from __future__ import with_statement
import os
import sys
import http
import server
import http_file

mapping = [
    ("^.*$", http_file.HttpFileAction ("/home/shell"), set (["GET"])),
];

if __name__ == "__main__":
    server.Logging (r'~/access.log', r'~/error.log');
    sock = server.HttpServer (http.HttpDispatcher (mapping));
    try: sock.run ();
    except KeyboardInterrupt: pass
