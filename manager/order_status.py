"""Shared order status buckets for tracking filters (books + marketplace)."""

TRACK_STATUS_BUCKETS = {
    'pending': frozenset({'pending', 'payment_pending'}),
    'processing': frozenset({'processing', 'paid', 'confirmed'}),
    'shipped': frozenset({'shipped'}),
    'delivered': frozenset({'delivered'}),
    'cancelled': frozenset({'cancelled', 'refunded'}),
}


def order_status_bucket(status):
    """Map raw DB status to a tracking filter bucket."""
    status = (status or '').strip()
    for bucket, codes in TRACK_STATUS_BUCKETS.items():
        if status in codes:
            return bucket
    return status or 'other'


def filter_orders_by_bucket(queryset, bucket):
    """Filter an order queryset by tracking bucket name."""
    if not bucket or queryset is None:
        return queryset
    codes = TRACK_STATUS_BUCKETS.get(bucket)
    if codes:
        return queryset.filter(status__in=codes)
    return queryset.filter(status=bucket)


def order_matches_bucket(status, bucket):
    if not bucket:
        return True
    return order_status_bucket(status) == bucket


# ---------------------------------------------------------------------------
# Status state machine — shared by book Order and MarketplaceOrder, since
# both use the same status vocabulary. Prevents admins from setting an order
# to any arbitrary status regardless of its current state (e.g. 'delivered'
# jumping back to 'pending', or 'paid' skipping straight to 'delivered').
# 'confirmed' only exists on book Order; it's harmless to include here since
# MarketplaceOrder simply never reaches that state.
#
# 'shipped' and 'delivered' are deliberately never valid *targets* here, from
# any source state — those two are the Shipment pipeline's job (vendor
# accept/pack/ship with a real tracking number, then a buyer delivery
# confirmation or the 14-day auto-confirm safety net), never a raw status
# field edit. Reaching 'delivered' is also what starts the vendor's escrow
# payout countdown (see manager/escrow_service.py sync_escrow_on_order_update
# and fulfillment_service.py's own module docstring: "'delivered' is only
# ever set by a buyer confirmation or the timed safety-net — never a vendor
# self-report"). A raw admin edit to 'shipped'/'delivered' would show that
# status while the real Shipment record — and escrow — never actually moved,
# then get silently overwritten again the next time the shipment does change
# state (sync_order_status_from_shipments recomputes the coarse status from
# the shipment's real progress), undoing the admin's edit with no
# explanation. The admin can still cancel/refund a shipped order by hand
# (e.g. a lost parcel) — that's the one exception, not a route to 'delivered'.
# ---------------------------------------------------------------------------
ORDER_STATUS_TRANSITIONS = {
    'pending': {'payment_pending', 'paid', 'cancelled'},
    'payment_pending': {'paid', 'cancelled'},
    'paid': {'confirmed', 'processing', 'cancelled', 'refunded'},
    'confirmed': {'processing', 'cancelled', 'refunded'},
    'processing': {'cancelled', 'refunded'},
    'shipped': {'cancelled', 'refunded'},
    # Terminal for direct admin status edits — once delivered/cancelled/
    # refunded, further changes go through the dedicated returns/refund flow
    # (which also handles inventory restoration), not this generic setter.
    'delivered': set(),
    'cancelled': set(),
    'refunded': set(),
}


def is_valid_status_transition(old_status, new_status):
    """True if `old_status` -> `new_status` is a sane, admin-editable order
    status change. Re-saving the same status is always a no-op allowed
    (e.g. just updating admin notes). An `old_status` the map doesn't
    recognize (legacy/unexpected data) is left permissive rather than
    blocking the admin from fixing it.
    """
    if old_status == new_status:
        return True
    if old_status not in ORDER_STATUS_TRANSITIONS:
        return True
    return new_status in ORDER_STATUS_TRANSITIONS[old_status]


PAYMENT_STATUS_TRANSITIONS = {
    'pending': {'processing', 'completed', 'failed', 'cancelled'},
    'processing': {'completed', 'failed', 'cancelled'},
    'completed': {'refunded'},
    'failed': {'pending', 'processing', 'cancelled'},
    'cancelled': set(),
    'refunded': set(),
}


def is_valid_payment_status_transition(old_status, new_status):
    """Same idea as is_valid_status_transition, for the payment_status field."""
    if old_status == new_status:
        return True
    if old_status not in PAYMENT_STATUS_TRANSITIONS:
        return True
    return new_status in PAYMENT_STATUS_TRANSITIONS[old_status]
