"""Post-delivery reviews: write form, submit, helpers."""
from __future__ import annotations

import os
import uuid

from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render
from django.core.files.storage import default_storage
from django.urls import reverse
from django.utils.translation import gettext as _
from django.views.decorators.http import require_http_methods

from marketplace.models import MarketplaceOrder, MarketplaceOrderItem, PostDeliveryReview
from . import models


def _mkt_order_owned_by_user(order, user: models.SiteUser) -> bool:
    if order.user_id and order.user_id == user.id:
        return True
    if order.user_email and order.user_email.strip().lower() == user.email.strip().lower():
        return True
    return False


def _eligible_book_order_item(user: models.SiteUser, oi_id: int) -> models.OrderItem | None:
    oi = get_object_or_404(models.OrderItem.objects.select_related('order', 'book'), pk=oi_id)
    o = oi.order
    if o.customer_email.strip().lower() != user.email.strip().lower():
        return None
    if o.status != 'delivered' or o.payment_status != 'completed':
        return None
    if PostDeliveryReview.objects.filter(book_order_item=oi).exists():
        return None
    return oi


def _eligible_marketplace_order_item(user: models.SiteUser, mi_id: int) -> MarketplaceOrderItem | None:
    mi = get_object_or_404(MarketplaceOrderItem.objects.select_related('order'), pk=mi_id)
    o = mi.order
    if not _mkt_order_owned_by_user(o, user):
        return None
    if o.status != 'delivered' or o.payment_status != 'completed':
        return None
    if PostDeliveryReview.objects.filter(marketplace_order_item=mi).exists():
        return None
    return mi


def _save_review_images(request, max_files: int = 5) -> list[str]:
    paths: list[str] = []
    for f in request.FILES.getlist('images')[:max_files]:
        if f.size > 3 * 1024 * 1024:
            continue
        ext = os.path.splitext(f.name)[1].lower() or '.jpg'
        if ext not in ('.jpg', '.jpeg', '.png', '.webp', '.gif'):
            continue
        name = f'review_uploads/{uuid.uuid4().hex}{ext}'
        saved = default_storage.save(name, f)
        paths.append(saved)
    return paths


@require_http_methods(['GET', 'HEAD'])
def review_write(request):
    uid = request.session.get('site_user_id')
    if not uid:
        messages.info(request, _('请先登录后再评价'))
        return redirect(f"{reverse('manager:user_login')}?next={request.get_full_path()}")
    user = get_object_or_404(models.SiteUser, pk=uid, is_active=True)

    book_item_id = request.GET.get('book_item')
    mkt_item_id = request.GET.get('mkt_item')
    oi = None
    mi = None
    if book_item_id:
        oi = _eligible_book_order_item(user, int(book_item_id))
    elif mkt_item_id:
        mi = _eligible_marketplace_order_item(user, int(mkt_item_id))

    if not oi and not mi:
        messages.error(request, _('无法评价此订单，或您已评价过'))
        return redirect(f"{reverse('manager:user_profile')}?tab=orders")

    ctx = {'site_user': user, 'book_order_item': oi, 'marketplace_order_item': mi}
    if oi:
        ctx['item_title'] = oi.book.name
        ctx['item_image'] = oi.book.get_cover_url()
        ctx['attrs_display'] = []
        ctx['quantity'] = oi.quantity
        ctx['order_date'] = oi.order.created_at
        ctx['delivered_at'] = oi.order.updated_at
    else:
        ctx['item_title'] = mi.item_name
        ctx['item_image'] = mi.item_image or ''
        ctx['attrs_display'] = list((mi.selected_attributes or {}).items()) if isinstance(mi.selected_attributes, dict) else []
        ctx['quantity'] = mi.quantity
        ctx['order_date'] = mi.order.created_at
        ctx['delivered_at'] = mi.order.updated_at

    return render(request, 'public/review_write.html', ctx)


@require_http_methods(['GET', 'POST', 'HEAD'])
def review_submit(request):
    if request.method == 'GET':
        return redirect('manager:review_write')

    uid = request.session.get('site_user_id')
    if not uid:
        return redirect('manager:user_login')
    user = get_object_or_404(models.SiteUser, pk=uid, is_active=True)

    book_item_id = request.POST.get('book_item_id')
    mkt_item_id = request.POST.get('mkt_item_id')
    oi = None
    mi = None
    if book_item_id:
        oi = _eligible_book_order_item(user, int(book_item_id))
    elif mkt_item_id:
        mi = _eligible_marketplace_order_item(user, int(mkt_item_id))

    if not oi and not mi:
        messages.error(request, _('提交失败'))
        return redirect(f"{reverse('manager:user_profile')}?tab=orders")

    try:
        rp = int(request.POST.get('rating_product', '0'))
        rs = int(request.POST.get('rating_service', '0'))
        rd = int(request.POST.get('rating_delivery', '0'))
    except ValueError:
        messages.error(request, _('评分无效'))
        return redirect(f"{reverse('manager:user_profile')}?tab=orders")

    if not all(1 <= x <= 5 for x in (rp, rs, rd)):
        messages.error(request, _('请为三项各选择 1–5 星'))
        return redirect(f"{reverse('manager:user_profile')}?tab=orders")

    msg = (request.POST.get('message') or '').strip()[:4000]
    imgs = _save_review_images(request)

    rev = PostDeliveryReview(
        site_user=user,
        book_order_item=oi,
        marketplace_order_item=mi,
        message=msg,
        images=imgs,
        rating_product=rp,
        rating_service=rs,
        rating_delivery=rd,
    )
    rev.full_clean()
    rev.save()

    messages.success(request, _('感谢您的评价！'))
    kind, lid = rev.listing_kind, rev.listing_id
    if kind == 'book':
        return redirect('manager:public_book_detail', book_id=lid)
    if kind == 'product':
        from marketplace.models import Product

        p = Product.objects.filter(pk=lid).first()
        return redirect('marketplace:product_detail', slug=p.slug) if p else redirect('marketplace:product_list')
    if kind == 'course':
        from marketplace.models import Course

        c = Course.objects.filter(pk=lid).first()
        return redirect('marketplace:course_detail', slug=c.slug) if c else redirect('marketplace:course_list')
    if kind == 'supermarket':
        from marketplace.models import SupermarketItem

        s = SupermarketItem.objects.filter(pk=lid).first()
        return redirect('marketplace:supermarket_detail', slug=s.slug) if s else redirect('marketplace:supermarket_list')
    return redirect('manager:public_home')


def collect_pending_reviews_for_user(user: models.SiteUser) -> list[dict]:
    """Build CTA rows for track order / profile."""
    from django.db.models import Q

    out: list[dict] = []
    orders = (
        models.Order.objects.filter(
            customer_email__iexact=user.email,
            status='delivered',
            payment_status='completed',
        )
        .order_by('-created_at')[:40]
        .prefetch_related('orderitem_set__book')
    )
    for o in orders:
        for oi in o.orderitem_set.all():
            if PostDeliveryReview.objects.filter(book_order_item=oi).exists():
                continue
            out.append(
                {
                    'title': oi.book.name,
                    'thumb': oi.book.get_cover_url(),
                    'url': f"{reverse('manager:review_write')}?book_item={oi.id}",
                }
            )

    morders = (
        MarketplaceOrder.objects.filter(status='delivered', payment_status='completed')
        .filter(Q(user_id=user.id) | Q(user_email__iexact=user.email))
        .order_by('-created_at')[:40]
        .prefetch_related('items')
    )
    for mo in morders:
        for mi in mo.items.all():
            if PostDeliveryReview.objects.filter(marketplace_order_item=mi).exists():
                continue
            img = mi.item_image or ''
            out.append(
                {
                    'title': mi.item_name,
                    'thumb': img,
                    'url': f"{reverse('manager:review_write')}?mkt_item={mi.id}",
                }
            )
    return out[:12]
