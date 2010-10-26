#!/usr/bin/make -f
PROJ_NAME=pyweb

all: build-deb

build-deb: build doc
	dpkg-buildpackage -rfakeroot

build:

doc:
	epydoc --html -o doc/ -name="$(PROJ_NAME)" --url="http://code.google.com/p/py-web-server/" $(PROJ_NAME)

lint:
	pylint --disable-msg=C0321,C0111,C0301 pyweb > pyweb.lint

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
