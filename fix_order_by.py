
import re
with open('marketplace/views.py', 'r', encoding='utf-8') as f:
    content = f.read()

content = content.replace(
    'order_by(\'-sold_delivered\', \'-sales_count\', \'-views_count\', \'-created_at\')',
    'order_by(\'-total_sold\', \'-views_count\', \'-created_at\')'
)
content = content.replace(
    'order_by(\'-sold_delivered\', \'-sales_count\')',
    'order_by(\'-total_sold\')'
)
content = content.replace(
    'order_by(\'-sold_delivered\', \'-enrollment_count\')',
    'order_by(\'-total_sold\')'
)

with open('marketplace/views.py', 'w', encoding='utf-8') as f:
    f.write(content)
print('Fixed order_by')

