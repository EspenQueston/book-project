import re
with open('marketplace/templates/marketplace/home.html', 'r', encoding='utf-8') as f:
    content = f.read()

content = content.replace(
    '.rec-feed-grid { display:grid; grid-template-columns:1fr; gap:14px; }',
    '.rec-feed-grid { display:grid; grid-template-columns:repeat(4, minmax(0,1fr)); gap:14px; }'
)
content = content.replace(
    '.rec-feed-card { background:#fff; border-radius:18px; overflow:hidden; box-shadow:0 10px 28px rgba(15,23,42,.08); border:1px solid rgba(102,126,234,.08); text-decoration:none; color:inherit; display:grid; grid-template-columns:180px minmax(0,1fr); transition:all .28s ease; }',
    '.rec-feed-card { background:#fff; border-radius:18px; overflow:hidden; box-shadow:0 10px 28px rgba(15,23,42,.08); border:1px solid rgba(102,126,234,.08); text-decoration:none; color:inherit; display:flex; flex-direction:column; transition:all .28s ease; }'
)

with open('marketplace/templates/marketplace/home.html', 'w', encoding='utf-8') as f:
    f.write(content)
print('Fixed feed CSS')
