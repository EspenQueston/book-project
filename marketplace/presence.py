"""Live product page presence (concurrent viewers) via Django cache."""

import time

from django.core.cache import cache

PRESENCE_TTL_SECONDS = 180
HEARTBEAT_INTERVAL_SECONDS = 45


def _cache_key(product_id):
    return f'marketplace:product:presence:{product_id}'


def get_visitor_id(request):
    if not request.session.session_key:
        request.session.create()
    return request.session.session_key


def _prune(viewers, now=None):
    now = now or time.time()
    cutoff = now - PRESENCE_TTL_SECONDS
    return {visitor_id: seen_at for visitor_id, seen_at in viewers.items() if seen_at >= cutoff}


def touch_product_presence(product_id, visitor_id):
    """Register or refresh a visitor on a product detail page."""
    key = _cache_key(product_id)
    now = time.time()
    viewers = _prune(cache.get(key) or {}, now)
    viewers[visitor_id] = now
    cache.set(key, viewers, timeout=PRESENCE_TTL_SECONDS + 60)
    return len(viewers)


def count_product_viewers(product_id):
    """Return active viewer count for a product."""
    key = _cache_key(product_id)
    now = time.time()
    viewers = _prune(cache.get(key) or {}, now)
    if viewers:
        cache.set(key, viewers, timeout=PRESENCE_TTL_SECONDS + 60)
    return len(viewers)


def clear_product_presence(product_id):
    """Remove all live viewer presence data for a product."""
    try:
        cache.delete(_cache_key(product_id))
    except Exception:
        pass
