import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
os.chdir(ROOT)
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "book_Project.settings")

import django

django.setup()

from marketplace.models import Product, Course, SupermarketItem

p = Product.objects.get(pk=51)
print(f"product #51: views={p.views_count}, sales={p.sales_count}, sold_delivered={p.get_units_sold_delivered()}")
c = Course.objects.get(pk=8)
print(f"course #8: enrollment={c.enrollment_count}, sold_delivered={c.get_units_sold_delivered()}")
s = SupermarketItem.objects.get(pk=10)
print(f"supermarket #10: sales={s.sales_count}, sold_delivered={s.get_units_sold_delivered()}")
