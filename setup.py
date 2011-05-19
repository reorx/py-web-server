#!/usr/bin/python
# -*- coding: utf-8 -*-
'''
@date: 2010-09-29
@author: shell.xu
'''
import os
from distutils.core import setup

setup(name = 'pyweb', version = os.environ['VERSION'], url = 'http://shell909090.com/',
      author = 'Shell.E.Xu', author_email = 'shell909090@gmail.com',
      maintainer = 'Shell.E.Xu', maintainer_email = 'shell909090@gmail.com',
      license = 'MIT', description = 'A web framework written by python.',
      packages = ['pyweb'])
