import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'book_Project.settings')
import django
django.setup()
from django.db import connections

# Check marketplace DB
cursor = connections['marketplace'].cursor()
cursor.execute(
    "SELECT column_name FROM information_schema.columns WHERE table_name = %s ORDER BY ordinal_position",
    ['marketplace_course_lesson']
)
columns = [r[0] for r in cursor.fetchall()]
print("Marketplace DB columns:", columns)

# Check default DB
cursor2 = connections['default'].cursor()
cursor2.execute(
    "SELECT column_name FROM information_schema.columns WHERE table_name = %s ORDER BY ordinal_position",
    ['marketplace_course_lesson']
)
columns2 = [r[0] for r in cursor2.fetchall()]
print("Default DB columns:", columns2)

# Check DATABASE_ROUTERS
from django.conf import settings
print("Routers:", settings.DATABASE_ROUTERS)
print("Databases:", list(settings.DATABASES.keys()))
