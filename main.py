#!/usr/bin/python
# -*- coding: utf-8 -*-
# @date: 20090921
# @author: shell.xu
from __future__ import with_statement
import os
import sys
import http
import socket
import server
import http_file
from os import path

use_mode = "Epoll";
log_root = "~";
mapping = [
    ("^.*$", http_file.HttpFileAction ("~"), set (["GET"])),
];

if __name__ == "__main__":
    server.HttpServer.__bases__ = (getattr (server, "Tcp%sServer" % use_mode),);
    server.Logging (path.join (log_root, "access.log"),
                    path.join (log_root, "error.log"),);
    try:
        sock = server.HttpServer (http.HttpDispatcher (mapping));
        sock.run ();
    except socket.error, e: print e.args[1];
    except KeyboardInterrupt: print "exit."
