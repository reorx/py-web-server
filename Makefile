#!/usr/bin/make -f
PROJ_NAME=pyweb

all: build-deb

build-deb: build doc
	dpkg-buildpackage -rfakeroot

build:

doc:
	epydoc --html -o doc/ -name $(PROJ_NAME) $(PROJ_NAME)

clean:
	rm -rf build
	rm -rf doc
	rm -f pyweb/*.pyc
	rm -f python-build-stamp*
	rm -rf debian/python-$(PROJ_NAME)
	rm -f debian/python-$(PROJ_NAME)*
	rm -f debian/pycompat
	rm -rf debian/python-module-stampdir

test:
	python test.py
