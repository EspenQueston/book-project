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


def review_summary(listing_kind: str, listing_id: int) -> dict:
    qs = PostDeliveryReview.objects.filter(listing_kind=listing_kind, listing_id=listing_id)
    agg = qs.aggregate(
        n=Count('id'),
        avg=Avg('avg_rating'),
    )
    n = agg['n'] or 0
    avg = agg['avg']
    return {
        'count': n,
        'avg': float(round(avg, 2)) if avg is not None else None,
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
