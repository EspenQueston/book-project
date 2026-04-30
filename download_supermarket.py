"""Download supermarket + fix business-english course images."""
import os, sys, time
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'book_Project.settings')
import django
django.setup()

import urllib.request
from marketplace.models import Course, SupermarketItem

DB = 'marketplace'
MEDIA = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'media')

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0 Safari/537.36',
    'Accept': 'image/webp,image/apng,image/*,*/*;q=0.8',
}

def unsplash(photo_id, w=600, h=600):
    return f"https://images.unsplash.com/{photo_id}?w={w}&h={h}&fit=crop&q=80&auto=format"

def download(url, dest_path, timeout=15):
    os.makedirs(os.path.dirname(dest_path), exist_ok=True)
    req = urllib.request.Request(url, headers=HEADERS)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = resp.read()
        if len(data) < 5000:
            return False, f"Too small ({len(data)} bytes)"
        with open(dest_path, 'wb') as f:
            f.write(data)
        return True, f"{len(data)//1024}KB"
    except Exception as e:
        return False, str(e)[:80]


# ── Business English fix (Unsplash free) ──────────────────────────────────────
COURSE_FIX = {
    'business-english-advanced': unsplash('photo-1456513080510-7bf3a84b82f8', 800, 450),
    # open book on table - free Unsplash
}

# ── Supermarket URLs (all Unsplash free) ──────────────────────────────────────
# photo IDs verified as free (no "plus" prefix)
SUPERMARKET = {
    'fresh-strawberries':     unsplash('photo-1464965911861-746a04b4bca6'),
    'imported-cherries':      unsplash('photo-1528821128474-27f963b062bf'),
    'organic-pure-milk':      unsplash('photo-1550583724-b2692b85b150'),
    'premium-coffee-beans':   unsplash('photo-1447933601403-0c6688de9ffd'),
    'mixed-nuts-premium':     unsplash('photo-1563411785-2a2e12d7a6e2'),
    'cold-pressed-juice-set': unsplash('photo-1534353436294-0dbd4bdac845'),
    'greek-yogurt-natural':   unsplash('photo-1571748982800-fa51082c2224'),
    'organic-apples':         unsplash('photo-1560806887-1e4cd0b6cbd6'),
}

ok = err = 0

# Fix business-english course
print("── Fixing business-english-advanced course image ──")
for c in Course.objects.using(DB).filter(slug='business-english-advanced'):
    url = COURSE_FIX.get(c.slug)
    if url:
        fname = f"{c.slug}.jpg"
        dest = os.path.join(MEDIA, 'marketplace', 'courses', fname)
        worked, msg = download(url, dest)
        if worked:
            c.image = f'marketplace/courses/{fname}'
            c.save(using=DB)
            print(f"  ✓ {c.slug}: {msg}")
            ok += 1
        else:
            print(f"  ✗ {c.slug}: {msg}")
            err += 1
        time.sleep(0.5)

# Supermarket items
print()
print("── Downloading supermarket images ──")
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

print(f"\nDone: {ok} OK, {err} failed")
