#!/usr/bin/python
# -*- coding: utf-8 -*-
'''
@date: 2010-09-29
@author: shell.xu
'''
import re
from distutils.core import setup

version_re = re.compile('.* \((.*)\) .*')
def get_version(filepath):
    changelog, rslt = open(filepath, 'r'), []
    for line in changelog:
        if not line.startswith('python-pyweb'): continue
        rslt.append(version_re.match(line).groups())
    changelog.close()
    return max(rslt)[0]
version = get_version('debian/changelog')

setup(name = 'pyweb', version = version, url = 'http://shell909090.com/',
      author = 'Shell.E.Xu', author_email = 'shell909090@gmail.com',
      maintainer = 'Shell.E.Xu', maintainer_email = 'shell909090@gmail.com',
      license = 'MIT', description = 'A web framework written by python.',
      packages = ['pyweb'])
