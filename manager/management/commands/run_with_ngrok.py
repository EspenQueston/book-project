"""
Django management command to start the dev server with ngrok tunnel.

Usage:
    python manage.py run_with_ngrok [--port 8000]

This will:
1. Start an ngrok tunnel pointing to localhost:<port>
2. Auto-configure MTN_MOMO_CALLBACK_URL and AIRTEL_MONEY_CALLBACK_URL
3. Update ALLOWED_HOSTS and CSRF_TRUSTED_ORIGINS
4. Print the public URL and callback endpoints
5. Start the Django dev server
"""

import os
import sys
import signal
import threading
from django.core.management.base import BaseCommand
from django.conf import settings


class Command(BaseCommand):
    help = 'Start Django development server with ngrok tunnel for MoMo callbacks'

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

        # Set auth token
        auth_token = getattr(settings, 'NGROK_AUTH_TOKEN', '')
        if auth_token:
            conf.get_default().auth_token = auth_token

        # Start tunnel
        self.stdout.write(self.style.WARNING(
            f'Starting ngrok tunnel on port {port}...'))
        tunnel = ngrok.connect(port, 'http')
        public_url = tunnel.public_url

        # Ensure HTTPS
        if public_url.startswith('http://'):
            public_url = public_url.replace('http://', 'https://')

        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS('=' * 60))
        self.stdout.write(self.style.SUCCESS(
            f'  ngrok tunnel active!'))
        self.stdout.write(self.style.SUCCESS(
            f'  Public URL: {public_url}'))
        self.stdout.write(self.style.SUCCESS('=' * 60))
        self.stdout.write('')

        # Configure callback URLs
        mtn_callback = f'{public_url}/manager/api/payment/mtn/callback/'
        airtel_callback = f'{public_url}/manager/api/payment/airtel/callback/'

        settings.MTN_MOMO_CALLBACK_URL = mtn_callback
        settings.AIRTEL_MONEY_CALLBACK_URL = airtel_callback

        # Update ALLOWED_HOSTS
        ngrok_host = public_url.replace('https://', '').replace('http://', '')
        if ngrok_host not in settings.ALLOWED_HOSTS:
            settings.ALLOWED_HOSTS.append(ngrok_host)

        # Update CSRF_TRUSTED_ORIGINS
        if public_url not in settings.CSRF_TRUSTED_ORIGINS:
            settings.CSRF_TRUSTED_ORIGINS.append(public_url)

        self.stdout.write(self.style.NOTICE('Callback endpoints:'))
        self.stdout.write(f'  MTN MoMo:     {mtn_callback}')
        self.stdout.write(f'  Airtel Money: {airtel_callback}')
        self.stdout.write('')
        self.stdout.write(self.style.NOTICE(
            'Configure these URLs in your MTN/Airtel developer dashboard.'))
        self.stdout.write('')
        self.stdout.write(self.style.NOTICE('Other useful endpoints:'))
        self.stdout.write(
            f'  Initiate payment: POST {public_url}/manager/api/payment/initiate/')
        self.stdout.write(
            f'  Check status:     GET  {public_url}/manager/api/payment/status/?order_number=...')
        self.stdout.write('')

        # Now start the Django dev server
        self.stdout.write(self.style.WARNING(
            f'Starting Django dev server on 0.0.0.0:{port}...'))
        self.stdout.write('')

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
