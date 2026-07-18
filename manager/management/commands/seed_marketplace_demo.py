from django.core.management.base import BaseCommand
from django.utils.text import slugify
from marketplace.models import Category, Product
from manager.models import SiteUser, Vendor
from decimal import Decimal


CATEGORY_DATA = [
    ('Marché', 'marche'),
    ('Tendance', 'tendance'),
    ('Véhicules', 'vehicules'),
    ('Propriété', 'propriete'),
    ('Téléphones portables & Tablettes', 'telephones-portables-tablettes'),
    ('Électronique', 'electronique'),
    ('Maison, Meubles & Électroménager', 'maison-meubles-electromenager'),
    ('Mode', 'mode'),
    ('Santé & Beauté', 'sante-beaute'),
    ('Prestations de service', 'prestations-de-service'),
    ('Réparation & Construction', 'reparation-construction'),
    ('Équipement & Outils', 'equipement-outils'),
    ('Sports, arts & plein air', 'sports-arts-plein-air'),
    ('Bébés & Enfants', 'bebes-enfants'),
    ('Agriculture & Alimentation', 'agriculture-alimentation'),
    ('Animaux & animaux de compagnie', 'animaux-animaux-compagnie'),
    ('Emplois', 'emplois'),
    ('À la recherche de...', 'a-la-recherche-de'),
]

DEMO_PRODUCTS = [
    {
        'category': 'mode',
        'name': 'Chemise casual premium homme',
        'price': Decimal('18500.00'),
        'brand': 'Urban Tailor',
        'description': 'Chemise casual respirante en coton premium, idéale pour bureau et sorties.',
        'image_url': 'https://images.unsplash.com/photo-1602810318383-e386cc2a3ccf?auto=format&fit=crop&w=1200&q=80',
        'image2_url': 'https://images.pexels.com/photos/428340/pexels-photo-428340.jpeg?auto=compress&cs=tinysrgb&w=1200',
    },
    {
        'category': 'vehicules',
        'name': 'Toyota Corolla 2018 très propre',
        'price': Decimal('7450000.00'),
        'brand': 'Toyota',
        'description': 'Berline essence bien entretenue, climatisation, caméra de recul et papiers à jour.',
        'image_url': 'https://images.unsplash.com/photo-1544636331-e26879cd4d9b?auto=format&fit=crop&w=1200&q=80',
        'image2_url': 'https://images.pexels.com/photos/170811/pexels-photo-170811.jpeg?auto=compress&cs=tinysrgb&w=1200',
    },
    {
        'category': 'telephones-portables-tablettes',
        'name': 'iPhone 13 128 Go état impeccable',
        'price': Decimal('420000.00'),
        'brand': 'Apple',
        'description': 'Smartphone débloqué avec batterie en très bon état, vendu avec câble et coque.',
        'image_url': 'https://images.unsplash.com/photo-1632661674596-df8be070a5c5?auto=format&fit=crop&w=1200&q=80',
        'image2_url': 'https://images.pexels.com/photos/699122/pexels-photo-699122.jpeg?auto=compress&cs=tinysrgb&w=1200',
    },
    {
        'category': 'maison-meubles-electromenager',
        'name': 'Canapé 3 places scandinave',
        'price': Decimal('210000.00'),
        'brand': 'Nord Living',
        'description': 'Canapé confortable au design moderne, tissu résistant et structure en bois massif.',
        'image_url': 'https://images.unsplash.com/photo-1555041469-a586c61ea9bc?auto=format&fit=crop&w=1200&q=80',
        'image2_url': 'https://images.pexels.com/photos/1866149/pexels-photo-1866149.jpeg?auto=compress&cs=tinysrgb&w=1200',
    },
]


class Command(BaseCommand):
    help = 'Seed marketplace categories and realistic demo products using Unsplash/Pexels source URLs.'

    def handle(self, *args, **options):
        user, _ = SiteUser.objects.get_or_create(
            email='demo-seller@duno360.com',
            defaults={
                'name': 'Demo Seller',
                'phone': '670000000',
                'password': 'demo-password',
                'role': 'seller',
            },
        )
        vendor, _ = Vendor.objects.get_or_create(
            email=user.email,
            defaults={
                'user': user,
                'company_name': 'Duno360 Demo Store',
                'contact_name': user.name,
                'phone': user.phone,
                'password': user.password,
                'status': 'approved',
                'is_active': True,
            },
        )

        # name/description are django-modeltranslation fields on Category
        # and Product — passing them via .get_or_create()/.objects.create()
        # kwargs silently drops them (the library skips populating the
        # per-language column while _mt_init is set during __init__), so
        # they're assigned as plain attributes after construction instead.
        category_map = {}
        for idx, (name, slug) in enumerate(CATEGORY_DATA, start=1):
            category, created = Category.objects.get_or_create(
                slug=slug,
                defaults={
                    'section': 'products',
                    'display_order': idx,
                    'is_active': True,
                },
            )
            if created:
                category.name = name
                category.description = f'Catégorie {name} sur Duno360'
                category.save()
            category_map[slug] = category

        created_count = 0
        for item in DEMO_PRODUCTS:
            slug = slugify(item['name'])
            if Product.objects.filter(slug=slug).exists():
                continue
            category = category_map.get(item['category'])
            product = Product(
                vendor=vendor,
                slug=slug,
                price=item['price'],
                original_price=item['price'] + Decimal('5000.00'),
                category=category,
                stock=8,
                brand=item['brand'],
                condition='like_new',
                is_active=True,
                is_featured=True,
            )
            product.name = item['name']
            product.description = item['description']
            product.save()
            # Safe storage of source image URLs as attributes for later manual import/review.
            product.attributes.create(name='Source image principale', value=item['image_url'])
            product.attributes.create(name='Source image secondaire', value=item['image2_url'])
            created_count += 1

        self.stdout.write(self.style.SUCCESS(f'{len(category_map)} catégories prêtes, {created_count} produits démo créés.'))
