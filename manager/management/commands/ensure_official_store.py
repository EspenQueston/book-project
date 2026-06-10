from django.core.management.base import BaseCommand

from manager.official_store import ensure_official_store


class Command(BaseCommand):
    help = 'Create Duno360 Official Store and assign orphan admin listings to it.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--no-backfill',
            action='store_true',
            help='Only ensure the vendor record exists; do not reassign listings.',
        )

    def handle(self, *args, **options):
        vendor, created = ensure_official_store(backfill=not options['no_backfill'])
        action = 'created' if created else 'updated'
        self.stdout.write(self.style.SUCCESS(
            f'Official store {action}: {vendor.company_name} (id={vendor.pk})'
        ))
