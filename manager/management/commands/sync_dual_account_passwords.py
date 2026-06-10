from django.core.management.base import BaseCommand
from django.utils import timezone

from manager import models
from manager.auth_password import (
    get_linked_site_user_and_vendor,
    link_dual_accounts_by_email,
)


class Command(BaseCommand):
    help = 'Link SiteUser↔Vendor dual accounts by email and sync passwords (SiteUser wins).'

    def add_arguments(self, parser):
        parser.add_argument(
            '--email',
            type=str,
            default='',
            help='Sync a single email only (e.g. bizkey2024@gmail.com)',
        )

    def handle(self, *args, **options):
        email_filter = (options.get('email') or '').strip().lower()
        vendors = models.Vendor.objects.filter(is_active=True)
        if email_filter:
            vendors = vendors.filter(email__iexact=email_filter)

        linked = 0
        synced = 0
        seen_emails = set()

        for vendor in vendors.select_related('user'):
            email = (vendor.email or '').strip().lower()
            if not email or email in seen_emails:
                continue
            seen_emails.add(email)

            user, linked_vendor = get_linked_site_user_and_vendor(email)
            if not user and not linked_vendor:
                continue

            before_user_fk = linked_vendor.user_id if linked_vendor else None
            link_dual_accounts_by_email(email)
            linked_vendor = models.Vendor.objects.filter(email__iexact=email, is_active=True).first()
            if linked_vendor and linked_vendor.user_id and linked_vendor.user_id != before_user_fk:
                linked += 1

            user = models.SiteUser.objects.filter(email__iexact=email, is_active=True).first()
            if user and linked_vendor and linked_vendor.password != user.password:
                linked_vendor.password = user.password
                linked_vendor.save(update_fields=['password', 'updated_at'])
                synced += 1
                self.stdout.write(f'  synced password: {email} (from SiteUser)')
            elif user and linked_vendor:
                self.stdout.write(f'  ok: {email}')

        # Site users with vendor profile via FK but different email on vendor row
        users = models.SiteUser.objects.filter(is_active=True, vendor_profile__isnull=False)
        if email_filter:
            users = users.filter(email__iexact=email_filter)
        for user in users.select_related('vendor_profile'):
            vendor = user.vendor_profile
            if vendor.password != user.password:
                vendor.password = user.password
                vendor.save(update_fields=['password', 'updated_at'])
                synced += 1
                self.stdout.write(f'  synced password via FK: user #{user.id} → vendor #{vendor.id}')

        self.stdout.write(self.style.SUCCESS(
            f'Done. {linked} link(s) updated, {synced} password(s) synced at {timezone.now():%Y-%m-%d %H:%M:%S}.'
        ))
