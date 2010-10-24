#!/usr/bin/python
# -*- coding: utf-8 -*-
'''
@date: 2010-10-24
@author: shell.xu
'''
from __future__ import with_statement
import os
import sys
import time
import fcntl
import signal

daemon = None

def handler(signum, frame):
    global daemon
    if signum == signal.SIGTERM:
        daemon.running = False
        while len(daemon.workers) >0:
            for i in workers: os.kill(i, signal.SIGTERM)
            time.sleep(1)

class Daemon(object):

    def __init__(self, server):
        global daemon
        self.server, self.workers = server, []
        self.running = True
        self.daemon = self

    def get_cpu(self):
        with open("/proc/cpuinfo", "r") as cpu_file:
            cpuinfo = cpu_file.readlines()
        self.cpu = len(filter(lambda x: x.startswith("processor"), cpuinfo))

    def run(self, num = 0):
        if num == 0:
            if not hasattr(self, 'cpu'): self.get_cpu()
            num = self.cpu
        for i in xrange(0, num): self.workers.append(self.run_child())
        self.running = True
        while True:
            pid, st = os.wait()
            self.workers.remove(pid)
            if running: self.workers.append(self.run_child())

    def run_child(self):
        pid = os.fork()
        if pid < 0: raise OSError('fork failed')
        if pid: return pid
        self.server.run()

    def lock_pidfile(self, pidfile):
        self.pidfile = pidfile
        try:
            os.stat(pidfile)
            raise Exception('a instance running')
        except OSError: pass
        self.fdpid = os.open(pidfile, os.O_RDWR | os.O_CREAT, 0600)
        fcntl.lockf(self.fdpid, fcntl.LOCK_EX)
        os.write(self.fdpid, str(os.getpid()))

    def free_pidfile(self):
        os.close(self.fdpid)
        try: os.remove(self.pidfile)
        except OSError: pass

    def daemonize(self, root_dir = '/tmp'):
        pid = os.fork()
        if pid < 0: raise OSError('fork failed')
        if pid > 0: sys.exit(-1)
        os.setsid()
        for i in xrange(0, 3): os.close(i)
        fdnul = os.open('/dev/null', os.O_RDWR) # this is fd:0
        if fdnul < 0: sys.exit(-1)
        for i in xrange(1, 3): os.dup2(fdnul, i)
        os.umask(027)
        os.chdir(root_dir)
        signal.signal(signal.SIGTERM, handler)
