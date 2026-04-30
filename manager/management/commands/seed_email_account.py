"""
Management command to seed the default email account (espen@profitexb2b.com).
Run:  python manage.py seed_email_account
"""
from django.core.management.base import BaseCommand
from manager.models import EmailAccount


class Command(BaseCommand):
    help = 'Create or update the default email account for espen@profitexb2b.com'

    def handle(self, *args, **options):
        account, created = EmailAccount.objects.update_or_create(
            email_address='espen@profitexb2b.com',
            defaults={
                'name': 'ProfitexB2B',
                'imap_host': 'mail.profitexb2b.com',
                'imap_port': 993,
                'imap_use_ssl': True,
                'smtp_host': 'mail.profitexb2b.com',
                'smtp_port': 465,
                'smtp_use_tls': False,  # Port 465 uses SMTP_SSL, NOT STARTTLS
                'username': 'espen@profitexb2b.com',
                'password': ')[&.b6aWqT',
                'is_active': True,
                'is_default': True,
            },
        )
        if created:
            self.stdout.write(self.style.SUCCESS('Email account created: espen@profitexb2b.com'))
        else:
            self.stdout.write(self.style.SUCCESS('Email account updated: espen@profitexb2b.com'))

        # Make sure no other account is default
        EmailAccount.objects.exclude(id=account.id).update(is_default=False)
