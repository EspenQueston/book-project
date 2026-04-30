"""Generate professional placeholder images for all marketplace items and save to DB."""
import os, sys, math, random
os.environ['DEBUG'] = 'True'
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'book_Project.settings')

import django
django.setup()

from PIL import Image, ImageDraw, ImageFont, ImageFilter
from marketplace.models import Product, Course, SupermarketItem

DB = 'marketplace'
BASE = os.path.dirname(os.path.abspath(__file__))
MEDIA = os.path.join(BASE, 'media')


def draw_rounded_rect(draw, xy, radius, fill):
    x0, y0, x1, y1 = xy
    draw.rectangle([x0+radius, y0, x1-radius, y1], fill=fill)
    draw.rectangle([x0, y0+radius, x1, y1-radius], fill=fill)
    draw.pieslice([x0, y0, x0+2*radius, y0+2*radius], 180, 270, fill=fill)
    draw.pieslice([x1-2*radius, y0, x1, y0+2*radius], 270, 360, fill=fill)
    draw.pieslice([x0, y1-2*radius, x0+2*radius, y1], 90, 180, fill=fill)
    draw.pieslice([x1-2*radius, y1-2*radius, x1, y1], 0, 90, fill=fill)


def create_product_image(name, icon_char, colors, size=(600, 600), variant=0):
    """Create a professional gradient product image with icon and text."""
    img = Image.new('RGB', size, colors[0])
    draw = ImageDraw.Draw(img)

    # Gradient background
    c1, c2 = colors
    for y in range(size[1]):
        r = int(c1[0] + (c2[0] - c1[0]) * y / size[1])
        g = int(c1[1] + (c2[1] - c1[1]) * y / size[1])
        b = int(c1[2] + (c2[2] - c1[2]) * y / size[1])
        draw.line([(0, y), (size[0], y)], fill=(r, g, b))

    # Decorative circles
    random.seed(hash(name) + variant)
    for _ in range(5):
        cx = random.randint(0, size[0])
        cy = random.randint(0, size[1])
        cr = random.randint(40, 120)
        alpha_val = random.randint(15, 40)
        overlay = Image.new('RGBA', size, (0, 0, 0, 0))
        od = ImageDraw.Draw(overlay)
        od.ellipse([cx-cr, cy-cr, cx+cr, cy+cr], fill=(255, 255, 255, alpha_val))
        img = Image.alpha_composite(img.convert('RGBA'), overlay).convert('RGB')
        draw = ImageDraw.Draw(img)

    # Central icon area - white circle
    center_x, center_y = size[0]//2, size[1]//2 - 40
    icon_radius = 100
    draw.ellipse(
        [center_x-icon_radius, center_y-icon_radius, center_x+icon_radius, center_y+icon_radius],
        fill=(255, 255, 255, 200)
    )

    # Icon character
    try:
        icon_font = ImageFont.truetype('arial.ttf', 72)
    except:
        icon_font = ImageFont.load_default()
    bbox = draw.textbbox((0, 0), icon_char, font=icon_font)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    draw.text((center_x - tw//2, center_y - th//2), icon_char, fill=colors[0], font=icon_font)

    # Product name - white text at bottom
    try:
        name_font = ImageFont.truetype('arial.ttf', 24)
    except:
        name_font = ImageFont.load_default()

    # Background bar for text
    bar_y = size[1] - 120
    draw_rounded_rect(draw, (40, bar_y, size[0]-40, bar_y+80), 16, (0, 0, 0))
    # Semi-transparent overlay
    overlay = Image.new('RGBA', size, (0, 0, 0, 0))
    od = ImageDraw.Draw(overlay)
    od.rounded_rectangle([40, bar_y, size[0]-40, bar_y+80], 16, fill=(0, 0, 0, 100))
    img = Image.alpha_composite(img.convert('RGBA'), overlay).convert('RGB')
    draw = ImageDraw.Draw(img)

    # Draw name text (use ASCII-safe portion or full name)
    display = name[:20] if len(name) > 20 else name
    try:
        # Try with a font that supports CJK
        cjk_font = ImageFont.truetype('msyh.ttc', 22)
        bbox = draw.textbbox((0, 0), display, font=cjk_font)
        tw = bbox[2] - bbox[0]
        draw.text((center_x - tw//2, bar_y + 20), display, fill=(255, 255, 255), font=cjk_font)
    except:
        bbox = draw.textbbox((0, 0), display, font=name_font)
        tw = bbox[2] - bbox[0]
        draw.text((center_x - tw//2, bar_y + 20), display, fill=(255, 255, 255), font=name_font)

    # Variant watermark
    if variant > 0:
        try:
            sm_font = ImageFont.truetype('arial.ttf', 14)
        except:
            sm_font = ImageFont.load_default()
        draw.text((size[0]-80, 20), f'View {variant+1}', fill=(255, 255, 255), font=sm_font)

    return img


# Color palettes for different categories
PALETTES = {
    'electronics': [(102, 126, 234), (118, 75, 162)],   # Purple
    'accessories': [(16, 185, 129), (5, 150, 105)],      # Green
    'stationery': [(245, 158, 11), (217, 119, 6)],       # Amber
    'programming': [(59, 130, 246), (37, 99, 235)],      # Blue
    'design': [(236, 72, 153), (219, 39, 119)],          # Pink
    'business': [(20, 184, 166), (13, 148, 136)],        # Teal
    'language': [(168, 85, 247), (147, 51, 234)],        # Violet
    'fruits': [(239, 68, 68), (220, 38, 38)],            # Red
    'beverages': [(6, 182, 212), (8, 145, 178)],         # Cyan
    'snacks': [(251, 146, 60), (249, 115, 22)],          # Orange
    'dairy': [(99, 102, 241), (79, 70, 229)],            # Indigo
}

# Icon characters for products
PRODUCT_ICONS = {
    'wireless-bluetooth-earbuds': '🎧',
    'smart-watch-pro': '⌚',
    'portable-power-bank-20000': '🔋',
    'phone-case-shockproof': '📱',
    'mechanical-keyboard-rgb': '⌨',
    'premium-fountain-pen-set': '✒',
    'usb-c-docking-station': '🔌',
    'laptop-stand-adjustable': '💻',
}

COURSE_ICONS = {
    'python-full-stack-development': '🐍',
    'react-nextjs-modern-frontend': '⚛',
    'ui-ux-design-masterclass': '🎨',
    'digital-marketing-practice': '📊',
    'business-english-advanced': '📝',
    'data-science-machine-learning': '🧠',
}

SUPERMARKET_ICONS = {
    'fresh-strawberries': '🍓',
    'imported-cherries': '🍒',
    'organic-pure-milk': '🥛',
    'premium-coffee-beans': '☕',
    'mixed-nuts-premium': '🥜',
    'cold-pressed-juice-set': '🧃',
    'greek-yogurt-natural': '🥄',
    'organic-apples': '🍎',
}


def get_palette(slug, category_slug=None):
    if category_slug and category_slug in PALETTES:
        return PALETTES[category_slug]
    # Default purple
    return [(102, 126, 234), (118, 75, 162)]


def save_image(img, subdir, filename):
    path = os.path.join(MEDIA, subdir, filename)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    img.save(path, 'JPEG', quality=90)
    return f'{subdir}/{filename}'


print("=== Generating Product Images ===")

# --- PRODUCTS ---
products = Product.objects.using(DB).all()
for p in products:
    cat_slug = p.category.slug if p.category else 'electronics'
    palette = get_palette(p.slug, cat_slug)
    icon = PRODUCT_ICONS.get(p.slug, '📦')

    # Image 1 - main
    img1 = create_product_image(p.name, icon, palette, variant=0)
    rel1 = save_image(img1, 'marketplace/products', f'{p.slug}_1.jpg')
    p.image = rel1

    # Image 2 - different angle/variant
    palette2 = [palette[1], palette[0]]  # Reverse gradient
    img2 = create_product_image(p.name, icon, palette2, variant=1)
    rel2 = save_image(img2, 'marketplace/products', f'{p.slug}_2.jpg')
    p.image_2 = rel2

    # Image 3 - third variant with shifted colors
    palette3 = [(min(255, c+30) for c in palette[0]), (max(0, c-30) for c in palette[1])]
    palette3 = [tuple(palette3[0]), tuple(palette3[1])]
    img3 = create_product_image(p.name, icon, palette3, variant=2)
    rel3 = save_image(img3, 'marketplace/products', f'{p.slug}_3.jpg')
    p.image_3 = rel3

    p.save(using=DB)
    print(f'  ✓ {p.name}: 3 images')

print(f'\nProducts: {products.count()} items with 3 images each')

# --- COURSES ---
print("\n=== Generating Course Images ===")
courses = Course.objects.using(DB).all()
for c in courses:
    cat_slug = c.category.slug if c.category else 'programming'
    palette = get_palette(c.slug, cat_slug)
    icon = COURSE_ICONS.get(c.slug, '📚')

    img = create_product_image(c.title, icon, palette, size=(800, 450), variant=0)
    rel = save_image(img, 'marketplace/courses', f'{c.slug}.jpg')
    c.image = rel
    c.save(using=DB)
    print(f'  ✓ {c.title}')

print(f'\nCourses: {courses.count()} items')

# --- SUPERMARKET ---
print("\n=== Generating Supermarket Images ===")
items = SupermarketItem.objects.using(DB).all()
for s in items:
    cat_slug = s.category.slug if s.category else 'fruits'
    palette = get_palette(s.slug, cat_slug)
    icon = SUPERMARKET_ICONS.get(s.slug, '🛒')

    img = create_product_image(s.name, icon, palette, variant=0)
    rel = save_image(img, 'marketplace/supermarket', f'{s.slug}.jpg')
    s.image = rel
    s.save(using=DB)
    print(f'  ✓ {s.name}')

print(f'\nSupermarket: {items.count()} items')

# Verify
print("\n=== Verification ===")
for p in Product.objects.using(DB).all():
    has_1 = bool(p.image)
    has_2 = bool(p.image_2)
    has_3 = bool(p.image_3)
    print(f'  {p.name}: img1={has_1} img2={has_2} img3={has_3}')

for c in Course.objects.using(DB).all():
    print(f'  {c.title}: img={bool(c.image)}')

for s in SupermarketItem.objects.using(DB).all():
    print(f'  {s.name}: img={bool(s.image)}')

print("\nDone! All images generated and saved to database.")
