#!/usr/bin/python
# -*- coding: utf-8 -*-
# @date: 20090921
# @author: shell.xu
from __future__ import with_statement
from urlparse import urlparse
from base import *

class HttpRequest (HttpMessage):
    """ """

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

    def message_header (self):
        """ """
        lines = [" ".join ([self.verb, self.url, self.version])];
        for k, v in self.header.items (): lines.append ("%s: %s" % (str (k), str (v)));
        return "\n".join (lines) + "\n\n";

    # 这个方式并不好
    def get_content (self, size = 4096):
        """ """
        if self.request_content:
            temp = self.request_content;
            self.request_content = None;
            return temp;
        return self.server.recv (size);

    def make_response (self, response_code):
        """ """
        response = HttpResponse (response_code);
        response.request = self;
        response.server = self.server;
        return response;

    http_date_fmts = ["%a %d %b %Y %H:%M:%S"];
    def get_http_date (self, date_str):
        """ """
        for fmt in HttpRequest.http_date_fmts:
            try: return datetime.datetime.strptime (date_str, fmt);
            except: pass

    def make_http_date (self, date_obj):
        """ """
        return date_obj.strftime (HttpRequest.http_date_fmts[0]);

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
        self.cache = 0;
        self.response_code = response_code;
        self.version = version;
        self.response_phrase = HttpResponse.default_pages[response_code][0];
        self.set_content (HttpResponse.default_pages[response_code][1]);

    def generate_header (self):
        """ 完成头部数据的填充，一般是response返回前的最后一步。
        注意由于可能对填充数据重写，因此不是每个action都会调用。 """
        if self.message_responsed: return ;
        if "Content-Length" not in self:
            self["Content-Length"] = len (self.content);
        if self.cache == 0: self.cache_time = None;
        else: self.cache_time = datetime.datetime.now () +\
                datetime.timedelta (seconds = self.cache);

    def message_header (self):
        """ """
        lines = [" ".join ([self.version, str (self.response_code),
                            self.response_phrase,])];
        for k, v in self.header.items (): lines.append ("%s: %s"% (str (k), str (v)));
        return "\n".join (lines) + "\n\n";

    def message_all (self):
        """ """
        if len (self.content) == 0: return self.message_header ();
        else: return self.message_header () + self.content;

    def send_response (self, generate_header = True):
        """ """
        if self.message_responsed: return ;
        if generate_header: self.generate_header ();
        self.server.send (self.message_all ());
        self.message_responsed = True;

    def set_content (self, content_data):
        """ """
        if self.message_responsed: raise Exception ("");
        self.content = content_data;

    def append_content (self, content_data):
        """ """
        if self.message_responsed: self.server.send (content_data);
        else: self.content += content_data;

class HttpException (Exception):
    """ """

    def __init__ (self, response_code, *params, **kargs):
        """ """
        super (HttpException, self).__init__ (*params, **kargs);
        if response_code not in HttpResponse.default_pages: response_code = 500;
        self.response_code = response_code;

class HttpAction (object):
    """ """

    def __init__ (self):
        """ """
        pass

    def action (self, request):
        """ """
        return HttpResponse (200);
