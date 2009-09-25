#!/usr/bin/python
# -*- coding: utf-8 -*-
# @date: 2009-09-24
# @author: shell.xu
from __future__ import with_statement
import os
import re
import sys
import copy
import time
import thread
import socket
import datetime
import traceback
import threading
from os import path

class TcpServerBase (object):
    """ """
    buffer_size = 4096;

    def __init__ (self, address = '', port = 8000):
        """ """
        self.sock = socket.socket (socket.AF_INET, socket.SOCK_STREAM);
        self.sock.bind ((address, port));
        self.sock.listen (5);

    def get_cpu_num (self):
        """ """
        with open ("/proc/cpuinfo", "r") as cpu_file:
            return len (filter (lambda x: x.startswith ("processor"),
                                cpu_file.readlines ()));

    def run (self, loop_func = None):
        """ """
        if loop_func == None: loop_func = self.do_loop;
        try:
            while loop_func (): pass
        finally: self.final ();

    def final (self):
        """ """
        self.sock.close ();

    def do_process (self, request_data):
        """ """
        sys.stdout.write (request_data);
        return True;

    def send (self, data):
        """ """
        return self.sock.send (data);

    def recv (self, size):
        """ """
        return self.sock.recv (data);

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
        self.access_path = path.expanduser (access_path);
        self.error_path = path.expanduser (error_path);
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
        if not data.endswith ("\n"): data += "\n";
        self.error_file.write ("[%s]: %s"% (self.get_time (), data));
        self.error_file.flush ();

