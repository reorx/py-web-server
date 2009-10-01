#!/bin/bash

gcc -pthread -fno-strict-aliasing -DNDEBUG -g -fwrapv -O2 -Wall -Wstrict-prototypes -fPIC -I/usr/include/python2.5 -c greenlet.c -o greenlet.o
gcc -pthread -shared -Wl,-O1 -Wl,-Bsymbolic-functions greenlet.o -o ../greenlet.so
rm greenlet.o
