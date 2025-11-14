import os
from django.core.wsgi import get_wsgi_application

# 导入配置文件
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'book_Project.settings')


application = get_wsgi_application()
