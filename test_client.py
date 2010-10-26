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

def main():
    client = pyweb.HttpClient()
    request = client.make_request('http://www.google.com/')
    response = client.handler(request)
    response.recv_body()
    print response.get_body()

if __name__ == '__main__': main()
