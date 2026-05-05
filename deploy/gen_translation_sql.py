#!/usr/bin/env python3
"""
Generate SQL to sync translation fields from local DB -> production DB.
Run locally: python deploy/gen_translation_sql.py > deploy/translation_sync.sql
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "book_Project.settings")

import django
django.setup()

from manager.models import Author, Book, Publisher
from marketplace.models import Product, Course, SupermarketItem, Category

def esc(s):
    return (s or "").replace("'", "''")

lines = ["-- Translation sync: local -> production", "BEGIN;", ""]

# Authors
lines.append("-- Authors")
for a in Author.objects.all().order_by("id"):
    lines.append(
        f"UPDATE manager_author SET name_en='{esc(a.name_en)}', name_fr='{esc(a.name_fr)}' WHERE id={a.id};"
    )

lines.append("")
lines.append("-- Books")
for b in Book.objects.all().order_by("id"):
    lines.append(
        f"UPDATE manager_book SET name_en='{esc(b.name_en)}', name_fr='{esc(b.name_fr)}' WHERE id={b.id};"
    )

lines.append("")
lines.append("-- Publishers")
for p in Publisher.objects.all().order_by("id"):
    lines.append(
        f"UPDATE manager_publisher SET publisher_name_en='{esc(p.publisher_name_en)}', publisher_name_fr='{esc(p.publisher_name_fr)}' WHERE id={p.id};"
    )

lines.append("")
lines.append("-- Categories")
for c in Category.objects.all().order_by("id"):
    lines.append(
        f"UPDATE marketplace_category SET name_en='{esc(c.name_en)}', name_fr='{esc(c.name_fr)}' WHERE id={c.id};"
    )

lines.append("")
lines.append("-- Products")
for p in Product.objects.all().order_by("id"):
    lines.append(
        f"UPDATE marketplace_product SET name_en='{esc(p.name_en)}', name_fr='{esc(p.name_fr)}' WHERE id={p.id};"
    )

lines.append("")
lines.append("-- Courses")
for c in Course.objects.all().order_by("id"):
    lines.append(
        f"UPDATE marketplace_course SET title_en='{esc(c.title_en)}', title_fr='{esc(c.title_fr)}' WHERE id={c.id};"
    )

lines.append("")
lines.append("-- SupermarketItems")
for s in SupermarketItem.objects.all().order_by("id"):
    lines.append(
        f"UPDATE marketplace_supermarketitem SET name_en='{esc(s.name_en)}', name_fr='{esc(s.name_fr)}' WHERE id={s.id};"
    )

lines.append("")
lines.append("COMMIT;")

print("\n".join(lines))
print(f"-- Total UPDATE statements: {len([l for l in lines if l.startswith('UPDATE')])}", file=sys.stderr)
