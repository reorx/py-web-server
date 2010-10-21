#!/usr/bin/python
# -*- coding: utf-8 -*-
'''
@date: 2010-10-21
@author: shell.xu
'''
from __future__ import with_statement
import binascii
import eventlet.pools
import server

def k_node_mod(srvs, k):
    if len(srvs) == 1: return srvs[0]
    crc = binascii.crc32(k)
    return srvs[crc % len(srvs)]

class MemcacheNode(eventlet.pools.Pool):

    def __init__(self, host, port):
        super(MemcacheNode, self).__init__()
        self.sockaddr = (host, port)

    def create(self):
        sock = server.EventletClient()
        sock.connect(self.sockaddr[0], self.sockaddr[1])
        return sock

k_node_func = k_node_mod
class Memcache(object):

    def __init__(self): self.srvs = []
    def add_server(self, host, port = 11211):
        self.srvs.append(MemcacheNode(host, port))

    def server_response(self, conn):
        line = conn.recv_until('\r\n')
        cmd, sp, data = line.partition(' ')
        if cmd == 'ERROR': raise Exception()
        elif cmd in ('CLIENT_ERROR', 'SERVER_ERROR'): raise Exception(data)
        return cmd, data

    def add(self, k, v, f = 0, exp = 0):
        if isinstance(v, unicode): v = v.encode('utf-8')
        with k_node_func(self.srvs, k).item() as conn:
            d = 'add %s %d %d %d\r\n%s\r\n' % (k, f, exp, len(v), v)
            conn.sendall(d)
            cmd, data = self.server_response(conn)
            return cmd == 'STORED'

    def set(self, k, v, f = 0, exp = 0):
        if isinstance(v, unicode): v = v.encode('utf-8')
        with k_node_func(self.srvs, k).item() as conn:
            conn.sendall('set %s %d %d %d\r\n%s\r\n' % (k, f, exp, len(v), v))
            cmd, data = self.server_response(conn)
            return cmd == 'STORED'

    def replace(self, k, v, f = 0, exp = 0):
        if isinstance(v, unicode): v = v.encode('utf-8')
        with k_node_func(self.srvs, k).item() as conn:
            conn.sendall('replace %s %d %d %d\r\n%s\r\n' % (k, f, exp, len(v), v))
            cmd, data = self.server_response(conn)
            return cmd == 'STORED'

    def get(self, k):
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

    def delete(self, k, exp = 0):
        with k_node_func(self.srvs, k).item() as conn:
            conn.sendall('delete %s %d\r\n' % (k, exp))
            cmd, data = self.server_response(conn)
            return cmd == 'DELETED'

    def incr(self, k, v):
        with k_node_func(self.srvs, k).item() as conn:
            conn.sendall('incr %s %d\r\n' % (k, v))
            cmd, data = self.server_response(conn)
            if cmd == 'NOT_FOUND': return None
            return int(cmd)
            
    def decr(self, k, v):
        with k_node_func(self.srvs, k).item() as conn:
            conn.sendall('decr %s %d\r\n' % (k, v))
            cmd, data = self.server_response(conn)
            if cmd == 'NOT_FOUND': return None
            return int(cmd)

    def flush_all(self, exp = 0):
        for srv in self.srvs:
            with srv.item() as conn:
                conn.sendall('flush_all\r\n')
                cmd, data = self.server_response(conn)
        
    def version(self, exp = 0):
        rslt = []
        for srv in self.srvs:
            with srv.item() as conn:
                conn.sendall('version\r\n')
                cmd, data = self.server_response(conn)
                assert(cmd == 'VERSION')
                rslt.append(data)
        return rslt
