"""
Django management command to provision MTN MoMo Sandbox credentials.

Usage:
    python manage.py setup_mtn_sandbox --subscription-key YOUR_KEY

This will:
1. Create a sandbox API User (UUID)
2. Generate an API Key for that user
3. Print the credentials to add to your .env file
"""

from django.core.management.base import BaseCommand
from django.conf import settings


class Command(BaseCommand):
    help = 'Provision MTN MoMo Sandbox API User and API Key'

    def add_arguments(self, parser):
        parser.add_argument(
            '--subscription-key', type=str,
            default=getattr(settings, 'MTN_MOMO_SUBSCRIPTION_KEY', ''),
            help='Your MTN MoMo Collection subscription key from the developer portal')
        parser.add_argument(
            '--callback-host', type=str, default='',
            help='Callback host URL (e.g., your ngrok URL)')

    def handle(self, *args, **options):
        sub_key = options['subscription_key']
        callback_host = options['callback_host']

        if not sub_key:
            self.stderr.write(self.style.ERROR(
                'Subscription key is required.\n'
                'Get it from https://momodeveloper.mtn.com/ → Collection → Subscribe\n'
                'Usage: python manage.py setup_mtn_sandbox '
                '--subscription-key YOUR_KEY'))
            return

        # Temporarily set the key so the service can use it
        settings.MTN_MOMO_SUBSCRIPTION_KEY = sub_key

        from manager.payments.mtn_momo import MTNMoMoService

        self.stdout.write(self.style.WARNING(
            'Provisioning MTN MoMo Sandbox credentials...'))
        self.stdout.write('')

        try:
            # Step 1: Create API User
            self.stdout.write('Step 1: Creating API User...')
            api_user = MTNMoMoService.create_sandbox_api_user(callback_host)
            self.stdout.write(self.style.SUCCESS(
                f'  API User (UUID): {api_user}'))

            # Step 2: Generate API Key
            self.stdout.write('Step 2: Generating API Key...')
            api_key = MTNMoMoService.create_sandbox_api_key(api_user)
            self.stdout.write(self.style.SUCCESS(
                f'  API Key: {api_key}'))

            self.stdout.write('')
            self.stdout.write(self.style.SUCCESS('=' * 60))
            self.stdout.write(self.style.SUCCESS(
                '  MTN MoMo Sandbox credentials ready!'))
            self.stdout.write(self.style.SUCCESS('=' * 60))
            self.stdout.write('')
            self.stdout.write(self.style.NOTICE(
                'Add these to your .env file:'))
            self.stdout.write('')
            self.stdout.write(f'MTN_MOMO_SUBSCRIPTION_KEY={sub_key}')
            self.stdout.write(f'MTN_MOMO_API_USER={api_user}')
            self.stdout.write(f'MTN_MOMO_API_KEY={api_key}')
            self.stdout.write(f'MTN_MOMO_ENVIRONMENT=sandbox')
            self.stdout.write(f'MTN_MOMO_CURRENCY=EUR')
            self.stdout.write('')
            self.stdout.write(self.style.NOTICE(
                'Sandbox test phone numbers:'))
            self.stdout.write('  Success:  46733123450')
            self.stdout.write('  Failed:   46733123451')
            self.stdout.write('  Pending:  46733123452')

        except Exception as e:
            self.stderr.write(self.style.ERROR(
                f'Error: {e}'))
            self.stderr.write(self.style.NOTICE(
                'Make sure your subscription key is correct and you have '
                'an active subscription on https://momodeveloper.mtn.com/'))
