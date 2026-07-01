import re
with open('manager/templates/public/home.html', 'r', encoding='utf-8') as f:
    content = f.read()

# Replace class="home-category-card home-category-extra" with class="home-category-card" for Mode, Sante, Cours
content = content.replace('class="home-category-card home-category-extra"><div class="home-category-icon"><i class="fas fa-tshirt"></i></div><h3>Mode</h3>',
                          'class="home-category-card"><div class="home-category-icon"><i class="fas fa-tshirt"></i></div><h3>Mode</h3>')
content = content.replace('class="home-category-card home-category-extra"><div class="home-category-icon"><i class="fas fa-spa"></i></div><h3>Santé & Beauté</h3>',
                          'class="home-category-card"><div class="home-category-icon"><i class="fas fa-spa"></i></div><h3>Santé & Beauté</h3>')
content = content.replace('class="home-category-card home-category-extra" style="--cat-bg:linear-gradient(135deg,#8b5cf6,#6366f1);--cat-glow:rgba(139,92,246,.14)"><div class="home-category-icon"><i class="fas fa-graduation-cap"></i></div><h3>Cours</h3>',
                          'class="home-category-card" style="--cat-bg:linear-gradient(135deg,#8b5cf6,#6366f1);--cat-glow:rgba(139,92,246,.14)"><div class="home-category-icon"><i class="fas fa-graduation-cap"></i></div><h3>Cours</h3>')

with open('manager/templates/public/home.html', 'w', encoding='utf-8') as f:
    f.write(content)
print('Fixed categories!')
