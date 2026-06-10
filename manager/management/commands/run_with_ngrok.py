"""
Django management command to start the dev server with ngrok tunnel.

Usage:
    python manage.py run_with_ngrok [--port 8000]

Configures KKiaPay + PawaPay webhook URLs for local payment testing.
"""

import os
import sys
import signal
from django.core.management.base import BaseCommand
from django.conf import settings


class Command(BaseCommand):
    help = 'Start Django dev server with ngrok tunnel for payment webhooks'

    def add_arguments(self, parser):
        parser.add_argument(
            '--port', type=int, default=8000,
            help='Port to run the dev server on (default: 8000)')

    def handle(self, *args, **options):
        port = options['port']

        try:
            from pyngrok import ngrok, conf
        except ImportError:
            self.stderr.write(self.style.ERROR(
                'pyngrok is not installed. Run: pip install pyngrok'))
            return

        auth_token = getattr(settings, 'NGROK_AUTH_TOKEN', '')
        if auth_token:
            conf.get_default().auth_token = auth_token

        self.stdout.write(self.style.WARNING(
            f'Starting ngrok tunnel on port {port}...'))
        tunnel = ngrok.connect(port, 'http')
        public_url = tunnel.public_url
        if public_url.startswith('http://'):
            public_url = public_url.replace('http://', 'https://')

        base = public_url + '/manager'
        kkiapay_webhook = f'{base}/api/payment/kkiapay/webhook/'
        pawapay_deposits = f'{base}/api/payment/pawapay/callback/deposits/'
        pawapay_payouts = f'{base}/api/payment/pawapay/callback/payouts/'
        pawapay_refunds = f'{base}/api/payment/pawapay/callback/refunds/'

        settings.NGROK_PUBLIC_URL = public_url
        settings.PAWAPAY_CALLBACK_DEPOSITS = pawapay_deposits
        settings.PAWAPAY_CALLBACK_PAYOUTS = pawapay_payouts
        settings.PAWAPAY_CALLBACK_REFUNDS = pawapay_refunds

        ngrok_host = public_url.replace('https://', '').replace('http://', '')
        if ngrok_host not in settings.ALLOWED_HOSTS:
            settings.ALLOWED_HOSTS.append(ngrok_host)
        if public_url not in settings.CSRF_TRUSTED_ORIGINS:
            settings.CSRF_TRUSTED_ORIGINS.append(public_url)

        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS('=' * 60))
        self.stdout.write(self.style.SUCCESS('  ngrok tunnel active!'))
        self.stdout.write(self.style.SUCCESS(f'  Public URL: {public_url}'))
        self.stdout.write(self.style.SUCCESS('=' * 60))
        self.stdout.write('')
        self.stdout.write(self.style.NOTICE('Webhook URLs — copy to provider dashboards:'))
        self.stdout.write(f'  KKiaPay:  {kkiapay_webhook}')
        self.stdout.write(f'  PawaPay Deposits: {pawapay_deposits}')
        self.stdout.write(f'  PawaPay Payouts:  {pawapay_payouts}')
        self.stdout.write(f'  PawaPay Refunds:  {pawapay_refunds}')
        self.stdout.write('')
        self.stdout.write(self.style.WARNING(
            f'Starting Django dev server on 0.0.0.0:{port}...'))

        from django.core.management import call_command

        def cleanup(signum, frame):
            self.stdout.write(self.style.WARNING('\nShutting down ngrok...'))
            ngrok.disconnect(tunnel.public_url)
            ngrok.kill()
            sys.exit(0)

        signal.signal(signal.SIGINT, cleanup)
        signal.signal(signal.SIGTERM, cleanup)

        try:
            call_command('runserver', f'0.0.0.0:{port}')
        finally:
            ngrok.disconnect(tunnel.public_url)
            ngrok.kill()
