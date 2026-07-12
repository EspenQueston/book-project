"""One-time backfill: create retroactive Shipment rows for orders that were
paid before the per-vendor fulfillment system existed, so track_order/review
eligibility/admin tooling have a shipment to show for every paid order.

Best-effort reconstruction from the old coarse Order.status — legacy orders
have no real tracking number/carrier and no real buyer-confirmed delivery,
so those fields are left blank/tagged 'admin' rather than invented.
"""
from django.core.management.base import BaseCommand
from django.utils import timezone

from manager import escrow_service
from manager.fulfillment_service import _item_type_and_id, AUTO_CONFIRM_RECEIPT_DAYS
from manager.models import Order, Shipment
from marketplace.models import MarketplaceOrder


LEGACY_STATUS_MAP = {
    'pending': None,
    'payment_pending': None,
    'paid': 'accepted',
    'confirmed': 'accepted',
    'processing': 'accepted',
    'shipped': 'shipped',
    'delivered': 'delivered',
    'cancelled': 'cancelled',
    'refunded': 'returned',
}


def _backfill_for_order(order, order_source, get_items):
    if Shipment.objects.filter(order_source=order_source, order_id=order.id).exists():
        return 0
    if order.payment_status != 'completed':
        return 0

    legacy_status = LEGACY_STATUS_MAP.get(order.status)
    if legacy_status is None:
        return 0

    items = get_items(order)
    if not items:
        return 0

    by_vendor = {}
    for item in items:
        item_type, item_id = _item_type_and_id(order_source, item)
        vendor = escrow_service.resolve_vendor_for_item(item_type, item_id)
        key = vendor.id if vendor else None
        by_vendor.setdefault(key, {'vendor': vendor, 'items': []})
        by_vendor[key]['items'].append(item)

    now = timezone.now()
    created = 0
    for group in by_vendor.values():
        shipment = Shipment(
            order_source=order_source, order_id=order.id, order_number=order.order_number,
            vendor=group['vendor'], fulfillment_status=legacy_status,
        )
        if legacy_status == 'accepted':
            shipment.accepted_at = order.payment_completed_at or order.updated_at
        elif legacy_status == 'shipped':
            shipment.shipped_at = order.updated_at
            shipment.auto_confirm_at = now  # legacy — eligible for the safety net right away
        elif legacy_status == 'delivered':
            shipment.delivered_at = order.updated_at
            shipment.delivered_confirmed_by = 'admin'
        elif legacy_status == 'cancelled':
            shipment.cancelled_at = order.updated_at
        shipment.save()
        for item in group['items']:
            item.shipment = shipment
            item.save(update_fields=['shipment'])
        created += 1

        if legacy_status == 'delivered':
            item_ids = [i.id for i in group['items']]
            escrow_service.mark_order_escrow_delivered(order_source, order.id, order_item_ids=item_ids)
    return created


class Command(BaseCommand):
    help = 'Create retroactive Shipment rows for orders paid before the fulfillment system existed.'

    def handle(self, *args, **options):
        from manager.models import OrderItem
        from marketplace.models import MarketplaceOrderItem

        book_created = 0
        for order in Order.objects.filter(payment_status='completed').iterator():
            book_created += _backfill_for_order(
                order, 'book', lambda o: list(OrderItem.objects.filter(order=o).select_related('book')),
            )

        mkt_created = 0
        for order in MarketplaceOrder.objects.filter(payment_status='completed').iterator():
            mkt_created += _backfill_for_order(
                order, 'marketplace', lambda o: list(MarketplaceOrderItem.objects.filter(order=o)),
            )

        self.stdout.write(self.style.SUCCESS(
            f'Backfill done: {book_created} book shipment(s), {mkt_created} marketplace shipment(s).'
        ))
