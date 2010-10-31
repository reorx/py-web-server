#!/usr/bin/python
# -*- coding: utf-8 -*-
'''
@date: 2010-09-23
@author: shell.xu
'''
import datetime

class Cond(object):
    ''' 用于生成条件语句的对象 '''

    def __init__(self, sql, vals): self.sql, self.vals = sql, vals
    def _binary_op(self, c):
        sql1, val1 = self._get_cond()
        sql2, val2 = cond_eval(c)
        val1.extend(val2)
        return sql1, sql2, filter(lambda v: v, val1)
    def _get_cond(self): return self.sql, self.vals
    def __repr__(self): return 'sql: %s\nval: %s' % (self.sql, str(self.vals))

    def __and__(self, c):
        sql1, sql2, vals = self._binary_op(c)
        return Cond('%s AND %s' % (sql1, sql2), vals)
    def __or__(self, c):
        sql1, sql2, vals = self._binary_op(c)
        return Cond('%s OR %s' % (sql1, sql2), vals)

    def __eq__(self, c):
        sql1, sql2, vals = self._binary_op(c)
        return Cond('%s = %s' % (sql1, sql2), vals)
    def __lt__(self, c):
        sql1, sql2, vals = self._binary_op(c)
        return Cond('%s < %s' % (sql1, sql2), vals)
    def __gt__(self, c):
        sql1, sql2, vals = self._binary_op(c)
        return Cond('%s > %s' % (sql1, sql2), vals)

    def like(self, c):
        sql1, sql2, vals = self._binary_op(c)
        return Cond('%s like %s' % (sql1, sql2), vals)
    def __in__(self, c):
        sql1, vals = self._get_cond()
        sqls = []
        for i in c:
            sql2, val2 = cond_eval(i)
            sqls.append(sql2)
            vals.extend(val2)
        return Cond('%s in (%s)' % (sql1, ', '.join(sqls)),
                    filter(lambda v: v, vals))

def cond_eval(obj):
    ''' 计算条件，获得对象的sql语句和参数 '''
    if hasattr(obj, '_get_cond'): return obj._get_cond()
    elif isinstance(obj, (str, unicode, int, float, datetime.datetime)):
        return '?', [obj, ]
    else: raise Exception('unsupported type')
