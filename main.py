#!/usr/bin/python
# -*- coding: utf-8 -*-
# @date: 20090921
# @author: shell.xu
import sys
import socket
import logging
from os import path

THIS_PATH = path.dirname (path.realpath (__file__))
sys.path.append (path.join (THIS_PATH, "addon"))
import webserver
import actions

USE_MODE = "Epoll"
LOG_ROOT = "~"
LOG_LEVEL = logging.INFO
MULTI_PROC = False
TGT_ACTION = actions.HttpCacheFilter (
    actions.HttpDispatcherFilter ([
            ("start:/", actions.HttpFileAction ("~"), set (["GET"])),
            ])
    )

if __name__ == "__main__":
    webserver.Logging (path.join (LOG_ROOT, "access.log"),
                       path.join (LOG_ROOT, "error.log"),
                       level = LOG_LEVEL).hook_std ()
    try:
        webserver.get_httpserver (action = TGT_ACTION,
                                  use_mode = USE_MODE,
                                  multi_proc = MULTI_PROC).run ()
    except KeyboardInterrupt:
        webserver.Logging.write_stdout ("exit.\r\n")
    except socket.error, err:
        webserver.Logging.write_stdout ("%d: %s\r\n" % \
                                            (err.args[0], err.args[1]))
