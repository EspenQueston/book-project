from django.core.management.base import BaseCommand

from manager.escrow_service import (
    create_escrow_for_book_order,
    create_escrow_for_marketplace_order,
    mark_order_escrow_delivered,
)
from manager.models import Order
from marketplace.models import MarketplaceOrder


class Command(BaseCommand):
    help = 'Create escrow rows for existing paid orders (one-time backfill).'

    def handle(self, *args, **options):
        book_created = 0
        for order in Order.objects.filter(payment_status='completed').iterator():
            book_created += create_escrow_for_book_order(order)
            if order.status == 'delivered':
                mark_order_escrow_delivered('book', order.id)

        mkt_created = 0
        for order in MarketplaceOrder.objects.filter(payment_status='completed').iterator():
            mkt_created += create_escrow_for_marketplace_order(order)
            if order.status == 'delivered':
                mark_order_escrow_delivered('marketplace', order.id)

        self.stdout.write(
            self.style.SUCCESS(
                f'Backfill done: {book_created} book line(s), {mkt_created} marketplace line(s).'
            )
        )
