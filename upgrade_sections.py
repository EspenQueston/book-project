import re

with open('manager/templates/public/home.html', 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Update backgrounds and hover for .home-section-mint (New Arrivals) and .home-section-lavender (Popular Picks)
# To make them look better.
# .home-section-mint -> use a nice gradient, animated.
# .home-section-lavender -> similar nice gradient.

content = content.replace(
    '.home-section-mint { background:linear-gradient(180deg,#f7fbff 0%,#f0fdf8 100%); }',
    '.home-section-mint { background:linear-gradient(135deg,#f0fdf4 0%,#e0f2fe 100%); position: relative; overflow: hidden; padding: 80px 0; }'
)
content = content.replace(
    '.home-section-lavender { background:linear-gradient(180deg,#f8fafc 0%,#eef2ff 100%); }',
    '.home-section-lavender { background:linear-gradient(135deg,#fdf4ff 0%,#f3e8ff 100%); position: relative; overflow: hidden; padding: 80px 0; }'
)

# 2. Extract the New Arrivals Section HTML to use as a template.
match = re.search(r'<!-- New Arrivals Section -->.*?<section class="new-arrivals-section home-section-mint">.*?</section>', content, re.DOTALL)
if not match:
    print('New Arrivals section not found!')
else:
    new_arrivals_html = match.group(0)

    # 3. Create the new Popular Picks HTML based on New Arrivals HTML
    popular_picks_html = new_arrivals_html.replace('<!-- New Arrivals Section -->', '<!-- Featured Content Showcase -->')
    popular_picks_html = popular_picks_html.replace('new-arrivals-section home-section-mint', 'featured-section home-section-lavender')
    popular_picks_html = popular_picks_html.replace('新书上架', '热门推荐')
    popular_picks_html = popular_picks_html.replace('New Arrivals', 'Popular Picks')
    popular_picks_html = popular_picks_html.replace('Nouveautés', 'Sélections populaires')
    popular_picks_html = popular_picks_html.replace('最新入库的精选图书与商城好物，抢先发现', '精选图书、热销商品与优质课程，为您推荐最受欢迎的内容')
    popular_picks_html = popular_picks_html.replace('Fresh books &amp; marketplace finds — discover first', 'Featured books, bestselling products &amp; top courses — the most popular content for you')
    popular_picks_html = popular_picks_html.replace('Nouveautés livres &amp; marché — découvrez en premier', 'Livres sélectionnés, produits populaires &amp; meilleurs cours — le contenu le plus populaire pour vous')

    # Replace variable names
    popular_picks_html = popular_picks_html.replace('recent_books', 'featured_books')
    popular_picks_html = popular_picks_html.replace('recent_products', 'featured_products')
    popular_picks_html = popular_picks_html.replace('recent_courses', 'featured_courses')
    popular_picks_html = popular_picks_html.replace('na-', 'pp-') # replace CSS classes for distinction, or leave them? Better to leave them so we can reuse na- CSS.
    
    # Actually, we shouldn't replace 'na-' with 'pp-' if we want them identical and to use the same CSS, unless we duplicate the CSS.
    # Let's keep 'na-' classes, so they share the exact same style. We will just change IDs.
    popular_picks_html = popular_picks_html.replace('id="na-', 'id="pp-')
    popular_picks_html = popular_picks_html.replace('data-panel="na-', 'data-panel="pp-')
    
    # Replace the old Popular Picks section
    old_pp_match = re.search(r'<!-- Featured Content Showcase -->.*?<section class="featured-section home-section-lavender">.*?</section>', content, re.DOTALL)
    if old_pp_match:
        content = content.replace(old_pp_match.group(0), popular_picks_html)
    else:
        print('Old Popular Picks section not found!')

    with open('manager/templates/public/home.html', 'w', encoding='utf-8') as f:
        f.write(content)
    print('Replaced sections successfully.')
