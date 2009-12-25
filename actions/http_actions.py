#!/usr/bin/python
# -*- coding: utf-8 -*-
# @date: 20090921
# @author: shell.xu
import re
import copy
import logging
import datetime
from urlparse import urlparse
import webserver

def append_rule (mapping, rule, rule_info, func):
    """ """
    new_rule = [func (rule_info[2])]
    new_rule.extend (rule[1:])
    mapping.append (new_rule)

class HttpDispatcherFilter (webserver.HttpAction):
    """ """

    def __init__ (self, mapping):
        """ """
        self.mapping_match = []
        self.mapping_start = []
        self.mapping_re = []
        for rule in mapping:
            rule_info = rule[0].partition (":")
            if rule_info[1] != ":":
                continue
            if rule_info[0] == "re":
                append_rule (self.mapping_re, rule, rule_info, re.compile)
            elif rule_info[0] == "start":
                append_rule (self.mapping_start, rule, rule_info, lambda x:x)
            elif rule_info[0] == "match":
                append_rule (self.mapping_match, rule, rule_info, lambda x:x)

    def action (self, request):
        """ """
        for rule in self.mapping_match:
            if request.url_path.lower () == rule[0].lower ():
                return self.match_rule (request, rule)
        for rule in self.mapping_start:
            if request.url_path.lower ().startswith (rule[0].lower ()):
                return self.match_rule (request, rule)
        for rule in self.mapping_re:
            match = rule[0].match (request.url)
            if not match:
                continue
            return self.match_rule (request, rule, match)

    @staticmethod
    def match_rule (request, rule, match = None):
        """ """
        if len (rule) > 2 and rule[2] != None and request.verb not in rule[2]:
            return webserver.HttpResponse (405)
        logging.debug ("%s requested %s matched." % \
                           (request.url_path, rule[1].__class__.__name__))
        request.match = match
        if len (rule) > 3:
            request.param = rule[3]
        return rule[1].action (request)

class HttpMemcacheFilter (webserver.HttpAction):
    """ """

    def __init__ (self, action, memcache_set = ["127.0.0.1:11211"]):
        """ """
        self.next_action = action
        self.memcache_set = memcache_set
        import pylibmc
        self.cache = pylibmc.Client (memcache_set)

    def action (self, request):
        """ """
        response = self.cache.get (request.url_path)
        if response:
            response.request = request
            response.server = request.server
            return response
        response = self.next_action.action (request)
        if hasattr (response, "memcache") and response.memcache:
            response_cache = copy.copy (response)
            response_cache.request = None
            response_cache.server = None
            self.cache.set (request.url_path, response_cache)
        return response

class HttpCacheFilter (webserver.HttpAction):
    """ """

    def __init__ (self, action, size = 20):
        """ """
        self.next_action = action
        from lrucache import LRUCache
        self.cache = LRUCache (size)

    def action (self, request):
        """ """
        if request.url_path in self.cache:
            response = self.cache[request.url_path]
            if response.cache_time > datetime.datetime.now ():
                logging.debug ("%s requested and cached hit." % \
                                   request.url_path)
                response = copy.copy (response)
                response.message_responsed = False
                response.request = request
                response.server = request.server
                return response
            else:
                del self.cache[request.url_path]
        logging.debug ("%s requested and no cached hit." % request.url_path)
        response = self.next_action.action (request)
        if response.cache != 0:
            self.cache[request.url_path] = response
        return response
