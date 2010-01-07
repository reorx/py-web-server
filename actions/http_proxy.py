#!/usr/bin/python
# -*- coding: utf-8 -*-
# @date: 2009-12-24
# @author: shell.xu
from __future__ import with_statement
import copy
import socket
import logging
from urlparse import urlparse
import webserver

output = webserver.Logging.write_stdout

class HttpForwardAction (webserver.HttpAction):
    ''' 针对某个地址的转发 '''

    # 分服务器长连接，比较困难
    # 不分服务器，每个地址一连接，很容易，效率低下
    def __init__ (self, target):
        ''' '''
        self.target_url = target
        temp = urlparse (target)
        self.target_host = temp[1].partition (':')[0]
        self.target_port = temp[1].partition (':')[2]
        self.target_path = temp[2]
        if not self.target_port:
            self.target_port = 80
        self.sock = socket.socket (socket.AF_INET, socket.SOCK_STREAM)
        self.sock.connect ((self.target_host, self.target_port))

    def action (self, request):
        ''' '''
        output ("forward url %s\n" % request.url)
        request.url_path = self.target_path + request.url_path.lstrip ('/')
        output ("forward to %s\n" % request.url_path)
        data = request.message_header () + "\r\n\r\n" + request.get_content ()
        # FIXME: add lock here
        output (data)
        self.sock.send (data)
        # Epoll模式怎么办？
        response = request.make_response (200)
        while True:
            data = self.sock.recv ()
            if len (data) == 0:
                break;
            response.server.send (data)
        response.message_responsed = True
        # FIXME: release lock here
        return response

# class HttpProxyAction (webserver.HttpAction):
#     ''' 针对协议的代理行为，一般要求是主action '''

#     def __init__ (self):
#         ''' '''
#         pass

#     def action (self, request):
#         ''' '''
#         return request.make_response (200)
