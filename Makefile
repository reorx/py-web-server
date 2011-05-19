#!/usr/bin/make -f
PROJ_NAME=pyweb

VERSION=$(shell grep '^python-pyweb' debian/changelog | head -n1 | sed 's/.*(\(.*\)).*/"\1"/g')
export VERSION

all: build-deb

build-deb: build doc
	dpkg-buildpackage -rfakeroot -kAC2DB116

build:

doc:
	epydoc --html -o doc/ -name="$(PROJ_NAME)" --url="http://code.google.com/p/py-web-server/" $(PROJ_NAME)

lint:
	pylint --disable-msg=C0321,C0111,C0301 pyweb > pyweb.lint

clean:
	fakeroot debian/rules clean
	rm -rf doc

test:
	python server.py
