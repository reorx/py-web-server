#!/usr/bin/python
# -*- coding: utf-8 -*-
'''
@date: 2010-10-21
@author: shell.xu
'''
from __future__ import with_statement
import socket
import binascii
import esock

def k_node_mod(srvs, k):
    if len(srvs) == 1: return srvs[0]
    crc = binascii.crc32(k)
    return srvs[crc % len(srvs)]

class ContConnectException(Exception): pass

k_node_func = k_node_mod
class Memcache(object):

    def __init__(self): self.srvs = []
    def add_server(self, host, port = 11211, max_size = 10000):
        self.srvs.append(esock.EpollSocketPool(host, port, max_size))

    def server_response(self, conn):
        line = conn.recv_until('\r\n')
        cmd, sp, data = line.partition(' ')
        if cmd == 'ERROR': raise Exception()
        elif cmd in ('CLIENT_ERROR', 'SERVER_ERROR'): raise Exception(data)
        return cmd, data

    def cmd_to_put(self, cmd, k, v, f, exp):
        if isinstance(v, unicode): v = v.encode('utf-8')
        try:
            with k_node_func(self.srvs, k).item() as conn:
                conn.sendall('%s %s %d %d %d\r\n%s\r\n' % (cmd, k, f, exp, len(v), v))
                cmd, data = self.server_response(conn)
                return cmd == 'STORED'
        except socket.error: raise ContConnectException()
        
    def add(self, k, v, f = 0, exp = 0):
        return self.cmd_to_put('add', k, v, f, exp)
    def set(self, k, v, f = 0, exp = 0):
        return self.cmd_to_put('set', k, v, f, exp)
    def replace(self, k, v, f = 0, exp = 0):
        return self.cmd_to_put('replace', k, v, f, exp)

    def get(self, k):
        try:
            with k_node_func(self.srvs, k).item() as conn:
                conn.sendall('get %s\r\n' % k)
                cmd, data = self.server_response(conn)
                if cmd == 'END': return 0, None
                assert(cmd == 'VALUE')
                kr, f, l = data.split()
                d = conn.recv_length(int(l)+2)[:-2]
                cmd, data = self.server_response(conn)
                assert(cmd == 'END' and k == kr)
                return f, d
        except socket.error: raise ContConnectException()

    def cmd_to_one(self, k, *params):
        try:
            with k_node_func(self.srvs, k).item() as conn:
                conn.sendall(' '.join(params))
                return self.server_response(conn)
        except socket.error: raise ContConnectException()

    def delete(self, k, exp = 0):
        cmd, data = self.cmd_to_one(k, 'delete', k, str(exp))
        return cmd == 'DELETED'

    def incr(self, k, v):
        cmd, data = self.cmd_to_one(k, 'incr', k, str(v))
        if cmd == 'NOT_FOUND': return None
        return int(cmd)
            
    def decr(self, k, v):
        cmd, data = self.cmd_to_one(k, 'decr', k, str(v))
        if cmd == 'NOT_FOUND': return None
        return int(cmd)

    def cmd_to_all(self, *params):
        try:
            for srv in self.srvs:
                with srv.item() as conn:
                    conn.sendall(' '.join(params) + '\r\n')
                    yield self.server_response(conn)
        except socket.error: raise ContConnectException()

    def flush_all(self, exp = 0):
        for cmd, data in self.cmd_to_all('flush_all'): pass
        
    def version(self, exp = 0):
        rslt = []
        for cmd, data in self.cmd_to_all('version'):
            assert(cmd == 'VERSION')
            rslt.append(data)
        return rslt
