如何安装

# 基础依赖库 #
整个系统基于eventlet编写，而eventlet基于greenlet，因此首先请安装这两个库。
  * 普通python用户，使用easy\_install greenlet和easy\_install eventlet进行安装升级。
  * debian系统控可以在[作者deb包](http://shell909090.3322.org/deb/)找到下载。
  * 源码控请上这两个网站的页面[greenlet](http://pypi.python.org/pypi/greenlet)和[eventlet](http://eventlet.net/)自行下载编译。

# 项目安装 #
系统使用setup.py进行安装，并针对debian系统做了打包处理。
  * 准备一个目录，执行以下指令'hg clone https://py-web-server.googlecode.com/hg/ py-web-server'。
  * debian系统控进入py-web-server目录，执行make，在上级目录会生成deb包。（如果这步出现问题，请向我汇报错误）
  * 源码控进入py-web-server目录，执行python setup.py install。