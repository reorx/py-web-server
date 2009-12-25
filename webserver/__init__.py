#!/usr/bin/python
# -*- coding: utf-8 -*-
# @date: 2009-12-25
# @author: shell.xu
from base import TcpServerBase, HttpMessage, Logging
from http import HttpRequest, HttpResponse, HttpException, HttpAction
from server import TcpPreforkServer, TcpThreadServer, HttpServer
from server_epoll import TcpEpollServer
import default_setting

def gen_HttpServer (action, use_mode, **kargs):
    ''' '''
    server = HttpServer (action, **kargs)
    server.__bases__ = (global ().get ("Tcp%sServer" % use_mode, None));
    return server;
