#!/usr/bin/python
# -*- coding: utf-8 -*-
# @date: 20090921
# @author: shell.xu
import sys
import logging
from os import path

THIS_PATH = path.dirname (path.realpath (__file__))
sys.path.append (path.join (THIS_PATH, "addon"))
import webserver
import http_actions
import http_file

USE_MODE = "Epoll"
LOG_ROOT = "~"
LOG_LEVEL = logging.INFO
MULTI_PROC = False
TGT_ACTION = http_actions.HttpCacheFilter (
    http_actions.HttpDispatcherFilter ([
            ("start:/", http_file.HttpFileAction ("~"), set (["GET"])),
            ])
    )

if __name__ == "__main__":
    http.Logging (path.join (LOG_ROOT, "access.log"),
                  path.join (LOG_ROOT, "error.log"), level = LOG_LEVEL)
    try:
        webserver.gen_HttpServer (action = TGT_ACTION,
                                  use_mode = USE_MODE,
                                  multi_proc = MULTI_PROC).run ()
    except KeyboardInterrupt:
        # http.Logging._instance.stdout.write ("exit.\r\n")
        pass
