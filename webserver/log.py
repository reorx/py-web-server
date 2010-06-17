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
    FORMAT = "[%(asctime)s]%(name)s:%(levelname)s:%(message)s"
    DATEFMT = "%Y%m%d %H:%M:%S"

    def __init__ (self, access_path, error_path, level = logging.INFO):
        self.access_path = path.expanduser (access_path)
        self.error_path = path.expanduser (error_path)
        self.access_file = open (self.access_path, "a")
        logging.basicConfig (level = level, filename = self.error_path,
                             format = self.FORMAT, datefmt = self.DATEFMT,)
        self.stderr, self.stdout = sys.stderr, sys.stdout
        self.stderr_hook = DummyStdoutput (self._stderr_write)
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
        return datetime.datetime.now ().strftime (self.DATEFMT)

    def action (self, req, res):
        if log == None: return
        output = '%s - %s [%s] "%s %s %s" %d %s "%s" "%s"\r\n' % \
            (req.from_addr[0], "-", self._get_time (), req.verb, req.url,
             req.version, res.code, res.body_len (), req.get ('Referer', '-'),
             req.get ('User-Agent', '-'))
        log.access_file.write (output)
        log.access_file.flush ()
