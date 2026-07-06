# -*- coding: utf-8 -*-
"""Preference-based recommendation engine.

Builds a lightweight preference profile for a shopper from the behavioural
signals we already store — favorites (wishlist), cart contents, paid orders,
followed publishers/vendors and the sellers they message most — then scores
candidate listings (books, products, courses, supermarket items) against that
profile. Used by the home infinite feed, the marketplace and the book catalog.

Design goals: no new tables, bounded query counts, graceful fallback to
popularity for anonymous or signal-less visitors, and stable ordering so
paginated slicing stays consistent within a session.
"""
from __future__ import annotations

from collections import defaultdict

from django.utils.translation import gettext as _

from manager import models

# Signal weights — how much each behaviour says about intent. Following /
# buying are the strongest signals; a cart or a favourite is medium; chatting a
# lot with a seller is a softer affinity hint.
W_FOLLOW = 5.0
W_PURCHASE = 4.0
W_FAVORITE = 3.0
W_CART = 2.5
W_DISCUSS = 2.0

# How much each kind of match contributes to an item's final score.
S_VENDOR = 8.0
S_PUBLISHER = 8.0
S_CATEGORY = 6.0
S_TYPE = 2.0
S_POPULARITY = 1.0  # applied to a 0..1 normalized popularity

# Bound candidate pools so scoring stays cheap regardless of catalog size.
POOL_PER_TYPE = 80


def _norm(counter):
    """Normalize a weight dict so the largest entry == 1.0 (keeps popularity
    and preference contributions on comparable scales)."""
    if not counter:
        return {}
    top = max(counter.values()) or 1.0
    return {k: v / top for k, v in counter.items()}


def build_preference_profile(user_id, session_key=''):
    """Return a dict of weighted preferences derived from the user's signals.

    Keys: book_categories, mkt_categories, vendors, publishers, types.
    Each maps id -> weight. Also returns `has_signal` and `owned` (item keys to
    optionally exclude) and `reasons` (id -> human label) for UI hints.
    """
    book_cats = defaultdict(float)
    mkt_cats = defaultdict(float)
    vendors = defaultdict(float)
    publishers = defaultdict(float)
    types = defaultdict(float)
    reasons = {}
    owned = set()

    user = None
    if user_id:
        user = models.SiteUser.objects.filter(pk=user_id).first()

    # ---- Followed publishers / vendors (strongest, explicit intent) ----
    if user:
        for pub_id in models.UserFollowedShop.objects.filter(user=user).values_list('publisher_id', flat=True):
            publishers[pub_id] += W_FOLLOW
            reasons[('publisher', pub_id)] = _('来自你关注的出版社')
            types['book'] += W_FOLLOW * 0.5
        for ven_id in models.UserFollowedVendor.objects.filter(user=user).values_list('vendor_id', flat=True):
            vendors[ven_id] += W_FOLLOW
            reasons[('vendor', ven_id)] = _('来自你关注的卖家')

    # ---- Favorites / wishlist ----
    if user:
        wl = models.Wishlist.objects.filter(user=user).select_related('book', 'book__category', 'book__publisher')
        for w in wl[:200]:
            types[w.item_type] += W_FAVORITE * 0.5
            if w.item_type == 'book' and w.book:
                owned.add(('book', w.book_id))
                if w.book.category_id:
                    book_cats[w.book.category_id] += W_FAVORITE
                if w.book.publisher_id:
                    publishers[w.book.publisher_id] += W_FAVORITE
            elif w.item_id:
                owned.add((w.item_type, w.item_id))
                _apply_mkt_item(w.item_type, w.item_id, W_FAVORITE, mkt_cats, vendors)

    # ---- Cart (book cart is session-scoped; marketplace cart too) ----
    if session_key:
        for ci in models.CartItem.objects.filter(session_key=session_key).select_related('book', 'book__category', 'book__publisher')[:100]:
            types['book'] += W_CART * 0.5
            if ci.book:
                if ci.book.category_id:
                    book_cats[ci.book.category_id] += W_CART
                if ci.book.publisher_id:
                    publishers[ci.book.publisher_id] += W_CART
        try:
            from marketplace.models import MarketplaceCartItem
            for mc in MarketplaceCartItem.objects.filter(session_key=session_key)[:100]:
                types[mc.item_type] += W_CART * 0.5
                _apply_mkt_item(mc.item_type, mc.item_id, W_CART, mkt_cats, vendors)
        except Exception:
            pass

    # ---- Paid orders (most paid articles) ----
    if user:
        # Book orders link by customer email.
        book_items = models.OrderItem.objects.filter(
            order__customer_email__iexact=user.email
        ).select_related('book', 'book__category', 'book__publisher')[:200]
        for oi in book_items:
            types['book'] += W_PURCHASE * 0.5
            if oi.book:
                owned.add(('book', oi.book_id))
                if oi.book.category_id:
                    book_cats[oi.book.category_id] += W_PURCHASE
                if oi.book.publisher_id:
                    publishers[oi.book.publisher_id] += W_PURCHASE
        try:
            from marketplace.models import MarketplaceOrder, MarketplaceOrderItem
            order_ids = MarketplaceOrder.objects.filter(user_id=user.id).values_list('id', flat=True)
            for mi in MarketplaceOrderItem.objects.filter(order_id__in=list(order_ids))[:200]:
                types[mi.item_type] += W_PURCHASE * 0.5
                owned.add((mi.item_type, mi.item_id))
                _apply_mkt_item(mi.item_type, mi.item_id, W_PURCHASE, mkt_cats, vendors)
        except Exception:
            pass

    # ---- Most-discussed sellers (conversation affinity) ----
    if user:
        convo_vendor_ids = models.Conversation.objects.filter(
            buyer=user, vendor__isnull=False
        ).values_list('vendor_id', flat=True)
        for ven_id in convo_vendor_ids:
            vendors[ven_id] += W_DISCUSS
            reasons.setdefault(('vendor', ven_id), _('来自你常联系的卖家'))

    profile = {
        'book_categories': _norm(book_cats),
        'mkt_categories': _norm(mkt_cats),
        'vendors': _norm(vendors),
        'publishers': _norm(publishers),
        'types': _norm(types),
        'reasons': reasons,
        'owned': owned,
    }
    profile['has_signal'] = bool(book_cats or mkt_cats or vendors or publishers or types)
    return profile


def _apply_mkt_item(item_type, item_id, weight, mkt_cats, vendors):
    """Add category/vendor weight for a marketplace item id."""
    try:
        from marketplace.models import Product, Course, SupermarketItem
        model = {'product': Product, 'course': Course, 'supermarket': SupermarketItem}.get(item_type)
        if not model:
            return
        obj = model.objects.filter(pk=item_id).only('id', 'category_id', 'vendor_id').first()
        if not obj:
            return
        if getattr(obj, 'category_id', None):
            mkt_cats[obj.category_id] += weight
        if getattr(obj, 'vendor_id', None):
            vendors[obj.vendor_id] += weight
    except Exception:
        pass


def _pop_norm(value, cap):
    if not value or cap <= 0:
        return 0.0
    return min(float(value) / float(cap), 1.0)


def _score_book(b, profile, pop_cap):
    score = S_POPULARITY * _pop_norm(b.sale_num, pop_cap)
    reason = None
    if b.category_id and b.category_id in profile['book_categories']:
        score += S_CATEGORY * profile['book_categories'][b.category_id]
    if b.publisher_id and b.publisher_id in profile['publishers']:
        score += S_PUBLISHER * profile['publishers'][b.publisher_id]
        reason = profile['reasons'].get(('publisher', b.publisher_id)) or reason
    score += S_TYPE * profile['types'].get('book', 0)
    return score, reason


def _score_mkt(obj, item_type, profile, pop_cap):
    pop = getattr(obj, 'sales_count', None)
    if pop is None:
        pop = getattr(obj, 'enrollment_count', 0)
    score = S_POPULARITY * _pop_norm(pop, pop_cap)
    reason = None
    cat_id = getattr(obj, 'category_id', None)
    if cat_id and cat_id in profile['mkt_categories']:
        score += S_CATEGORY * profile['mkt_categories'][cat_id]
    ven_id = getattr(obj, 'vendor_id', None)
    if ven_id and ven_id in profile['vendors']:
        score += S_VENDOR * profile['vendors'][ven_id]
        reason = profile['reasons'].get(('vendor', ven_id)) or reason
    score += S_TYPE * profile['types'].get(item_type, 0)
    return score, reason


def _book_item(b, recommended=False, reason=None):
    return {
        'type': 'book', 'type_label': _('图书'),
        'name': b.name[:40], 'price': str(b.price),
        'image': b.get_cover_url(), 'url': f'/manager/public/books/{b.id}/',
        'recommended': recommended, 'reason': reason or '',
    }


def _mkt_item(obj, item_type, recommended=False, reason=None):
    if item_type == 'course':
        name, url = obj.title[:40], f'/marketplace/courses/{obj.slug}/'
        label = _('课程')
    elif item_type == 'supermarket':
        name, url = obj.name[:40], f'/marketplace/supermarket/{obj.slug}/'
        label = _('超市')
    else:
        name, url = obj.name[:40], f'/marketplace/products/{obj.slug}/'
        label = _('商品')
    return {
        'type': item_type, 'type_label': label,
        'name': name, 'price': str(obj.price),
        'image': obj.get_image_url(), 'url': url,
        'recommended': recommended, 'reason': reason or '',
    }


def _domain_types(domain):
    if domain == 'books':
        return ['book']
    if domain == 'marketplace':
        return ['product', 'course', 'supermarket']
    return ['book', 'product', 'course', 'supermarket']


def rank_candidates(profile, types, exclude=None, pool_per_type=POOL_PER_TYPE):
    """Return a fully-scored, descending list of item dicts for the given types."""
    exclude = exclude or set()
    scored = []  # (score, tiebreak, item_dict)

    if 'book' in types:
        qs = models.Book.objects.filter(is_active=True).select_related('publisher', 'category')
        candidates = list(qs.order_by('-sale_num')[:pool_per_type])
        # Ensure favourite publishers/categories surface even if not top sellers.
        pref_pub = [p for p, w in profile['publishers'].items()]
        if pref_pub:
            for b in qs.filter(publisher_id__in=pref_pub).order_by('-sale_num')[:pool_per_type]:
                if b not in candidates:
                    candidates.append(b)
        pop_cap = max([b.sale_num for b in candidates] or [1])
        for b in candidates:
            if ('book', b.id) in exclude:
                continue
            score, reason = _score_book(b, profile, pop_cap)
            scored.append((score, ('book', b.id), _book_item(b, recommended=bool(reason) or score > S_POPULARITY, reason=reason)))

    mkt_types = [t for t in types if t != 'book']
    if mkt_types:
        try:
            from marketplace.models import Product, Course, SupermarketItem
            model_map = {'product': (Product, 'sales_count'), 'course': (Course, 'enrollment_count'),
                         'supermarket': (SupermarketItem, 'sales_count')}
            pref_ven = [v for v in profile['vendors']]
            for t in mkt_types:
                model, pop_field = model_map[t]
                qs = model.objects.filter(is_active=True).select_related('category', 'vendor')
                candidates = list(qs.order_by('-' + pop_field)[:pool_per_type])
                if pref_ven:
                    for o in qs.filter(vendor_id__in=pref_ven).order_by('-' + pop_field)[:pool_per_type]:
                        if o not in candidates:
                            candidates.append(o)
                pop_cap = max([getattr(o, pop_field, 0) for o in candidates] or [1])
                for o in candidates:
                    if (t, o.id) in exclude:
                        continue
                    score, reason = _score_mkt(o, t, profile, pop_cap)
                    scored.append((score, (t, o.id), _mkt_item(o, t, recommended=bool(reason) or score > S_POPULARITY, reason=reason)))
        except Exception:
            pass

    # Stable sort: score desc, then type/id for determinism.
    scored.sort(key=lambda x: (-x[0], x[1]))
    return [item for _s, _k, item in scored]


def recommend(user_id, session_key='', domain='mixed', page=1, per_page=12, exclude_owned=False):
    """Top-level entry point. Returns (items, has_more).

    Falls back to popularity ordering when there is no usable signal, so
    anonymous visitors still get a sensible feed.
    """
    types = _domain_types(domain)
    profile = build_preference_profile(user_id, session_key)
    exclude = profile['owned'] if exclude_owned else set()
    ranked = rank_candidates(profile, types, exclude=exclude)

    start = max(0, (page - 1) * per_page)
    window = ranked[start:start + per_page]
    has_more = len(ranked) > start + per_page
    return window, has_more, profile['has_signal']
