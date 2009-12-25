#!/usr/bin/python
# -*- coding: utf-8 -*-
# @date: 2009-12-25
# @author: shell.xu
from base import TcpServerBase, HttpMessage
from log import Logging
from http import HttpRequest, HttpResponse, HttpException, HttpAction
from server import TcpPreforkServer, TcpThreadServer, HttpServer
from server_epoll import TcpEpollServer
import default_setting

def get_httpserver (action, use_mode, **kargs):
    ''' '''
    server = HttpServer (action, **kargs)
    server.__bases__ = (globals ().get ("Tcp%sServer" % use_mode, None))
    return server
