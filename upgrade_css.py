import re
with open('manager/templates/public/home.html', 'r', encoding='utf-8') as f:
    content = f.read()

new_na_card = '''.na-card { background: rgba(255,255,255,0.7) !important; backdrop-filter: blur(16px); -webkit-backdrop-filter: blur(16px); border-radius: 24px !important; overflow: hidden; transition: all .4s cubic-bezier(0.175, 0.885, 0.32, 1.275); border: 1px solid rgba(255,255,255,0.5) !important; box-shadow: 0 10px 30px rgba(0,0,0,0.04), inset 0 0 0 1px rgba(255,255,255,0.6); }'''
new_na_card_hover = '''.na-card:hover { transform: translateY(-12px) scale(1.02); box-shadow: 0 30px 60px rgba(102,126,234,0.25), inset 0 0 0 1px rgba(255,255,255,0.8); border-color: rgba(102,126,234,0.4) !important; }'''
new_na_cover = '''.na-cover { height: 240px; background: radial-gradient(circle at 20% 10%, rgba(255,255,255,.95), transparent 40%), linear-gradient(135deg, #f1f5f9 0%, #e2e8f0 100%); display: flex; align-items: center; justify-content: center; padding: 20px; overflow: hidden; position: relative; }'''

content = re.sub(r'\.na-card, \.book-card, \.product-card \{.*?\}', new_na_card, content, flags=re.DOTALL)
content = re.sub(r'\.na-card:hover, \.book-card:hover, \.product-card:hover \{.*?\}', new_na_card_hover, content, flags=re.DOTALL)
content = re.sub(r'\.na-cover \{.*?\}', new_na_cover, content, flags=re.DOTALL)

with open('manager/templates/public/home.html', 'w', encoding='utf-8') as f:
    f.write(content)
print('CSS upgraded!')
