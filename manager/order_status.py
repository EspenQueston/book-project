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
