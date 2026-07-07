import random
from django.core.cache import cache
from django.urls import reverse
from django.utils.translation import gettext, get_language

from .models import Product, Course, SupermarketItem


def _price(value):
    try:
        return str(int(value)) if value == int(value) else str(value)
    except Exception:
        return str(value or 0)


def _serialize_product(product):
    in_stock = product.stock > 0
    return {
        'id': product.id,
        'type': 'product',
        'name': product.name,
        'price': _price(product.price),
        'image': product.get_image_url(),
        'url': reverse('marketplace:product_detail', args=[product.slug]),
        'badge': gettext('商品'),
        'meta': product.brand or (product.category.name if product.category else gettext('市场')),
        'in_stock': in_stock,
        'stock_text': gettext('有货') if in_stock else gettext('缺货'),
    }


def _serialize_course(course):
    return {
        'id': course.id,
        'type': 'course',
        'name': course.title,
        'price': _price(course.price),
        'image': course.get_image_url(),
        'url': reverse('marketplace:course_detail', args=[course.slug]),
        'badge': gettext('课程'),
        'meta': f"{course.duration_hours}h · {course.lessons_count} {gettext('课时')}",
        'in_stock': True,
        'stock_text': gettext('可报名'),
    }


def _serialize_supermarket(item):
    in_stock = item.stock > 0
    return {
        'id': item.id,
        'type': 'supermarket',
        'name': item.name,
        'price': _price(item.price),
        'image': item.get_image_url(),
        'url': reverse('marketplace:supermarket_detail', args=[item.slug]),
        'badge': gettext('超市'),
        'meta': item.brand or item.get_unit_display(),
        'unit': item.get_unit_display(),
        'in_stock': in_stock,
        'stock_text': gettext('有货') if in_stock else gettext('缺货'),
    }


def recommended_items(request, limit=20, include=(), category_slug='', query=''):
    """Randomized marketplace feed refreshed every 30 minutes."""
    include = tuple(include or ('product', 'course', 'supermarket'))
    cache_key = f'marketplace:random_feed:v2:{get_language()}:{include}:{category_slug}:{query}:{limit}'
    cached = cache.get(cache_key)
    if cached is not None:
        return cached

    items = []
    if 'product' in include:
        qs = Product.objects.filter(is_active=True).select_related('category')
        if category_slug:
            qs = qs.filter(category__slug=category_slug)
        if query:
            qs = qs.filter(name__icontains=query)
        items.extend(_serialize_product(obj) for obj in qs.order_by('-sales_count', '-created_at')[: max(limit * 2, 24)])
    if 'course' in include:
        qs = Course.objects.filter(is_active=True).select_related('category')
        if category_slug:
            qs = qs.filter(category__slug=category_slug)
        if query:
            qs = qs.filter(title__icontains=query)
        items.extend(_serialize_course(obj) for obj in qs.order_by('-enrollment_count', '-created_at')[: max(limit, 16)])
    if 'supermarket' in include:
        qs = SupermarketItem.objects.filter(is_active=True).select_related('category')
        if category_slug:
            qs = qs.filter(category__slug=category_slug)
        if query:
            qs = qs.filter(name__icontains=query)
        items.extend(_serialize_supermarket(obj) for obj in qs.order_by('-sales_count', '-created_at')[: max(limit, 16)])

    random.shuffle(items)
    result = items[:limit]
    cache.set(cache_key, result, 1800)
    return result
