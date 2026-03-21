import os
from django.core.wsgi import get_wsgi_application

# 导入配置文件
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'book_Project.settings')
"""
WSGI（Python Web Server GateWay Interface）:
它是用在 python web 框架编写的应用程序与后端服务器之间的规范（本例就是 Django 和 uWSGI 之间），
让你写的应用程序可以与后端服务器顺利通信。在 WSGI 出现之前你不得不专门为某个后端服务器而写特定的 API，
并且无法更换后端服务器，而 WSGI 就是一种统一规范， 
所有使用 WSGI 的服务器都可以运行使用 WSGI 规范的 web 框架。
WSGI和ASGI，都是基于Python设计的网关接口（Gateway Interface，GI）。
# 说白了asgi和wsgi帮助我们处理底层的通信（tcp,http）
"""
application = get_wsgi_application()
