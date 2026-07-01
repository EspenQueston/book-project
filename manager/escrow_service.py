"""Escrow: platform holds customer payments, then pays vendors after delivery + refund window."""
import logging
import uuid
from datetime import timedelta
from decimal import Decimal

from django.db import transaction
from django.utils import timezone

from manager.commission import split_gross_amount

logger = logging.getLogger(__name__)

REFUND_HOLD_DAYS = 7


def generate_escrow_ref():
    return f"ESC{timezone.now().strftime('%Y%m%d%H%M%S')}{uuid.uuid4().hex[:8].upper()}"


def resolve_vendor_for_item(item_type, item_id):
    """Return Vendor for a sold item, or None if platform-owned."""
    from manager import models as mgr_models
    from marketplace.models import Product, Course, SupermarketItem

    if item_type == 'book':
        vb = (
            mgr_models.VendorBook.objects.filter(book_id=item_id, is_active=True)
            .select_related('vendor')
            .first()
        )
        return vb.vendor if vb else None
    if item_type == 'product':
        row = Product.objects.filter(pk=item_id).select_related('vendor').first()
        return row.vendor if row else None
    if item_type == 'course':
        row = Course.objects.filter(pk=item_id).select_related('vendor').first()
        return row.vendor if row else None
    if item_type == 'supermarket':
        row = SupermarketItem.objects.filter(pk=item_id).select_related('vendor').first()
        return row.vendor if row else None
    return None


def _buyer_fields_from_book_order(order):
    return {
        'buyer_user_id': None,
        'buyer_email': order.customer_email,
        'buyer_name': order.customer_name,
    }


def _buyer_fields_from_marketplace_order(order):
    return {
        'buyer_user_id': order.user_id,
        'buyer_email': order.user_email,
        'buyer_name': order.user_name or '',
    }


def create_escrow_for_book_order(order):
    """Create held escrow rows when a book order payment is completed."""
    from manager.models import OrderItem, PlatformEscrowTransaction

    if order.payment_status != 'completed':
        return 0
    created = 0
    for item in OrderItem.objects.filter(order=order).select_related('book'):
        if PlatformEscrowTransaction.objects.filter(
            order_source='book', order_item_id=item.id
        ).exists():
            continue
        vendor = resolve_vendor_for_item('book', item.book_id)
        if not vendor:
            continue
        rate, commission, vendor_net = split_gross_amount(item.total_price, 'book')
        PlatformEscrowTransaction.objects.create(
            transaction_ref=generate_escrow_ref(),
            order_source='book',
            order_id=order.id,
            order_number=order.order_number,
            order_item_id=item.id,
            vendor=vendor,
            **_buyer_fields_from_book_order(order),
            item_type='book',
            item_id=item.book_id,
            item_name=item.book.name,
            quantity=item.quantity,
            unit_price=item.unit_price,
            gross_amount=item.total_price,
            commission_rate=rate,
            commission_amount=commission,
            vendor_payout_amount=vendor_net,
            payment_transaction_id=order.payment_transaction_id or '',
            status='held',
        )
        created += 1
    return created


def create_escrow_for_marketplace_order(order):
    """Create held escrow rows when a marketplace order payment is completed."""
    from marketplace.models import MarketplaceOrderItem
    from manager.models import PlatformEscrowTransaction

    if order.payment_status != 'completed':
        return 0
    created = 0
    for item in MarketplaceOrderItem.objects.filter(order=order):
        if PlatformEscrowTransaction.objects.filter(
            order_source='marketplace', order_item_id=item.id
        ).exists():
            continue
        vendor = resolve_vendor_for_item(item.item_type, item.item_id)
        if not vendor:
            continue
        rate, commission, vendor_net = split_gross_amount(item.subtotal, item.item_type)
        PlatformEscrowTransaction.objects.create(
            transaction_ref=generate_escrow_ref(),
            order_source='marketplace',
            order_id=order.id,
            order_number=order.order_number,
            order_item_id=item.id,
            vendor=vendor,
            **_buyer_fields_from_marketplace_order(order),
            item_type=item.item_type,
            item_id=item.item_id,
            item_name=item.item_name,
            quantity=item.quantity,
            unit_price=item.unit_price,
            gross_amount=item.subtotal,
            commission_rate=rate,
            commission_amount=commission,
            vendor_payout_amount=vendor_net,
            payment_transaction_id=order.payment_transaction_id or '',
            status='held',
        )
        created += 1
    return created


def mark_order_escrow_delivered(order_source, order_id):
    """Mark escrow as releasable after delivery is confirmed."""
    from manager.models import PlatformEscrowTransaction

    now = timezone.now()
    eligible_at = now + timedelta(days=REFUND_HOLD_DAYS)
    updated = PlatformEscrowTransaction.objects.filter(
        order_source=order_source,
        order_id=order_id,
        status='held',
    ).update(
        status='releasable',
        delivered_at=now,
        release_eligible_at=eligible_at,
    )
    return updated


def cancel_escrow_for_order(order_source, order_id, new_status='refunded'):
    """Cancel or refund escrow when order is cancelled/refunded."""
    from manager.models import PlatformEscrowTransaction

    return PlatformEscrowTransaction.objects.filter(
        order_source=order_source,
        order_id=order_id,
        status__in=('held', 'releasable'),
    ).update(status=new_status)


def release_escrow_transaction(escrow_tx):
    """Pay vendor net amount and mark escrow released."""
    from manager.models import VendorWallet

    if escrow_tx.status not in ('releasable', 'held'):
        return False
    if escrow_tx.status == 'held' and escrow_tx.release_eligible_at:
        if timezone.now() < escrow_tx.release_eligible_at:
            return False

    with transaction.atomic():
        escrow_tx = escrow_tx.__class__.objects.select_for_update().get(pk=escrow_tx.pk)
        if escrow_tx.status == 'released':
            return False
        if escrow_tx.vendor_id and escrow_tx.vendor_payout_amount > 0:
            wallet, _ = VendorWallet.objects.select_for_update().get_or_create(
                vendor_id=escrow_tx.vendor_id,
                defaults={
                    'balance': Decimal('0.00'),
                    'total_earned': Decimal('0.00'),
                    'total_paid_out': Decimal('0.00'),
                },
            )
            wallet.credit(
                escrow_tx.vendor_payout_amount,
                source='escrow_release',
                description=(
                    f'Payout {escrow_tx.transaction_ref} — '
                    f'{escrow_tx.item_name} ({escrow_tx.order_number})'
                ),
                source_id=escrow_tx.transaction_ref,
            )
        escrow_tx.status = 'released'
        escrow_tx.released_at = timezone.now()
        escrow_tx.save(update_fields=['status', 'released_at'])
    return True


def process_due_escrow_releases():
    """Release all escrow rows past the refund hold period."""
    from manager.models import PlatformEscrowTransaction

    now = timezone.now()
    qs = PlatformEscrowTransaction.objects.filter(
        status='releasable',
        release_eligible_at__lte=now,
    ).order_by('release_eligible_at')
    count = 0
    for row in qs.iterator():
        if release_escrow_transaction(row):
            count += 1
    return count


def sync_escrow_on_payment(order, order_source):
    """Create escrow entries when payment completes."""
    if order_source == 'book':
        return create_escrow_for_book_order(order)
    return create_escrow_for_marketplace_order(order)


def sync_escrow_on_order_update(order, order_source, old_status, old_payment_status):
    """React to order status / payment changes."""
    if order.payment_status == 'completed' and old_payment_status != 'completed':
        sync_escrow_on_payment(order, order_source)

    if order.payment_status in ('refunded', 'cancelled') or order.status in ('refunded', 'cancelled'):
        status = 'refunded' if order.payment_status == 'refunded' or order.status == 'refunded' else 'cancelled'
        cancel_escrow_for_order(order_source, order.id, new_status=status)
        return

    if order.status == 'delivered' and old_status != 'delivered':
        mark_order_escrow_delivered(order_source, order.id)
        process_due_escrow_releases()


def admin_mark_escrow_delivered(escrow_id):
    """Admin: mark one escrow line delivered and start refund hold countdown."""
    from manager.models import PlatformEscrowTransaction

    now = timezone.now()
    eligible_at = now + timedelta(days=REFUND_HOLD_DAYS)
    updated = PlatformEscrowTransaction.objects.filter(
        pk=escrow_id,
        status='held',
    ).update(
        status='releasable',
        delivered_at=now,
        release_eligible_at=eligible_at,
    )
    return updated > 0


def admin_force_release_escrow(escrow_id):
    """Admin: force immediate vendor payout for one escrow line."""
    from manager.models import PlatformEscrowTransaction

    tx = PlatformEscrowTransaction.objects.filter(pk=escrow_id).first()
    if not tx:
        return False
    if tx.status in ('refunded', 'cancelled', 'released'):
        return False
    now = timezone.now()
    if tx.status == 'held':
        if not tx.delivered_at:
            tx.delivered_at = now
        tx.status = 'releasable'
        tx.release_eligible_at = now
        tx.save(update_fields=['status', 'delivered_at', 'release_eligible_at'])
    elif tx.status == 'releasable' and tx.release_eligible_at and tx.release_eligible_at > now:
        tx.release_eligible_at = now
        tx.save(update_fields=['release_eligible_at'])
    return release_escrow_transaction(tx)


def admin_cancel_escrow(escrow_id, new_status='cancelled'):
    """Admin: cancel or refund a single escrow line."""
    from manager.models import PlatformEscrowTransaction

    if new_status not in ('cancelled', 'refunded'):
        new_status = 'cancelled'
    return PlatformEscrowTransaction.objects.filter(
        pk=escrow_id,
        status__in=('held', 'releasable'),
    ).update(status=new_status)


def admin_wallet_adjust(vendor_id, amount, description=''):
    """Admin: credit or debit vendor wallet balance."""
    from manager.models import VendorWallet, VendorWalletTransaction

    amount = Decimal(str(amount))
    if amount == 0:
        return False
    with transaction.atomic():
        wallet, _ = VendorWallet.objects.select_for_update().get_or_create(
            vendor_id=vendor_id,
            defaults={
                'balance': Decimal('0.00'),
                'total_earned': Decimal('0.00'),
                'total_paid_out': Decimal('0.00'),
            },
        )
        if amount > 0:
            wallet.credit(amount, source='admin_adjust', description=description or 'Admin adjustment')
            return True
        debit = abs(amount)
        if wallet.balance < debit:
            return False
        wallet.balance -= debit
        wallet.save(update_fields=['balance', 'updated_at'])
        VendorWalletTransaction.objects.create(
            vendor_id=vendor_id,
            amount=debit,
            txn_type='debit',
            source='admin_adjust',
            description=description or 'Admin adjustment',
        )
        return True

