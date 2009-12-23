#!/bin/bash

gcc -pthread -fno-strict-aliasing -DNDEBUG -g -fwrapv -O2 -Wall -Wstrict-prototypes -fPIC -I/usr/include/python2.5 -c _pylibmcmodule.c -o _pylibmcmodule.o
gcc -pthread -shared -Wl,-O1 -Wl,-Bsymbolic-functions _pylibmcmodule.o -lmemcached -o ../_pylibmc.so
rm _pylibmcmodule.o

