CC=gcc
INCLUDE_PATH=/usr/include/python2.5
CFLAGS=-pthread -fno-strict-aliasing -DNDEBUG -g -fwrapv -O2 -Wall -Wstrict-prototypes -fPIC -I$(INCLUDE_PATH)
LDFLAGS=-pthread -shared -Wl,-O1 -Wl,-Bsymbolic-functions
SOURCE=webserver/*.py actions/*.py *.py
TARGET=pylint.txt addon/greenlet.so addon/_pylibmc.so addon/epoll.so

all: $(TARGET)

clean:
	rm -f $(TARGET)
	find addon -name *.o -exec rm -f {} \;
	find . -name "*.pyc" -o -name "*.pyo" -exec rm -f {} \;

.IGNORE: pylint.txt
pylint.txt: $(SOURCE)
	pylint $^ > $@

addon/greenlet.so: addon/greenlet-src/greenlet.o
	$(CC) $(LDFLAGS) $< -o $@

addon/_pylibmc.so: addon/pylibmc/_pylibmcmodule.o
	$(CC) $(LDFLAGS) $< -o $@

addon/epoll.so: addon/python-epoll/epollmodule.o
	$(CC) $(LDFLAGS) $< -o $@
