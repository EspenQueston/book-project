#!/usr/bin/env python3
"""
Generates deploy/apply_translations_prod.py — a script with hardcoded translation
values that can be uploaded to VPS and run with Django setup.

Run locally: python deploy/gen_prod_translation_script.py
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "book_Project.settings")

import django
django.setup()

from manager.models import Author, Book, Publisher
from marketplace.models import Product, Course, SupermarketItem, Category

out_path = os.path.join(os.path.dirname(__file__), "apply_translations_prod.py")
lines = [
    "#!/usr/bin/env python3",
    "# Auto-generated translation sync script — run on production VPS",
    "import os, sys",
    "os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'book_Project.settings')",
    "import django; django.setup()",
    "from manager.models import Author, Book, Publisher",
    "from marketplace.models import Product, Course, SupermarketItem, Category",
    "changed = 0",
    "",
]

for a in Author.objects.all().order_by("id"):
    en = repr(a.name_en or "")
    fr = repr(a.name_fr or "")
    lines.append(f"Author.objects.filter(pk={a.id}).update(name_en={en}, name_fr={fr}); changed += 1")

lines.append("")
for b in Book.objects.all().order_by("id"):
    en = repr(b.name_en or "")
    fr = repr(b.name_fr or "")
    lines.append(f"Book.objects.filter(pk={b.id}).update(name_en={en}, name_fr={fr}); changed += 1")

lines.append("")
for p in Publisher.objects.all().order_by("id"):
    en = repr(p.publisher_name_en or "")
    fr = repr(p.publisher_name_fr or "")
    lines.append(f"Publisher.objects.filter(pk={p.id}).update(publisher_name_en={en}, publisher_name_fr={fr}); changed += 1")

lines.append("")
for c in Category.objects.all().order_by("id"):
    en = repr(c.name_en or "")
    fr = repr(c.name_fr or "")
    lines.append(f"Category.objects.filter(pk={c.id}).update(name_en={en}, name_fr={fr}); changed += 1")

lines.append("")
for p in Product.objects.all().order_by("id"):
    en = repr(p.name_en or "")
    fr = repr(p.name_fr or "")
    lines.append(f"Product.objects.filter(pk={p.id}).update(name_en={en}, name_fr={fr}); changed += 1")

lines.append("")
for c in Course.objects.all().order_by("id"):
    en = repr(c.title_en or "")
    fr = repr(c.title_fr or "")
    lines.append(f"Course.objects.filter(pk={c.id}).update(title_en={en}, title_fr={fr}); changed += 1")

lines.append("")
for s in SupermarketItem.objects.all().order_by("id"):
    en = repr(s.name_en or "")
    fr = repr(s.name_fr or "")
    lines.append(f"SupermarketItem.objects.filter(pk={s.id}).update(name_en={en}, name_fr={fr}); changed += 1")

lines.append("")
lines.append('print(f"Done. Processed {changed} records.")')

with open(out_path, "w", encoding="utf-8") as f:
    f.write("\n".join(lines) + "\n")

print(f"Generated {out_path} ({len(lines)} lines)")
