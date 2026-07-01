import re
with open('manager/templates/public/vendor_inventory.html', 'r', encoding='utf-8') as f:
    content = f.read()

content = content.replace(\"{% extends 'public/vendor_panel_base.html' %}\", \"{% extends 'admin/base.html' %}\")
content = content.replace(\"{% block vendor_panel_content %}\", \"{% block content %}\")
content = content.replace(\"{% endblock vendor_panel_content %}\", \"{% endblock %}\")
content = content.replace(\"{% block panel_extra_css %}\", \"{% block extra_css %}\")
content = content.replace(\"{% block panel_extra_js %}\", \"{% block extra_js %}\")
content = content.replace(\"{% block panel_title %}\", \"{% block title %}\")
content = content.replace(\"· {{ vendor.company_name }}\", \"Admin\")
content = content.replace(\"{% url 'manager:vendor_inventory' %}\", \"{% url 'manager:admin_inventory' %}\")

content = content.replace(\"{% if vendor_books %}\", \"{% if books %}\")
content = content.replace(\"{% for b in vendor_books %}\", \"{% for b in books %}\")

content = content.replace(\"{% if vendor_products %}\", \"{% if products %}\")
content = content.replace(\"{% for p in vendor_products %}\", \"{% for p in products %}\")

with open('manager/templates/admin/inventory.html', 'w', encoding='utf-8') as f:
    f.write(content)
print('Done!')
