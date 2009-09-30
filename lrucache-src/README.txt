================
README: lrucache
================

arch-tag: README file for lrucache

:Author: Evan Prodromou
:Contact: evan@bad.dynu.ca
:Date: 9 Nov 2004
:Web site: http://bad.dynu.ca/~evan/lrucache/
:Copyright: Copyright 2004 Evan Prodromou. Licensed under the Academic Free License 2.1

This is the lrucache package, version 0.2. It provides a simple module
for creating fairly efficient least-recently-used (LRU) caches in
Python programs. It's mainly of interest to Python programmers who
don't want to implement and debug their own LRU cache module.

LRU caches are useful for storing the results of long processes for
later re-use, without using up all available memory. Common examples
are data read from the file system or a network.

License
=======

Copyright 2004 Evan Prodromou <evan@bad.dynu.ca>.

Licensed under the Academic Free License 2.1.

You should have received a copy of the Academic Free License (AFL)
with this package in the file afl-2.1.txt. It's also available at
http://opensource.org/licenses/afl-2.1.php

Requirements
============

This module is for the Python_ programming language and probably won't
be of much use for any other system. I developed it using Python
2.3.4, and since I use generators (2.2 and above) and heaps (2.3 and
above), it should probably only work for version 2.3 Pythons and
above.

.. _Python: http://www.python.org/

Download
========

The latest versions of this module are at
http://bad.dynu.ca/~evan/lrucache.

Version control
---------------

If you use the GNU arch_ program, you can also track my
between-release revisions. My arch repository is at
http://bad.dynu.ca/~evan/arch/, and the category is "lrucache".
"users@bad.dynu.ca--main" is the arch archive name.

If you have arch set up, you should probably be able to do this::

   tla register-archive http://bad.dynu.ca/~evan/arch/
   tla getrev users@bad.dynu.ca--main/lrucache

Between-release revisions of this software are probably going to be
much more unstable and less useful than release versions.

.. _arch: http://www.gnu.org/software/gnu-arch/

Installation
============

I used the handy distutils_ tools for installation. You should be able
to install this package by running::

   python setup.py install
   
in the current directory. For more options, see the documentation on
`Installing Python Modules`_.

.. _distutils: http://www.python.org/sigs/distutils-sig/
.. _Installing Python Modules: http://www.python.org/doc/current/inst/

Usage
=====

The kernel of interest in the lrucache module is the LRUCache class.
To use the class, add the following to your Python program::

   from lrucache import LRUCache
   
You can then create a new cache object, defining the maximum number of
objects to cache::

   cache = LRUCache(size=32)
   
You can add items to the cache using subscripts, as with a sequence or
dictionary::

   fo = fopen("myfile.txt")
   lines = fo.readlines()
   fo.close()
   cache["myfile.txt"] = lines

You can then refer to items in the cache::

   other_lines = cache["myfile.txt"]
   for line in other_lines:
       print line
       
As you add more key-value pairs to the cache, it will eventually reach
its maximum size. When you add a new item after the maximum size is
reached, the oldest item in the cache is discarded. Here, "oldest"
means the item that hasn't been read or written since any of the other
objects were read or written. That's the "least-recently-used" part --
we discard the key-value pair that was least-recently-used.

Since things get discarded from the cache in hard-to-predict ways, you
shouldn't count on objects being in the cache at any particular time.
Instead, check the cache for a key, and if it's not present,
re-generate the object::

   def get_file_contents(filename):
       if filename in cache:
       	  return cache[filename]
       else:
          fo = fopen(filename)
	  lines = fo.readlines()
	  fo.close()
	  cache[filename] = lines
	  return lines

You can also delete items from the cache directly using the del
statement::

   del cache["myfile.txt"]

You can iterate over the keys of the cache::

   for key in cache:
       print key, len(cache[key])

You can also check its length::

   clen = len(cache)
   
Or its maximum size::

   csize = cache.size
   
If you assign to the cache's size, and the new size is smaller than
the current length, it will automatically shrink to the new size.

If the contents of your cache can get 'stale', you may want to check
the modification time of the cache record. Use the mtime method for
this::

   import os.path
   
   def get_file_contents(filename):
       if filename in cache and 
           os.path.getmtime(filename) <= cache.mtime(filename):
	   return cache[filename]
       else:
          fo = fopen(filename)
	  lines = fo.readlines()
	  fo.close()
	  cache[filename] = lines
	  return lines

Todo
====

* CacheWrapper. A class that wraps another container object but caches
  results. Useful for implementing a transparent network, database, or
  filesystem cache. Will need to check for "freshness" of the cache.
* LRU memoization. Wrap a function with a callable class that uses an
  LRU cache to store previous results.

Bugs
====

Please feel free to send bug reports or patches to me, Evan Prodromou,
at evan@bad.dynu.ca.
