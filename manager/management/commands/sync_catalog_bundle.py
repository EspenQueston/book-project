"""
Export / import the public catalog (books + marketplace) for local → production sync.

Usage (local Windows):
  .venv\\Scripts\\python.exe manage.py sync_catalog_bundle export

Usage (production VPS — after uploading deploy/catalog_export.json):
  sudo -u duno360 bash -lc 'cd /opt/duno360/app && set -a && . /opt/duno360/.env && set +a && \\
    .venv/bin/python manage.py sync_catalog_bundle import --replace'
"""
from __future__ import annotations

import json
from pathlib import Path

from django.apps import apps
from django.core import serializers
from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError
from django.db import connection, transaction

# Fixture load order (parents before children).
CATALOG_LABELS = [
    'manager.bookcategory',
    'manager.publisher',
    'manager.book',
    'manager.author',
    'manager.siteuser',
    'manager.vendor',
    'manager.vendorbook',
    'marketplace.category',
    'marketplace.product',
    'marketplace.productattribute',
    'marketplace.course',
    'marketplace.coursesection',
    'marketplace.courselesson',
    'marketplace.supermarketitem',
    'marketplace.supermarketitemattribute',
    'marketplace.flashsale',
]

DEFAULT_EXPORT = Path('deploy/catalog_export.json')

# Child-first deletion order for --replace.
PURGE_MODELS = [
    'marketplace.CourseProgress',
    'marketplace.CourseLesson',
    'marketplace.CourseSection',
    'marketplace.ProductAttribute',
    'marketplace.SupermarketItemAttribute',
    'marketplace.PostDeliveryReview',
    'marketplace.FlashSale',
    'marketplace.MarketplaceCartItem',
    'marketplace.Product',
    'marketplace.Course',
    'marketplace.SupermarketItem',
    'marketplace.Category',
    'manager.CartItem',
    'manager.Wishlist',
    'manager.OrderItem',
    'manager.VendorBook',
    'manager.Author',
    'manager.Book',
    'manager.BookCategory',
    'manager.Publisher',
    'manager.Vendor',
]

# SiteUser is handled separately (only rows present in the export file).

SEQUENCE_TABLES = [
    ('book', 'id'),
    ('publisher', 'id'),
    ('author', 'id'),
    ('book_category', 'id'),
    ('site_user', 'id'),
    ('vendor', 'id'),
    ('vendor_book', 'id'),
    ('marketplace_category', 'id'),
    ('marketplace_product', 'id'),
    ('marketplace_product_attribute', 'id'),
    ('marketplace_course', 'id'),
    ('marketplace_course_section', 'id'),
    ('marketplace_course_lesson', 'id'),
    ('marketplace_supermarket_item', 'id'),
    ('marketplace_supermarket_item_attribute', 'id'),
    ('marketplace_flash_sale', 'id'),
]


def _reset_sequences() -> None:
    """Reset Postgres serial sequences after fixture import (whitelist table names only)."""
    with connection.cursor() as cursor:
        for table, column in SEQUENCE_TABLES:
            # Table/column names come from a fixed whitelist — safe to embed as identifiers.
            cursor.execute(
                f"""
                SELECT setval(
                    pg_get_serial_sequence('{table}', '{column}'),
                    COALESCE((SELECT MAX({column}) FROM {table}), 1)
                )
                """
            )


class Command(BaseCommand):
    help = 'Export or import the books + marketplace catalog bundle for production sync.'

    def add_arguments(self, parser):
        sub = parser.add_subparsers(dest='action', required=True)

        export = sub.add_parser('export', help='Export local catalog to JSON')
        export.add_argument(
            '--output', '-o', default=str(DEFAULT_EXPORT),
            help=f'Output JSON path (default: {DEFAULT_EXPORT})',
        )

        imp = sub.add_parser('import', help='Import catalog JSON into the current database')
        imp.add_argument(
            '--input', '-i', default=str(DEFAULT_EXPORT),
            help=f'Input JSON path (default: {DEFAULT_EXPORT})',
        )
        imp.add_argument(
            '--replace', action='store_true',
            help='Delete existing catalog rows before import (recommended on production)',
        )

    def handle(self, *args, **options):
        action = options['action']
        if action == 'export':
            self._export(options['output'])
        elif action == 'import':
            self._import(options['input'], options['replace'])

    def _export(self, output_path: str) -> None:
        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        call_command(
            'dumpdata',
            *CATALOG_LABELS,
            '--natural-foreign',
            '--natural-primary',
            '--indent', '2',
            stdout=path.open('w', encoding='utf-8'),
        )
        count = len(json.loads(path.read_text(encoding='utf-8')))
        self.stdout.write(self.style.SUCCESS(
            f'Exported {count} objects to {path.resolve()}'
        ))
        self.stdout.write(
            'Upload this file to /opt/duno360/app/deploy/catalog_export.json on the VPS, '
            'then run: manage.py sync_catalog_bundle import --replace'
        )

    def _import(self, input_path: str, replace: bool) -> None:
        path = Path(input_path)
        if not path.exists():
            raise CommandError(f'File not found: {path}')

        payload = json.loads(path.read_text(encoding='utf-8'))
        if not payload:
            raise CommandError('Export file is empty.')

        export_siteuser_ids = {
            row['pk'] for row in payload
            if row.get('model') == 'manager.siteuser'
        }
        export_siteuser_emails = {
            row['fields']['email'] for row in payload
            if row.get('model') == 'manager.siteuser'
        }

        if not replace:
            self.stdout.write(self.style.WARNING(
                'Loading without --replace may fail on duplicate primary keys. '
                'Use --replace on production.'
            ))

        with transaction.atomic():
            if replace:
                self._purge_catalog(export_siteuser_ids, export_siteuser_emails)
            for obj in serializers.deserialize('json', json.dumps(payload)):
                obj.save()

        _reset_sequences()

        self.stdout.write(self.style.SUCCESS(
            f'Imported {len(payload)} objects from {path}'
        ))

    def _purge_catalog(self, siteuser_ids: set, siteuser_emails: set) -> None:
        self.stdout.write('Purging existing catalog data…')
        for label in PURGE_MODELS:
            model = apps.get_model(label)
            deleted, _ = model.objects.all().delete()
            if deleted:
                self.stdout.write(f'  - {label}: {deleted} rows')
        if siteuser_ids or siteuser_emails:
            from manager.models import SiteUser
            qs = SiteUser.objects.filter(id__in=siteuser_ids) | SiteUser.objects.filter(
                email__in=siteuser_emails
            )
            deleted, _ = qs.distinct().delete()
            if deleted:
                self.stdout.write(f'  - manager.SiteUser (export only): {deleted} rows')
