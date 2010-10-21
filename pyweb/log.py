#!/usr/bin/python
# -*- coding: utf-8 -*-
# @date: 2010-06-03
# @author: shell.xu
import sys
import logging
import datetime
from os import path

log = None
weblog = None

class ApacheLog(object):
    DATEFMT = "%Y%m%d %H:%M:%S"
    def __init__(self, filepath):
        if hasattr(filepath, 'write'): self.logfile = filepath
        else:
            self.filepath = path.expanduser(filepath)
            self.logfile = open(self.filepath, "a")
    def _get_time(self): return datetime.datetime.now().strftime(self.DATEFMT)
    def action(self, req, res):
        output = '%s - %s [%s] "%s %s %s" %d %s "%s" "%s"\r\n' % \
            (req.sock.from_addr[0], "-", self._get_time(), req.verb, req.url,
             req.version, res.code, res.body_len(), req.get('Referer', '-'),
             req.get('User-Agent', '-'))
        self.logfile.write(output)
        self.logfile.flush()
    def set_weblog(self):
        global weblog
        weblog = self

class DummyStdoutput(object):
    def __init__(self, func): self.func = func
    def write(self, data): self.func(data)

class Logging(object):
    '''
    指定一个filepath，并set到log上。当hook_std后，所有输出全部输出到指定文件中。当unhook后，输出按原本方式进行。
    '''
    FORMAT = "[%(asctime)s]%(name)s:%(levelname)s:%(message)s"

    def __init__(self, filepath, level = logging.INFO):
        self.filepath = path.expanduser(filepath)
        logging.basicConfig(level = level, filename = self.filepath,
                            format = self.FORMAT, datefmt = self.DATEFMT)
        self.stderr, self.stdout = sys.stderr, sys.stdout
        self.hkerr = DummyStdoutput(self._stderr_write)
        self.hkout = DummyStdoutput(self._stdout_write)

    def hook_std(self): sys.stdout, sys.stderr = self.hkout, self.hkerr
    def unhook_std(self): sys.stdout, sys.stderr = self.stdout, self.stderr

    def write_stdout(self, data): return log.stdout.write(data)
    def write_stderr(self, data): return log.stderr.write(data)

    def _stderr_write(self, data): logging.error(data.rstrip("\r\n"))
    def _stdout_write(self, data): logging.info(data.rstrip("\r\n"))

    def set_log(self):
        global log
        log = self
