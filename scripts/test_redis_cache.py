import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
os.chdir(ROOT)
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "book_Project.settings")

import django

django.setup()

from django.core.cache import cache

cache.set("redis_smoke_test", "ok", 30)
value = cache.get("redis_smoke_test")
print("cache_backend:", cache.__class__.__module__)
print("redis_smoke_test:", value)
sys.exit(0 if value == "ok" else 1)
