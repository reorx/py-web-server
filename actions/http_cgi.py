#!/usr/bin/python
# -*- coding: utf-8 -*-
# @date: 2009-12-24
# @author: shell.xu
from __future__ import with_statement
from urlparse import urlparse
import webserver

class HttpCgiAction (webserver.HttpAction):
    ''' 针对某个地址的转发 '''

    def __init__ (self, target):
        ''' '''
        self.target = target

    def action (self, request):
        ''' '''
        return request.make_response (200)
