import random
from django.core.cache import cache
from django.urls import reverse

from .models import Product, Course, SupermarketItem


def _price(value):
    try:
        return str(int(value)) if value == int(value) else str(value)
    except Exception:
        return str(value or 0)


def _serialize_product(product):
    return {
        'id': product.id,
        'type': 'product',
        'name': product.name,
        'price': _price(product.price),
        'image': product.get_image_url(),
        'url': reverse('marketplace:product_detail', args=[product.slug]),
        'badge': 'Product',
        'meta': product.brand or (product.category.name if product.category else 'Marketplace'),
        'stock_text': 'In stock' if product.stock > 0 else 'Out of stock',
    }


def _serialize_course(course):
    return {
        'id': course.id,
        'type': 'course',
        'name': course.title,
        'price': _price(course.price),
        'image': course.get_image_url(),
        'url': reverse('marketplace:course_detail', args=[course.slug]),
        'badge': 'Course',
        'meta': f'{course.duration_hours}h · {course.lessons_count} lessons',
        'stock_text': 'Available',
    }


def _serialize_supermarket(item):
    return {
        'id': item.id,
        'type': 'supermarket',
        'name': item.name,
        'price': _price(item.price),
        'image': item.get_image_url(),
        'url': reverse('marketplace:supermarket_detail', args=[item.slug]),
        'badge': 'Supermarket',
        'meta': item.brand or item.get_unit_display(),
        'stock_text': 'In stock' if item.stock > 0 else 'Out of stock',
    }


def recommended_items(request, limit=20, include=(), category_slug='', query=''):
    """Randomized marketplace feed refreshed every 30 minutes."""
    include = tuple(include or ('product', 'course', 'supermarket'))
    cache_key = f'marketplace:random_feed:v1:{include}:{category_slug}:{query}:{limit}'
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
