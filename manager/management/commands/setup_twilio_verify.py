"""Check Twilio Verify setup and optionally create a Verify Service."""
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = 'Validate Twilio credentials and list or create a Verify Service (SID starts with VA...)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--create',
            action='store_true',
            help='Create a Verify Service if none exists on the account',
        )

    def handle(self, *args, **options):
        sid = settings.TWILIO_ACCOUNT_SID
        token = settings.TWILIO_AUTH_TOKEN
        service_sid = settings.TWILIO_VERIFY_SERVICE_SID

        if not sid or not token:
            raise CommandError(
                'Set TWILIO_ACCOUNT_SID and TWILIO_AUTH_TOKEN in .env first.'
            )

        try:
            from twilio.rest import Client
        except ImportError as exc:
            raise CommandError('Install twilio: pip install twilio>=9.0.0') from exc

        client = Client(sid, token)
        self.stdout.write(f'Account SID: {sid[:8]}...')

        try:
            services = client.verify.v2.services.list(limit=20)
        except Exception as exc:
            raise CommandError(f'Twilio API error: {exc}') from exc

        if services:
            self.stdout.write(self.style.SUCCESS('\nVerify Services on this account:'))
            for svc in services:
                marker = '  <-- configured in .env' if svc.sid == service_sid else ''
                self.stdout.write(f'  {svc.sid}  {svc.friendly_name}{marker}')
        else:
            self.stdout.write(self.style.WARNING('\nNo Verify Service found on this account.'))

        if service_sid:
            if not service_sid.startswith('VA'):
                self.stdout.write(self.style.ERROR(
                    f'\nTWILIO_VERIFY_SERVICE_SID={service_sid} is invalid '
                    '(must start with VA..., not NUT... or other prefixes).'
                ))
            else:
                try:
                    svc = client.verify.v2.services(service_sid).fetch()
                    self.stdout.write(self.style.SUCCESS(
                        f'\nConfigured service OK: {svc.sid} ({svc.friendly_name})'
                    ))
                    self.stdout.write(self.style.SUCCESS(
                        'TWILIO_VERIFY_ENABLED is active — dual email + SMS signup enabled.'
                    ))
                    return
                except Exception as exc:
                    self.stdout.write(self.style.ERROR(
                        f'\nConfigured service not found: {exc}'
                    ))

        if options['create']:
            svc = client.verify.v2.services.create(
                friendly_name='DUNO 360 Signup Verification',
            )
            self.stdout.write(self.style.SUCCESS(
                f'\nCreated Verify Service: {svc.sid}'
            ))
            self.stdout.write(
                f'\nAdd this line to your .env file:\n'
                f'TWILIO_VERIFY_SERVICE_SID={svc.sid}\n'
                f'\nThen restart runserver.'
            )
            return

        self.stdout.write(
            '\nNext steps:\n'
            '  1. Create a service: python manage.py setup_twilio_verify --create\n'
            '     OR in console: https://console.twilio.com/us1/develop/verify/services\n'
            '  2. Copy the SID (starts with VA...) into .env as TWILIO_VERIFY_SERVICE_SID\n'
            '  3. Restart runserver\n'
        )
