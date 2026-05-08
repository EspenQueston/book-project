"""
Management command to seed KKiaPay supported countries.

Usage:
    python manage.py seed_kkiapay_countries          # Insert or update all countries
    python manage.py seed_kkiapay_countries --reset  # Delete all then re-insert
"""
from django.core.management.base import BaseCommand
from manager.models import KkiapayCountry


KKIAPAY_COUNTRIES_DATA = [
    {
        'iso_code': 'BJ',
        'name_fr': 'Bénin',
        'name_en': 'Benin',
        'phone_code': '+229',
        'currency_code': 'XOF',
        'currency_name_fr': 'Franc CFA (UEMOA)',
        'mobile_operators': ['MTN', 'Moov'],
        'flag_emoji': '🇧🇯',
        'display_order': 1,
    },
    {
        'iso_code': 'CI',
        'name_fr': "Côte d'Ivoire",
        'name_en': 'Ivory Coast',
        'phone_code': '+225',
        'currency_code': 'XOF',
        'currency_name_fr': 'Franc CFA (UEMOA)',
        'mobile_operators': ['MTN', 'Orange', 'Moov', 'Wave'],
        'flag_emoji': '🇨🇮',
        'display_order': 2,
    },
    {
        'iso_code': 'TG',
        'name_fr': 'Togo',
        'name_en': 'Togo',
        'phone_code': '+228',
        'currency_code': 'XOF',
        'currency_name_fr': 'Franc CFA (UEMOA)',
        'mobile_operators': ['T-Money', 'Flooz'],
        'flag_emoji': '🇹🇬',
        'display_order': 3,
    },
    {
        'iso_code': 'SN',
        'name_fr': 'Sénégal',
        'name_en': 'Senegal',
        'phone_code': '+221',
        'currency_code': 'XOF',
        'currency_name_fr': 'Franc CFA (UEMOA)',
        'mobile_operators': ['Wave', 'Orange', 'Free'],
        'flag_emoji': '🇸🇳',
        'display_order': 4,
    },
    {
        'iso_code': 'NE',
        'name_fr': 'Niger',
        'name_en': 'Niger',
        'phone_code': '+227',
        'currency_code': 'XOF',
        'currency_name_fr': 'Franc CFA (UEMOA)',
        'mobile_operators': ['Airtel', 'Orange'],
        'flag_emoji': '🇳🇪',
        'display_order': 5,
    },
    {
        'iso_code': 'GN',
        'name_fr': 'Guinée',
        'name_en': 'Guinea',
        'phone_code': '+224',
        'currency_code': 'GNF',
        'currency_name_fr': 'Franc guinéen',
        'mobile_operators': ['Orange', 'MTN'],
        'flag_emoji': '🇬🇳',
        'display_order': 6,
    },
    {
        'iso_code': 'BF',
        'name_fr': 'Burkina Faso',
        'name_en': 'Burkina Faso',
        'phone_code': '+226',
        'currency_code': 'XOF',
        'currency_name_fr': 'Franc CFA (UEMOA)',
        'mobile_operators': ['Orange', 'Moov'],
        'flag_emoji': '🇧🇫',
        'display_order': 7,
    },
    {
        'iso_code': 'ML',
        'name_fr': 'Mali',
        'name_en': 'Mali',
        'phone_code': '+223',
        'currency_code': 'XOF',
        'currency_name_fr': 'Franc CFA (UEMOA)',
        'mobile_operators': ['Orange', 'Moov'],
        'flag_emoji': '🇲🇱',
        'display_order': 8,
    },
    {
        'iso_code': 'CM',
        'name_fr': 'Cameroun',
        'name_en': 'Cameroon',
        'phone_code': '+237',
        'currency_code': 'XAF',
        'currency_name_fr': 'Franc CFA (CEMAC)',
        'mobile_operators': ['MTN', 'Orange'],
        'flag_emoji': '🇨🇲',
        'display_order': 9,
    },
]


class Command(BaseCommand):
    help = 'Seed KKiaPay supported countries into the kkiapay_country table'

    def add_arguments(self, parser):
        parser.add_argument(
            '--reset',
            action='store_true',
            help='Delete existing records before inserting',
        )

    def handle(self, *args, **options):
        if options['reset']:
            deleted, _ = KkiapayCountry.objects.all().delete()
            self.stdout.write(self.style.WARNING(f'Deleted {deleted} existing records.'))

        created_count = 0
        updated_count = 0

        for data in KKIAPAY_COUNTRIES_DATA:
            iso_code = data.pop('iso_code')
            obj, created = KkiapayCountry.objects.update_or_create(
                iso_code=iso_code,
                defaults=data,
            )
            data['iso_code'] = iso_code  # restore for possible reuse
            if created:
                created_count += 1
            else:
                updated_count += 1
            self.stdout.write(
                f"  {'[CREATED]' if created else '[UPDATED]'} {obj}"
            )

        self.stdout.write(
            self.style.SUCCESS(
                f'\nDone: {created_count} created, {updated_count} updated. '
                f'Total active countries: {KkiapayCountry.objects.filter(is_active=True).count()}'
            )
        )
