import re
with open('manager/templates/admin/inventory.html', 'r', encoding='utf-8') as f:
    content = f.read()

# Replace vendor_books with books
content = content.replace('vendor_books', 'books')
# Replace vb.book with vb
content = content.replace('vb.book', 'vb')
# Replace vb.vendor_price with vb.price
content = content.replace('vb.vendor_price', 'vb.price')

with open('manager/templates/admin/inventory.html', 'w', encoding='utf-8') as f:
    f.write(content)
print('Fixed!')
