#!/usr/bin/python
# -*- coding: utf-8 -*-
# @date: 2009-09-24
# @author: shell.xu
from __future__ import with_statement
import os
import sys
import datetime

class HttpMessage (object):
    """ """

    def __init__ (self):
        """ """
        self.header = {};

    def __setitem__ (self, k, v):
        """ """
        self.header[str (k)] = str (v);

    def __contains__ (self, k):
        """ """
        return k in self.header;

    def get_header (self, k, default = ""):
        """ """
        return self.header.get (k, default);

    def __getitem__ (self, k):
        """ """
        return self.get_header (k);

class Logging (object):
    """ """

    def __init__ (self, access_path, error_path, debug_mode = False):
        """ """
        Logging._instance = self;
        self.access_path = access_path;
        self.error_path = error_path;
        self.debug_mode = debug_mode;
        self.access_file = open (self.access_path, "a");
        self.error_file = open (self.error_path, "a");
        sys.stderr = self;

    def output_debug (self, data):
        """ """
        if self.debug_mode:
            sys.stdout.write (data);
            sys.stdout.flush ();

    def get_time (self):
        """ """
        return datetime.datetime.now ().strftime ("%Y%m%d %H:%M:%S");

    def request (self, request, response):
        """ """
        output = '%s - %s [%s] "%s %s %s" %d %s "-" "%s"\r\n' %\
            (request.from_addr[0], "-", self.get_time (),
             request.verb, request.url, request.version,
             response.response_code,
             response.get_header ("Content-Length", default = "0"),
             response.response_phrase);
        self.output_debug (response.message_head ());
        self.access_file.write (output);
        self.access_file.flush ();

    def write (self, data):
        """ """
        self.error_file.write ("[%s]: %s\n"% (self.get_time (), data));
        self.error_file.flush ();

