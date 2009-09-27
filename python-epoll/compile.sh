#!/bin/bash

gcc -pthread -fno-strict-aliasing -DNDEBUG -g -fwrapv -O2 -Wall -Wstrict-prototypes -fPIC -I/usr/include/python2.5 -c epollmodule.c -o epollmodule.o
gcc -pthread -shared -Wl,-O1 -Wl,-Bsymbolic-functions epollmodule.o -o ../epoll.so
rm epollmodule.o
