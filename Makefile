#!/usr/bin/make
SOURCE:=webserver/*.py actions/*.py pywebserver

all: $(TARGET)

clean:
	find . -name "*.pyc" -exec rm -f {} \;
	find . -name "*.pyo" -exec rm -f {} \;

.IGNORE: pylint.txt
pylint.txt: $(SOURCE)
	test -z $$(which pylint) || pylint $^ > $@
