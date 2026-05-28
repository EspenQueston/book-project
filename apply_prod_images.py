#!/usr/bin/env python
"""
apply_prod_images.py
====================
Paste the JSON from the VPS export into PROD_DATA below,
then run:  python apply_prod_images.py

This syncs image field values from production DB → local DB.
"""
import os, django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'book_Project.settings')
django.setup()

from marketplace.models import Product, Course, SupermarketItem

# ── PASTE VPS JSON OUTPUT HERE ─────────────────────────────────────────────
PROD_DATA = {"products": [["sac-bandouliere-noir-croco", "marketplace/products/e58995539b3f9cb79d4a2_images_sac-hermes-767975e4-6990-4ec2-81ba-681_db779dV.png"], ["young-vision-coffret-6-gloss", "marketplace/products/95539b3f9cb79d4a2_images_rouge-a-levres-3f88a50a-0b5a-48b0-aba9-4ea_xJtI9QU.png"], ["sac-bicolore-moutarde-marron", "marketplace/products/b1073a3e58995539b3f9cb79d4a2_images_sac-6fd4ae93-7645-4569-8626-a75_NzkTQrv.png"], ["robe-2-1", "marketplace/products/Weixin_Image_20240621201449_lJdMEEc.jpg"], ["robe", "marketplace/products/Weixin_Image_20240621201440.jpg"], ["laptop-stand-adjustable", "marketplace/products/laptop-stand-adjustable_1.jpg"], ["usb-c-docking-station", "marketplace/products/usb-c-docking-station_1.jpg"], ["premium-fountain-pen-set", "marketplace/products/premium-fountain-pen-set_1.jpg"], ["mechanical-keyboard-rgb", "marketplace/products/mechanical-keyboard-rgb_1.jpg"], ["phone-case-shockproof", "marketplace/products/phone-case-shockproof_1.jpg"], ["portable-power-bank-20000", "marketplace/products/portable-power-bank-20000_1.jpg"], ["smart-watch-pro", "marketplace/products/smart-watch-pro_1.jpg"], ["wireless-bluetooth-earbuds", "marketplace/products/wireless-bluetooth-earbuds_1.jpg"]], "courses": [["data-science-machine-learning-bvbvvv", "marketplace/courses/desifgn_24.png"], ["data-science-machine-learning", "marketplace/courses/data-science-machine-learning.jpg"], ["business-english-advanced", "marketplace/courses/business-english-advanced.jpg"], ["digital-marketing-practice", "marketplace/courses/digital-marketing-practice.jpg"], ["ui-ux-design-masterclass", "marketplace/courses/ui-ux-design-masterclass.jpg"], ["react-nextjs-modern-frontend", "marketplace/courses/react-nextjs-modern-frontend.jpg"], ["python-full-stack-development", "marketplace/courses/python-full-stack-development.jpg"]], "supermarket": [["organic-apples", "marketplace/supermarket/organic-apples.jpg"], ["greek-yogurt-natural", "marketplace/supermarket/greek-yogurt-natural.jpg"], ["cold-pressed-juice-set", "marketplace/supermarket/cold-pressed-juice-set.jpg"], ["mixed-nuts-premium", "marketplace/supermarket/mixed-nuts-premium.jpg"], ["premium-coffee-beans", "marketplace/supermarket/premium-coffee-beans.jpg"], ["organic-pure-milk", "marketplace/supermarket/organic-pure-milk.jpg"], ["imported-cherries", "marketplace/supermarket/imported-cherries.jpg"], ["fresh-strawberries", "marketplace/supermarket/fresh-strawberries.jpg"]]}
# ── END PASTE ──────────────────────────────────────────────────────────────

if not PROD_DATA:
    print('ERROR: Paste the VPS JSON into PROD_DATA before running.')
    exit(1)

updated = 0
skipped = 0

def sync(model, items, label):
    global updated, skipped
    for slug, image_path in items:
        if not image_path:
            continue
        try:
            obj = model.objects.get(slug=slug)
            if str(obj.image) != image_path:
                obj.image = image_path
                obj.save(update_fields=['image'])
                print(f'  ✓ [{label}] {slug} → {image_path}')
                updated += 1
            else:
                skipped += 1
        except model.DoesNotExist:
            print(f'  ⚠ [{label}] slug not found locally: {slug}')

sync(Product,        PROD_DATA.get('products', []),    'Product')
sync(Course,         PROD_DATA.get('courses', []),     'Course')
sync(SupermarketItem, PROD_DATA.get('supermarket', []), 'Supermarket')

print(f'\n✅  Updated: {updated}   Skipped (already matching): {skipped}')
