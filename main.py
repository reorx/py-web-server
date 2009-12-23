#!/usr/bin/python
# -*- coding: utf-8 -*-
# @date: 20090921
# @author: shell.xu
from __future__ import with_statement
import os
import sys
from os import path

addon_path = path.join (path.dirname (path.realpath (__file__)), "addon");
sys.path.append (addon_path);
import http
import server
import http_actions
import http_file

use_mode = "Epoll";
log_root = "~";
log_level = server.logging.INFO;
multi_proc = False;
tgt_action = http_actions.HttpCacheFilter (
    http_actions.HttpDispatcherFilter ([
            ("start:/", http_file.HttpFileAction ("~"), set (["GET"])),
            ])
    );

if __name__ == "__main__":
    server.HttpServer.__bases__ = (getattr (server, "Tcp%sServer" % use_mode),);
    server.Logging (path.join (log_root, "access.log"),
                    path.join (log_root, "error.log"), level = log_level);
    try: server.HttpServer (tgt_action, multi_proc = multi_proc).run ();
    except KeyboardInterrupt: server.Logging._instance.stdout.write ("exit.\r\n");
