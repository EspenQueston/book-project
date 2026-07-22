"""Post-delivery reviews: queries, eligibility, and listing helpers."""
from __future__ import annotations

from decimal import Decimal
from typing import Optional

from django.conf import settings
from django.db.models import Avg, Count, Q, QuerySet

from .models import PostDeliveryReview


def reviews_for_listing(listing_kind: str, listing_id: int) -> QuerySet[PostDeliveryReview]:
    return (
        PostDeliveryReview.objects.filter(listing_kind=listing_kind, listing_id=listing_id)
        .select_related('site_user')
        .order_by('-avg_rating', '-created_at')
    )


def _round_or_none(value) -> Optional[float]:
    return float(round(value, 2)) if value is not None else None


def review_summary(listing_kind: str, listing_id: int) -> dict:
    qs = PostDeliveryReview.objects.filter(listing_kind=listing_kind, listing_id=listing_id)
    agg = qs.aggregate(
        n=Count('id'),
        avg=Avg('avg_rating'),
        avg_product=Avg('rating_product'),
        avg_service=Avg('rating_service'),
        avg_delivery=Avg('rating_delivery'),
    )
    n = agg['n'] or 0
    return {
        'count': n,
        'avg': _round_or_none(agg['avg']),
        'avg_product': _round_or_none(agg['avg_product']),
        'avg_service': _round_or_none(agg['avg_service']),
        'avg_delivery': _round_or_none(agg['avg_delivery']),
    }


def vendor_review_summary(vendor) -> dict:
    """Same shape as review_summary(), aggregated across every listing this
    vendor sells (books via VendorBook, products/courses/supermarket items
    via their direct vendor FK) — the "store rating" (Taobao/JD-style DSR:
    product quality / service / delivery speed), not a single listing's.
    count == 0 means the store has no reviews yet; callers should show a
    "new store" state rather than treating 0 as a real score."""
    from manager.models import VendorBook
    from .models import Product, Course, SupermarketItem

    book_ids = list(VendorBook.objects.filter(vendor=vendor, is_active=True).values_list('book_id', flat=True))
    product_ids = list(Product.objects.filter(vendor=vendor).values_list('id', flat=True))
    course_ids = list(Course.objects.filter(vendor=vendor).values_list('id', flat=True))
    supermarket_ids = list(SupermarketItem.objects.filter(vendor=vendor).values_list('id', flat=True))

    q = Q(pk__in=[])
    if book_ids:
        q |= Q(listing_kind='book', listing_id__in=book_ids)
    if product_ids:
        q |= Q(listing_kind='product', listing_id__in=product_ids)
    if course_ids:
        q |= Q(listing_kind='course', listing_id__in=course_ids)
    if supermarket_ids:
        q |= Q(listing_kind='supermarket', listing_id__in=supermarket_ids)

    agg = PostDeliveryReview.objects.filter(q).aggregate(
        n=Count('id'),
        avg=Avg('avg_rating'),
        avg_product=Avg('rating_product'),
        avg_service=Avg('rating_service'),
        avg_delivery=Avg('rating_delivery'),
    )
    n = agg['n'] or 0
    return {
        'count': n,
        'avg': _round_or_none(agg['avg']),
        'avg_product': _round_or_none(agg['avg_product']),
        'avg_service': _round_or_none(agg['avg_service']),
        'avg_delivery': _round_or_none(agg['avg_delivery']),
    }


def filter_reviews(qs: QuerySet[PostDeliveryReview], fl: str) -> QuerySet[PostDeliveryReview]:
    fl = (fl or 'all').lower()
    if fl == 'good':
        return qs.filter(avg_rating__gte=Decimal('4'))
    if fl == 'medium':
        return qs.filter(avg_rating__gte=Decimal('2.5'), avg_rating__lt=Decimal('4'))
    if fl == 'bad':
        return qs.filter(avg_rating__lt=Decimal('2.5'))
    if fl == 'with_image':
        return qs.filter(has_images=True)
    return qs


def serialize_review(r: PostDeliveryReview) -> dict:
    def img_url(p):
        if not p:
            return ''
        if isinstance(p, str) and (p.startswith('http://') or p.startswith('https://')):
            return p
        base = settings.MEDIA_URL.rstrip('/')
        sub = (p or '').lstrip('/')
        return f'{base}/{sub}' if sub else ''

    imgs = r.images if isinstance(r.images, list) else []
    return {
        'id': r.id,
        'user_name': r.site_user.name,
        'user_avatar': r.site_user.get_avatar_url(),
        'message': r.message,
        'images': [img_url(x) for x in imgs if x],
        'rating_product': r.rating_product,
        'rating_service': r.rating_service,
        'rating_delivery': r.rating_delivery,
        'avg_rating': float(r.avg_rating),
        'created_at': r.created_at.isoformat(),
        'has_images': r.has_images,
    }
