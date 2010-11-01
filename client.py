#!/usr/bin/python
# -*- coding: utf-8 -*-
'''
@date: 2010-06-04
@author: shell.xu
'''
import sys
import logging
import traceback
import pyweb

def test_google():
    request = pyweb.HttpRequest.make_request('http://www.google.com/')
    response = pyweb.http_client(request)
    print response.get_body()

def test_self():
    request = pyweb.HttpRequest.make_request(
        'http://localhost:8080/pyweb/post/')
    request.append_body('abcde')
    response = pyweb.http_client(request)
    print response.get_body()

if __name__ == '__main__': test_self()
