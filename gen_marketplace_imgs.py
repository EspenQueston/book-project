"""Generate professional product images with proper emoji icons for marketplace."""
import os, random
os.environ['DEBUG'] = 'True'
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'book_Project.settings')

import django
django.setup()

from PIL import Image, ImageDraw, ImageFont
from marketplace.models import Product, Course, SupermarketItem

DB = 'marketplace'
MEDIA = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'media')

# Fonts
emoji_font = ImageFont.truetype('seguiemj.ttf', 64)
cjk_font = ImageFont.truetype('msyh.ttc', 24)
label_font = ImageFont.truetype('arial.ttf', 14)
badge_font = ImageFont.truetype('arial.ttf', 16)


def make_gradient(draw, size, c1, c2, angle=0):
    for y in range(size[1]):
        t = y / size[1]
        r = int(c1[0] + (c2[0] - c1[0]) * t)
        g = int(c1[1] + (c2[1] - c1[1]) * t)
        b = int(c1[2] + (c2[2] - c1[2]) * t)
        draw.line([(0, y), (size[0], y)], fill=(r, g, b))


def add_bubbles(img, seed):
    random.seed(seed)
    size = img.size
    for _ in range(6):
        cx, cy = random.randint(0, size[0]), random.randint(0, size[1])
        cr = random.randint(30, 140)
        alpha = random.randint(12, 35)
        overlay = Image.new('RGBA', size, (0, 0, 0, 0))
        ImageDraw.Draw(overlay).ellipse([cx-cr, cy-cr, cx+cr, cy+cr], fill=(255, 255, 255, alpha))
        img = Image.alpha_composite(img.convert('RGBA'), overlay).convert('RGB')
    return img


def create_image(name, emoji, colors, size=(600, 600), variant=0, badge=None):
    img = Image.new('RGB', size, colors[0])
    draw = ImageDraw.Draw(img)
    make_gradient(draw, size, colors[0], colors[1])
    img = add_bubbles(img, hash(name) + variant * 1000)
    draw = ImageDraw.Draw(img)

    cx, cy = size[0] // 2, size[1] // 2 - 50

    # White circle for icon
    r = 95
    draw.ellipse([cx-r, cy-r, cx+r, cy+r], fill=(255, 255, 255))

    # Draw emoji with Segoe UI Emoji (supports color emoji on Windows)
    try:
        bbox = draw.textbbox((0, 0), emoji, font=emoji_font)
        tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
        # Use embedded_color for color emojis
        img_rgba = img.convert('RGBA')
        txt_layer = Image.new('RGBA', size, (0, 0, 0, 0))
        txt_draw = ImageDraw.Draw(txt_layer)
        txt_draw.text((cx - tw//2, cy - th//2 - 5), emoji, font=emoji_font, embedded_color=True)
        img = Image.alpha_composite(img_rgba, txt_layer).convert('RGB')
        draw = ImageDraw.Draw(img)
    except Exception:
        draw.text((cx - 20, cy - 20), '?', fill=colors[0], font=badge_font)

    # Name bar at bottom
    bar_y = size[1] - 100
    overlay = Image.new('RGBA', size, (0, 0, 0, 0))
    od = ImageDraw.Draw(overlay)
    od.rounded_rectangle([30, bar_y, size[0]-30, bar_y+70], 14, fill=(0, 0, 0, 140))
    img = Image.alpha_composite(img.convert('RGBA'), overlay).convert('RGB')
    draw = ImageDraw.Draw(img)

    # Name text
    display = name[:18]
    bbox = draw.textbbox((0, 0), display, font=cjk_font)
    tw = bbox[2] - bbox[0]
    draw.text((cx - tw//2, bar_y + 18), display, fill=(255, 255, 255), font=cjk_font)

    # Badge (e.g. "Featured", "Organic")
    if badge:
        overlay = Image.new('RGBA', size, (0, 0, 0, 0))
        od = ImageDraw.Draw(overlay)
        od.rounded_rectangle([size[0]-140, 15, size[0]-15, 45], 8, fill=(239, 68, 68, 220))
        img = Image.alpha_composite(img.convert('RGBA'), overlay).convert('RGB')
        draw = ImageDraw.Draw(img)
        draw.text((size[0]-132, 19), badge, fill=(255, 255, 255), font=badge_font)

    # Variant label
    if variant > 0:
        draw.text((18, 18), f'#{variant+1}', fill=(255, 255, 255, 180), font=label_font)

    return img


def save(img, subdir, filename):
    path = os.path.join(MEDIA, subdir, filename)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    img.save(path, 'JPEG', quality=92)
    return f'{subdir}/{filename}'


# ========== COLOR PALETTES ==========
PAL = {
    'electronics': [(102, 126, 234), (118, 75, 162)],
    'accessories': [(16, 185, 129), (5, 150, 105)],
    'stationery':  [(245, 158, 11), (217, 119, 6)],
    'programming': [(59, 130, 246), (37, 99, 235)],
    'design':      [(236, 72, 153), (219, 39, 119)],
    'business':    [(20, 184, 166), (13, 148, 136)],
    'languages':   [(168, 85, 247), (147, 51, 234)],
    'fruits':      [(239, 68, 68), (220, 38, 38)],
    'beverages':   [(6, 182, 212), (8, 145, 178)],
    'snacks':      [(251, 146, 60), (249, 115, 22)],
    'dairy':       [(99, 102, 241), (79, 70, 229)],
}

EMOJI_P = {
    'wireless-bluetooth-earbuds': '\U0001F3A7',
    'smart-watch-pro': '\u231A',
    'portable-power-bank-20000': '\U0001F50B',
    'phone-case-shockproof': '\U0001F4F1',
    'mechanical-keyboard-rgb': '\u2328',
    'premium-fountain-pen-set': '\u2712',
    'usb-c-docking-station': '\U0001F50C',
    'laptop-stand-adjustable': '\U0001F4BB',
}

EMOJI_C = {
    'python-full-stack-development': '\U0001F40D',
    'react-nextjs-modern-frontend': '\u269B',
    'ui-ux-design-masterclass': '\U0001F3A8',
    'digital-marketing-practice': '\U0001F4CA',
    'business-english-advanced': '\U0001F4DD',
    'data-science-machine-learning': '\U0001F9E0',
}

EMOJI_S = {
    'fresh-strawberries': '\U0001F353',
    'imported-cherries': '\U0001F352',
    'organic-pure-milk': '\U0001F95B',
    'premium-coffee-beans': '\u2615',
    'mixed-nuts-premium': '\U0001F95C',
    'cold-pressed-juice-set': '\U0001F9C3',
    'greek-yogurt-natural': '\U0001F963',
    'organic-apples': '\U0001F34E',
}


def get_pal(cat):
    return PAL.get(cat.slug if cat else '', PAL['electronics'])


# ========== GENERATE ==========
print("=== Products (3 images each) ===")
for p in Product.objects.using(DB).all():
    pal = get_pal(p.category)
    em = EMOJI_P.get(p.slug, '\U0001F4E6')
    badge = 'Featured' if p.is_featured else None

    img1 = create_image(p.name, em, pal, variant=0, badge=badge)
    p.image = save(img1, 'marketplace/products', f'{p.slug}_1.jpg')

    pal2 = [pal[1], pal[0]]
    img2 = create_image(p.name, em, pal2, variant=1)
    p.image_2 = save(img2, 'marketplace/products', f'{p.slug}_2.jpg')

    pal3 = [(min(255, c+40) for c in pal[0]), (max(0, c-20) for c in pal[1])]
    pal3 = [tuple(pal3[0]), tuple(pal3[1])]
    img3 = create_image(p.name, em, pal3, variant=2)
    p.image_3 = save(img3, 'marketplace/products', f'{p.slug}_3.jpg')

    p.save(using=DB)
    print(f'  \u2713 {p.name}: 3 images')

print("\n=== Courses (1 image each) ===")
for c in Course.objects.using(DB).all():
    pal = get_pal(c.category)
    em = EMOJI_C.get(c.slug, '\U0001F4DA')
    badge = 'Featured' if c.is_featured else None

    img = create_image(c.title, em, pal, size=(800, 450), badge=badge)
    c.image = save(img, 'marketplace/courses', f'{c.slug}.jpg')
    c.save(using=DB)
    print(f'  \u2713 {c.title}')

print("\n=== Supermarket (1 image each) ===")
for s in SupermarketItem.objects.using(DB).all():
    pal = get_pal(s.category)
    em = EMOJI_S.get(s.slug, '\U0001F6D2')
    badge = 'Organic' if s.is_organic else ('Featured' if s.is_featured else None)

    img = create_image(s.name, em, pal, badge=badge)
    s.image = save(img, 'marketplace/supermarket', f'{s.slug}.jpg')
    s.save(using=DB)
    print(f'  \u2713 {s.name}')

print("\n=== All images generated and saved to database ===")
total = Product.objects.using(DB).count() * 3 + Course.objects.using(DB).count() + SupermarketItem.objects.using(DB).count()
print(f'Total images: {total}')
