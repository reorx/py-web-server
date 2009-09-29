#!/usr/bin/python
# -*- coding: utf-8 -*-
# @date: 20090921
# @author: shell.xu
from __future__ import with_statement
from urlparse import urlparse
from http import *

class HttpDispatcherAction (HttpAction):
    """ """

    def __init__ (self, mapping):
        """ """
        self.mapping = [];
        for rule in mapping:
            new_rule = [re.compile(rule[0])];
            new_rule.extend (rule[1:]);
            self.mapping.append (new_rule);

    def action (self, request):
        """ """
        for rule in self.mapping:
            m = rule[0].match (request.url);
            if not m: continue;
            if len (rule) > 2 and rule[2] != None and request.verb not in rule[2]:
                return HttpResponse (405);
            request.match = m;
            if len (rule) > 3: request.param = rule[3];
            return rule[1].action (request);

class CachePool (object):
    """ """

    def __init__ (self, pool_size = 1024):
        """ """
        self.pool_size = pool_size;
        self.pool = {};
        self.frq_queue = [];

    def update_less_frq (self, obj):
        """ """
        if len (self.pool) == 0: return ;
        less_frq = self.pool[0]; self.less_frq = 
        for k, v in self.pool.items ():
            if v[1] < less_frq

    def reduce_all (self, frq):
        """ """
        pass

    def __setitem__ (self, k, v):
        """ """
        if k in self.frq:
            if v == self.pool[k][0]: self.pool[k][1] += 1;
            else: self.pool[k] = [v, 1];
        elif len (self.pool) < self.pool_size: self.pool[k] = [v, 1];
        else:
            rk, rf = self.frq_queue.pop (0);
            del self.pool[rk];
            self.pool[k] = [v, 1];

    def __getitem__ (self, k):
        """ """
        self.pool[k][1] += 1;
        return self.pool[0];

    def __delitem__ (self, k):
        """ """
        del self.frq_queue
        del self.pool[k];
        if k == self.less_frq: self.update_less_frq ();

# class HttpCacheAction (HttpAction):
#     """ """
#     pool = CachePool ();

#     def __init__ (self, action):
#         """ """
#         self.action = action;

#     def action (self, request):
#         """ """
#         if request.url_path in HttpCacheAction.pool:
#             return HttpCacheAction.pool[request.url_path];
#         else: 
#             response = action.action (request);
#             self.pool[request.url_path] = response;
#             return response;
