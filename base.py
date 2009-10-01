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
import logging
import datetime
import traceback
import threading
from os import path

class TcpServerBase (object):
    """ """
    buffer_size = 4096;

    def __init__ (self, address = '', port = 8000, *params, **kargs):
        """ """
        self.sock = socket.socket (socket.AF_INET, socket.SOCK_STREAM);
        self.sock.bind ((address, port));
        self.sock.listen (5);
        self.loop_func = self.do_loop;

    def get_cpu_num (self):
        """ """
        with open ("/proc/cpuinfo", "r") as cpu_file:
            return len (filter (lambda x: x.startswith ("processor"),
                                cpu_file.readlines ()));

    def run (self):
        """ """
        try:
            while self.loop_func (): pass
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
        return self.sock.recv (size);

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

class DummyStdoutput (object):
    """ """

    def __init__ (self, func):
        """ """
        self.func = func;

    def write (self, data):
        """ """
        self.func (data);

class Logging (object):
    """ """
    format = "[%(asctime)s]%(name)s:%(levelname)s:%(message)s";
    datefmt = "%Y%m%d %H:%M:%S";

    def __init__ (self, access_path, error_path, level = logging.INFO):
        """ """
        Logging._instance = self;
        self.access_path = path.expanduser (access_path);
        self.error_path = path.expanduser (error_path);
        self.access_file = open (self.access_path, "a");
        logging.basicConfig (level = level,
                             format = Logging.format,
                             datefmt = Logging.datefmt,
                             filename = self.error_path);
        self.stderr_hook = DummyStdoutput (self.stderr_write);
        self.stdout_hook = DummyStdoutput (self.stdout_write);
        self.hook_std ();

    def hook_std (self):
        """ """
        self.stderr = sys.stderr;
        sys.stderr = self.stderr_hook;
        self.stdout = sys.stdout;
        sys.stdout = self.stdout_hook;

    def unhook_std (self):
        """ """
        sys.stderr = self.stderr;
        sys.stdout = self.stdout;

    def get_time (self):
        """ """
        return datetime.datetime.now ().strftime (Logging.datefmt);

    def request (self, request, response):
        """ """
        output = '%s - %s [%s] "%s %s %s" %d %s "-" "%s"\r\n' %\
            (request.from_addr[0], "-", self.get_time (),
             request.verb, request.url, request.version,
             response.response_code,
             response.get_header ("Content-Length", default = "0"),
             response.response_phrase);
        self.access_file.write (output);
        self.access_file.flush ();
        logging.debug (request.message_header ());
        logging.debug (response.message_header ());

    def stderr_write (self, data):
        """ """
        logging.error (data.rstrip ("\r\n"));

    def stdout_write (self, data):
        """ """
        logging.info (data.rstrip ("\r\n"));
