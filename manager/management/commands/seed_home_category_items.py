"""Seed home-page marketplace categories with demo items and downloaded images."""

import uuid
from decimal import Decimal
from urllib.error import URLError
from urllib.request import Request, urlopen

from django.core.cache import cache
from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand
from django.utils.text import slugify

from marketplace.models import Category, Course, Product, SupermarketItem
from manager.models import Manager


# Slugs must match manager/templates/public/home.html category links.
PRODUCT_CATEGORIES = [
    ('Véhicules', 'vehicules', 'products'),
    ('Propriété', 'propriete', 'products'),
    ('Téléphones & Tablettes', 'telephones-tablettes', 'products'),
    ('Électronique', 'electronique', 'products'),
    ('Maison, Meubles & Électroménager', 'maison-meubles-electromenager', 'products'),
    ('Mode', 'mode', 'products'),
    ('Santé & Beauté', 'sante-beaute', 'products'),
    ('Prestations de service', 'services', 'products'),
    ('Réparation & Construction', 'reparation-construction', 'products'),
    ('Équipement & Outils', 'equipement-outils', 'products'),
    ('Sports, arts & plein air', 'sports-arts-plein-air', 'products'),
    ('Bébés & Enfants', 'bebes-enfants', 'products'),
    ('Animaux', 'animaux', 'products'),
    ('Emplois', 'emplois', 'products'),
    ('À la recherche de...', 'recherche', 'products'),
    ('Formations', 'formations', 'courses'),
    ('Agriculture & Alimentation', 'agriculture-alimentation', 'supermarket'),
    ('Supermarché', 'supermarche', 'supermarket'),
]

PRODUCTS = [
    {
        'category': 'vehicules',
        'name': 'Toyota Corolla 2019 — très propre',
        'price': Decimal('6850000'),
        'brand': 'Toyota',
        'description': 'Berline essence, climatisation, caméra de recul, entretien suivi.',
        'image_url': 'https://images.unsplash.com/photo-1549317661-bd32c8ce0db2?auto=format&fit=crop&w=1200&q=80',
        'featured': True,
        'sales_count': 12,
    },
    {
        'category': 'vehicules',
        'name': 'Moto Honda CB500X 2021',
        'price': Decimal('3200000'),
        'brand': 'Honda',
        'description': 'Trail urbain, faible kilométrage, casque offert.',
        'image_url': 'https://picsum.photos/seed/duno-moto-honda/1200/800',
        'featured': True,
        'sales_count': 8,
    },
    {
        'category': 'propriete',
        'name': 'Appartement 3 pièces — centre-ville',
        'price': Decimal('45000000'),
        'brand': 'Immobilier',
        'description': '85 m², balcon, parking, proche commerces et écoles.',
        'image_url': 'https://picsum.photos/seed/duno-apartment/1200/800',
        'featured': True,
        'sales_count': 5,
    },
    {
        'category': 'propriete',
        'name': 'Terrain viabilisé 500 m²',
        'price': Decimal('12000000'),
        'brand': 'Terrain',
        'description': 'Parcelle clôturée, titre foncier, accès goudronné.',
        'image_url': 'https://images.unsplash.com/photo-1500382017468-9049fed747ef?auto=format&fit=crop&w=1200&q=80',
        'sales_count': 3,
    },
    {
        'category': 'telephones-tablettes',
        'name': 'iPhone 14 Pro 256 Go',
        'price': Decimal('520000'),
        'brand': 'Apple',
        'description': 'État impeccable, batterie 92 %, boîte et accessoires.',
        'image_url': 'https://picsum.photos/seed/duno-iphone14/1200/800',
        'featured': True,
        'sales_count': 22,
    },
    {
        'category': 'telephones-tablettes',
        'name': 'Samsung Galaxy Tab S9',
        'price': Decimal('385000'),
        'brand': 'Samsung',
        'description': 'Tablette 11", stylet S Pen, idéale études et bureautique.',
        'image_url': 'https://images.unsplash.com/photo-1544244015-0df4b3ffc6b0?auto=format&fit=crop&w=1200&q=80',
        'sales_count': 9,
    },
    {
        'category': 'electronique',
        'name': 'Smart TV Samsung 55" 4K',
        'price': Decimal('295000'),
        'brand': 'Samsung',
        'description': 'HDR, Smart Hub, ports HDMI et USB.',
        'image_url': 'https://images.unsplash.com/photo-1593359677879-a4bb92f829d1?auto=format&fit=crop&w=1200&q=80',
        'featured': True,
        'sales_count': 15,
    },
    {
        'category': 'electronique',
        'name': 'Ordinateur portable HP 15"',
        'price': Decimal('410000'),
        'brand': 'HP',
        'description': 'Intel i5, 16 Go RAM, SSD 512 Go, Windows 11.',
        'image_url': 'https://images.unsplash.com/photo-1496181133206-80ce9b88a853?auto=format&fit=crop&w=1200&q=80',
        'sales_count': 11,
    },
    {
        'category': 'maison-meubles-electromenager',
        'name': 'Canapé 3 places scandinave',
        'price': Decimal('215000'),
        'brand': 'Nord Living',
        'description': 'Tissu résistant, design moderne, livraison possible.',
        'image_url': 'https://images.unsplash.com/photo-1555041469-a586c61ea9bc?auto=format&fit=crop&w=1200&q=80',
        'featured': True,
        'sales_count': 7,
    },
    {
        'category': 'maison-meubles-electromenager',
        'name': 'Réfrigérateur double porte 350 L',
        'price': Decimal('265000'),
        'brand': 'Hisense',
        'description': 'No Frost, classe énergétique A, garantie 2 ans.',
        'image_url': 'https://images.unsplash.com/photo-1571175443880-49e1d25b2bc5?auto=format&fit=crop&w=1200&q=80',
        'sales_count': 6,
    },
    {
        'category': 'mode',
        'name': 'Chemise premium homme coton',
        'price': Decimal('18500'),
        'brand': 'Urban Tailor',
        'description': 'Coupe slim, respirante, disponible en plusieurs coloris.',
        'image_url': 'https://images.unsplash.com/photo-1602810318383-e386cc2a3ccf?auto=format&fit=crop&w=1200&q=80',
        'featured': True,
        'sales_count': 18,
    },
    {
        'category': 'mode',
        'name': 'Baskets sport unisex',
        'price': Decimal('42000'),
        'brand': 'ActiveStep',
        'description': 'Semelle confort, usage quotidien et sport léger.',
        'image_url': 'https://images.unsplash.com/photo-1542291026-7eec264c27ff?auto=format&fit=crop&w=1200&q=80',
        'sales_count': 14,
    },
    {
        'category': 'sante-beaute',
        'name': 'Kit soin visage complet',
        'price': Decimal('24000'),
        'brand': 'GlowCare',
        'description': 'Nettoyant, sérum vitamine C et crème hydratante.',
        'image_url': 'https://images.unsplash.com/photo-1556228578-0d85b1a4d571?auto=format&fit=crop&w=1200&q=80',
        'sales_count': 10,
    },
    {
        'category': 'sante-beaute',
        'name': 'Parfum eau de toilette 100 ml',
        'price': Decimal('35000'),
        'brand': 'Aura',
        'description': 'Notes florales, tenue longue durée.',
        'image_url': 'https://images.unsplash.com/photo-1541643600914-78b084683601?auto=format&fit=crop&w=1200&q=80',
        'sales_count': 8,
    },
    {
        'category': 'services',
        'name': 'Service plomberie à domicile',
        'price': Decimal('15000'),
        'brand': 'ProFix',
        'description': 'Intervention rapide, devis gratuit, garantie main-d\'œuvre.',
        'image_url': 'https://images.unsplash.com/photo-1581578731548-c64695cc6952?auto=format&fit=crop&w=1200&q=80',
        'sales_count': 20,
    },
    {
        'category': 'services',
        'name': 'Dépannage informatique & réseau',
        'price': Decimal('12000'),
        'brand': 'TechAssist',
        'description': 'Installation, maintenance PC, configuration Wi-Fi.',
        'image_url': 'https://images.unsplash.com/photo-1517430816045-df4b7de11d1d?auto=format&fit=crop&w=1200&q=80',
        'sales_count': 16,
    },
    {
        'category': 'reparation-construction',
        'name': 'Perceuse visseuse sans fil Bosch',
        'price': Decimal('65000'),
        'brand': 'Bosch',
        'description': '2 batteries, mandrin 13 mm, mallette incluse.',
        'image_url': 'https://images.pexels.com/photos/162553/keys-workshop-mechanic-tools-162553.jpeg?auto=compress&cs=tinysrgb&w=1200',
        'sales_count': 9,
    },
    {
        'category': 'reparation-construction',
        'name': 'Lot ciment + sable prêt à l\'emploi',
        'price': Decimal('28000'),
        'brand': 'BuildPro',
        'description': 'Matériaux de construction, livraison sur chantier.',
        'image_url': 'https://images.unsplash.com/photo-1504307651254-35680f356dfd?auto=format&fit=crop&w=1200&q=80',
        'sales_count': 5,
    },
    {
        'category': 'equipement-outils',
        'name': 'Groupe électrogène 3 kVA',
        'price': Decimal('185000'),
        'brand': 'PowerGen',
        'description': 'Silencieux, démarrage manuel, usage pro et maison.',
        'image_url': 'https://images.unsplash.com/photo-1621905252507-b35492cc74b4?auto=format&fit=crop&w=1200&q=80',
        'sales_count': 4,
    },
    {
        'category': 'equipement-outils',
        'name': 'Armoire pharmacie professionnelle',
        'price': Decimal('95000'),
        'brand': 'MedEquip',
        'description': 'Acier, 4 étagères, verrouillage sécurisé.',
        'image_url': 'https://images.unsplash.com/photo-1582719478250-c89cae4dc85b?auto=format&fit=crop&w=1200&q=80',
        'sales_count': 3,
    },
    {
        'category': 'sports-arts-plein-air',
        'name': 'Vélo de route aluminium',
        'price': Decimal('175000'),
        'brand': 'VeloCity',
        'description': '21 vitesses, freins à disque, cadre léger.',
        'image_url': 'https://images.unsplash.com/photo-1571068316344-75bc76f77890?auto=format&fit=crop&w=1200&q=80',
        'featured': True,
        'sales_count': 6,
    },
    {
        'category': 'sports-arts-plein-air',
        'name': 'Raquettes de tennis pro',
        'price': Decimal('48000'),
        'brand': 'AceSport',
        'description': 'Paire avec housse, cordage pré-monté.',
        'image_url': 'https://images.unsplash.com/photo-1554068865-24cecd4e34b8?auto=format&fit=crop&w=1200&q=80',
        'sales_count': 5,
    },
    {
        'category': 'bebes-enfants',
        'name': 'Poussette compacte pliable',
        'price': Decimal('89000'),
        'brand': 'BabyJoy',
        'description': 'Harnais 5 points, capote UV, panier spacieux.',
        'image_url': 'https://images.unsplash.com/photo-1587654780291-39c9404d746b?auto=format&fit=crop&w=1200&q=80',
        'sales_count': 7,
    },
    {
        'category': 'bebes-enfants',
        'name': 'Jouets éducatifs Montessori',
        'price': Decimal('22000'),
        'brand': 'KidLearn',
        'description': 'Lot de 12 pièces, bois certifié, 3-6 ans.',
        'image_url': 'https://images.unsplash.com/photo-1558618666-fcd25c85cd64?auto=format&fit=crop&w=1200&q=80',
        'sales_count': 11,
    },
    {
        'category': 'animaux',
        'name': 'Croquettes premium chien 15 kg',
        'price': Decimal('32000'),
        'brand': 'PetNutri',
        'description': 'Sans céréales, riche en protéines, toutes races.',
        'image_url': 'https://images.unsplash.com/photo-1587300003388-59208cc962cb?auto=format&fit=crop&w=1200&q=80',
        'sales_count': 13,
    },
    {
        'category': 'animaux',
        'name': 'Cage oiseaux XL avec accessoires',
        'price': Decimal('45000'),
        'brand': 'AviHome',
        'description': 'Perchoirs, mangeoires et bac amovible.',
        'image_url': 'https://images.unsplash.com/photo-1450778869180-41d0601e046e?auto=format&fit=crop&w=1200&q=80',
        'sales_count': 4,
    },
    {
        'category': 'emplois',
        'name': 'Offre — Développeur web Django',
        'price': Decimal('0'),
        'brand': 'Duno360',
        'description': 'CDI, télétravail partiel, stack Python/Django/React.',
        'image_url': 'https://images.unsplash.com/photo-1522071820081-009f0129c71c?auto=format&fit=crop&w=1200&q=80',
        'sales_count': 0,
    },
    {
        'category': 'emplois',
        'name': 'Offre — Commercial marketplace',
        'price': Decimal('0'),
        'brand': 'Duno360',
        'description': 'Prospection vendeurs, commission attractive.',
        'image_url': 'https://images.unsplash.com/photo-1600880292203-757bb62b4baf?auto=format&fit=crop&w=1200&q=80',
        'sales_count': 0,
    },
    {
        'category': 'recherche',
        'name': 'Recherche appartement 2 chambres',
        'price': Decimal('0'),
        'brand': 'Annonce',
        'description': 'Budget 150 000 FCFA/mois, quartier calme, parking souhaité.',
        'image_url': 'https://images.pexels.com/photos/2724749/pexels-photo-2724749.jpeg?auto=compress&cs=tinysrgb&w=1200',
        'sales_count': 0,
    },
    {
        'category': 'recherche',
        'name': 'Recherche véhicule familial SUV',
        'price': Decimal('0'),
        'brand': 'Annonce',
        'description': 'Budget 5 M FCFA max, bon état, climatisation obligatoire.',
        'image_url': 'https://images.unsplash.com/photo-1519641471654-76ce0107ad1b?auto=format&fit=crop&w=1200&q=80',
        'sales_count': 0,
    },
]

COURSES = [
    {
        'category': 'formations',
        'title': 'Python & Django — Développement web',
        'price': Decimal('45000'),
        'instructor': 'Duno360 Academy',
        'description': 'Créez des applications web complètes avec Django, HTML, CSS et déploiement.',
        'image_url': 'https://images.unsplash.com/photo-1516321318423-f06f85b504e3?auto=format&fit=crop&w=1200&q=80',
        'duration_hours': Decimal('24'),
        'lessons_count': 48,
        'featured': True,
    },
    {
        'category': 'formations',
        'title': 'Marketing digital & e-commerce',
        'price': Decimal('35000'),
        'instructor': 'Duno360 Academy',
        'description': 'SEO, réseaux sociaux, publicité en ligne et vente sur marketplace.',
        'image_url': 'https://images.unsplash.com/photo-1460925895917-afdab827c52f?auto=format&fit=crop&w=1200&q=80',
        'duration_hours': Decimal('18'),
        'lessons_count': 36,
        'featured': True,
    },
]

SUPERMARKET_ITEMS = [
    {
        'category': 'agriculture-alimentation',
        'name': 'Tomates fraîches bio — 1 kg',
        'price': Decimal('1200'),
        'brand': 'Ferme Locale',
        'description': 'Tomates cultivées localement, récolte du jour.',
        'image_url': 'https://images.unsplash.com/photo-1592924357888-277fc67e288b?auto=format&fit=crop&w=1200&q=80',
        'unit': 'kg',
        'is_organic': True,
        'featured': True,
    },
    {
        'category': 'agriculture-alimentation',
        'name': 'Riz parfumé local — sac 5 kg',
        'price': Decimal('4500'),
        'brand': 'AgriPlus',
        'description': 'Riz de qualité supérieure, origine locale.',
        'image_url': 'https://images.unsplash.com/photo-1586201375761-83865001e31c?auto=format&fit=crop&w=1200&q=80',
        'unit': 'bag',
    },
    {
        'category': 'supermarche',
        'name': 'Lait entier UHT — pack 6',
        'price': Decimal('3200'),
        'brand': 'DairyFresh',
        'description': 'Lait 1 L × 6 briques, conservation longue.',
        'image_url': 'https://images.unsplash.com/photo-1563636619-e9143da7973b?auto=format&fit=crop&w=1200&q=80',
        'unit': 'pack',
        'featured': True,
    },
    {
        'category': 'supermarche',
        'name': 'Pain complet artisanal',
        'price': Decimal('800'),
        'brand': 'Boulangerie Duno',
        'description': 'Pain frais cuit le matin, sans conservateurs.',
        'image_url': 'https://images.unsplash.com/photo-1509440159596-0249088772ff?auto=format&fit=crop&w=1200&q=80',
        'unit': 'piece',
    },
]


def _download_image(url):
    request = Request(url, headers={'User-Agent': 'Duno360SeedBot/1.0'})
    with urlopen(request, timeout=45) as response:
        return response.read()


def _unique_slug(model, base_slug):
    slug = base_slug
    counter = 1
    while model.objects.filter(slug=slug).exists():
        slug = f'{base_slug}-{counter}'
        counter += 1
    return slug


def _save_image_field(instance, field_name, url, prefix):
    if not url:
        return False
    try:
        raw = _download_image(url)
    except (URLError, OSError, TimeoutError) as exc:
        return str(exc)
    ext = 'jpg'
    if '.png' in url.lower():
        ext = 'png'
    elif '.webp' in url.lower():
        ext = 'webp'
    filename = f'{prefix}-{uuid.uuid4().hex[:10]}.{ext}'
    getattr(instance, field_name).save(filename, ContentFile(raw), save=False)
    return True


class Command(BaseCommand):
    help = 'Fill home-page categories with admin-owned items and download product images.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--skip-download',
            action='store_true',
            help='Create items without downloading images (URLs stored only).',
        )
        parser.add_argument(
            '--force-images',
            action='store_true',
            help='Re-download images for items that already exist but have no image.',
        )

    def handle(self, *args, **options):
        skip_download = options['skip_download']
        force_images = options['force_images']

        admin = Manager.objects.filter(is_admin=True).order_by('id').first()
        admin_label = admin.name if admin else 'Administrator'
        self.stdout.write(f'Admin owner: {admin_label} (marketplace items use vendor=NULL)')

        category_map = {}
        for idx, (name, slug, section) in enumerate(PRODUCT_CATEGORIES, start=1):
            category, _ = Category.objects.update_or_create(
                slug=slug,
                defaults={
                    'name': name,
                    'section': section,
                    'description': f'Catégorie {name} — Duno360',
                    'display_order': idx,
                    'is_active': True,
                },
            )
            category_map[slug] = category

        created_products = 0
        updated_images = 0
        for item in PRODUCTS:
            category = category_map.get(item['category'])
            product = Product.objects.filter(name=item['name'], category=category).first()
            created = product is None
            if created:
                base_slug = slugify(item['name']) or f'item-{uuid.uuid4().hex[:8]}'
                product = Product(
                    vendor=None,
                    name=item['name'],
                    slug=_unique_slug(Product, base_slug),
                    description=item['description'],
                    price=item['price'],
                    original_price=item['price'] + Decimal('5000') if item['price'] > 0 else None,
                    category=category,
                    stock=25,
                    brand=item.get('brand', ''),
                    condition='new',
                    is_active=True,
                    is_featured=item.get('featured', False),
                    sales_count=item.get('sales_count', 0),
                )
                product.save()
                created_products += 1
            if not skip_download and (created or force_images or not product.image):
                result = _save_image_field(product, 'image', item['image_url'], 'product')
                if result is True:
                    product.save(update_fields=['image'])
                    updated_images += 1
                elif isinstance(result, str):
                    self.stdout.write(self.style.WARNING(f'Image failed for {product.name}: {result}'))

        created_courses = 0
        for item in COURSES:
            category = category_map.get(item['category'])
            course = Course.objects.filter(title=item['title'], category=category).first()
            created = course is None
            if created:
                base_slug = slugify(item['title']) or f'course-{uuid.uuid4().hex[:8]}'
                course = Course(
                    vendor=None,
                    title=item['title'],
                    slug=_unique_slug(Course, base_slug),
                    description=item['description'],
                    price=item['price'],
                    original_price=item['price'] + Decimal('8000'),
                    category=category,
                    instructor=item['instructor'],
                    duration_hours=item['duration_hours'],
                    lessons_count=item['lessons_count'],
                    stock=999,
                    is_active=True,
                    is_featured=item.get('featured', False),
                    enrollment_count=15,
                )
                course.save()
                created_courses += 1
            if not skip_download and (created or force_images or not course.image):
                result = _save_image_field(course, 'image', item['image_url'], 'course')
                if result is True:
                    course.save(update_fields=['image'])
                    updated_images += 1

        created_super = 0
        for item in SUPERMARKET_ITEMS:
            category = category_map.get(item['category'])
            sm_item = SupermarketItem.objects.filter(name=item['name'], category=category).first()
            created = sm_item is None
            if created:
                base_slug = slugify(item['name']) or f'super-{uuid.uuid4().hex[:8]}'
                sm_item = SupermarketItem(
                    vendor=None,
                    name=item['name'],
                    slug=_unique_slug(SupermarketItem, base_slug),
                    description=item['description'],
                    price=item['price'],
                    original_price=item['price'] + Decimal('500'),
                    category=category,
                    stock=100,
                    brand=item.get('brand', ''),
                    unit=item.get('unit', 'piece'),
                    is_organic=item.get('is_organic', False),
                    is_active=True,
                    is_featured=item.get('featured', False),
                    sales_count=10,
                )
                sm_item.save()
                created_super += 1
            if not skip_download and (created or force_images or not sm_item.image):
                result = _save_image_field(sm_item, 'image', item['image_url'], 'supermarket')
                if result is True:
                    sm_item.save(update_fields=['image'])
                    updated_images += 1

        cache.delete('home:best_deals:v3:24')

        self.stdout.write(self.style.SUCCESS(
            f'Categories: {len(category_map)} | '
            f'New products: {created_products} | '
            f'New courses: {created_courses} | '
            f'New supermarket: {created_super} | '
            f'Images saved: {updated_images}'
        ))
