#!/usr/bin/python
# -*- coding: utf-8 -*-
# @date: 20090921
# @author: shell.xu
from __future__ import with_statement
import os
import re
import sys
import datetime
from urlparse import urlparse
from base import *

class HttpRequest (HttpMessage):
    """ """

    # 当这里发生错误，request没有拼装出来，因此会报错
    def __init__ (self, server, header_lines):
        """ """
        super (HttpRequest, self).__init__ ();
        self.server = server;
        self.from_addr = server.from_addr;
        main_info = header_lines[0].split ();
        if len (main_info) < 3: raise HttpException (400);
        self.verb, self.url, self.version =\
            main_info[0].upper (), main_info[1], main_info[2];
        self.url_scheme, self.url_netloc, self.url_path, self.url_params,\
            self.url_query, self.url_fragment = urlparse (self.url);
        for line in header_lines[1:]:
            part = line.partition (": ");
            if len (part[1]) == 0: continue;
            self[part[0]] = part[2];        

    # 这个方式并不好
    def get_content (self, size = 4096):
        """ """
        if self.request_content:
            temp = self.request_content;
            self.request_content = None;
            return temp;
        return self.server.sock.recv (size);

    def make_response (self, response_code):
        """ """
        response = HttpResponse (response_code);
        response.request = self;
        response.server = self.server;
        return response;

    http_date_fmt = "%a %d %b %Y %H:%M:%S %Z"
    def get_http_date (self, date_str):
        """ """
        return datetime.datetime.strptime (date_str, HttpRequest.http_date_fmt);

    def make_http_date (self, date_obj):
        """ """
        return date_obj.strftime (HttpRequest.http_date_fmt);

class HttpResponse (HttpMessage):
    """ """
    from default_setting import default_pages

    @staticmethod
    def set_default_page (response_code, response_phrase, response_message):
        HttpResponse.default_pages[response_code] =\
            (response_phrase, response_message);

    def __init__ (self, response_code, version = "HTTP/1.0"):
        """ """
        super (HttpResponse, self).__init__ ();
        self.message_responsed = False;
        self.connection = True;
        self.response_code = response_code;
        self.version = version;
        self.response_phrase = HttpResponse.default_pages[response_code][0];
        self.set_content (HttpResponse.default_pages[response_code][1]);

    def message_head (self):
        """ """
        lines = [" ".join ([self.version, str (self.response_code),
                            self.response_phrase,])];
        for k, v in self.header.items ():
            lines.append ("%s: %s"% (str (k), str (v)));
        return "\r\n".join (lines) + "\r\n\r\n";

    def response_message (self):
        """ """
        if self.message_responsed: return ;
        self.server.sock.send (self.message_head ());
        if len (self.content) > 0: self.server.sock.send (self.content);            
        self.message_responsed = True;

    def set_content (self, content_data):
        """ """
        if self.message_responsed: raise Exception ("");
        self.content = content_data;
        self["Content-Length"] = len (self.content);

    def append_content (self, content_data):
        """ """
        if self.message_responsed: self.server.sock.send (content_data);
        else:
            self.content += content_data;
            self["Content-Length"] = len (self.content);

class HttpException (Exception):
    """ """

    def __init__ (self, response_code, *params, **kargs):
        """ """
        super (HttpException, self).__init__ (*params, **kargs);
        if response_code not in HttpResponse.default_pages: response_code = 500;
        self.response_code = response_code;

class HttpDispatcher (object):
    """ """

    def __init__ (self, mapping):
        """ """
        self.mapping = [];
        for rule in mapping:
            new_rule = [re.compile(rule[0])];
            new_rule.extend (rule[1:]);
            self.mapping.append (new_rule);

    def action (self, request):
        """ """
        for rule in self.mapping:
            m = rule[0].match (request.url);
            if not m: continue;
            if len (rule) > 2 and rule[2] != None and request.verb not in rule[2]:
                return HttpResponse (405);
            request.match = m;
            if len (rule) > 3: request.param = rule[3];
            return rule[1].action (request);

class HttpAction (object):
    """ """

    def __init__ (self):
        """ """
        pass

    def action (self, request):
        """ """
        return HttpResponse (200);
