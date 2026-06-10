from django.core.management.base import BaseCommand

from manager.escrow_service import process_due_escrow_releases


class Command(BaseCommand):
    help = 'Release vendor escrow payouts when delivery + refund hold period have passed.'

    def handle(self, *args, **options):
        count = process_due_escrow_releases()
        self.stdout.write(self.style.SUCCESS(f'Released {count} escrow transaction(s).'))
