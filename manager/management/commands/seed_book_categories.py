"""Seed BookCategory entries and assign existing books to categories based on keywords."""
from django.core.management.base import BaseCommand
from manager.models import BookCategory, Book


CATEGORIES = [
    {
        'name': '文学小说', 'name_en': 'Fiction', 'name_fr': 'Fiction',
        'slug': 'fiction', 'icon': 'fas fa-feather-alt', 'color': '#8b5cf6',
        'display_order': 1,
        'keywords': ['novel', 'fiction', 'story', 'tales', 'roman', '小说', '故事'],
    },
    {
        'name': '科学技术', 'name_en': 'Science & Tech', 'name_fr': 'Science & Tech',
        'slug': 'science-tech', 'icon': 'fas fa-flask', 'color': '#06b6d4',
        'display_order': 2,
        'keywords': ['science', 'tech', 'computer', 'programming', 'python', 'java',
                     'algorithm', 'data', 'physics', 'chemistry', 'engineering', '科学', '技术'],
    },
    {
        'name': '商业经济', 'name_en': 'Business', 'name_fr': 'Affaires',
        'slug': 'business', 'icon': 'fas fa-chart-line', 'color': '#10b981',
        'display_order': 3,
        'keywords': ['business', 'economy', 'finance', 'marketing', 'management',
                     'invest', 'money', 'stock', '商业', '经济', '金融'],
    },
    {
        'name': '历史传记', 'name_en': 'History', 'name_fr': 'Histoire',
        'slug': 'history', 'icon': 'fas fa-landmark', 'color': '#f59e0b',
        'display_order': 4,
        'keywords': ['history', 'biography', 'war', 'ancient', 'century', '历史', '传记'],
    },
    {
        'name': '教育学习', 'name_en': 'Education', 'name_fr': 'Éducation',
        'slug': 'education', 'icon': 'fas fa-graduation-cap', 'color': '#3b82f6',
        'display_order': 5,
        'keywords': ['education', 'learn', 'study', 'textbook', 'school', 'exam',
                     'course', 'guide', '教育', '学习', '教材'],
    },
    {
        'name': '艺术设计', 'name_en': 'Art & Design', 'name_fr': 'Art & Design',
        'slug': 'art-design', 'icon': 'fas fa-palette', 'color': '#ec4899',
        'display_order': 6,
        'keywords': ['art', 'design', 'photo', 'paint', 'draw', 'music',
                     'architecture', '艺术', '设计', '绘画'],
    },
    {
        'name': '生活健康', 'name_en': 'Lifestyle', 'name_fr': 'Mode de vie',
        'slug': 'lifestyle', 'icon': 'fas fa-heartbeat', 'color': '#ef4444',
        'display_order': 7,
        'keywords': ['health', 'cook', 'food', 'travel', 'fitness', 'diet',
                     'yoga', 'self-help', '健康', '生活', '旅行', '美食'],
    },
    {
        'name': '儿童读物', 'name_en': 'Kids', 'name_fr': 'Enfants',
        'slug': 'kids', 'icon': 'fas fa-child', 'color': '#f97316',
        'display_order': 8,
        'keywords': ['kid', 'child', 'fairy', 'picture book', 'nursery',
                     'young', 'junior', '儿童', '童话', '少儿'],
    },
    {
        'name': '哲学心理', 'name_en': 'Philosophy', 'name_fr': 'Philosophie',
        'slug': 'philosophy', 'icon': 'fas fa-brain', 'color': '#6366f1',
        'display_order': 9,
        'keywords': ['philosophy', 'psychology', 'mind', 'think', 'logic',
                     'soul', 'consciousness', '哲学', '心理'],
    },
    {
        'name': '综合其他', 'name_en': 'General', 'name_fr': 'Général',
        'slug': 'general', 'icon': 'fas fa-globe', 'color': '#64748b',
        'display_order': 10,
        'keywords': [],
    },
]


class Command(BaseCommand):
    help = 'Seed book categories and assign existing books'

    def handle(self, *args, **options):
        created_count = 0
        for cat_data in CATEGORIES:
            kw = cat_data.pop('keywords')
            obj, created = BookCategory.objects.update_or_create(
                slug=cat_data['slug'],
                defaults=cat_data,
            )
            cat_data['keywords'] = kw
            if created:
                created_count += 1
            self.stdout.write(f"  {'Created' if created else 'Updated'}: {obj.name}")

        self.stdout.write(self.style.SUCCESS(f'\n{created_count} new categories created.'))

        uncategorized = Book.objects.filter(category__isnull=True)
        assigned = 0
        general = BookCategory.objects.filter(slug='general').first()

        for book in uncategorized:
            text = f"{book.name} {book.description or ''}".lower()
            matched = False
            for cat_data in CATEGORIES:
                if not cat_data['keywords']:
                    continue
                for kw in cat_data['keywords']:
                    if kw.lower() in text:
                        cat = BookCategory.objects.get(slug=cat_data['slug'])
                        book.category = cat
                        book.save(update_fields=['category'])
                        assigned += 1
                        matched = True
                        break
                if matched:
                    break
            if not matched and general:
                book.category = general
                book.save(update_fields=['category'])
                assigned += 1

        self.stdout.write(self.style.SUCCESS(f'{assigned} books assigned to categories.'))
