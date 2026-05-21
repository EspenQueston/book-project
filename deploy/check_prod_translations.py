#!/usr/bin/env python3
"""Check production DB for Chinese characters in EN/FR translation fields."""
import base64
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from vps_client import connect_vps

check_script = """import os, sys
os.environ.setdefault('DJANGO_SETTINGS_MODULE','book_Project.settings')
import django; django.setup()
from manager.models import Author, Book
from marketplace.models import Product, Course, Category

def has_chinese(s): return s and any(chr(0x4e00) <= c <= chr(0x9fff) for c in str(s))
issues = []
for a in Author.objects.all():
    if has_chinese(a.name_en): issues.append('Author %d name_en=%r' % (a.id, a.name_en))
    if has_chinese(a.name_fr): issues.append('Author %d name_fr=%r' % (a.id, a.name_fr))
for b in Book.objects.all():
    if has_chinese(b.name_en): issues.append('Book %d name_en=%r' % (b.id, b.name_en))
    if has_chinese(b.name_fr): issues.append('Book %d name_fr=%r' % (b.id, b.name_fr))
for c in Category.objects.all():
    if has_chinese(c.name_en): issues.append('Cat %d name_en=%r' % (c.id, c.name_en))
    if has_chinese(c.name_fr): issues.append('Cat %d name_fr=%r' % (c.id, c.name_fr))
for p in Product.objects.all():
    if has_chinese(p.name_en): issues.append('Product %d name_en=%r' % (p.id, p.name_en))
    if has_chinese(p.name_fr): issues.append('Product %d name_fr=%r' % (p.id, p.name_fr))
for c in Course.objects.all():
    if has_chinese(c.title_en): issues.append('Course %d title_en=%r' % (c.id, c.title_en))
    if has_chinese(c.title_fr): issues.append('Course %d title_fr=%r' % (c.id, c.title_fr))
if issues:
    for i in issues: print(i)
else:
    print('PROD OK: No Chinese in EN/FR translation fields')
b7 = Book.objects.filter(pk=7).first()
print('Book id=7 name_en:', b7.name_en if b7 else 'NOT FOUND')
print('Book id=7 name_fr:', b7.name_fr if b7 else 'NOT FOUND')
"""

b64 = base64.b64encode(check_script.encode()).decode()

client, host = connect_vps(timeout=30)
print(f"Connected to {host}")

_, sw, _ = client.exec_command("echo " + b64 + " | base64 -d > /tmp/_chk.py && echo wrote")
result = sw.read().decode().strip()
print("Upload:", result)

run_cmd = (
    "sudo -u duno360 bash -lc "
    "'cp /tmp/_chk.py /opt/duno360/app/_chk.py && "
    "cd /opt/duno360/app && "
    "set -a && . /opt/duno360/.env && set +a && "
    ".venv/bin/python _chk.py; "
    "rm -f _chk.py /tmp/_chk.py'"
)
_, so, se = client.exec_command(run_cmd, timeout=60)
for line in iter(so.readline, ""):
    print(line, end="", flush=True)
err = se.read().decode()
if err.strip():
    print("STDERR:", err)
client.close()
