"""Reset views, presence cache, and sold stats for the N most recent marketplace listings."""

from django.core.management.base import BaseCommand
from django.db.models import Q

from marketplace.models import (
    Course,
    MarketplaceOrderItem,
    Product,
    SupermarketItem,
)
from marketplace.presence import clear_product_presence


class Command(BaseCommand):
    help = 'Reset views, live presence, and sold quantities for the latest marketplace listings.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--limit',
            type=int,
            default=20,
            help='Number of most recently created listings to reset (default: 20).',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be reset without writing changes.',
        )

    def handle(self, *args, **options):
        limit = max(1, options['limit'])
        dry_run = options['dry_run']

        listings = []
        for obj in Product.objects.all().only('id', 'name', 'created_at', 'views_count', 'sales_count'):
            listings.append(('product', obj.pk, obj.name, obj.created_at, obj.views_count, obj.sales_count))
        for obj in Course.objects.all().only('id', 'title', 'created_at', 'enrollment_count'):
            listings.append(('course', obj.pk, obj.title, obj.created_at, 0, obj.enrollment_count))
        for obj in SupermarketItem.objects.all().only('id', 'name', 'created_at', 'sales_count'):
            listings.append(('supermarket', obj.pk, obj.name, obj.created_at, 0, obj.sales_count))

        listings.sort(key=lambda row: row[3], reverse=True)
        targets = listings[:limit]

        if not targets:
            self.stdout.write(self.style.WARNING('No marketplace listings found.'))
            return

        self.stdout.write(f"{'[DRY RUN] ' if dry_run else ''}Resetting {len(targets)} listing(s):\n")

        product_ids = []
        order_filters = Q()
        for item_type, pk, label, created_at, views, sold_field in targets:
            self.stdout.write(
                f"  - [{item_type}] #{pk} {label[:60]} "
                f"(created {created_at:%Y-%m-%d %H:%M}, views={views}, sold={sold_field})"
            )
            if item_type == 'product':
                product_ids.append(pk)
            order_filters |= Q(item_type=item_type, item_id=pk)

        delivered_items = MarketplaceOrderItem.objects.filter(
            order_filters,
            order__status='delivered',
            order__payment_status='completed',
        )
        delivered_count = delivered_items.count()
        delivered_qty = sum(delivered_items.values_list('quantity', flat=True))

        if dry_run:
            self.stdout.write(
                self.style.WARNING(
                    f'\nWould delete {delivered_count} delivered order line(s) '
                    f'({delivered_qty} units) and clear presence for {len(product_ids)} product(s).'
                )
            )
            return

        if product_ids:
            Product.objects.filter(pk__in=product_ids).update(views_count=0, sales_count=0)
            for pk in product_ids:
                clear_product_presence(pk)

        course_ids = [pk for t, pk, *_ in targets if t == 'course']
        if course_ids:
            Course.objects.filter(pk__in=course_ids).update(enrollment_count=0)

        supermarket_ids = [pk for t, pk, *_ in targets if t == 'supermarket']
        if supermarket_ids:
            SupermarketItem.objects.filter(pk__in=supermarket_ids).update(sales_count=0)

        deleted, _ = delivered_items.delete()

        self.stdout.write(self.style.SUCCESS(
            f'\nDone: reset stats for {len(targets)} listing(s), '
            f'cleared presence for {len(product_ids)} product(s), '
            f'removed {deleted} delivered order line(s) ({delivered_qty} units).'
        ))
