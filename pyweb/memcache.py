#!/usr/bin/python
# -*- coding: utf-8 -*-
'''
@date: 2010-10-21
@author: shell.xu
@todo: 目前只实现了同余算法，没有实现一致性哈希算法。
'''
from __future__ import with_statement
import socket
import binascii
import esock

def k_node_mod(srvs, k):
    ''' 从服务器列表中，根据k，挑选一个合适的服务器
    @param srvs: 服务器的list
    @param k: 键值对象
    @return: 获得一个服务器
    '''
    if len(srvs) == 1: return srvs[0]
    crc = binascii.crc32(k)
    return srvs[crc % len(srvs)]

class ContConnectException(Exception): pass

k_node_func = k_node_mod
class Memcache(object):
    ''' memcache的客户端驱动 '''

    def __init__(self): self.srvs = []
    def add_server(self, host, port = 11211, max_size = 10000):
        ''' 增加一个服务器
        @param host: 服务器地址
        @param port: 端口，默认11211
        @param max_size: 该服务器最大可使用的连接数 '''
        self.srvs.append(esock.EpollSocketPool(host, port, max_size))

    def _server_response(self, conn):
        ''' 从服务器获得响应。 '''
        line = conn.recv_until('\r\n')
        cmd, sp, data = line.partition(' ')
        if cmd == 'ERROR': raise Exception()
        elif cmd in ('CLIENT_ERROR', 'SERVER_ERROR'): raise Exception(data)
        return cmd, data

    def _cmd_to_put(self, cmd, k, v, f, exp):
        if isinstance(v, unicode): v = v.encode('utf-8')
        try:
            with k_node_func(self.srvs, k).item() as conn:
                conn.sendall('%s %s %d %d %d\r\n%s\r\n' % (cmd, k, f, exp, len(v), v))
                cmd, data = self._server_response(conn)
                return cmd == 'STORED'
        except socket.error: raise ContConnectException()
        
    def add(self, k, v, f = 0, exp = 0):
        ''' 增加一个k-v对象 '''
        return self._cmd_to_put('add', k, v, f, exp)
    def set(self, k, v, f = 0, exp = 0):
        ''' set一个k-v对象 '''
        return self._cmd_to_put('set', k, v, f, exp)
    def replace(self, k, v, f = 0, exp = 0):
        ''' replace一个k-v对象 '''
        return self._cmd_to_put('replace', k, v, f, exp)

    def get(self, k):
        ''' get一个k-v对象 '''
        try:
            with k_node_func(self.srvs, k).item() as conn:
                conn.sendall('get %s\r\n' % k)
                cmd, data = self._server_response(conn)
                if cmd == 'END': return 0, None
                assert(cmd == 'VALUE')
                kr, f, l = data.split()
                d = conn.recv_length(int(l)+2)[:-2]
                cmd, data = self._server_response(conn)
                assert(cmd == 'END' and k == kr)
                return f, d
        except socket.error: raise ContConnectException()

    def _cmd_to_one(self, k, *params):
        try:
            with k_node_func(self.srvs, k).item() as conn:
                conn.sendall(' '.join(params))
                return self._server_response(conn)
        except socket.error: raise ContConnectException()

    def delete(self, k, exp = 0):
        ''' 删除一个k-v对象 '''
        cmd, data = self._cmd_to_one(k, 'delete', k, str(exp))
        return cmd == 'DELETED'

    def incr(self, k, v):
        ''' 增加一个k-v对象的值 '''
        cmd, data = self._cmd_to_one(k, 'incr', k, str(v))
        if cmd == 'NOT_FOUND': return None
        return int(cmd)
            
    def decr(self, k, v):
        ''' 减少一个k-v对象的值 '''
        cmd, data = self._cmd_to_one(k, 'decr', k, str(v))
        if cmd == 'NOT_FOUND': return None
        return int(cmd)

    def _cmd_to_all(self, *params):
        try:
            for srv in self.srvs:
                with srv.item() as conn:
                    conn.sendall(' '.join(params) + '\r\n')
                    yield self._server_response(conn)
        except socket.error: raise ContConnectException()

    def flush_all(self, exp = 0):
        ''' 丢弃所有数据 '''
        for cmd, data in self._cmd_to_all('flush_all'): pass
        
    def version(self, exp = 0):
        ''' 获得所有服务器的版本信息
        @return: 版本信息的list，按照服务器添加的次序。 '''
        rslt = []
        for cmd, data in self._cmd_to_all('version'):
            assert(cmd == 'VERSION')
            rslt.append(data)
        return rslt
