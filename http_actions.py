#!/usr/bin/python
# -*- coding: utf-8 -*-
# @date: 20090921
# @author: shell.xu
from __future__ import with_statement
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

class HttpMemcacheFilter (HttpAction):
    """ """

    def __init__ (self, action, memcache_set = ["127.0.0.1:11211"]):
        """ """
        self.next_action = action;
        self.memcache_set = memcache_set;
        import pylibmc
        self.cache = pylibmc.Client (memcache_set);

    def action (self, request):
        """ """
        response = self.cache.get (request.url_path);
        if response: 
            response.request = request;
            response.server = request.server;
            return response;
        response = self.next_action.action (request);
        if hasattr (response, "memcache") and response.memcache:
            response_cache = copy.copy (response);
            response_cache.request = None;
            response_cache.server = None;
            self.cache.set (request.url_path, response_cache);
        return response;

class HttpCacheFilter (HttpAction):
    """ """

    def __init__ (self, action, size = 20):
        """ """
        self.next_action = action;
        from lrucache import LRUCache;
        self.cache = LRUCache (size);

    def action (self, request):
        """ """
        if request.url_path in self.cache:
            response = self.cache[request.url_path];
            if response.cache_time > datetime.datetime.now ():
                response = copy.copy (response);
                response.message_responsed = False;
                response.request = request;
                response.server = request.server;
                return response;
            else: del self.cache[request.url_path];
        response = self.next_action.action (request);
        if response.cache != 0: self.cache[request.url_path] = response;
        return response;
