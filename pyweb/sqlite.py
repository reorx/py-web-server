#!/usr/bin/python
# -*- coding: utf-8 -*-
'''
@date: 2010-09-23
@author: shell.xu
'''
from __future__ import with_statement
import os
import sys
import sqlite3
import threading
from os import path
import sql

class SqliteCursor(object):
    def __init__(self, db): self.db, self.cur = db, db.db.cursor()
    def execute(self, sql, args = ()):
        print sql, args
        with self.db.lock: self.cur.execute(sql, args)
    def fetchone(self): return self.cur.fetchone()
    def fetchall(self): return self.cur.fetchall()

class SqliteDB(object):

    def __init__(self, filename = None):
        self.db, self.lock, self.tables = None, threading.RLock(), {}
        if filename: self.filename = filename
    def add_table(self, tab):
        ''' 注册表 '''
        self.tables[tab.tabname] = tab
    def connect(self, filename = None):
        if filename: self.filename = filename
        self.db = sqlite3.connect(self.filename)
    def close(self):
        if not self.db: return
        self.db.close()
        self.db = None

    def create_database(self):
        ''' 创建数据库，创建注册的所有表 '''
        if not self.db: self.connect()
        dep = set()
        for tab in self.tables.values(): tab.create_table(self, dep)
        self.commit()
    def destory_database(self):
        ''' 删除数据库，关闭连接，并删除文件 '''
        self.close()
        try: os.remove(path.realpath(self.filename))
        except OSError: pass

    def cursor(self):
        ''' 获得光标 '''
        assert(self.db), 'database not open.'
        return SqliteCursor(self)
    def execute(self, sql, args = ()):
        ''' 执行语句 '''
        assert(self.db), 'database not open.'
        print sql, args
        with self.lock: self.db.execute(sql, args)
    def commit(self):
        ''' 提交修改 '''
        assert(self.db), 'database not open.'
        print 'COMMIT'
        self.db.commit()

class Table(object):
    '''
    定义表对象，包括表名，列，和索引项。定义表后需要加入数据库才能进行统一的创立/删除。
    例子：
    main = pyweb.SqliteDB('money.db')
    tAccount = pyweb.Table('account', columns = {'username': 'TEXT', 'type': 'TEXT'})
    main.add_table(tAccount)
    tType = pyweb.Table('type', columns = {'typename': 'TEXT'})
    main.add_table(tType)
    tMoney = pyweb.Table('money', columns = {'from_acc': tAccount,
    	'to_acc': tAccount, 'happen_time': 'DATETIME', 'record_time': 'DATETIME',
        'type': tType, 'money': 'REAL', 'comment': 'TEXT'})
    main.add_table(tMoney)

    main.connect()
    rows = tAccount.get_all(main)
    for row in rows: print row.values
    rows = tMoney.get_all(main, cond = (tMoney.money < 100) & (tMoney.from_acc.__in__(rows)))
    for row in rows: print row.values
    print rows[0].from_acc.username
    '''

    def __init__(self, tabname, columns, indexes = None):
        '''
        @param tabname: 表名
        @param columns: 列描述，词典类型。列名为键值，类的定义为值。如果是外键，则用所关联的表的Table对象。
        @param indexes: 索引项，列表类型。每个元素如果是字符，则对本表的该字段进行索引。如果是列表对象，则对列表内所有名字的字段联合进行索引。
        '''
        self.tabname, self.columns, self.indexes = tabname, columns, indexes
        if not self.indexes: self.indexes = []
        if 'id' not in self.columns:
            self.columns['id'] = 'INTEGER PRIMARY KEY AUTOINCREMENT'
            self.indexes.append('id')
        for col in self.columns.keys(): setattr(self, col, sql.Cond(col, []))

    def create_table(self, db, dep):
        ''' 创立表
        @param dep: 已经创立的表集合，避免重复创立 '''
        c = []
        for k, v in self.columns.items():
            if hasattr(v, 'upper'): c.append('%s %s' % (k, v.upper()))
            elif isinstance(v, Table):
                if v not in dep: v.create_table(db, dep)
                c.append('%s INT REFERENCES %s(id)' % (k, v.tabname))
            else: raise Exception('Table column wrong.')
        p = (self.tabname, ', \n\t'.join(c))
        db.execute('CREATE TABLE IF NOT EXISTS %s(%s)' % p)
        for idx in self.indexes:
            if isinstance(idx, (tuple, list)):
                p = (self.tabname, '_'.join(idx), self.tabname, ', '.join(idx))
            elif isinstance(idx, (str, unicode)):
                p = (self.tabname, idx, self.tabname, idx)
            else: raise Exception('index type wrong.')
            db.execute('CREATE INDEX IF NOT EXISTS %s_%s ON %s(%s)' % p)
        dep.add(self)

    def create_row(self): return Row(self)

    def get_one(self, db, uid, cols = None):
        ''' 从某个数据库对象中读取本表uid为特定值的对象
        @param cols: 如果有cols，则只读取特定属性 '''
        cur = db.cursor()
        if not cols: cols = self.columns.keys()
        if 'id' not in cols: cols.append('id')
        sql = 'SELECT %s FROM %s WHERE id=?' % (', '.join(cols), self.tabname)
        cur.execute(sql, (uid,))
        return Row(self).load(db, zip(cols, cur.fetchone()))

    def get_all(self, db, cols = None, cond = None):
        ''' 从某个数据库对象中读取本表满足条件的对象
        @param cond: 如果有cond，则只选择满足条件的对象
        @param cols: 如果有cols，则只读取特定属性 '''
        cur = db.cursor()
        if not cols: cols = self.columns.keys()
        if 'id' not in cols: cols.append('id')
        sql, args = 'SELECT %s FROM %s' % (', '.join(cols), self.tabname), ()
        if cond:
            sqlw, args = cond_eval(cond)
            sql += ' WHERE %s' % sqlw
        cur.execute(sql, tuple(args))
        return [Row(self).load(db, zip(cols, d)) for d in cur.fetchall()]

class Row(object):
    ''' 数据对象 '''

    def __init__(self, tab):
        ''' @param tab: 数据对象的表 '''
        self.__dict__['tab'] = tab
        self.values, self.modified = {}, set()
    def load(self, db, data):
        ''' 初始化数据 '''
        self.db, self.values = db, dict(data)
        self.modified.add('id')
        return self

    def save(self, db):
        ''' 将改动后的数据保存到某个数据库对象中 '''
        if not self.modified: return
        cols, vals = list(self.modified), []
        for v in map(lambda c: self.values[c], cols):
            if isinstance(v, Row):
                v.save(db)
                vals.append(v.id)
            else: vals.append(v)
        self.db, cur = db, db.cursor()
        cur.execute('INSERT OR REPLACE INTO %s (%s) VALUES (%s)' %\
                        (self.tab.tabname, ', '.join(cols),
                         ', '.join(['?',]*len(cols))), tuple(vals))
        self.db.commit()
        cur.execute('SELECT id FROM %s WHERE rowid=last_insert_rowid()' %\
                        self.tab.tabname)
        self.id = cur.fetchone()
        self.modified = set(['id',])

    def delete(self, db):
        self.db, cur = db, db.cursor()
        cur.execute('DELETE FROM %s WHERE id=?' % self.tab.tabname, (self.id,))
        self.db.commit()

    def _get_cond(self): return '?', [self.id, ]

    def __setitem__(self, k, v):
        if k not in self.modified: self.modified.add(k)
        self.values[k] = v
    # k + 1 times load.
    def __getitem__(self, k):
        schema, obj = self.tab.columns[k], self.values.get(k, None)
        if isinstance(schema, Table) and isinstance(obj, int):
            assert(self.db), 'db not set yet, try load or save first.'
            obj = schema.get_one(self.db, obj)
        return obj
    def __setattr__(self, k, v):
        if k not in self.tab.columns: self.__dict__[k] = v
        else: return self.__setitem__(k, v)
    def __getattr__(self, k):
        if k not in self.tab.columns: return self.__dict__[k]
        else: return self.__getitem__(k)
