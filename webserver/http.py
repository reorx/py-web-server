#!/usr/bin/python
# -*- coding: utf-8 -*-
# @date: 20090921
# @author: shell.xu
import urllib
import datetime
from urlparse import urlparse
import base

class HttpRequest (base.HttpMessage):
    """ Http请求封装对象 """

    def __init__ (self, server, header_lines):
        """ 从某个连接实例和头部中构造出请求对象 """
        super (HttpRequest, self).__init__ ()
        self.server = server
        self.from_addr = server.from_addr
        main_info = header_lines[0].split ()
        if len (main_info) < 3:
            raise HttpException (400)
        self.verb, self.url, self.version = \
            main_info[0].upper (), main_info[1], main_info[2]
        self.url_scheme, self.url_netloc, self.url_path, self.url_params, \
            self.url_query, self.url_fragment = urlparse (self.url)
        self.url_unquoted_path = urllib.unquote (self.url_path)
        for line in header_lines[1:]:
            part = line.partition (": ")
            if len (part[1]) == 0:
                continue
            self[part[0]] = part[2]
        self.request_content = None

    def message_header (self):
        """ 反向生成请求对象头部 """
        lines = [" ".join ([self.verb, self.url, self.version])]
        for k, val in self.header.items ():
            lines.append ("%s: %s" % (str (k), str (val)))
        return "\n".join (lines) + "\n\n"

    # 这个方式并不好
    def get_content (self, size = 4096):
        """ 获得请求内容
        有可能已经直接获得，也有可能需要读取 """
        if self.request_content:
            temp = self.request_content
            self.request_content = None
            return temp
        return self.server.recv (size)

    def make_response (self, response_code):
        """ 获得和请求对应的响应对象 """
        response = HttpResponse (response_code, self)
        return response

    http_date_fmts = ["%a %d %b %Y %H:%M:%S"]
    @staticmethod
    def get_http_date (date_str):
        """ 将一个字符串解析为日期对象
        可能的格式在上面指定 """
        for fmt in HttpRequest.http_date_fmts:
            try:
                return datetime.datetime.strptime (date_str, fmt)
            except ValueError:
                pass
        return None

    @staticmethod
    def make_http_date (date_obj):
        """ 将日期对象生成字符串，使用头种格式 """
        return date_obj.strftime (HttpRequest.http_date_fmts[0])

class HttpResponse (base.HttpMessage):
    """ Http响应对象 """
    from default_setting import DEFAULT_PAGES

    @staticmethod
    def set_default_page (response_code, response_phrase, response_message):
        """ 新增一个默认页 """
        HttpResponse.DEFAULT_PAGES[response_code] = \
            (response_phrase, response_message)

    def __init__ (self, response_code, request, version = "HTTP/1.0"):
        """ 根据响应代号和请求，生成响应对象 """
        super (HttpResponse, self).__init__ ()
        self.request = request
        if request != None and hasattr (request, 'server'):
            self.server = request.server
        self.message_responsed = False
        self.connection = True
        self.cache = 0
        self.cache_time = None
        self.response_code = response_code
        self.version = version
        self.response_phrase = HttpResponse.DEFAULT_PAGES[response_code][0]
        self.set_content (HttpResponse.DEFAULT_PAGES[response_code][1])
        self.content = ""

    def generate_header (self):
        """
        完成头部数据的填充，一般是response返回前的最后一步。
        注意由于可能对填充数据重写，因此不是每个action都会调用。
        """
        if self.message_responsed:
            return 
        if "Content-Length" not in self:
            self["Content-Length"] = len (self.content)
        if self.cache == 0:
            self.cache_time = None
        else: self.cache_time = datetime.datetime.now () +\
                datetime.timedelta (seconds = self.cache)

    def message_header (self):
        """ 生成相应对象头部 """
        lines = [" ".join ([self.version, str (self.response_code),
                            self.response_phrase,])]
        for k, val in self.header.items ():
            lines.append ("%s: %s"% (str (k), str (val)))
        return "\n".join (lines) + "\n\n"

    def message_all (self):
        """ 生成完整的响应对象 """
        if len (self.content) == 0:
            return self.message_header ()
        else:
            return self.message_header () + self.content

    def send_response (self, generate_header = True):
        """ 将相应对象从连接中发出
        generate_header为真时自动填充头部 """
        if self.message_responsed:
            return 
        if generate_header:
            self.generate_header ()
        self.server.send (self.message_all ())
        self.message_responsed = True

    def set_content (self, content_data):
        """ 设定响应正文 """
        if self.message_responsed:
            raise Exception ("append content after responsed.")
        self.content = content_data

    def append_content (self, content_data):
        """ 增加相应正文 """
        if self.message_responsed:
            self.server.send (content_data)
        else:
            self.content += content_data

class HttpException (Exception):
    """ Http异常 """

    def __init__ (self, response_code):
        """ 生成Http异常 """
        super (HttpException, self).__init__ ()
        if response_code not in HttpResponse.DEFAULT_PAGES:
            response_code = 500
        self.response_code = response_code

class HttpAction (object):
    """ 处理动作的基类 """

    def action (self, request):
        """ 一个函数过程，接受一个request生成一个response """
        return HttpResponse (200)
