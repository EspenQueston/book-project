"""Download real photos from Pexels/Unsplash CDN and update marketplace DB."""
import os, sys, time
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'book_Project.settings')
import django
django.setup()

import urllib.request
from marketplace.models import Product, Course, SupermarketItem

DB = 'marketplace'
MEDIA = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'media')

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0 Safari/537.36',
    'Accept': 'image/webp,image/apng,image/*,*/*;q=0.8',
    'Referer': 'https://www.pexels.com/',
}

# ─── CDN URL builders ─────────────────────────────────────────────────────────
def unsplash(photo_id, w=600, h=600):
    return f"https://images.unsplash.com/{photo_id}?w={w}&h={h}&fit=crop&q=80&auto=format"

def pexels(photo_id, w=600, h=600):
    # Use the Pexels CDN resize format
    return f"https://images.pexels.com/photos/{photo_id}/pexels-photo-{photo_id}.jpeg?auto=compress&cs=tinysrgb&w={w}&h={h}&dpr=1"

# ─── Image maps ───────────────────────────────────────────────────────────────
# Products: slug -> [img_url1, img_url2, img_url3]
PRODUCTS = {
    'wireless-bluetooth-earbuds': [
        unsplash('photo-1606220945770-b5b6c2c55bf1'),       # black gray earbuds (FREE)
        unsplash('photo-1613497646519-ee1ab64293af'),       # black silver earbuds (FREE)
        pexels(3394656, 600, 600),                          # blue wireless earbuds
    ],
    'smart-watch-pro': [
        unsplash('photo-1575311373937-040b8e1fd5b6'),       # black LED smartwatch (FREE)
        unsplash('photo-1523394643039-a2770cf4a2a0'),       # round black smartwatch (FREE)
        unsplash('photo-1585823311348-b4ea5e15a5a4'),       # dark smartwatch hand (FREE)
    ],
    'portable-power-bank-20000': [
        pexels(8137313),   # hand holding power bank
        pexels(10104284),  # flat lay black power bank on wood
        pexels(4072683),   # white power bank with cables
    ],
    'phone-case-shockproof': [
        pexels(607812),    # smartphone on table
        pexels(699122),    # phone photography
        pexels(1092644),   # modern phone
    ],
    'mechanical-keyboard-rgb': [
        pexels(6460801),   # mechanical keyboard switches
        pexels(7915211),   # close-up mechanical keyboard
        pexels(28842075),  # RGB keyboard gaming setup
    ],
    'premium-fountain-pen-set': [
        unsplash('photo-1509652839609-d94a8ad572db'),  # fountain pen with ink (FREE)
        pexels(5238117),   # pen on paper writing
        pexels(4226140),   # luxury pen set
    ],
    'usb-c-docking-station': [
        pexels(442150),    # technology cables
        pexels(325153),    # desk tech setup
        pexels(2588757),   # USB hub tech
    ],
    'laptop-stand-adjustable': [
        unsplash('flagged/photo-1576697011479-349e2a52bdf6'),  # MacBook Pro on stand (FREE)
        pexels(1181244),   # laptop workspace desk
        pexels(574069),    # laptop on stand
    ],
}

# Courses: slug -> img_url
COURSES = {
    'python-full-stack-development': pexels(1972464),        # code on screen
    'react-nextjs-modern-frontend':  pexels(29459444, 800, 450),  # JSX React code
    'ui-ux-design-masterclass':      pexels(196644, 800, 450),    # design workspace
    'digital-marketing-practice':    pexels(905163, 800, 450),    # analytics charts
    'business-english-advanced':     pexels(159711, 800, 450),    # open books
    'data-science-machine-learning': pexels(5825573, 800, 450),   # data analytics screen
}

# Supermarket: slug -> img_url
SUPERMARKET = {
    'fresh-strawberries':   pexels(4399938),   # strawberries in container
    'imported-cherries':    pexels(557659),    # cherries
    'organic-pure-milk':    pexels(248412),    # milk glass
    'premium-coffee-beans': pexels(4109751),   # coffee beans flat lay
    'mixed-nuts-premium':   pexels(1295572),   # mixed nuts
    'cold-pressed-juice-set': pexels(1337825), # fresh juice
    'greek-yogurt-natural': pexels(1126760),   # yogurt
    'organic-apples':       pexels(1510392),   # red apples
}


def download(url, dest_path):
    os.makedirs(os.path.dirname(dest_path), exist_ok=True)
    req = urllib.request.Request(url, headers=HEADERS)
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            data = resp.read()
        if len(data) < 5000:
            return False, f"Response too small ({len(data)} bytes) — likely a placeholder"
        with open(dest_path, 'wb') as f:
            f.write(data)
        return True, f"{len(data)//1024}KB"
    except Exception as e:
        return False, str(e)


ok = err = 0

print("=" * 60)
print("DOWNLOADING PRODUCTS (3 images each)")
print("=" * 60)
for p in Product.objects.using(DB).all():
    urls = PRODUCTS.get(p.slug)
    if not urls:
        print(f"  SKIP {p.slug} — no URL map")
        continue

    fields = ['image', 'image_2', 'image_3']
    paths = []
    success = True

    for i, url in enumerate(urls[:3]):
        fname = f"{p.slug}_{i+1}.jpg"
        dest = os.path.join(MEDIA, 'marketplace', 'products', fname)
        worked, msg = download(url, dest)
        time.sleep(0.5)  # polite rate limiting
        if worked:
            paths.append(f'marketplace/products/{fname}')
            print(f"  ✓ {p.slug} img{i+1}: {msg}")
            ok += 1
        else:
            print(f"  ✗ {p.slug} img{i+1}: {msg}")
            paths.append(None)
            err += 1

    # Update DB — only set fields where download succeeded
    update = {}
    for i, (field, path) in enumerate(zip(fields, paths)):
        if path:
            update[field] = path
    if update:
        for field, val in update.items():
            setattr(p, field, val)
        p.save(using=DB)

print()
print("=" * 60)
print("DOWNLOADING COURSES (1 image each)")
print("=" * 60)
for c in Course.objects.using(DB).all():
    url = COURSES.get(c.slug)
    if not url:
        print(f"  SKIP {c.slug} — no URL map")
        continue
    fname = f"{c.slug}.jpg"
    dest = os.path.join(MEDIA, 'marketplace', 'courses', fname)
    worked, msg = download(url, dest)
    time.sleep(0.5)
    if worked:
        c.image = f'marketplace/courses/{fname}'
        c.save(using=DB)
        print(f"  ✓ {c.slug}: {msg}")
        ok += 1
    else:
        print(f"  ✗ {c.slug}: {msg}")
        err += 1

print()
print("=" * 60)
print("DOWNLOADING SUPERMARKET (1 image each)")
print("=" * 60)
for s in SupermarketItem.objects.using(DB).all():
    url = SUPERMARKET.get(s.slug)
    if not url:
        print(f"  SKIP {s.slug} — no URL map")
        continue
    fname = f"{s.slug}.jpg"
    dest = os.path.join(MEDIA, 'marketplace', 'supermarket', fname)
    worked, msg = download(url, dest)
    time.sleep(0.5)
    if worked:
        s.image = f'marketplace/supermarket/{fname}'
        s.save(using=DB)
        print(f"  ✓ {s.slug}: {msg}")
        ok += 1
    else:
        print(f"  ✗ {s.slug}: {msg}")
        err += 1

print()
print(f"DONE — {ok} downloaded successfully, {err} failed")
print("Failed items still have the previous Pillow-generated images.")
