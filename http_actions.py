#!/usr/bin/python
# -*- coding: utf-8 -*-
# @date: 20090921
# @author: shell.xu
from __future__ import with_statement
import pylibmc
from urlparse import urlparse
from http import *

class HttpDispatcherFilter (HttpAction):
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

class HttpCacheFilter (HttpAction):
    """ """
    pool = CachePool ();

    def __init__ (self, action, memcache_set = ["127.0.0.1:11211"]):
        """ """
        self.action = action;
        self.memcache_set = memcache_set;
        self.mc = pylibmc.Client (memcache_set);

    def action (self, request):
        """ """
        response = self.mc.get (request.url_path);
        if response: return response;
        response = action.action (request);
        if hasattr (response, "memcache") ans response.memcache:
            self.mc.set (request.url_path, request);
        return response;
