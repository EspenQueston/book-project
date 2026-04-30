with open('marketplace/views.py', 'r', encoding='utf-8') as f:
    content = f.read()

content = content.replace(
    'if not request.session.get("info"):',
    'if not request.session.get("name"):'
)
content = content.replace(
    'request.session.get("info", {}).get("name", "Admin")',
    'request.session.get("name", "Admin")'
)

with open('marketplace/views.py', 'w', encoding='utf-8') as f:
    f.write(content)

print('Done')
