#!/usr/bin/python
# -*- coding: utf-8 -*-
'''
@date: 2010-06-04
@author: shell.xu
'''
import os
import errno
import socket
from greenlet import greenlet
from contextlib import contextmanager
import ebus

class SockBase(object):
    buffer_size = 65536

    def __init__(self, sock = None, socktype = socket.AF_INET, reuse = True):
        if sock: self.sock = sock
        else: self.sock = socket.socket(socktype, socket.SOCK_STREAM)
        if reuse:
            self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        if hasattr(self, 'setsock'): self.setsock()
        self.recv_rest = ""
    def fileno(self): return self.sock.fileno()

    def listen(self, addr = '', port = 8080, listen_queue = 50, **kargs):
        self.sockaddr = (addr, port)
        self.sock.bind(self.sockaddr)
        self.sock.listen(listen_queue)

    def listen_unix(self, sockpath = '', listen_queue = 50, **kargs):
        self.sockaddr = sockpath
        try: os.remove(sockpath)
        except OSError: pass
        self.sock.bind(self.sockaddr)
        self.sock.listen(listen_queue)

    def connect(self, hostaddr, port):
        self.sockaddr = (hostaddr, port)
        self.sock.connect(self.sockaddr)

    def close(self): self.sock.close()

    def sendall(self, data):
        return self.sock.sendall(data)

    def recv(self, size):
        data = self.sock.recv(size)
        if len(data) == 0: raise EOFError
        return data

    def datas(self):
        ''' 通过迭代器，获得数据对象。
        用法：
        for data in sock.datas():
            do things with data...
        '''
        if self.recv_rest:
            d, self.recv_rest = self.recv_rest, ''
            yield d
        while True:
            d = self.sock.recv(self.buffer_size)
            if len(d) == 0: raise StopIteration
            yield d

    def recv_until(self, break_str = "\r\n\r\n"):
        ''' 读取数据，直到读取到特定字符串为止。
        @param break_str: 中断字符串。
        @return: 读取到的内容，不包括break_str。 '''
        while self.recv_rest.rfind(break_str) == -1:
            self.recv_rest += self.recv(self.buffer_size)
        data, part, self.recv_rest = self.recv_rest.partition(break_str)
        return data

    def recv_length(self, length):
        ''' 调用recv，直到读取了特定长度。
        @param length: 读取长度。 '''
        while len(self.recv_rest) < length:
            self.recv_rest += self.recv(length - len(self.recv_rest))
        if len(self.recv_rest) != length:
            data, self.recv_rest = self.recv_rest[:length], self.recv_rest[length:]
        else: data, self.recv_rest = self.recv_rest, ''
        return data

class EpollSocket(SockBase):
    ''' 使用ebus调度的socket对象。 '''
    def setsock(self): self.sock.setblocking(0)

    conn_errset = set((errno.EINPROGRESS, errno.EALREADY, errno.EWOULDBLOCK))
    def connect(self, hostaddr, port, timeout = 60):
        ''' 连接某个主机
        @param hostaddr: 主机名
        @param port: 端口号
        @param timeout: 超时时间
        '''
        self.sockaddr = (hostaddr, port)
        ton = ebus.bus.set_timeout(timeout)
        try:
            try:
                while True:
                    err = self.sock.connect_ex(self.sockaddr)
                    if not err: return
                    elif err in self.conn_errset:
                        ebus.bus.wait_for_write(self.sock.fileno())
                    else: raise socket.error(err, errno.errorcode[err])
            except ebus.TimeOutException:
                raise socket.error(111, no.errorcode[111])
        finally: ton.cancel()

    def close(self):
        ''' 关闭端口，包括unreg fd。 '''
        ebus.bus.unreg(self.sock.fileno())
        super(EpollSocket, self).close()

    def send(self, data, flags = 0):
        ''' 对原生send的封装 '''
        while True:
            try: return self.sock.send(data, flags)
            except socket.error, err:
                if err.args[0] != errno.EAGAIN: raise
                ebus.bus.wait_for_write(self.sock.fileno())

    def sendall(self, data, flags = 0):
        ''' 对原生sendall的封装 '''
        tail, len_data = self.send(data, flags), len(data)
        while tail < len_data: tail += self.send(data[tail:], flags)

    def recv(self, size):
        ''' 对原生recv的封装 '''
        while True:
            try:
                data = self.sock.recv(size)
                if len(data) == 0: raise EOFError
                return data
            except socket.error, err:
                if err.args[0] != errno.EAGAIN: raise
                ebus.bus.wait_for_read(self.sock.fileno())

    def datas(self):
        ''' 通过迭代器，获得数据对象。
        用法：
        for data in sock.datas():
            do things with data...
        '''
        if self.recv_rest:
            data, self.recv_rest = self.recv_rest, ''
            yield data
        while True:
            try:
                data = self.sock.recv(self.buffer_size)
                if len(data) == 0: raise StopIteration
                yield data
            except socket.error, err:
                if err.args[0] != errno.EAGAIN: raise
                ebus.bus.wait_for_read(self.sock.fileno())

    def accept(self):
        ''' 对原生accept的封装 '''
        while True:
            try: return self.sock.accept()
            except socket.error, err:
                if err.args[0] != errno.EAGAIN: raise
                ebus.bus.wait_for_read(self.sock.fileno())

    def run(self):
        ''' 对某个监听中的端口，接受连接，并调用on_accept方法。 '''
        ebus.bus.init_poll()
        self.gr = greenlet.getcurrent()
        try:
            while True:
                ebus.bus.wait_for_read(self.sock.fileno())
                s, addr = self.accept()
                ebus.bus.fork_gr(self.on_accept, s, addr)
        finally: ebus.bus.unreg(self.sock.fileno())

    def on_accept(self, s, addr):
        ''' 协程起点，处理某个sock。
        @param s: 基于epoll的socket对象。
        @param addr: accept的地址。 '''
        sock = EpollSocket(s)
        try:
            sock.from_addr, sock.server = addr, self
            sock.gr = greenlet.getcurrent()
            self.handler(sock)
        finally: sock.close()

class ObjPool(object):
    ''' 对象池，程序可以从中获得一个对象。当对象耗尽时，阻塞直到有程序释放对象为止。
    具体实现必须重载create函数和unbind函数。
    用法：
    objpool = ObjPool(10)
    with token.item() as obj:
        do things with obj... '''

    def __init__(self, max_item):
        self.max_item = max_item
        self.pool, self.count, self.gr_wait = [], 0, []

    @contextmanager
    def item(self):
        gr = greenlet.getcurrent()
        while self.count >= self.max_item:
            if gr not in self.gr_wait: self.gr_wait.append(gr)
            bus.schedule()
        if not self.pool: self.pool.append(self.create())
        self.count += 1
        obj = self.pool.pop()
        try: yield obj
        finally:
            self.unbind(obj)
            self.pool.append(obj)
            self.count -= 1
            if self.count == self.max_item - 1 and self.gr_wait:
                bus.switch_out(self.gr_wait.pop())

    def create(self):
        ''' 返回一个对象，用于对象创建 '''
        pass

    def unbind(self):
        ''' 将对象和当前gr分离，常用于socket对象的unreg。 '''
        pass
        
class EpollSocketPool(ObjPool):
    ''' 基于epoll socket的连接池。 '''

    def __init__(self, host, port, max_size):
        super(EpollSocketPool, self).__init__(max_size)
        self.sockaddr = (host, port)

    def create(self):
        sock = EpollSocket()
        sock.connect(self.sockaddr[0], self.sockaddr[1])
        return sock
    def unbind(self, sock): ebus.bus.unreg(sock.fileno())
