"""Centralized, idempotent stock/inventory and sales-counter adjustments.

Stock must only ever move on a real business event — a confirmed successful
payment, or a completed refund — never at order creation. The previous
implementation decremented book.inventory / product.stock / course
enrollment_count unconditionally the moment an order row was created,
regardless of whether the payment ever actually completed. A customer who
abandoned a PawaPay/KKiaPay checkout, or an unpaid cash-on-delivery order
that later auto-cancelled, permanently lost that stock from the count even
though nothing was ever sold — understating real availability over time.

apply_inventory_for_order() is the single place stock/sales move down, and
is guarded by Order.inventory_applied / MarketplaceOrder.inventory_applied
so it only ever runs once per order, no matter how many times a webhook or
admin action re-touches payment_status. restore_inventory_for_shipment() is
the mirror image, used once a real refund for that shipment's items
completes at the gateway.
"""

import logging

from django.db import transaction
from django.db.models import F
from django.db.models.functions import Greatest

logger = logging.getLogger(__name__)


def apply_inventory_for_order(order, order_source):
    """Deduct stock/inventory and bump sales counters for every item in this
    order. Call exactly when payment_status first becomes 'completed'.
    Safe to call more than once — a no-op after the first successful call.

    Stock decrements use a single atomic UPDATE (F()/Greatest), not a
    Python read-modify-write, so two orders for the same book/product
    completing at the same moment can't both read the same starting stock
    value and silently lose one of the decrements."""
    model = type(order)
    with transaction.atomic():
        locked = model.objects.select_for_update().get(pk=order.pk)
        if locked.inventory_applied:
            return False

        if order_source == 'book':
            from manager.models import OrderItem
            for item in OrderItem.objects.filter(order=locked).select_related('book'):
                type(item.book).objects.filter(pk=item.book_id).update(
                    inventory=Greatest(F('inventory') - item.quantity, 0),
                    sale_num=F('sale_num') + item.quantity,
                )
        else:
            from marketplace.models import MarketplaceOrderItem
            for item in MarketplaceOrderItem.objects.filter(order=locked):
                _apply_marketplace_item(item)

        locked.inventory_applied = True
        locked.save(update_fields=['inventory_applied'])

    order.inventory_applied = True
    logger.info('Inventory applied for %s order %s', order_source, getattr(order, 'order_number', order.pk))
    return True


def _apply_marketplace_item(item):
    obj = item.get_related_object()
    if not obj:
        return
    model = type(obj)
    if item.item_type in ('product', 'supermarket'):
        model.objects.filter(pk=obj.pk).update(
            stock=Greatest(F('stock') - item.quantity, 0),
            sales_count=F('sales_count') + item.quantity,
        )
    elif item.item_type == 'course':
        model.objects.filter(pk=obj.pk).update(
            enrollment_count=F('enrollment_count') + 1,
        )


def _restore_marketplace_item(item):
    obj = item.get_related_object()
    if not obj:
        return
    if item.item_type in ('product', 'supermarket'):
        obj.stock = obj.stock + item.quantity
        obj.sales_count = max(0, obj.sales_count - item.quantity)
        obj.save(update_fields=['stock', 'sales_count'])
    elif item.item_type == 'course':
        obj.enrollment_count = max(0, obj.enrollment_count - 1)
        obj.save(update_fields=['enrollment_count'])


def restore_inventory_for_order(order, order_source):
    """Reverse apply_inventory_for_order() for a whole order at once.

    Mirrors apply_inventory_for_order(): used when an admin cancels/refunds
    an order directly (not through a Returns & Shipments shipment record,
    which has its own restore_inventory_for_shipment()). Guarded by the same
    inventory_applied flag, so it's a no-op if stock was never deducted for
    this order in the first place, and safe to call more than once."""
    model = type(order)
    with transaction.atomic():
        locked = model.objects.select_for_update().get(pk=order.pk)
        if not locked.inventory_applied:
            return False

        if order_source == 'book':
            from manager.models import OrderItem
            for item in OrderItem.objects.filter(order=locked).select_related('book'):
                type(item.book).objects.filter(pk=item.book_id).update(
                    inventory=F('inventory') + item.quantity,
                    sale_num=Greatest(F('sale_num') - item.quantity, 0),
                )
        else:
            from marketplace.models import MarketplaceOrderItem
            for item in MarketplaceOrderItem.objects.filter(order=locked):
                _restore_marketplace_item(item)

        locked.inventory_applied = False
        locked.save(update_fields=['inventory_applied'])

    order.inventory_applied = False
    logger.info('Inventory restored for %s order %s', order_source, getattr(order, 'order_number', order.pk))
    return True


def restore_inventory_for_shipment(shipment):
    """Reverse the stock/sales effect for exactly the items covered by this
    shipment. Called once a refund for it actually completes at the gateway
    (a shipment is only ever refunded after inventory was applied, since
    that only happens post-payment — so this is always reversing a real
    deduction, never restoring stock that was never taken)."""
    if shipment.order_source == 'book':
        for item in shipment.items.select_related('book'):
            book = item.book
            book.inventory += item.quantity
            book.sale_num = max(0, book.sale_num - item.quantity)
            book.save(update_fields=['inventory', 'sale_num'])
    else:
        for item in shipment.items.all():
            _restore_marketplace_item(item)
    logger.info('Inventory restored for shipment %s (%s order %s)',
                shipment.id, shipment.order_source, shipment.order_number)
