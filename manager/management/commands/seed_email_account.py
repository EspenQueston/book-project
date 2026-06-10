"""
Seed the default platform email account (admin@duno360.com via Zoho SMTP).
Run:  python manage.py seed_email_account
"""
from django.core.management.base import BaseCommand

from manager.email_utils import ensure_platform_email_account, platform_email_address


class Command(BaseCommand):
    help = 'Create or update the default DUNO 360 email account from .env settings'

    def handle(self, *args, **options):
        email = platform_email_address()
        account = ensure_platform_email_account()
        if not account:
            self.stdout.write(self.style.ERROR('EMAIL_HOST_USER / CONTACT_EMAIL is not configured.'))
            return

        self.stdout.write(self.style.SUCCESS(f'Email account ready: {account.name} <{email}>'))
