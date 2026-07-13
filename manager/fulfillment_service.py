"""
Fulfillment: per-vendor shipments, buyer-confirmed delivery, and returns.

This is the orchestration layer sitting on top of Shipment / OrderReturnRequest
(manager/models.py) and the escrow system (manager/escrow_service.py). It is
the single place that decides how a Shipment moves through its lifecycle and
keeps Order.status / MarketplaceOrder.status in sync as a coarse,
backward-compatible summary field so every existing view/template/filter
that reads order.status keeps working unchanged.

Design rules (see the delivery-system redesign this implements):
  - 'delivered' is only ever set by a buyer confirmation or the timed
    safety-net — never a vendor self-report — because it is also what starts
    the escrow release countdown for that vendor.
  - A shipment moving to 'shipped' requires a tracking number + carrier;
    there is no way to mark something shipped without it.
  - A shipment with an open return dispute freezes its escrow release even
    if the refund-hold window has already passed.
"""
import logging
from datetime import timedelta

from django.db import transaction
from django.utils import timezone

from manager import escrow_service

logger = logging.getLogger(__name__)

# How long a seller has to accept a newly-paid order before we auto-accept it
# for them, so an inactive seller never silently blocks a paid order.
SELLER_ACCEPT_SLA_HOURS = 48

# Safety-net window: if a shipment has been 'shipped' this many days with no
# buyer confirmation and no open dispute, we auto-confirm receipt. Set longer
# than Taobao's ~10 days to account for genuinely slower regional last-mile
# logistics in Central Africa rather than risk auto-confirming (and paying
# the vendor for) a parcel that is still legitimately in transit.
AUTO_CONFIRM_RECEIPT_DAYS = 14

# Buyer's window to open a return/dispute after delivery is confirmed.
RETURN_WINDOW_DAYS = 7

# How long after a confirmed delivery to invite the buyer to leave a review.
REVIEW_REQUEST_DELAY_DAYS = 3

_ORDER_MODEL_MAP = {}  # populated lazily to avoid app-loading order issues


def _get_order(order_source, order_id):
    from manager.models import Order
    from marketplace.models import MarketplaceOrder
    if not _ORDER_MODEL_MAP:
        _ORDER_MODEL_MAP['book'] = Order
        _ORDER_MODEL_MAP['marketplace'] = MarketplaceOrder
    model = _ORDER_MODEL_MAP[order_source]
    return model.objects.filter(pk=order_id).first()


def _get_order_items(order_source, order_id):
    from manager.models import OrderItem
    from marketplace.models import MarketplaceOrderItem
    if order_source == 'book':
        return list(OrderItem.objects.filter(order_id=order_id).select_related('book'))
    return list(MarketplaceOrderItem.objects.filter(order_id=order_id))


def _item_type_and_id(order_source, item):
    if order_source == 'book':
        return 'book', item.book_id
    return item.item_type, item.item_id


# ---------------------------------------------------------------------------
# Delivery-days resolution: item override -> vendor default -> platform
# fallback. Lets a vendor (including the official store, which is itself a
# Vendor record) configure a general delivery estimate once, override it for
# specific slower-shipping items, and still have a sane fallback for sellers
# who never configured anything.
# ---------------------------------------------------------------------------

# Deliberately conservative for Central African last-mile logistics.
PLATFORM_DEFAULT_DELIVERY_DAYS_MIN = 3
PLATFORM_DEFAULT_DELIVERY_DAYS_MAX = 7


def _resolve_item_and_vendor(item_type, item_id):
    from manager.models import Book
    from marketplace.models import Product, Course, SupermarketItem

    if item_type == 'book':
        item = Book.objects.filter(pk=item_id).first()
        vendor = escrow_service.resolve_vendor_for_item('book', item_id)
        return item, vendor
    if item_type == 'product':
        item = Product.objects.filter(pk=item_id).select_related('vendor').first()
        return item, (item.vendor if item else None)
    if item_type == 'course':
        item = Course.objects.filter(pk=item_id).select_related('vendor').first()
        return item, (item.vendor if item else None)
    if item_type == 'supermarket':
        item = SupermarketItem.objects.filter(pk=item_id).select_related('vendor').first()
        return item, (item.vendor if item else None)
    return None, None


def resolve_delivery_days(item_type, item_id):
    """Return (min_days, max_days) for one order item: the item's own
    override if set, else the vendor's configured default, else the
    platform-wide fallback. Courses (digital) never have their own override
    but still resolve through vendor/platform for consistency."""
    item, vendor = _resolve_item_and_vendor(item_type, item_id)

    item_min = getattr(item, 'delivery_days_min', None)
    item_max = getattr(item, 'delivery_days_max', None)
    if item_min and item_max:
        return item_min, item_max

    if vendor is not None and vendor.default_delivery_days_min and vendor.default_delivery_days_max:
        return vendor.default_delivery_days_min, vendor.default_delivery_days_max

    return PLATFORM_DEFAULT_DELIVERY_DAYS_MIN, PLATFORM_DEFAULT_DELIVERY_DAYS_MAX


def suggested_delivery_date(shipment):
    """Conservative (max-days) estimated delivery date across every item in
    a shipment — used to pre-fill the vendor's ship-form date input, which
    they can still override per-shipment before submitting."""
    max_days = PLATFORM_DEFAULT_DELIVERY_DAYS_MAX
    found_any = False
    for item in shipment.items:
        item_type, item_id = _item_type_and_id(shipment.order_source, item)
        _, days_max = resolve_delivery_days(item_type, item_id)
        if not found_any or days_max > max_days:
            max_days = days_max
        found_any = True
    return (timezone.now() + timedelta(days=max_days)).date()


# ---------------------------------------------------------------------------
# Shipment creation (fires once payment completes)
# ---------------------------------------------------------------------------

def create_shipments_for_order(order, order_source):
    """Group an order's line items by vendor into one Shipment per vendor,
    then hand off to escrow_service to create the held escrow rows exactly
    as before. Idempotent — safe to call more than once for the same order."""
    from manager.models import Shipment

    if order.payment_status != 'completed':
        return []

    items = _get_order_items(order_source, order.id)
    if not items:
        return []

    # Already fanned out for this order? Don't duplicate.
    existing = list(Shipment.objects.filter(order_source=order_source, order_id=order.id))
    if existing:
        return existing

    by_vendor = {}
    for item in items:
        item_type, item_id = _item_type_and_id(order_source, item)
        vendor = escrow_service.resolve_vendor_for_item(item_type, item_id)
        by_vendor.setdefault(vendor.id if vendor else None, {'vendor': vendor, 'items': []})
        by_vendor[vendor.id if vendor else None]['items'].append(item)

    now = timezone.now()
    accept_by = now + timedelta(hours=SELLER_ACCEPT_SLA_HOURS)
    created_shipments = []

    with transaction.atomic():
        for group in by_vendor.values():
            shipment = Shipment.objects.create(
                order_source=order_source,
                order_id=order.id,
                order_number=order.order_number,
                vendor=group['vendor'],
                fulfillment_status='awaiting_acceptance',
                accept_by=accept_by,
            )
            for item in group['items']:
                item.shipment = shipment
                item.save(update_fields=['shipment'])
            created_shipments.append(shipment)

            if group['vendor']:
                _notify_vendor_new_order(group['vendor'], shipment)

        # Escrow rows are still created per order-item exactly as before —
        # shipment grouping doesn't change the payout math, only when it fires.
        escrow_service.sync_escrow_on_payment(order, order_source)

    sync_order_status_from_shipments(order, order_source)
    return created_shipments


def _notify_vendor_new_order(vendor, shipment):
    from manager.models import VendorNotification
    try:
        VendorNotification.objects.create(
            vendor=vendor,
            notification_type='new_order',
            title='Nouvelle commande à confirmer',
            message=f'Commande {shipment.order_number} — merci de confirmer sous 48h.',
            icon='fas fa-box',
            color='#1d4ed8',
            link='/manager/vendor/orders/',
            related_id=shipment.id,
        )
    except Exception:
        logger.exception('Failed to create vendor notification for shipment %s', shipment.id)

    try:
        from manager import notifications_service
        notifications_service.send_seller_sla_nudge(shipment)
    except Exception:
        logger.exception('Failed to email vendor about new shipment %s', shipment.id)


# ---------------------------------------------------------------------------
# Seller actions: accept / reject / pack / ship
# ---------------------------------------------------------------------------

def accept_shipment(shipment):
    if shipment.fulfillment_status != 'awaiting_acceptance':
        return False
    shipment.fulfillment_status = 'accepted'
    shipment.accepted_at = timezone.now()
    shipment.save(update_fields=['fulfillment_status', 'accepted_at', 'updated_at'])
    _sync_after_shipment_change(shipment)

    order = _get_order(shipment.order_source, shipment.order_id)
    if order:
        from manager import notifications_service
        notifications_service.send_order_accepted(order, shipment.order_source, shipment)
    return True


def reject_shipment(shipment, reason):
    if shipment.fulfillment_status not in ('awaiting_acceptance', 'accepted'):
        return False
    shipment.fulfillment_status = 'rejected'
    shipment.rejected_at = timezone.now()
    shipment.rejection_reason = (reason or '')[:255]
    shipment.save(update_fields=['fulfillment_status', 'rejected_at', 'rejection_reason', 'updated_at'])

    item_ids = _shipment_item_ids(shipment)
    escrow_service.cancel_escrow_for_order(
        shipment.order_source, shipment.order_id, new_status='cancelled', order_item_ids=item_ids,
    )
    # The seller can't fulfill it — the buyer already paid, so refund them
    # for real via the gateway rather than just cancelling the escrow entry.
    initiate_refund_for_shipment(shipment)
    _sync_after_shipment_change(shipment)

    order = _get_order(shipment.order_source, shipment.order_id)
    if order:
        from manager import notifications_service
        notifications_service.send_order_cancelled(order, shipment.order_source, reason=shipment.rejection_reason)
    return True


def mark_packing(shipment):
    if shipment.fulfillment_status != 'accepted':
        return False
    shipment.fulfillment_status = 'packing'
    shipment.packed_at = timezone.now()
    shipment.save(update_fields=['fulfillment_status', 'packed_at', 'updated_at'])
    _sync_after_shipment_change(shipment)
    return True


def mark_shipped(shipment, tracking_number, carrier, estimated_delivery_date=None):
    """Requires tracking info — there is no path to 'shipped' without it."""
    tracking_number = (tracking_number or '').strip()
    carrier = (carrier or '').strip()
    if not tracking_number or not carrier:
        raise ValueError('tracking_number and carrier are both required to mark a shipment shipped.')
    if shipment.fulfillment_status not in ('accepted', 'packing'):
        return False

    now = timezone.now()
    shipment.fulfillment_status = 'shipped'
    shipment.tracking_number = tracking_number[:100]
    shipment.carrier = carrier[:100]
    shipment.shipped_at = now
    shipment.estimated_delivery_date = estimated_delivery_date
    shipment.auto_confirm_at = now + timedelta(days=AUTO_CONFIRM_RECEIPT_DAYS)
    shipment.save(update_fields=[
        'fulfillment_status', 'tracking_number', 'carrier', 'shipped_at',
        'estimated_delivery_date', 'auto_confirm_at', 'updated_at',
    ])
    _sync_after_shipment_change(shipment)

    order = _get_order(shipment.order_source, shipment.order_id)
    if order:
        from manager import notifications_service
        notifications_service.send_shipment_shipped(order, shipment.order_source, shipment)
    return True


def mark_in_transit(shipment):
    if shipment.fulfillment_status not in ('shipped',):
        return False
    shipment.fulfillment_status = 'in_transit'
    shipment.save(update_fields=['fulfillment_status', 'updated_at'])
    _sync_after_shipment_change(shipment)
    return True


def mark_out_for_delivery(shipment):
    if shipment.fulfillment_status not in ('shipped', 'in_transit'):
        return False
    shipment.fulfillment_status = 'out_for_delivery'
    shipment.out_for_delivery_at = timezone.now()
    shipment.save(update_fields=['fulfillment_status', 'out_for_delivery_at', 'updated_at'])
    _sync_after_shipment_change(shipment)

    order = _get_order(shipment.order_source, shipment.order_id)
    if order:
        from manager import notifications_service
        notifications_service.send_out_for_delivery(order, shipment.order_source, shipment)
    return True


# ---------------------------------------------------------------------------
# Delivery confirmation — buyer-driven (or timed safety-net), never seller
# ---------------------------------------------------------------------------

def confirm_delivery(shipment, confirmed_by='buyer'):
    """confirmed_by is one of Shipment.DELIVERY_CONFIRMED_BY_CHOICES
    ('buyer', 'auto_timeout', 'admin'). Starts the escrow release countdown
    for exactly this shipment's items."""
    if not shipment.can_confirm_receipt:
        return False

    now = timezone.now()
    shipment.fulfillment_status = 'delivered'
    shipment.delivered_at = now
    shipment.delivered_confirmed_by = confirmed_by
    shipment.save(update_fields=['fulfillment_status', 'delivered_at', 'delivered_confirmed_by', 'updated_at'])

    item_ids = _shipment_item_ids(shipment)
    escrow_service.mark_order_escrow_delivered(shipment.order_source, shipment.order_id, order_item_ids=item_ids)
    _sync_after_shipment_change(shipment)
    return True


def process_auto_confirmations():
    """Safety net: shipments 'shipped'/'in_transit'/'out_for_delivery' past
    their auto_confirm_at with no open return request get auto-confirmed.
    Meant to run from a scheduled management command, not on page load."""
    from manager.models import Shipment

    now = timezone.now()
    qs = Shipment.objects.filter(
        fulfillment_status__in=('shipped', 'in_transit', 'out_for_delivery'),
        auto_confirm_at__lte=now,
    )
    count = 0
    for shipment in qs.iterator():
        if confirm_delivery(shipment, confirmed_by='auto_timeout'):
            count += 1
    return count


def process_seller_sla_auto_accept():
    """Safety net: an inactive seller never silently blocks a paid order."""
    from manager.models import Shipment

    now = timezone.now()
    qs = Shipment.objects.filter(fulfillment_status='awaiting_acceptance', accept_by__lte=now)
    count = 0
    for shipment in qs.iterator():
        if accept_shipment(shipment):
            count += 1
    return count


def process_due_shipment_completions():
    """Release escrow for shipments whose refund-hold window has passed —
    unless a return dispute is open, in which case release stays frozen —
    then mark those shipments 'completed'."""
    from manager.models import Shipment, PlatformEscrowTransaction

    now = timezone.now()
    disputed_shipment_ids = set(
        Shipment.objects.filter(
            fulfillment_status__in=('return_requested', 'return_approved'),
        ).values_list('id', flat=True)
    )

    releasable_items = {}  # (order_source, order_id) -> set(order_item_id)
    for tx in PlatformEscrowTransaction.objects.filter(status='releasable', release_eligible_at__lte=now):
        releasable_items.setdefault((tx.order_source, tx.order_id), set()).add(tx.order_item_id)

    completed = 0
    delivered_shipments = Shipment.objects.filter(fulfillment_status='delivered').select_related('vendor')
    for shipment in delivered_shipments.iterator():
        if shipment.id in disputed_shipment_ids:
            continue
        item_ids = _shipment_item_ids(shipment)
        due_ids = releasable_items.get((shipment.order_source, shipment.order_id), set())
        if not item_ids or not due_ids.intersection(item_ids):
            continue
        # Only release/complete this shipment's own items.
        qs = PlatformEscrowTransaction.objects.filter(
            order_source=shipment.order_source, order_id=shipment.order_id,
            order_item_id__in=item_ids, status='releasable', release_eligible_at__lte=now,
        )
        released_any = False
        for tx in qs:
            if escrow_service.release_escrow_transaction(tx):
                released_any = True
        if released_any:
            shipment.fulfillment_status = 'completed'
            shipment.completed_at = now
            shipment.save(update_fields=['fulfillment_status', 'completed_at', 'updated_at'])
            completed += 1
    return completed


def _shipment_item_ids(shipment):
    return list(shipment.items.values_list('id', flat=True))


def _shipment_item_names(shipment):
    if shipment.order_source == 'book':
        return [item.book.name for item in shipment.items.select_related('book')]
    return [item.item_name for item in shipment.items]


def send_due_review_requests():
    """Invite buyers to review their purchase a few days after delivery is
    confirmed. Sent once per shipment (review_request_sent_at guards it)."""
    from manager.models import Shipment

    cutoff = timezone.now() - timedelta(days=REVIEW_REQUEST_DELAY_DAYS)
    qs = Shipment.objects.filter(
        fulfillment_status__in=('delivered', 'completed'),
        delivered_at__lte=cutoff,
        review_request_sent_at__isnull=True,
    )
    sent = 0
    for shipment in qs.iterator():
        order = _get_order(shipment.order_source, shipment.order_id)
        if not order:
            continue
        names = _shipment_item_names(shipment)
        if not names:
            continue
        item_label = names[0] if len(names) == 1 else f'{names[0]} (+{len(names) - 1})'
        try:
            from manager import notifications_service
            notifications_service.send_review_request(order, shipment.order_source, item_label)
        except Exception:
            logger.exception('Failed to send review request for shipment %s', shipment.id)
            continue
        shipment.review_request_sent_at = timezone.now()
        shipment.save(update_fields=['review_request_sent_at', 'updated_at'])
        sent += 1
    return sent


# ---------------------------------------------------------------------------
# Returns / disputes
# ---------------------------------------------------------------------------

def open_return_request(shipment, buyer_name, buyer_email, reason, description='', images=None):
    from manager.models import OrderReturnRequest

    if not shipment.can_open_return:
        return None
    if shipment.delivered_at and timezone.now() > shipment.delivered_at + timedelta(days=RETURN_WINDOW_DAYS):
        return None

    req = OrderReturnRequest.objects.create(
        shipment=shipment,
        buyer_name=buyer_name or '',
        buyer_email=buyer_email,
        reason=reason,
        description=description or '',
        images=images or [],
    )
    shipment.fulfillment_status = 'return_requested'
    shipment.save(update_fields=['fulfillment_status', 'updated_at'])
    _sync_after_shipment_change(shipment)

    order = _get_order(shipment.order_source, shipment.order_id)
    if order:
        from manager import notifications_service
        notifications_service.send_return_opened(order, shipment.order_source, req)
    return req


def resolve_return_request(return_request, decision, resolution_note='', resolved_by='admin'):
    """decision: 'approved' or 'rejected'."""
    if return_request.status != 'pending':
        return False
    if decision not in ('approved', 'rejected'):
        return False

    return_request.status = decision
    return_request.resolution_note = resolution_note or ''
    return_request.resolved_by = resolved_by
    return_request.save(update_fields=['status', 'resolution_note', 'resolved_by', 'updated_at'])

    shipment = return_request.shipment
    shipment.fulfillment_status = 'return_approved' if decision == 'approved' else 'return_rejected'
    shipment.save(update_fields=['fulfillment_status', 'updated_at'])
    _sync_after_shipment_change(shipment)

    order = _get_order(shipment.order_source, shipment.order_id)
    if order:
        from manager import notifications_service
        notifications_service.send_return_resolved(order, shipment.order_source, return_request)
    return True


def confirm_return_received(return_request, resolution_note=''):
    """Final step once the returned item has physically been received back —
    marks the shipment 'returned' and cancels/refunds its escrow so the
    vendor is not paid for a returned item."""
    if return_request.status != 'approved':
        return False

    shipment = return_request.shipment
    item_ids = _shipment_item_ids(shipment)
    escrow_service.cancel_escrow_for_order(
        shipment.order_source, shipment.order_id, new_status='refunded', order_item_ids=item_ids,
    )
    shipment.fulfillment_status = 'returned'
    shipment.save(update_fields=['fulfillment_status', 'updated_at'])
    initiate_refund_for_shipment(shipment)

    return_request.status = 'resolved'
    if resolution_note:
        return_request.resolution_note = resolution_note
    return_request.save(update_fields=['status', 'resolution_note', 'updated_at'])
    _sync_after_shipment_change(shipment)
    return True


# ---------------------------------------------------------------------------
# Real refunds — actually moves money back via the payment gateway, rather
# than an admin flipping payment_status='refunded' with nothing behind it.
# ---------------------------------------------------------------------------

def _shipment_gross_amount(shipment):
    from manager.models import PlatformEscrowTransaction
    from django.db.models import Sum

    item_ids = _shipment_item_ids(shipment)
    if not item_ids:
        return None
    total = PlatformEscrowTransaction.objects.filter(
        order_source=shipment.order_source, order_id=shipment.order_id, order_item_id__in=item_ids,
    ).aggregate(total=Sum('gross_amount'))['total']
    return total


def initiate_refund_for_shipment(shipment):
    """Refund exactly this shipment's share of the order's payment. No-op if
    the order wasn't paid via a gateway that supports refunds, or if a
    refund for this shipment already exists (idempotent)."""
    from manager.models import OrderRefund
    from manager.payments.pawapay import create_refund

    if OrderRefund.objects.filter(shipment=shipment).exists():
        return None

    order = _get_order(shipment.order_source, shipment.order_id)
    if not order or order.payment_method != 'pawapay' or not order.payment_transaction_id:
        logger.info('Skipping refund for shipment %s — not a refundable pawaPay payment.', shipment.id)
        return None

    amount = _shipment_gross_amount(shipment)
    if not amount or amount <= 0:
        return None

    result = create_refund(
        deposit_id=order.payment_transaction_id,
        amount=amount,
        currency='XAF',
    )
    refund = OrderRefund.objects.create(
        order_source=shipment.order_source,
        order_id=shipment.order_id,
        order_number=shipment.order_number,
        shipment=shipment,
        provider='pawapay',
        provider_refund_id=result.get('refund_id') or '',
        provider_deposit_id=order.payment_transaction_id,
        amount=amount,
        currency='XAF',
        status='pending' if result.get('success') else 'failed',
        provider_message=(result.get('error') or '')[:255],
    )
    return refund


def process_pending_refunds():
    """Poll pawaPay for the real status of every in-flight refund and finalize
    the ones that have completed or failed. Meant to run from the scheduled
    management command."""
    from manager.models import OrderRefund
    from manager.payments.pawapay import get_refund_status, normalize_pawapay_status

    updated = 0
    for refund in OrderRefund.objects.filter(status='pending').exclude(provider_refund_id=''):
        result = get_refund_status(refund.provider_refund_id)
        internal = normalize_pawapay_status(result.get('status', 'PENDING'))
        if internal == 'SUCCESSFUL':
            refund.status = 'completed'
            refund.completed_at = timezone.now()
            refund.save(update_fields=['status', 'completed_at', 'updated_at'])
            updated += 1
            if refund.shipment:
                from manager.inventory_service import restore_inventory_for_shipment
                restore_inventory_for_shipment(refund.shipment)
            order = _get_order(refund.order_source, refund.order_id)
            if order:
                from manager import notifications_service
                notifications_service.send_refund_processed(order, refund.order_source, refund.amount)
        elif internal == 'FAILED':
            refund.status = 'failed'
            refund.provider_message = (result.get('error') or 'Refund failed')[:255]
            refund.save(update_fields=['status', 'provider_message', 'updated_at'])
            updated += 1
    return updated


# ---------------------------------------------------------------------------
# Coarse Order.status sync (backward compatibility with existing code)
# ---------------------------------------------------------------------------

# Maps the rich per-shipment fulfillment_status onto the existing, much
# coarser Order.status vocabulary so every pre-existing view/template/filter
# that branches on order.status keeps working exactly as before.
_COARSE_STATUS_MAP = {
    'awaiting_acceptance': 'processing',
    'accepted': 'processing',
    'packing': 'processing',
    'shipped': 'shipped',
    'in_transit': 'shipped',
    'out_for_delivery': 'shipped',
    'delivered': 'delivered',
    'completed': 'delivered',
    'return_requested': 'delivered',
    'return_approved': 'delivered',
    'return_rejected': 'delivered',
    'returned': 'refunded',
    'rejected': 'cancelled',
    'cancelled': 'cancelled',
}

# Ordering used to pick the "least advanced" shipment when an order fans out
# into several vendor shipments — the order as a whole isn't further along
# than its slowest-moving parcel.
_PROGRESS_ORDER = [
    'awaiting_acceptance', 'accepted', 'packing', 'shipped', 'in_transit',
    'out_for_delivery', 'delivered', 'completed',
]


def sync_order_status_from_shipments(order, order_source):
    from manager.models import Shipment

    shipments = list(Shipment.objects.filter(order_source=order_source, order_id=order.id))
    if not shipments:
        return

    active = [s for s in shipments if s.fulfillment_status not in ('cancelled', 'rejected')]
    if not active:
        new_status = 'cancelled'
    else:
        def rank(s):
            try:
                return _PROGRESS_ORDER.index(s.fulfillment_status)
            except ValueError:
                return len(_PROGRESS_ORDER)  # returns/etc. sort last, handled by their own mapping below
        least_advanced = min(active, key=rank)
        new_status = _COARSE_STATUS_MAP.get(least_advanced.fulfillment_status, order.status)

    if new_status != order.status:
        order.status = new_status
        order.save(update_fields=['status', 'updated_at'])


def _sync_after_shipment_change(shipment):
    order = _get_order(shipment.order_source, shipment.order_id)
    if order:
        sync_order_status_from_shipments(order, shipment.order_source)
