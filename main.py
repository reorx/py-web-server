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

use_mode = "Epoll";
log_root = "~";
mapping = [
    ("^.*$", http_file.HttpFileAction ("/home/shell"), set (["GET"])),
];

if __name__ == "__main__":
    server.HttpServer.__bases__ = (getattr (server, "Tcp%sServer" % use_mode),);
    server.Logging (path.join (log_root, "access.log"), path.join (log_root, "error.log"));
    sock = server.HttpServer (http.HttpDispatcher (mapping));
    try: sock.run ();
    except KeyboardInterrupt: pass
