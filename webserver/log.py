#!/usr/bin/python
# -*- coding: utf-8 -*-
# @date: 2010-06-03
# @author: shell.xu
import sys
import logging
import datetime
from os import path

log = None

class DummyStdoutput (object):
    def __init__ (self, func): self.func = func
    def write (self, data): self.func (data)

class Logging (object):
    format = "[%(asctime)s]%(name)s:%(levelname)s:%(message)s"
    datefmt = "%Y%m%d %H:%M:%S"

    def __init__ (self, access_path, error_path, level = logging.INFO):
        self.access_path = path.expanduser (access_path)
        self.error_path = path.expanduser (error_path)
        self.access_file = open (self.access_path, "a")
        logging.basicConfig (level = level, format = Logging.format,
                             datefmt = Logging.datefmt,
                             filename = self.error_path)
        self.stderr = sys.stderr
        self.stderr_hook = DummyStdoutput (self._stderr_write)
        self.stdout = sys.stdout
        self.stdout_hook = DummyStdoutput (self._stdout_write)

    def hook_std (self):
        sys.stdout, sys.stderr = self.stdout_hook, self.stderr_hook

    def unhook_std (self):
        sys.stdout, sys.stderr = self.stdout, self.stderr

    def write_stdout (self, data): return log.stdout.write (data)
    def write_stderr (self, data): return log.stderr.write (data)

    def _stderr_write (self, data): logging.error (data.rstrip ("\r\n"))
    def _stdout_write (self, data): logging.info (data.rstrip ("\r\n"))

    def _get_time (self):
        return datetime.datetime.now ().strftime (Logging.datefmt)

    def action (self, request, response):
        if log == None: return
        res_len = 0
        output = '%s - %s [%s] "%s %s %s" %d %s "%s" "%s"\r\n' % \
            (request.from_addr[0], "-", self._get_time (),
             request.verb, request.url, request.version,
             response.code, response.body_len (),
             request.get ('Referer', '-'), request.get ('User-Agent', '-'))
        log.access_file.write (output)
        log.access_file.flush ()
