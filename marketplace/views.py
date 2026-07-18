from django.shortcuts import render, get_object_or_404, redirect
from django.urls import reverse
from django.http import JsonResponse, FileResponse, Http404, HttpResponseForbidden
from django.db.models import Q, Sum, Count, Avg, OuterRef, Subquery, Value, IntegerField, F
from django.db.models.functions import Coalesce, TruncMonth
from django.core.paginator import Paginator
from django.core.validators import URLValidator
from django.core.exceptions import ValidationError
from django.contrib import messages
from django.utils.text import slugify
from django.utils import timezone
from django.views.decorators.http import require_POST
from django.utils.translation import gettext as _
from django.views.decorators.clickjacking import xframe_options_sameorigin
from .models import (
    Category, Product, Course, SupermarketItem,
    MarketplaceOrder, MarketplaceOrderItem,
    MarketplaceCartItem, CourseSection, CourseLesson, CourseProgress,
    ProductAttribute, SupermarketItemAttribute,
    PostDeliveryReview,
)
from .utils import build_attribute_groups, validate_selected_attributes, normalize_selected_attributes
from .review_service import reviews_for_listing, review_summary, filter_reviews, serialize_review
from .pricing_rules import validate_quantity, pricing_display_context
from .presence import (
    get_visitor_id,
    touch_product_presence,
    HEARTBEAT_INTERVAL_SECONDS,
)
from book_Project.payment_config import build_payment_options

try:
    from .recommendations import recommended_items
except ModuleNotFoundError:
    def recommended_items(request, limit=20, include=(), category_slug='', query=''):
        """Safe fallback when optional recommendations module is absent."""
        return []
from decimal import Decimal
from datetime import timedelta
from django.db import transaction
from django.core.cache import cache
import uuid
import json
import io
import zipfile
from manager.models import SiteUser, Vendor, UserFollowedVendor
from manager.official_store import assign_official_vendor, resolve_listing_vendor


def _cached_categories(section):
    """Active categories for a listing section — identical for every visitor
    and requested on every listing page load, so it's cached with a short
    TTL (matches the trending-feed cache pattern) rather than hitting the
    DB fresh each time. Never used on admin pages, which need to see a
    just-added category immediately."""
    cache_key = f'listing:categories:{section}:v1'
    cached = cache.get(cache_key)
    if cached is not None:
        return cached
    result = list(Category.objects.filter(section=section, is_active=True))
    cache.set(cache_key, result, 300)
    return result


def _seller_follow_context(request, vendor=None):
    """Follow state for marketplace listing detail pages."""
    ctx = {
        'is_following_vendor': False,
        'vendor_follower_count': 0,
    }
    if not vendor:
        return ctx
    ctx['vendor_follower_count'] = UserFollowedVendor.objects.filter(vendor=vendor).count()
    user_id = request.session.get('site_user_id')
    if user_id:
        ctx['is_following_vendor'] = UserFollowedVendor.objects.filter(
            user_id=user_id, vendor=vendor
        ).exists()
    return ctx


def _annotate_product_delivered(qs):
    sub = MarketplaceOrderItem.objects.filter(
        item_type='product',
        item_id=OuterRef('pk'),
        order__status='delivered',
        order__payment_status='completed',
    ).values('item_id').annotate(total=Sum('quantity')).values('total')[:1]
    return qs.annotate(
        sold_delivered=Coalesce(Subquery(sub, output_field=IntegerField()), Value(0))
    )


def _annotate_course_delivered(qs):
    sub = MarketplaceOrderItem.objects.filter(
        item_type='course',
        item_id=OuterRef('pk'),
        order__status='delivered',
        order__payment_status='completed',
    ).values('item_id').annotate(total=Sum('quantity')).values('total')[:1]
    return qs.annotate(
        sold_delivered=Coalesce(Subquery(sub, output_field=IntegerField()), Value(0))
    )


def _annotate_supermarket_delivered(qs):
    sub = MarketplaceOrderItem.objects.filter(
        item_type='supermarket',
        item_id=OuterRef('pk'),
        order__status='delivered',
        order__payment_status='completed',
    ).values('item_id').annotate(total=Sum('quantity')).values('total')[:1]
    return qs.annotate(
        sold_delivered=Coalesce(Subquery(sub, output_field=IntegerField()), Value(0))
    )


# ─── Helper ───────────────────────────────────────────────────────────────────

def _admin_required(request):
    """Check if admin is logged in via session."""
    if not request.session.get("name"):
        return redirect('/manager/login/')
    return None


def _apply_uploaded_media(obj, request):
    """Attach any uploaded image_4/image_5/video files from request.FILES
    onto obj (Product or SupermarketItem). Mirrors the existing per-field
    image/image_2/image_3 handling at each call site — kept separate so the
    5-image + 1-video slots stay in sync across all 4 product/supermarket
    admin+vendor create/edit views without duplicating this list everywhere."""
    for field in ('image_4', 'image_5', 'video'):
        if request.FILES.get(field):
            setattr(obj, field, request.FILES[field])


def _positive_int(value, default=1):
    try:
        return max(1, int(value))
    except (TypeError, ValueError):
        return default


def _non_negative_int(value, default=0):
    try:
        return max(0, int(value))
    except (TypeError, ValueError):
        return default


def _optional_positive_int(value):
    if value in (None, ''):
        return None
    try:
        return max(1, int(value))
    except (TypeError, ValueError):
        return None


def _positive_decimal(value, default=None):
    try:
        decimal_value = Decimal(str(value))
        return decimal_value if decimal_value > 0 else default
    except Exception:
        return default


def _valid_url_or_blank(value):
    value = (value or '').strip()
    if not value:
        return True
    validator = URLValidator()
    try:
        validator(value)
        return True
    except ValidationError:
        return False


def _minimum_quantity_message(item):
    return f'最低购买数量为 {getattr(item, "min_order_quantity", 1)} 件'


def _pricing_rules_from_post(request):
    """Build the internal rules JSON from friendly form fields."""
    rules = {}

    tiers = []
    for min_qty, max_qty, unit_price in zip(
        request.POST.getlist('tier_min'),
        request.POST.getlist('tier_max'),
        request.POST.getlist('tier_unit_price'),
    ):
        min_qty = (min_qty or '').strip()
        max_qty = (max_qty or '').strip()
        unit_price = (unit_price or '').strip()
        if min_qty and unit_price:
            tier = {'min': _positive_int(min_qty, 1), 'unit_price': unit_price}
            if max_qty:
                tier['max'] = _positive_int(max_qty, 1)
            tiers.append(tier)
    if tiers:
        rules['tiers'] = tiers

    discount_value = (request.POST.get('discount_value') or '').strip()
    if discount_value:
        discount = {
            'type': request.POST.get('discount_type', 'percent'),
            'value': discount_value,
            'priority': _positive_int(request.POST.get('discount_priority'), 1),
        }
        min_total = (request.POST.get('discount_min_total') or '').strip()
        if min_total:
            discount['min_cart_total'] = min_total
        rules['discounts'] = [discount]

    buy_qty = _optional_positive_int(request.POST.get('bogo_buy_qty'))
    get_qty = _optional_positive_int(request.POST.get('bogo_get_qty'))
    if buy_qty and get_qty:
        rules['bogo'] = {
            'buy_qty': buy_qty,
            'get_qty': get_qty,
            'discount_percent': request.POST.get('bogo_discount_percent') or '100',
        }

    raw = (request.POST.get('pricing_rules') or '').strip()
    if not rules and raw:
        try:
            parsed = json.loads(raw)
            return parsed if isinstance(parsed, dict) else {}
        except json.JSONDecodeError:
            messages.warning(request, 'Les règles avancées sont invalides et ont été ignorées.')
    return rules


def _rules_json_for_form(obj=None):
    rules = getattr(obj, 'pricing_rules', None) or {}
    if not rules:
        return ''
    return json.dumps(rules, ensure_ascii=False, indent=2)


def _pricing_rule_form(obj=None):
    rules = getattr(obj, 'pricing_rules', None) or {}
    if not isinstance(rules, dict):
        rules = {}
    tiers = list(rules.get('tiers') or [])
    if not tiers:
        tiers = [{'min': '', 'max': '', 'unit_price': ''}]

    discounts = list(rules.get('discounts') or [])
    discount = discounts[0] if discounts else {}
    bogo = rules.get('bogo') or {}
    return {
        'tiers': tiers,
        'discount': discount,
        'bogo': bogo,
        'has_rules': bool(rules),
    }


def _form_context_with_pricing(context, obj=None):
    context['pricing_rule_form'] = _pricing_rule_form(obj)
    context['pricing_rules_json'] = _rules_json_for_form(obj)
    return context


def _field_error_map(request):
    if not hasattr(request, '_field_errors'):
        request._field_errors = {}
    return request._field_errors


def _add_field_error(request, field_name, message):
    _field_error_map(request)[field_name] = message
    messages.error(request, message)


def _posted_value(request, field_name, default=''):
    return request.POST.get(field_name, default)


def _posted_list(request, field_name):
    return request.POST.getlist(field_name)


def _required_text(request, field_name, label, min_length=1):
    value = (request.POST.get(field_name) or '').strip()
    if not value:
        _add_field_error(request, field_name, f'{label} est obligatoire.')
        return None
    if len(value) < min_length:
        _add_field_error(request, field_name, f'{label} doit contenir au moins {min_length} caractères.')
        return None
    return value


def _required_category(request, section, redirect_name, pk=None):
    category_id = (request.POST.get('category') or '').strip()
    if not category_id:
        _add_field_error(request, 'category', 'La catégorie est obligatoire.')
        return None
    category = Category.objects.filter(pk=category_id, section=section, is_active=True).first()
    if not category:
        _add_field_error(request, 'category', 'Catégorie invalide.')
        return None
    return category


def _build_marketplace_form_state(request, base_obj=None):
    return {
        'values': dict(request.POST.items()),
        'lists': {key: request.POST.getlist(key) for key in request.POST.keys()},
        'errors': _field_error_map(request),
        'base_obj': base_obj,
    }


def _validate_marketplace_business_rules(request, require_images=0, allow_existing_images=False):
    price = _positive_decimal(request.POST.get('price'))
    if price is None:
        _add_field_error(request, 'price', _('价格必须大于 0。'))

    stock_raw = request.POST.get('stock')
    if stock_raw not in (None, ''):
        try:
            if int(stock_raw) < 0:
                _add_field_error(request, 'stock', _('库存不能小于 0。'))
        except (TypeError, ValueError):
            _add_field_error(request, 'stock', _('库存格式无效。'))

    min_qty = _positive_int(request.POST.get('min_order_quantity'), 1)
    max_qty = _optional_positive_int(request.POST.get('max_order_quantity'))
    step_qty = _positive_int(request.POST.get('quantity_step'), 1)
    if max_qty and max_qty < min_qty:
        _add_field_error(request, 'max_order_quantity', _('最大购买量必须大于或等于最小购买量。'))
    if step_qty > min_qty and min_qty % step_qty != 0:
        _add_field_error(request, 'quantity_step', _('购买步长必须与最小购买量逻辑一致。'))

    preview_url = request.POST.get('preview_url')
    if preview_url is not None and not _valid_url_or_blank(preview_url):
        _add_field_error(request, 'preview_url', _('请输入有效的 URL。'))

    download_link = request.POST.get('download_link')
    if download_link is not None and not _valid_url_or_blank(download_link):
        _add_field_error(request, 'download_link', _('请输入有效的 URL。'))

    image_count = sum(1 for key in ['image', 'image_2', 'image_3', 'cover_image'] if request.FILES.get(key))
    if require_images and image_count < require_images and not allow_existing_images:
        _add_field_error(request, 'image', _('请至少上传一张图片。') if require_images == 1 else _('请至少上传所需数量的图片。'))

    return len(_field_error_map(request)) == 0


def _max_purchase_quantity(item):
    max_qty = getattr(item, 'max_order_quantity', None)
    stock = getattr(item, 'stock', 0) or 0
    return min(stock, max_qty) if max_qty else stock


# ═══════════════════════════════════════════════════════════════════════════════
#  PUBLIC VIEWS
# ═══════════════════════════════════════════════════════════════════════════════

def marketplace_home(request):
    """Marketplace landing page with featured items from all sections."""
    featured_products = _annotate_product_delivered(
        Product.objects.filter(is_active=True).select_related('category')
    ).order_by('-sold_delivered', '-sales_count', '-created_at')[:8]
    featured_courses = _annotate_course_delivered(
        Course.objects.filter(is_active=True).select_related('category')
    ).order_by('-sold_delivered', '-enrollment_count', '-created_at')[:4]
    featured_supermarket = _annotate_supermarket_delivered(
        SupermarketItem.objects.filter(is_active=True).select_related('category')
    ).order_by('-sold_delivered', '-sales_count', '-created_at')[:4]

    if request.GET.get('format') == 'json':
        page_num = int(request.GET.get('page', 1) or 1)
        rec_items = recommended_items(request, limit=24, include=('product', 'course', 'supermarket'))
        page_size = 12
        start = (page_num - 1) * page_size
        end = start + page_size
        sliced = rec_items[start:end]
        if not sliced and rec_items:
            sliced = rec_items[:page_size]
            page_num = 1
        return JsonResponse({
            'items': sliced,
            'page': page_num,
            'has_more': bool(rec_items),
        })

    product_count = Product.objects.filter(is_active=True).count()
    course_count = Course.objects.filter(is_active=True).count()
    supermarket_count = SupermarketItem.objects.filter(is_active=True).count()
    recommended_feed = recommended_items(request, limit=12, include=('product', 'course', 'supermarket'))

    context = {
        'featured_products': featured_products,
        'featured_courses': featured_courses,
        'featured_supermarket': featured_supermarket,
        'product_count': product_count,
        'course_count': course_count,
        'supermarket_count': supermarket_count,
        'recommended_feed': recommended_feed,
    }
    return render(request, 'marketplace/home.html', context)


def product_list(request):
    """Browse all products with search and category filter."""
    products = _annotate_product_delivered(
        Product.objects.filter(is_active=True).select_related('category')
    )
    categories = _cached_categories('products')

    q = request.GET.get('q', '').strip()
    cat = request.GET.get('category', '')
    sort = request.GET.get('sort', '-created_at')

    if q:
        products = products.filter(Q(name__icontains=q) | Q(description__icontains=q) | Q(brand__icontains=q))
    if cat:
        products = products.filter(category__slug=cat)
    if sort == '-sales_count':
        products = products.order_by('-sold_delivered', '-sales_count')
    elif sort in ['price', '-price', '-created_at', 'name']:
        products = products.order_by(sort)

    paginator = Paginator(products, 12)
    page = paginator.get_page(request.GET.get('page', 1))

    if request.GET.get('format') == 'json':
        if request.GET.get('recommend') == '1':
            rec_items = recommended_items(request, limit=20, include=('product',), category_slug=cat, query=q)
            return JsonResponse({'items': rec_items, 'page': int(request.GET.get('page', 1) or 1), 'has_more': True})
        data_products = []
        for product in page:
            data_products.append({
                'id': product.id,
                'name': product.name,
                'price': str(product.price),
                'image': product.get_image_url(),
                'url': reverse('marketplace:product_detail', args=[product.slug]),
                'badge': _('商品'),
                'stock_text': _('有货') if product.in_stock else _('缺货'),
                'sold_delivered': int(getattr(product, 'sold_delivered', 0) or 0),
                'in_stock': product.in_stock,
            })
        return JsonResponse({
            'items': data_products,
            'page': page.number,
            'has_more': page.has_next(),
        })

    context = {
        'products': page,
        'categories': categories,
        'query': q,
        'current_category': cat,
        'current_sort': sort,
    }
    return render(request, 'marketplace/products.html', context)


def product_detail(request, slug):
    """Single product detail page."""
    product = get_object_or_404(Product, slug=slug, is_active=True)

    view_key = f'product_viewed_{product.pk}'
    if not request.session.get(view_key):
        Product.objects.filter(pk=product.pk).update(views_count=F('views_count') + 1)
        request.session[view_key] = True
        product.views_count = (product.views_count or 0) + 1

    visitor_id = get_visitor_id(request)
    live_viewers = touch_product_presence(product.pk, visitor_id)

    related = Product.objects.filter(
        is_active=True, category=product.category
    ).exclude(pk=product.pk)[:4] if product.category else Product.objects.none()
    attribute_context = build_attribute_groups(product.attributes.all())

    sold_delivered = product.get_units_sold_delivered()
    preview = list(reviews_for_listing('product', product.pk)[:3])
    summary = review_summary('product', product.pk)
    seller_vendor = resolve_listing_vendor(product.vendor)
    from manager.fulfillment_service import get_delivery_estimate
    context = {
        'product': product,
        'seller_vendor': seller_vendor,
        'related_products': related,
        'attribute_groups': attribute_context['groups'],
        'selectable_attributes': attribute_context['selectable_groups'],
        'specification_attributes': attribute_context['specification_groups'],
        'sold_delivered': sold_delivered,
        'live_viewers': live_viewers,
        'presence_heartbeat_seconds': HEARTBEAT_INTERVAL_SECONDS,
        'listing_reviews_preview': preview,
        'listing_review_summary': summary,
        'listing_kind': 'product',
        'listing_id': product.pk,
        'max_purchase_quantity': _max_purchase_quantity(product),
        'pricing_display': pricing_display_context(product),
        'delivery_estimate': get_delivery_estimate('product', product.pk),
        **_seller_follow_context(request, seller_vendor),
    }
    return render(request, 'marketplace/product_detail.html', context)


@require_POST
def product_presence(request, product_id):
    """Heartbeat: keep session active on product page; return live viewer count."""
    get_object_or_404(Product, pk=product_id, is_active=True)
    visitor_id = get_visitor_id(request)
    count = touch_product_presence(product_id, visitor_id)
    return JsonResponse({'success': True, 'count': count})


def course_list(request):
    """Browse all courses with search and filter."""
    courses = _annotate_course_delivered(
        Course.objects.filter(is_active=True).select_related('category')
    )
    categories = _cached_categories('courses')

    q = request.GET.get('q', '').strip()
    cat = request.GET.get('category', '')
    level = request.GET.get('level', '')
    sort = request.GET.get('sort', '-created_at')

    if q:
        courses = courses.filter(Q(title__icontains=q) | Q(description__icontains=q) | Q(instructor__icontains=q))
    if cat:
        courses = courses.filter(category__slug=cat)
    if level:
        courses = courses.filter(level=level)
    if sort == '-enrollment_count':
        courses = courses.order_by('-sold_delivered', '-enrollment_count')
    elif sort in ['price', '-price', '-rating', '-created_at']:
        courses = courses.order_by(sort)

    paginator = Paginator(courses, 12)
    page = paginator.get_page(request.GET.get('page', 1))

    if request.GET.get('format') == 'json':
        if request.GET.get('recommend') == '1':
            rec_items = recommended_items(request, limit=20, include=('course',), category_slug=cat, query=q)
            return JsonResponse({'items': rec_items, 'page': int(request.GET.get('page', 1) or 1), 'has_more': True})
        data_courses = []
        for course in page:
            data_courses.append({
                'id': course.id,
                'name': course.title,
                'price': str(course.price),
                'image': course.get_image_url(),
                'url': reverse('marketplace:course_detail', args=[course.slug]),
                'badge': _('课程'),
                'meta': f"{course.duration_hours}h · {course.lessons_count} {_('课时')}",
                'sold_delivered': int(getattr(course, 'sold_delivered', 0) or 0),
            })
        return JsonResponse({
            'items': data_courses,
            'page': page.number,
            'has_more': page.has_next(),
        })

    context = {
        'courses': page,
        'categories': categories,
        'query': q,
        'current_category': cat,
        'current_level': level,
        'current_sort': sort,
    }
    return render(request, 'marketplace/courses.html', context)


def user_can_access_course(request, course):
    """True if the current visitor has a completed purchase of this course,
    OR is the vendor who owns it.

    Checked at course level, not per-lesson, since ownership of a course
    unlocks every non-free lesson in it — this keeps the check to a single
    query per request regardless of how many lessons are rendered.

    Payment completion (not order/shipment status) is the gate for buyers:
    courses are digital, so tying access to the physical-goods fulfillment
    pipeline (which can take up to 14 days to reach 'delivered') would lock
    out a buyer who already paid.

    A logged-in vendor always has full access to their own course's content
    — they don't need to "buy" what they're selling to preview or download
    it, whether they're on the public course page or their own dashboard.
    """
    vendor_id = request.session.get('vendor_id')
    if vendor_id and course.vendor_id == vendor_id:
        return True

    order_filter = {
        'item_type': 'course',
        'item_id': course.pk,
        'order__payment_status': 'completed',
    }
    site_user_id = request.session.get('site_user_id')
    if site_user_id and MarketplaceOrderItem.objects.filter(
        order__user_id=site_user_id, **order_filter
    ).exists():
        return True

    accessible = request.session.get('accessible_orders') or []
    if accessible and MarketplaceOrderItem.objects.filter(
        order__order_number__in=accessible, **order_filter
    ).exists():
        return True

    return False


def user_can_access_lesson(request, lesson):
    """True if the current visitor may view/download this lesson's content."""
    if lesson.is_free:
        return True
    return user_can_access_course(request, lesson.section.course)


def course_detail(request, slug):
    """Single course detail page with video playlist and progress tracking."""
    course = get_object_or_404(Course, slug=slug, is_active=True)
    sections = course.sections.prefetch_related('lessons').all()
    related = Course.objects.filter(
        is_active=True, category=course.category
    ).exclude(pk=course.pk)[:4] if course.category else Course.objects.none()

    # Get session key for progress tracking
    if not request.session.session_key:
        request.session.create()
    session_key = request.session.session_key

    # Get completed lesson IDs
    completed_ids = set(
        CourseProgress.objects.filter(
            session_key=session_key, course=course, completed=True
        ).values_list('lesson_id', flat=True)
    )

    # Count total and completed
    total_lessons = CourseLesson.objects.filter(section__course=course).count()
    completed_count = len(completed_ids)
    progress_percent = int((completed_count / total_lessons) * 100) if total_lessons > 0 else 0

    # Get current lesson (from query param or first incomplete)
    current_lesson_id = request.GET.get('lesson')
    current_lesson = None
    if current_lesson_id:
        current_lesson = CourseLesson.objects.filter(pk=current_lesson_id, section__course=course).first()
    if not current_lesson and sections.exists():
        # Find first incomplete lesson
        for section in sections:
            for lesson in section.lessons.all():
                if lesson.id not in completed_ids:
                    current_lesson = lesson
                    break
            if current_lesson:
                break
        # All done? Show first lesson
        if not current_lesson:
            first_section = sections.first()
            if first_section and first_section.lessons.exists():
                current_lesson = first_section.lessons.first()

    # Access control: ownership unlocks every non-free lesson at once, so
    # this is a single check regardless of how many lessons are rendered.
    can_access_course = user_can_access_course(request, course)
    locked_lesson_ids = set()
    remaining_minutes = 0
    for section in sections:
        for lesson in section.lessons.all():
            if lesson.is_free or can_access_course:
                if lesson.id not in completed_ids:
                    remaining_minutes += lesson.duration_minutes
            else:
                locked_lesson_ids.add(lesson.id)

    current_lesson_locked = bool(current_lesson and current_lesson.id in locked_lesson_ids)
    current_lesson_source = None
    if current_lesson and not current_lesson_locked:
        current_lesson_source = current_lesson.get_video_source()

    seller_vendor = resolve_listing_vendor(course.vendor)
    context = {
        'course': course,
        'seller_vendor': seller_vendor,
        'sections': sections,
        'related_courses': related,
        'completed_ids': completed_ids,
        'total_lessons': total_lessons,
        'completed_count': completed_count,
        'progress_percent': progress_percent,
        'current_lesson': current_lesson,
        'current_lesson_locked': current_lesson_locked,
        'current_lesson_source': current_lesson_source,
        'can_access_course': can_access_course,
        'locked_lesson_ids': locked_lesson_ids,
        'remaining_minutes': remaining_minutes,
        'sold_delivered': course.get_units_sold_delivered(),
        'listing_reviews_preview': list(reviews_for_listing('course', course.pk)[:3]),
        'listing_review_summary': review_summary('course', course.pk),
        'listing_kind': 'course',
        'listing_id': course.pk,
        **_seller_follow_context(request, seller_vendor),
    }
    return render(request, 'marketplace/course_detail.html', context)


def supermarket_list(request):
    """Browse supermarket items with search and filter."""
    items = _annotate_supermarket_delivered(
        SupermarketItem.objects.filter(is_active=True).select_related('category')
    )
    categories = _cached_categories('supermarket')

    q = request.GET.get('q', '').strip()
    cat = request.GET.get('category', '')
    sort = request.GET.get('sort', '-created_at')

    if q:
        items = items.filter(Q(name__icontains=q) | Q(description__icontains=q) | Q(brand__icontains=q))
    if cat:
        items = items.filter(category__slug=cat)
    if sort == '-sales_count':
        items = items.order_by('-sold_delivered', '-sales_count')
    elif sort in ['price', '-price', '-created_at', 'name']:
        items = items.order_by(sort)

    paginator = Paginator(items, 16)
    page = paginator.get_page(request.GET.get('page', 1))

    if request.GET.get('format') == 'json':
        if request.GET.get('recommend') == '1':
            rec_items = recommended_items(request, limit=20, include=('supermarket',), category_slug=cat, query=q)
            return JsonResponse({'items': rec_items, 'page': int(request.GET.get('page', 1) or 1), 'has_more': True})
        data_items = []
        for item in page:
            data_items.append({
                'id': item.id,
                'name': item.name,
                'price': str(item.price),
                'image': item.get_image_url(),
                'url': reverse('marketplace:supermarket_detail', args=[item.slug]),
                'badge': _('超市'),
                'unit': item.get_unit_display(),
                'stock_text': _('有货') if item.in_stock else _('缺货'),
            })
        return JsonResponse({
            'items': data_items,
            'page': page.number,
            'has_more': page.has_next(),
        })

    context = {
        'items': page,
        'categories': categories,
        'query': q,
        'current_category': cat,
        'current_sort': sort,
    }
    return render(request, 'marketplace/supermarket.html', context)


def supermarket_detail(request, slug):
    """Single supermarket item detail page."""
    item = get_object_or_404(SupermarketItem, slug=slug, is_active=True)
    related = SupermarketItem.objects.filter(
        is_active=True, category=item.category
    ).exclude(pk=item.pk)[:4] if item.category else SupermarketItem.objects.none()
    attribute_context = build_attribute_groups(item.attributes.all())

    seller_vendor = resolve_listing_vendor(item.vendor)

    from manager.fulfillment_service import get_delivery_estimate
    context = {
        'item': item,
        'seller_vendor': seller_vendor,
        'related_items': related,
        'attribute_groups': attribute_context['groups'],
        'selectable_attributes': attribute_context['selectable_groups'],
        'specification_attributes': attribute_context['specification_groups'],
        'sold_delivered': item.get_units_sold_delivered(),
        'listing_reviews_preview': list(reviews_for_listing('supermarket', item.pk)[:3]),
        'listing_review_summary': review_summary('supermarket', item.pk),
        'listing_kind': 'supermarket',
        'listing_id': item.pk,
        'max_purchase_quantity': _max_purchase_quantity(item),
        'pricing_display': pricing_display_context(item),
        'delivery_estimate': get_delivery_estimate('supermarket', item.pk),
        **_seller_follow_context(request, seller_vendor),
    }
    return render(request, 'marketplace/supermarket_detail.html', context)


# ═══════════════════════════════════════════════════════════════════════════════
#  CART & CHECKOUT
# ═══════════════════════════════════════════════════════════════════════════════

def _get_session_key(request):
    if not request.session.session_key:
        request.session.create()
    return request.session.session_key


@require_POST
def add_to_cart(request):
    """Add any marketplace item to cart via AJAX."""
    try:
        item_type = request.POST.get('item_type')
        item_id = int(request.POST.get('item_id'))
        quantity = int(request.POST.get('quantity', 1))
        session_key = _get_session_key(request)

        # Validate item exists and has stock
        if item_type == 'product':
            item = get_object_or_404(Product, pk=item_id, is_active=True)
            qty_check = validate_quantity(item, quantity)
            if not qty_check.is_valid:
                return JsonResponse({'success': False, 'message': qty_check.message, 'suggested_quantity': qty_check.suggested_quantity})
            if quantity > item.stock:
                return JsonResponse({'success': False, 'message': f'库存不足！当前库存：{item.stock}'})
            item_name = item.name
        elif item_type == 'course':
            item = get_object_or_404(Course, pk=item_id, is_active=True)
            quantity = 1  # Courses always qty 1
            item_name = item.title
        elif item_type == 'supermarket':
            item = get_object_or_404(SupermarketItem, pk=item_id, is_active=True)
            qty_check = validate_quantity(item, quantity)
            if not qty_check.is_valid:
                return JsonResponse({'success': False, 'message': qty_check.message, 'suggested_quantity': qty_check.suggested_quantity})
            if quantity > item.stock:
                return JsonResponse({'success': False, 'message': f'库存不足！当前库存：{item.stock}'})
            item_name = item.name
        else:
            return JsonResponse({'success': False, 'message': '无效的商品类型'})

        cart_item, created = MarketplaceCartItem.objects.get_or_create(
            session_key=session_key,
            item_type=item_type,
            item_id=item_id,
            defaults={'quantity': quantity}
        )

        if not created:
            if item_type == 'course':
                return JsonResponse({'success': False, 'message': '该课程已在购物车中'})
            new_qty = cart_item.quantity + quantity
            if item_type in ('product', 'supermarket'):
                qty_check = validate_quantity(item, new_qty)
                if not qty_check.is_valid:
                    return JsonResponse({'success': False, 'message': qty_check.message, 'suggested_quantity': qty_check.suggested_quantity})
                if new_qty > item.stock:
                    return JsonResponse({'success': False, 'message': f'库存不足！购物车已有{cart_item.quantity}件'})
            cart_item.quantity = new_qty
            cart_item.save()

        cart_count = MarketplaceCartItem.objects.filter(session_key=session_key).count()
        return JsonResponse({
            'success': True,
            'message': f'已将「{item_name}」添加到购物车',
            'cart_count': cart_count,
        })
    except Exception as e:
        return JsonResponse({'success': False, 'message': '添加失败，请重试'})


def view_cart(request):
    """Display marketplace shopping cart."""
    session_key = _get_session_key(request)
    cart_items = MarketplaceCartItem.objects.filter(session_key=session_key).order_by('-created_at')

    items_with_details = []
    total_amount = Decimal('0')
    total_qty = 0
    for ci in cart_items:
        item = ci.get_item()
        if item:
            subtotal = ci.get_total_price()
            total_amount += subtotal
            total_qty += ci.quantity
            items_with_details.append({
                'cart_item': ci,
                'cart_item_id': ci.id,
                'item': item,
                'item_type': ci.item_type,
                'name': ci.get_item_name(),
                'price': ci.get_item_price(),
                'quantity': ci.quantity,
                'image_url': ci.get_item_image_url(),
                'total_price': subtotal,
                'pricing_rule_log': ci.pricing_rule_log or {},
            })

    context = {
        'cart_items': items_with_details,
        'total_amount': total_amount,
        'total_price': total_amount,
        'total_quantity': total_qty,
        'total_count': len(items_with_details),
    }
    return render(request, 'marketplace/cart.html', context)


@require_POST
def update_cart(request):
    """Update cart item quantity via AJAX."""
    try:
        data = json.loads(request.body)
        cart_item_id = data.get('cart_item_id') or data.get('item_id')
        quantity = int(data.get('quantity', 1))
        session_key = _get_session_key(request)

        ci = get_object_or_404(MarketplaceCartItem, pk=cart_item_id, session_key=session_key)

        if quantity <= 0:
            ci.delete()
        else:
            # Validate stock
            item = ci.get_item()
            if ci.item_type in ('product', 'supermarket') and item:
                qty_check = validate_quantity(item, quantity)
                if not qty_check.is_valid:
                    return JsonResponse({'success': False, 'message': qty_check.message, 'suggested_quantity': qty_check.suggested_quantity})
                if quantity > item.stock:
                    return JsonResponse({'success': False, 'message': f'库存不足！最大可购买：{item.stock}'})
            ci.quantity = quantity
            ci.save()

        # Recalculate
        all_items = MarketplaceCartItem.objects.filter(session_key=session_key)
        total = sum(i.get_total_price() for i in all_items)

        return JsonResponse({
            'success': True,
            'cart_total': float(total),
            'cart_count': all_items.count(),
            'item_total': float(ci.get_total_price()) if quantity > 0 else 0,
        })
    except Exception:
        return JsonResponse({'success': False, 'message': '更新失败'})


@require_POST
def remove_from_cart(request, item_id):
    """Remove item from cart."""
    session_key = _get_session_key(request)
    ci = get_object_or_404(MarketplaceCartItem, pk=item_id, session_key=session_key)
    ci.delete()

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        all_items = MarketplaceCartItem.objects.filter(session_key=session_key)
        total = sum(i.get_total_price() for i in all_items)
        return JsonResponse({
            'success': True,
            'cart_total': float(total),
            'cart_count': all_items.count(),
        })

    messages.success(request, '已移除商品')
    return redirect('marketplace:view_cart')


def get_cart_count(request):
    """Return cart count for header badge."""
    session_key = _get_session_key(request)
    count = MarketplaceCartItem.objects.filter(session_key=session_key).count()
    return JsonResponse({'cart_count': count})


@require_POST
def buy_now(request):
    """Direct purchase - add to cart and go to unified checkout."""
    item_type = request.POST.get('item_type')
    item_id = int(request.POST.get('item_id'))
    quantity = int(request.POST.get('quantity', 1))
    session_key = _get_session_key(request)

    # Clear both carts for buy-now
    MarketplaceCartItem.objects.filter(session_key=session_key).delete()
    from manager.models import CartItem
    CartItem.objects.filter(session_key=session_key).delete()

    selected_attributes = normalize_selected_attributes(request.POST.get('selected_attributes', '{}'))
    item = None
    if item_type == 'product':
        item = get_object_or_404(Product, pk=item_id, is_active=True)
    elif item_type == 'supermarket':
        item = get_object_or_404(SupermarketItem, pk=item_id, is_active=True)

    if item:
        qty_check = validate_quantity(item, quantity)
        if not qty_check.is_valid:
            messages.error(request, qty_check.message)
            return redirect(request.META.get('HTTP_REFERER', 'marketplace:home'))
        if quantity > item.stock:
            messages.error(request, f'库存不足！当前库存：{item.stock}')
            return redirect(request.META.get('HTTP_REFERER', 'marketplace:home'))
        validation = validate_selected_attributes(
            build_attribute_groups(item.attributes.all()),
            selected_attributes,
        )
        if not validation['is_valid']:
            messages.error(request, validation['errors'][0])
            return redirect(request.META.get('HTTP_REFERER', 'marketplace:home'))
        selected_attributes = validation['cleaned']

    MarketplaceCartItem.objects.create(
        session_key=session_key,
        item_type=item_type,
        item_id=item_id,
        quantity=quantity,
        selected_attributes=selected_attributes,
    )
    return redirect('manager:checkout')


# Optional checkout donation supporting children in need — flat amount,
# not user-adjustable, shown as a clearly optional toggle at checkout.
DONATION_AMOUNT = Decimal('500.00')


def _donation_admin_note(amount):
    """Bilingual note auto-attached to admin_notes whenever a checkout
    included a donation, so whoever ends up looking at the order/payment
    (admin, finance, vendor) immediately sees that part of what was
    collected is a solidarity donation, not revenue for an item. Mirrors
    manager.views.donation_admin_note (kept local to avoid a manager.views
    <-> marketplace.views circular import for a 10-line helper)."""
    from manager.templatetags.currency_filters import to_fcfa
    amt = to_fcfa(amount)
    return (
        f"\U0001F49B Ce paiement inclut un don solidaire de {amt} "
        f"(soutien aux enfants dans le besoin) — à ne pas compter comme "
        f"chiffre d'affaires produit.\n"
        f"This payment includes a {amt} solidarity donation "
        f"(supporting children in need) — do not count as product revenue."
    )


def checkout(request):
    """Checkout page with payment methods."""
    session_key = _get_session_key(request)
    cart_items = MarketplaceCartItem.objects.filter(session_key=session_key)

    if not cart_items.exists():
        messages.warning(request, '购物车为空')
        return redirect('marketplace:home')

    from manager.fulfillment_service import get_delivery_estimate

    items_with_details = []
    total_amount = Decimal('0')
    total_qty = 0
    overall_delivery_estimate = None
    for ci in cart_items:
        item = ci.get_item()
        if item:
            subtotal = ci.get_total_price()
            total_amount += subtotal
            total_qty += ci.quantity
            # Courses are digital — no shipping estimate applies.
            item_delivery = get_delivery_estimate(ci.item_type, item.pk) if ci.item_type != 'course' else None
            if item_delivery and (overall_delivery_estimate is None or item_delivery['days_max'] > overall_delivery_estimate['days_max']):
                overall_delivery_estimate = item_delivery
            items_with_details.append({
                'cart_item': ci,
                'cart_item_id': ci.id,
                'item': item,
                'item_type': ci.item_type,
                'name': ci.get_item_name(),
                'price': ci.get_item_price(),
                'quantity': ci.quantity,
                'image_url': ci.get_item_image_url(),
                'total_price': subtotal,
                'selected_attributes': ci.selected_attributes or {},
                'pricing_rule_log': ci.pricing_rule_log or {},
                'delivery_estimate': item_delivery,
            })

    if request.method == 'POST':
        from manager.views import _get_client_ip, _is_rate_limited_key, _record_attempt_key
        ip = _get_client_ip(request)
        rl_key = f'checkout_fail:{ip}'
        if _is_rate_limited_key(rl_key, 20):
            messages.error(request, '请求过于频繁，请稍后再试。')
            return redirect('marketplace:checkout')
        _record_attempt_key(rl_key, 300)
        try:
            for detail in items_with_details:
                item = detail['item']
                ci = detail['cart_item']
                if ci.item_type in ('product', 'supermarket'):
                    qty_check = validate_quantity(item, ci.quantity)
                    if not qty_check.is_valid:
                        messages.error(request, qty_check.message)
                        return redirect('marketplace:view_cart')
                    if ci.quantity > item.stock:
                        messages.error(request, f'库存不足！当前库存：{item.stock}')
                        return redirect('marketplace:view_cart')
            country = request.POST.get('country', 'China')
            city = request.POST.get('city', '').strip()
            shipping_address = request.POST.get('shipping_address', '').strip()
            payment_method = request.POST.get('payment_method', 'wechat_pay')

            from book_Project.checkout_cities import is_valid_checkout_city
            if not is_valid_checkout_city(country, city):
                messages.error(request, '请选择有效的城市。')
                return redirect('marketplace:checkout')

            available_methods = {
                option['method']
                for region_options in build_payment_options(country).values()
                for option in region_options
            }
            # Wallet balance isn't a region-gated gateway like the others —
            # it's available to any logged-in user regardless of country —
            # so it's never listed in build_payment_options() and must be
            # exempted here rather than added to a region.
            if payment_method != 'wallet' and payment_method not in available_methods:
                messages.error(request, _('当前国家暂不支持该支付方式，请重新选择。'))
                return redirect('marketplace:checkout')

            # Optional 500 FCFA donation supporting children in need — added
            # to the charged total before the wallet-balance check below, so
            # a wallet payment can't succeed while under-covering it.
            donation = DONATION_AMOUNT if request.POST.get('donate') == 'yes' else Decimal('0.00')
            total_amount = total_amount + donation

            # Handle wallet payment
            user_id = request.session.get('site_user_id')
            if payment_method == 'wallet':
                from manager import models as mgr_models
                if not user_id:
                    messages.error(request, 'Please log in to use wallet payment.')
                    return redirect('manager:user_login')
                site_user = get_object_or_404(mgr_models.SiteUser, pk=user_id)
                # Named (not "_") — Django's gettext "_" is imported at module
                # level; shadowing it with a local throwaway variable made
                # every _('...') call later in this function raise
                # UnboundLocalError instead of translating, crashing checkout
                # whenever an earlier validation error needed to render.
                wallet, _wallet_created = mgr_models.UserWallet.objects.get_or_create(user=site_user, defaults={
                    'balance': Decimal('0.00'),
                    'total_deposited': Decimal('0.00'),
                    'total_spent': Decimal('0.00'),
                })
                if wallet.balance < total_amount:
                    messages.error(request, 'Insufficient wallet balance.')
                    return redirect('marketplace:checkout')

            order = MarketplaceOrder(
                user_id=user_id,
                user_name=request.POST.get('customer_name', ''),
                user_email=request.POST.get('customer_email', ''),
                customer_phone=request.POST.get('customer_phone', ''),
                country=country,
                city=city,
                payment_method=payment_method,
                total_amount=total_amount,
                donation_amount=donation,
                shipping_address=shipping_address,
                notes=request.POST.get('notes', ''),
                admin_notes=_donation_admin_note(donation) if donation else '',
            )
            order.save()

            # Debit wallet after order is created. Payment confirmation
            # (status flip, shipment creation, email, inventory deduction)
            # happens once below via _update_order_status — not here — so a
            # wallet payment goes through the exact same pipeline every
            # other payment method uses.
            if payment_method == 'wallet' and user_id:
                from django.db import transaction
                with transaction.atomic():
                    wallet = mgr_models.UserWallet.objects.select_for_update().get(user_id=user_id)
                    if wallet.balance < total_amount:
                        messages.error(request, 'Insufficient wallet balance.')
                        order.delete()
                        return redirect('marketplace:checkout')
                    wallet.debit(
                        total_amount,
                        source='order_payment',
                        description=f'Payment for {order.order_number}',
                        source_id=str(order.id),
                    )

            for detail in items_with_details:
                ci = detail['cart_item']
                MarketplaceOrderItem.objects.create(
                    order=order,
                    item_type=ci.item_type,
                    item_id=ci.item_id,
                    item_name=detail['name'],
                    item_image=detail['image_url'],
                    quantity=ci.quantity,
                    unit_price=detail['price'],
                    selected_attributes=detail.get('selected_attributes', {}),
                    pricing_rule_log=detail.get('pricing_rule_log', {}),
                )
                # Stock/sales/enrollment are deducted only once payment is
                # actually confirmed (see below), never here at order
                # creation — an abandoned/failed payment must never
                # permanently reduce stock.

            if payment_method == 'wallet':
                from manager.payments.views import _update_order_status
                _update_order_status(order, 'SUCCESSFUL', transaction_id='wallet')

            cart_items.delete()
            _accessible = request.session.get('accessible_orders', [])
            if str(order.order_number) not in _accessible:
                _accessible.append(str(order.order_number))
            request.session['accessible_orders'] = _accessible
            if payment_method == 'kkiapay':
                return redirect('manager:kkiapay_pay', order_number=order.order_number)
            if payment_method == 'pawapay':
                return redirect('manager:pawapay_pay', order_number=order.order_number)
            return redirect('marketplace:order_confirmation', order_number=order.order_number)

        except Exception as e:
            messages.error(request, '订单创建失败，请重试')

    payment_methods = build_payment_options()

    # Load wallet balance for logged-in user
    wallet_balance = None
    user_id = request.session.get('site_user_id')
    if user_id:
        try:
            from manager import models as mgr_models
            wallet = mgr_models.UserWallet.objects.filter(user_id=user_id).first()
            if wallet:
                wallet_balance = wallet.balance
        except Exception:
            pass

    from book_Project.checkout_cities import get_checkout_cities_by_country

    context = {
        'cart_items': items_with_details,
        'total_amount': total_amount,
        'total_price': total_amount,
        'total_quantity': total_qty,
        'total_count': len(items_with_details),
        'payment_methods': payment_methods,
        'wallet_balance': wallet_balance,
        'checkout_cities_by_country': get_checkout_cities_by_country(),
        'donation_amount': DONATION_AMOUNT,
        'delivery_estimate': overall_delivery_estimate,
    }
    return render(request, 'marketplace/checkout.html', context)


def order_confirmation(request, order_number):
    """Order confirmation page."""
    order = get_object_or_404(MarketplaceOrder, order_number=order_number)
    context = {'order': order, 'items': order.items.all()}
    return render(request, 'marketplace/order_confirmation.html', context)


# ═══════════════════════════════════════════════════════════════════════════════
#  COURSE PROGRESS
# ═══════════════════════════════════════════════════════════════════════════════

@require_POST
def toggle_lesson_complete(request, lesson_id):
    """Toggle lesson completion status."""
    if not request.session.session_key:
        request.session.create()
    session_key = request.session.session_key

    lesson = get_object_or_404(CourseLesson, pk=lesson_id)
    course = lesson.section.course

    if not user_can_access_lesson(request, lesson):
        return JsonResponse({'success': False, 'message': _('请先购买本课程')}, status=403)

    progress, created = CourseProgress.objects.get_or_create(
        session_key=session_key,
        course=course,
        lesson=lesson,
    )

    if not created and progress.completed:
        progress.completed = False
        progress.completed_at = None
        progress.save()
        completed = False
    else:
        progress.completed = True
        progress.completed_at = timezone.now()
        progress.save()
        completed = True

    # Recalculate progress
    total = CourseLesson.objects.filter(section__course=course).count()
    done = CourseProgress.objects.filter(
        session_key=session_key, course=course, completed=True
    ).count()
    percent = int((done / total) * 100) if total > 0 else 0

    return JsonResponse({
        'success': True,
        'completed': completed,
        'completed_count': done,
        'total_lessons': total,
        'progress_percent': percent,
    })


@xframe_options_sameorigin
def serve_lesson_pdf(request, lesson_id):
    """Serve PDF file for a lesson."""
    lesson = get_object_or_404(CourseLesson, pk=lesson_id)
    if not lesson.pdf_file:
        return JsonResponse({'error': 'No PDF available'}, status=404)
    if not user_can_access_lesson(request, lesson):
        return HttpResponseForbidden(_('请先购买本课程后再查看该文件'))
    response = FileResponse(lesson.pdf_file.open('rb'), content_type='application/pdf')
    response['Content-Disposition'] = 'inline'
    return response


def download_lesson(request, lesson_id):
    """Download a single lesson's video file for offline viewing."""
    lesson = get_object_or_404(CourseLesson, pk=lesson_id)
    if not user_can_access_lesson(request, lesson):
        return HttpResponseForbidden(_('请先购买本课程后再下载该文件'))
    if not lesson.video_file:
        raise Http404('No downloadable video for this lesson')
    filename = f'{lesson.order:02d}_{slugify(lesson.title) or "lesson"}.mp4'
    response = FileResponse(lesson.video_file.open('rb'), content_type='video/mp4', as_attachment=True, filename=filename)
    return response


def download_lesson_resource(request, lesson_id):
    """Download a lesson's attached resource file (any file type, uploaded
    by the vendor/admin as supplementary material — slides, source code,
    datasets, etc.), distinct from the lesson's own video/PDF."""
    lesson = get_object_or_404(CourseLesson, pk=lesson_id)
    if not user_can_access_lesson(request, lesson):
        return HttpResponseForbidden(_('请先购买本课程后再下载该文件'))
    if not lesson.resource_file:
        raise Http404('No resource file for this lesson')
    filename = lesson.resource_file.name.split('/')[-1]
    response = FileResponse(lesson.resource_file.open('rb'), as_attachment=True, filename=filename)
    return response


def _write_lesson_to_zip(zf, lesson):
    """Add one lesson's downloadable content to an open ZipFile."""
    base = f'{lesson.order:02d}_{slugify(lesson.title) or "lesson"}'
    if lesson.video_file:
        with lesson.video_file.open('rb') as f:
            zf.writestr(f'{base}.mp4', f.read())
    elif lesson.video_url:
        note = _('本课时为外部视频链接，无法打包下载，请在线观看：') + lesson.video_url
        zf.writestr(f'{base}_external_link.txt', note)
    if lesson.pdf_file:
        with lesson.pdf_file.open('rb') as f:
            zf.writestr(f'{base}.pdf', f.read())
    if lesson.resource_file:
        resource_name = lesson.resource_file.name.split('/')[-1]
        with lesson.resource_file.open('rb') as f:
            zf.writestr(f'{base}_{resource_name}', f.read())


def download_course_bundle(request, slug):
    """Download all accessible lessons of a course (or one section) as a zip."""
    course = get_object_or_404(Course, slug=slug, is_active=True)
    if not user_can_access_course(request, course):
        return HttpResponseForbidden(_('请先购买本课程后再下载课程内容'))

    section_id = request.GET.get('section')
    sections = course.sections.prefetch_related('lessons').all()
    if section_id:
        sections = sections.filter(pk=section_id)
        if not sections.exists():
            raise Http404('Section not found')

    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, 'w', zipfile.ZIP_STORED) as zf:
        for section in sections:
            for lesson in section.lessons.all():
                _write_lesson_to_zip(zf, lesson)
    buffer.seek(0)

    filename = f'{course.slug}-lessons.zip'
    response = FileResponse(buffer, as_attachment=True, filename=filename)
    return response


# ═══════════════════════════════════════════════════════════════════════════════
#  ADMIN VIEWS
# ═══════════════════════════════════════════════════════════════════════════════

def _marketplace_admin_chart_payload(product_count, course_count, supermarket_count):
    """Build JSON-serializable chart data (same pattern as books admin dashboard)."""
    local_today = timezone.localdate()
    start_day = local_today - timedelta(days=6)
    daily_sales = []
    for i in range(7):
        d = start_day + timedelta(days=i)
        agg = MarketplaceOrder.objects.filter(created_at__date=d).aggregate(
            revenue=Sum('total_amount'),
            orders=Count('id'),
        )
        daily_sales.append({
            'date': d.strftime('%m-%d'),
            'revenue': float(agg['revenue'] or 0),
            'orders': int(agg['orders'] or 0),
        })

    status_rows = list(
        MarketplaceOrder.objects.values('status').annotate(c=Count('id')).order_by('-c')
    )
    status_display = dict(MarketplaceOrder.STATUS_CHOICES)
    order_status = {
        'labels': [str(_(status_display.get(r['status'], r['status']))) for r in status_rows],
        'data': [int(r['c']) for r in status_rows],
    }
    if not order_status['labels']:
        order_status = {'labels': [str(_('暂无数据'))], 'data': [1]}

    pay_rows = list(
        MarketplaceOrder.objects.values('payment_status').annotate(c=Count('id')).order_by('-c')
    )
    pay_display = dict(MarketplaceOrder.PAYMENT_STATUS_CHOICES)
    payment_status = {
        'labels': [str(_(pay_display.get(r['payment_status'], r['payment_status']))) for r in pay_rows],
        'data': [int(r['c']) for r in pay_rows],
    }
    if not payment_status['labels']:
        payment_status = {'labels': [str(_('暂无数据'))], 'data': [1]}

    item_display = dict(MarketplaceOrderItem.ITEM_TYPE_CHOICES)
    item_rows = list(
        MarketplaceOrderItem.objects.values('item_type').annotate(
            lines=Count('id'), qty=Sum('quantity')
        ).order_by('-qty')
    )
    item_type_breakdown = {
        'labels': [str(_(item_display.get(r['item_type'], r['item_type']))) for r in item_rows],
        'data': [int(r['qty'] or 0) for r in item_rows],
    }
    if not item_type_breakdown['labels']:
        item_type_breakdown = {'labels': [str(_('暂无数据'))], 'data': [0]}

    now = timezone.now()
    monthly_rows = list(
        MarketplaceOrder.objects.filter(
            payment_status='completed',
            created_at__gte=now - timedelta(days=400),
        )
        .annotate(m=TruncMonth('created_at'))
        .values('m')
        .annotate(revenue=Sum('total_amount'), orders=Count('id'))
        .order_by('-m')[:6]
    )
    monthly_rows.reverse()
    monthly = []
    for r in monthly_rows:
        m = r.get('m')
        label = m.strftime('%Y-%m') if m else ''
        monthly.append({
            'month': label,
            'revenue': float(r['revenue'] or 0),
            'orders': int(r['orders'] or 0),
        })
    if not monthly:
        monthly = [{'month': str(_('暂无数据')), 'revenue': 0.0, 'orders': 0}]

    catalog = {
        'labels': [str(_('商品')), str(_('课程')), str(_('超市商品'))],
        'data': [int(product_count), int(course_count), int(supermarket_count)],
    }

    top_lines = list(
        MarketplaceOrderItem.objects.values('item_name')
        .annotate(qty=Sum('quantity'))
        .order_by('-qty')[:6]
    )
    top_items = [
        {'name': (row['item_name'] or '')[:16], 'qty': int(row['qty'] or 0)}
        for row in top_lines
    ]
    if not top_items:
        top_items = [{'name': str(_('暂无数据')), 'qty': 0}]

    return {
        'mkt_daily_sales_json': json.dumps(daily_sales),
        'mkt_order_status_json': json.dumps(order_status),
        'mkt_payment_status_json': json.dumps(payment_status),
        'mkt_item_type_json': json.dumps(item_type_breakdown),
        'mkt_monthly_json': json.dumps(monthly),
        'mkt_catalog_json': json.dumps(catalog),
        'mkt_top_items_json': json.dumps(top_items),
    }


def admin_dashboard(request):
    """Marketplace admin dashboard with stats."""
    auth = _admin_required(request)
    if auth:
        return auth

    product_count = Product.objects.count()
    course_count = Course.objects.count()
    supermarket_count = SupermarketItem.objects.count()

    context = {
        'product_count': product_count,
        'course_count': course_count,
        'supermarket_count': supermarket_count,
        'order_count': MarketplaceOrder.objects.count(),
        'category_count': Category.objects.count(),
        'recent_orders': MarketplaceOrder.objects.order_by('-created_at')[:10],
        'featured_products': Product.objects.filter(is_featured=True).count(),
        'featured_courses': Course.objects.filter(is_featured=True).count(),
        'total_revenue': MarketplaceOrder.objects.filter(
            status__in=['paid', 'processing', 'shipped', 'delivered']
        ).aggregate(total=Sum('total_amount'))['total'] or 0,
        'name': request.session.get("name", "Admin"),
    }
    context.update(_marketplace_admin_chart_payload(product_count, course_count, supermarket_count))
    return render(request, 'marketplace/admin/dashboard.html', context)


# ─── Product CRUD ─────────────────────────────────────────────────────────────

def admin_products(request):
    auth = _admin_required(request)
    if auth:
        return auth

    products = Product.objects.select_related('category').all()
    q = request.GET.get('q', '').strip()
    if q:
        products = products.filter(Q(name__icontains=q) | Q(sku__icontains=q) | Q(brand__icontains=q))

    paginator = Paginator(products, 15)
    page = paginator.get_page(request.GET.get('page', 1))
    context = {'products': page, 'query': q, 'name': request.session.get("name", "Admin")}
    return render(request, 'marketplace/admin/products.html', context)


def admin_product_add(request):
    auth = _admin_required(request)
    if auth:
        return auth

    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        if not name:
            messages.error(request, '商品名称不能为空')
            return redirect('marketplace:admin_product_add')

        from manager.views import _parse_delivery_days_override
        delivery_days_min, delivery_days_max = _parse_delivery_days_override(request.POST)

        product = Product(
            name_en=request.POST.get('name_en', '').strip(),
            slug=slugify(name) or f'product-{uuid.uuid4().hex[:8]}',
            price=request.POST.get('price', 0),
            original_price=request.POST.get('original_price') or None,
            stock=request.POST.get('stock', 0),
            min_order_quantity=_positive_int(request.POST.get('min_order_quantity'), 1),
            max_order_quantity=_optional_positive_int(request.POST.get('max_order_quantity')),
            quantity_step=_positive_int(request.POST.get('quantity_step'), 1),
            pricing_rules=_pricing_rules_from_post(request),
            brand=request.POST.get('brand', '').strip(),
            condition=request.POST.get('condition', 'new'),
            weight=request.POST.get('weight') or None,
            is_featured=request.POST.get('is_featured') == 'on',
            is_active=request.POST.get('is_active', 'on') == 'on',
            delivery_days_min=delivery_days_min,
            delivery_days_max=delivery_days_max,
        )
        # name/description are django-modeltranslation fields — passing them
        # as constructor kwargs above silently drops them (the library skips
        # populating the per-language column while _mt_init is set during
        # __init__), so they must be assigned as plain attributes instead.
        product.name = name
        product.description = request.POST.get('description', '')
        cat_id = request.POST.get('category')
        if cat_id:
            product.category_id = int(cat_id)
        if 'image' in request.FILES:
            product.image = request.FILES['image']
        if 'image_2' in request.FILES:
            product.image_2 = request.FILES['image_2']
        if 'image_3' in request.FILES:
            product.image_3 = request.FILES['image_3']
        _apply_uploaded_media(product, request)

        # Ensure unique slug
        base_slug = product.slug
        counter = 1
        while Product.objects.filter(slug=product.slug).exists():
            product.slug = f'{base_slug}-{counter}'
            counter += 1

        assign_official_vendor(product)
        product.save()

        # Save dynamic attributes
        attr_names = request.POST.getlist('attr_name')
        attr_values = request.POST.getlist('attr_value')
        for a_name, a_val in zip(attr_names, attr_values):
            a_name = a_name.strip()
            a_val = a_val.strip()
            if a_name and a_val:
                ProductAttribute.objects.create(product=product, name=a_name, value=a_val)

        messages.success(request, f'商品 "{name}" 已添加')
        return redirect('marketplace:admin_products')

    categories = Category.objects.filter(section='products', is_active=True)
    context = _form_context_with_pricing({'categories': categories, 'name': request.session.get("name", "Admin")})
    return render(request, 'marketplace/admin/product_form.html', context)


def admin_product_edit(request, pk):
    auth = _admin_required(request)
    if auth:
        return auth

    product = get_object_or_404(Product, pk=pk)
    if request.method == 'POST':
        product_name = _required_text(request, 'name', '商品名称', min_length=3)
        product_description = _required_text(request, 'description', '商品描述', min_length=12)
        if not product_name or not product_description or not _validate_marketplace_business_rules(request, require_images=0, allow_existing_images=bool(product.image or product.image_2 or product.image_3)):
            categories = Category.objects.filter(section='products', is_active=True)
            context = _form_context_with_pricing({'product': product, 'categories': categories, 'form_state': _build_marketplace_form_state(request, product)}, product)
            return render(request, 'marketplace/admin/product_form.html', context)
        from manager.views import _parse_delivery_days_override
        product.delivery_days_min, product.delivery_days_max = _parse_delivery_days_override(request.POST)
        product.name = product_name
        product.name_en = request.POST.get('name_en', '').strip()
        product.description = product_description
        product.price = request.POST.get('price', product.price)
        product.original_price = request.POST.get('original_price') or None
        product.stock = request.POST.get('stock', product.stock)
        product.min_order_quantity = _positive_int(request.POST.get('min_order_quantity'), product.min_order_quantity)
        product.max_order_quantity = _optional_positive_int(request.POST.get('max_order_quantity'))
        product.quantity_step = _positive_int(request.POST.get('quantity_step'), product.quantity_step)
        product.pricing_rules = _pricing_rules_from_post(request)
        product.brand = request.POST.get('brand', '').strip()
        product.condition = request.POST.get('condition', 'new')
        product.weight = request.POST.get('weight') or None
        product.is_featured = request.POST.get('is_featured') == 'on'
        product.is_active = request.POST.get('is_active', 'on') == 'on'
        cat_id = request.POST.get('category')
        product.category_id = int(cat_id) if cat_id else None
        if 'image' in request.FILES:
            product.image = request.FILES['image']
        if 'image_2' in request.FILES:
            product.image_2 = request.FILES['image_2']
        if 'image_3' in request.FILES:
            product.image_3 = request.FILES['image_3']
        _apply_uploaded_media(product, request)
        assign_official_vendor(product)
        product.save()

        # Update dynamic attributes: clear old, save new
        product.attributes.all().delete()
        dynamic_fields = {
            'seller_name': 'Nom du vendeur',
            'seller_phone': 'Téléphone vendeur',
            'delivery_available': 'Livraison',
        }
        for field_name, label in dynamic_fields.items():
            raw_value = request.POST.get(field_name, '')
            value = raw_value.strip() if isinstance(raw_value, str) else str(raw_value).strip()
            if value:
                ProductAttribute.objects.create(product=product, name=label, value=value)

        attr_names = request.POST.getlist('attr_name')
        attr_values = request.POST.getlist('attr_value')
        for a_name, a_val in zip(attr_names, attr_values):
            a_name = a_name.strip()
            a_val = a_val.strip()
            if a_name and a_val:
                ProductAttribute.objects.create(product=product, name=a_name, value=a_val)

        messages.success(request, f'商品 "{product.name}" 已更新')
        return redirect('marketplace:admin_products')

    categories = Category.objects.filter(section='products', is_active=True)
    context = _form_context_with_pricing({'product': product, 'categories': categories, 'name': request.session.get("name", "Admin")}, product)
    return render(request, 'marketplace/admin/product_form.html', context)


def admin_product_delete(request, pk):
    auth = _admin_required(request)
    if auth:
        return auth

    if request.method == 'POST':
        product = get_object_or_404(Product, pk=pk)
        name = product.name
        product.delete()
        messages.success(request, f'商品 "{name}" 已删除')
    return redirect('marketplace:admin_products')


# ─── Course CRUD ──────────────────────────────────────────────────────────────

def admin_courses(request):
    auth = _admin_required(request)
    if auth:
        return auth

    courses = Course.objects.select_related('category').all()
    q = request.GET.get('q', '').strip()
    if q:
        courses = courses.filter(Q(title__icontains=q) | Q(instructor__icontains=q))

    paginator = Paginator(courses, 15)
    page = paginator.get_page(request.GET.get('page', 1))
    context = {'courses': page, 'query': q, 'name': request.session.get("name", "Admin")}
    return render(request, 'marketplace/admin/courses.html', context)


def admin_course_add(request):
    auth = _admin_required(request)
    if auth:
        return auth

    if request.method == 'POST':
        title = request.POST.get('title', '').strip()
        if not title:
            messages.error(request, '课程标题不能为空')
            return redirect('marketplace:admin_course_add')

        course = Course(
            title_en=request.POST.get('title_en', '').strip(),
            slug=slugify(title) or f'course-{uuid.uuid4().hex[:8]}',
            price=request.POST.get('price', 0),
            original_price=request.POST.get('original_price') or None,
            instructor=request.POST.get('instructor', '').strip(),
            duration_hours=request.POST.get('duration_hours', 0) or 0,
            lessons_count=request.POST.get('lessons_count', 0) or 0,
            level=request.POST.get('level', 'all'),
            language=request.POST.get('language', '中文'),
            preview_url=request.POST.get('preview_url', ''),
            is_featured=request.POST.get('is_featured') == 'on',
            is_active=request.POST.get('is_active', 'on') == 'on',
        )
        # title/description are django-modeltranslation fields — passing them
        # as constructor kwargs above silently drops them (the library skips
        # populating the per-language column while _mt_init is set during
        # __init__), so they must be assigned as plain attributes instead.
        course.title = title
        course.description = request.POST.get('description', '')
        cat_id = request.POST.get('category')
        if cat_id:
            course.category_id = int(cat_id)
        if 'image' in request.FILES:
            course.image = request.FILES['image']

        base_slug = course.slug
        counter = 1
        while Course.objects.filter(slug=course.slug).exists():
            course.slug = f'{base_slug}-{counter}'
            counter += 1

        assign_official_vendor(course)
        course.save()
        messages.success(request, f'课程 "{title}" 已添加')
        return redirect('marketplace:admin_courses')

    categories = Category.objects.filter(section='courses', is_active=True)
    context = {'categories': categories, 'name': request.session.get("name", "Admin")}
    return render(request, 'marketplace/admin/course_form.html', context)


def admin_course_edit(request, pk):
    auth = _admin_required(request)
    if auth:
        return auth

    course = get_object_or_404(Course, pk=pk)
    if request.method == 'POST':
        title = request.POST.get('title', '').strip()
        if not title:
            messages.error(request, '课程标题不能为空')
            return redirect('marketplace:admin_course_edit', pk=course.pk)
        course.title = title
        course.title_en = request.POST.get('title_en', '').strip()
        course.description = request.POST.get('description', '')
        course.price = request.POST.get('price', course.price)
        course.original_price = request.POST.get('original_price') or None
        course.instructor = request.POST.get('instructor', '').strip()
        course.duration_hours = request.POST.get('duration_hours', 0) or 0
        course.lessons_count = request.POST.get('lessons_count', 0) or 0
        course.level = request.POST.get('level', 'all')
        course.language = request.POST.get('language', '中文')
        course.preview_url = request.POST.get('preview_url', '')
        course.is_featured = request.POST.get('is_featured') == 'on'
        course.is_active = request.POST.get('is_active', 'on') == 'on'
        cat_id = request.POST.get('category')
        course.category_id = int(cat_id) if cat_id else None
        if 'image' in request.FILES:
            course.image = request.FILES['image']
        assign_official_vendor(course)
        course.save()
        messages.success(request, f'课程 "{course.title}" 已更新')
        return redirect('marketplace:admin_courses')

    categories = Category.objects.filter(section='courses', is_active=True)
    context = {'course': course, 'categories': categories, 'name': request.session.get("name", "Admin")}
    return render(request, 'marketplace/admin/course_form.html', context)


def admin_course_delete(request, pk):
    auth = _admin_required(request)
    if auth:
        return auth

    if request.method == 'POST':
        course = get_object_or_404(Course, pk=pk)
        name = course.title
        course.delete()
        messages.success(request, f'课程 "{name}" 已删除')
    return redirect('marketplace:admin_courses')


# ─── Course Content Management (Sections + Lessons) ──────────────────────────

def admin_course_content(request, pk):
    """Manage sections and lessons for a specific course."""
    auth = _admin_required(request)
    if auth:
        return auth

    course = get_object_or_404(Course, pk=pk)
    sections = course.sections.prefetch_related('lessons').all()

    context = {
        'course': course,
        'sections': sections,
        'name': request.session.get("name", "Admin"),
    }
    return render(request, 'marketplace/admin/course_content.html', context)


@require_POST
def admin_section_add(request, course_pk):
    """Add a new section to a course."""
    auth = _admin_required(request)
    if auth:
        return JsonResponse({'success': False, 'message': '未登录'}, status=403)

    course = get_object_or_404(Course, pk=course_pk)
    title = request.POST.get('title', '').strip()
    title_en = request.POST.get('title_en', '').strip()
    if not title:
        return JsonResponse({'success': False, 'message': '章节标题不能为空'})

    max_order = course.sections.count()
    section = CourseSection.objects.create(
        course=course,
        title=title,
        title_en=title_en,
        order=max_order,
    )
    return JsonResponse({
        'success': True,
        'message': f'章节 "{title}" 已添加',
        'section': {'id': section.id, 'title': section.title, 'title_en': section.title_en, 'order': section.order}
    })


@require_POST
def admin_section_edit(request, pk):
    """Edit a section."""
    auth = _admin_required(request)
    if auth:
        return JsonResponse({'success': False, 'message': '未登录'}, status=403)

    section = get_object_or_404(CourseSection, pk=pk)
    title = request.POST.get('title', '').strip()
    if not title:
        return JsonResponse({'success': False, 'message': '章节标题不能为空'})

    section.title = title
    section.title_en = request.POST.get('title_en', '').strip()
    order = request.POST.get('order')
    if order is not None:
        section.order = int(order)
    section.save()
    return JsonResponse({'success': True, 'message': f'章节 "{title}" 已更新'})


@require_POST
def admin_section_delete(request, pk):
    """Delete a section and its lessons."""
    auth = _admin_required(request)
    if auth:
        return JsonResponse({'success': False, 'message': '未登录'}, status=403)

    section = get_object_or_404(CourseSection, pk=pk)
    name = section.title
    section.delete()
    return JsonResponse({'success': True, 'message': f'章节 "{name}" 已删除'})


@require_POST
def admin_lesson_add(request, section_pk):
    """Add a new lesson to a section."""
    auth = _admin_required(request)
    if auth:
        return JsonResponse({'success': False, 'message': '未登录'}, status=403)

    section = get_object_or_404(CourseSection, pk=section_pk)
    title = request.POST.get('title', '').strip()
    if not title:
        return JsonResponse({'success': False, 'message': '课时标题不能为空'})

    max_order = section.lessons.count()
    lesson = CourseLesson(
        section=section,
        title=title,
        title_en=request.POST.get('title_en', '').strip(),
        description=request.POST.get('description', ''),
        video_url=request.POST.get('video_url', ''),
        duration_minutes=int(request.POST.get('duration_minutes', 0) or 0),
        order=max_order,
        is_free=request.POST.get('is_free') == 'on',
    )
    if 'video_file' in request.FILES:
        lesson.video_file = request.FILES['video_file']
    if 'pdf_file' in request.FILES:
        lesson.pdf_file = request.FILES['pdf_file']
    if 'resource_file' in request.FILES:
        lesson.resource_file = request.FILES['resource_file']
    lesson.save()

    return JsonResponse({
        'success': True,
        'message': f'课时 "{title}" 已添加',
        'lesson': {
            'id': lesson.id,
            'title': lesson.title,
            'duration_minutes': lesson.duration_minutes,
            'is_free': lesson.is_free,
            'has_video': bool(lesson.video_file or lesson.video_url),
            'has_pdf': bool(lesson.pdf_file),
            'has_resource': bool(lesson.resource_file),
        }
    })


@require_POST
def admin_lesson_edit(request, pk):
    """Edit a lesson."""
    auth = _admin_required(request)
    if auth:
        return JsonResponse({'success': False, 'message': '未登录'}, status=403)

    lesson = get_object_or_404(CourseLesson, pk=pk)
    title = request.POST.get('title', '').strip()
    if not title:
        return JsonResponse({'success': False, 'message': '课时标题不能为空'})

    lesson.title = title
    lesson.title_en = request.POST.get('title_en', '').strip()
    lesson.description = request.POST.get('description', '')
    lesson.video_url = request.POST.get('video_url', '')
    lesson.duration_minutes = int(request.POST.get('duration_minutes', 0) or 0)
    lesson.is_free = request.POST.get('is_free') == 'on'
    order = request.POST.get('order')
    if order is not None:
        lesson.order = int(order)

    # Move lesson to a different section if section_id is provided
    section_id = request.POST.get('section_id')
    if section_id:
        lesson.section_id = int(section_id)

    if 'video_file' in request.FILES:
        lesson.video_file = request.FILES['video_file']
    if request.POST.get('clear_video_file') == '1':
        lesson.video_file = None
    if 'pdf_file' in request.FILES:
        lesson.pdf_file = request.FILES['pdf_file']
    if request.POST.get('clear_pdf_file') == '1':
        lesson.pdf_file = None
    if 'resource_file' in request.FILES:
        lesson.resource_file = request.FILES['resource_file']
    if request.POST.get('clear_resource_file') == '1':
        lesson.resource_file = None
    lesson.save()

    return JsonResponse({'success': True, 'message': f'课时 "{title}" 已更新'})


@require_POST
def admin_lesson_delete(request, pk):
    """Delete a lesson."""
    auth = _admin_required(request)
    if auth:
        return JsonResponse({'success': False, 'message': '未登录'}, status=403)

    lesson = get_object_or_404(CourseLesson, pk=pk)
    name = lesson.title
    lesson.delete()
    return JsonResponse({'success': True, 'message': f'课时 "{name}" 已删除'})


# ─── SupermarketItem CRUD ─────────────────────────────────────────────────────

def admin_supermarket(request):
    auth = _admin_required(request)
    if auth:
        return auth

    items = SupermarketItem.objects.select_related('category').all()
    q = request.GET.get('q', '').strip()
    if q:
        items = items.filter(Q(name__icontains=q) | Q(brand__icontains=q))

    paginator = Paginator(items, 15)
    page = paginator.get_page(request.GET.get('page', 1))
    context = {'items': page, 'query': q, 'name': request.session.get("name", "Admin")}
    return render(request, 'marketplace/admin/supermarket.html', context)


def admin_supermarket_add(request):
    auth = _admin_required(request)
    if auth:
        return auth

    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        if not name:
            messages.error(request, '商品名称不能为空')
            return redirect('marketplace:admin_supermarket_add')

        category = _required_category(request, 'supermarket', 'marketplace:admin_supermarket_add')
        if not category:
            messages.error(request, 'La catégorie est obligatoire.')
            return redirect('marketplace:admin_supermarket_add')

        from manager.views import _parse_delivery_days_override
        delivery_days_min, delivery_days_max = _parse_delivery_days_override(request.POST)

        item = SupermarketItem(
            name_en=request.POST.get('name_en', '').strip(),
            slug=slugify(name) or f'item-{uuid.uuid4().hex[:8]}',
            price=request.POST.get('price', 0),
            original_price=request.POST.get('original_price') or None,
            stock=request.POST.get('stock', 0),
            min_order_quantity=_positive_int(request.POST.get('min_order_quantity'), 1),
            max_order_quantity=_optional_positive_int(request.POST.get('max_order_quantity')),
            quantity_step=_positive_int(request.POST.get('quantity_step'), 1),
            pricing_rules=_pricing_rules_from_post(request),
            unit=request.POST.get('unit', 'piece'),
            brand=request.POST.get('brand', '').strip(),
            origin=request.POST.get('origin', '').strip(),
            is_organic=request.POST.get('is_organic') == 'on',
            is_featured=request.POST.get('is_featured') == 'on',
            is_active=request.POST.get('is_active', 'on') == 'on',
            delivery_days_min=delivery_days_min,
            delivery_days_max=delivery_days_max,
        )
        # name/description are django-modeltranslation fields — passing them
        # as constructor kwargs above silently drops them (the library skips
        # populating the per-language column while _mt_init is set during
        # __init__), so they must be assigned as plain attributes instead.
        item.name = name
        item.description = request.POST.get('description', '')
        item.category = category
        vendor_id = request.POST.get('vendor')
        if vendor_id:
            item.vendor_id = int(vendor_id)
        if 'image' in request.FILES:
            item.image = request.FILES['image']
        if 'image_2' in request.FILES:
            item.image_2 = request.FILES['image_2']
        if 'image_3' in request.FILES:
            item.image_3 = request.FILES['image_3']
        _apply_uploaded_media(item, request)

        base_slug = item.slug
        counter = 1
        while SupermarketItem.objects.filter(slug=item.slug).exists():
            item.slug = f'{base_slug}-{counter}'
            counter += 1

        if not item.vendor_id:
            assign_official_vendor(item)
        item.save()

        # Save dynamic attributes
        attr_names = request.POST.getlist('attr_name')
        attr_values = request.POST.getlist('attr_value')
        for a_name, a_val in zip(attr_names, attr_values):
            a_name = a_name.strip()
            a_val = a_val.strip()
            if a_name and a_val:
                SupermarketItemAttribute.objects.create(item=item, name=a_name, value=a_val)

        messages.success(request, f'超市商品 "{name}" 已添加')
        return redirect('marketplace:admin_supermarket')

    categories = Category.objects.filter(section='supermarket', is_active=True)
    from manager.models import Vendor
    vendors = Vendor.objects.filter(is_active=True)
    context = _form_context_with_pricing({'categories': categories, 'vendors': vendors, 'name': request.session.get("name", "Admin")})
    return render(request, 'marketplace/admin/supermarket_form.html', context)


def admin_supermarket_edit(request, pk):
    auth = _admin_required(request)
    if auth:
        return auth

    item = get_object_or_404(SupermarketItem, pk=pk)
    if request.method == 'POST':
        item_name = _required_text(request, 'name', '商品名称', min_length=3)
        item_description = _required_text(request, 'description', '商品描述', min_length=12)
        category = _required_category(request, 'supermarket', 'marketplace:admin_supermarket_edit', pk=item.pk)
        if not item_name or not item_description or not category or not _validate_marketplace_business_rules(request, require_images=0, allow_existing_images=bool(item.image or item.image_2 or item.image_3)):
            categories = Category.objects.filter(section='supermarket', is_active=True)
            context = _form_context_with_pricing({'categories': categories, 'item': item, 'unit_choices': SupermarketItem.UNIT_CHOICES, 'form_state': _build_marketplace_form_state(request, item)}, item)
            return render(request, 'marketplace/admin/supermarket_form.html', context)
        from manager.views import _parse_delivery_days_override
        item.delivery_days_min, item.delivery_days_max = _parse_delivery_days_override(request.POST)
        item.name = item_name
        item.name_en = request.POST.get('name_en', '').strip()
        item.description = item_description
        item.price = request.POST.get('price', item.price)
        item.original_price = request.POST.get('original_price') or None
        item.stock = request.POST.get('stock', item.stock)
        item.min_order_quantity = _positive_int(request.POST.get('min_order_quantity'), item.min_order_quantity)
        item.max_order_quantity = _optional_positive_int(request.POST.get('max_order_quantity'))
        item.quantity_step = _positive_int(request.POST.get('quantity_step'), item.quantity_step)
        item.pricing_rules = _pricing_rules_from_post(request)
        item.unit = request.POST.get('unit', 'piece')
        item.brand = request.POST.get('brand', '').strip()
        item.origin = request.POST.get('origin', '').strip()
        item.is_organic = request.POST.get('is_organic') == 'on'
        item.is_featured = request.POST.get('is_featured') == 'on'
        item.is_active = request.POST.get('is_active', 'on') == 'on'
        item.category = category
        vendor_id = request.POST.get('vendor')
        if vendor_id:
            item.vendor_id = int(vendor_id)
        else:
            item.vendor_id = None
            assign_official_vendor(item)
        if 'image' in request.FILES:
            item.image = request.FILES['image']
        if 'image_2' in request.FILES:
            item.image_2 = request.FILES['image_2']
        if 'image_3' in request.FILES:
            item.image_3 = request.FILES['image_3']
        _apply_uploaded_media(item, request)
        item.save()

        # Update dynamic attributes: clear old, save new
        item.attributes.all().delete()
        attr_names = request.POST.getlist('attr_name')
        attr_values = request.POST.getlist('attr_value')
        for a_name, a_val in zip(attr_names, attr_values):
            a_name = a_name.strip()
            a_val = a_val.strip()
            if a_name and a_val:
                SupermarketItemAttribute.objects.create(item=item, name=a_name, value=a_val)

        messages.success(request, f'超市商品 "{item.name}" 已更新')
        return redirect('marketplace:admin_supermarket')

    categories = Category.objects.filter(section='supermarket', is_active=True)
    from manager.models import Vendor
    vendors = Vendor.objects.filter(is_active=True)
    context = _form_context_with_pricing({'item': item, 'categories': categories, 'vendors': vendors, 'name': request.session.get("name", "Admin")}, item)
    return render(request, 'marketplace/admin/supermarket_form.html', context)


def admin_supermarket_delete(request, pk):
    auth = _admin_required(request)
    if auth:
        return auth

    if request.method == 'POST':
        item = get_object_or_404(SupermarketItem, pk=pk)
        name = item.name
        item.delete()
        messages.success(request, f'超市商品 "{name}" 已删除')
    return redirect('marketplace:admin_supermarket')


# ─── Category CRUD ────────────────────────────────────────────────────────────

def admin_categories(request):
    auth = _admin_required(request)
    if auth:
        return auth

    categories = Category.objects.all().order_by('section', 'display_order')
    context = {'categories': categories, 'name': request.session.get("name", "Admin")}
    return render(request, 'marketplace/admin/categories.html', context)


def admin_category_add(request):
    auth = _admin_required(request)
    if auth:
        return auth

    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        if not name:
            messages.error(request, '分类名称不能为空')
            return redirect('marketplace:admin_category_add')

        cat = Category(
            name_en=request.POST.get('name_en', '').strip(),
            slug=slugify(name) or f'cat-{uuid.uuid4().hex[:8]}',
            section=request.POST.get('section', 'products'),
            display_order=request.POST.get('display_order', 0) or 0,
            is_active=request.POST.get('is_active', 'on') == 'on',
        )
        # name/description are django-modeltranslation fields — constructor
        # kwargs silently drop them, so assign as plain attributes instead.
        cat.name = name
        cat.description = request.POST.get('description', '')
        parent_id = request.POST.get('parent')
        if parent_id:
            cat.parent_id = int(parent_id)
        if 'image' in request.FILES:
            cat.image = request.FILES['image']

        base_slug = cat.slug
        counter = 1
        while Category.objects.filter(slug=cat.slug).exists():
            cat.slug = f'{base_slug}-{counter}'
            counter += 1

        cat.save()
        messages.success(request, f'分类 "{name}" 已添加')
        return redirect('marketplace:admin_categories')

    parent_categories = Category.objects.filter(parent__isnull=True, is_active=True)
    context = {'parent_categories': parent_categories, 'name': request.session.get("name", "Admin")}
    return render(request, 'marketplace/admin/category_form.html', context)


def admin_category_edit(request, pk):
    auth = _admin_required(request)
    if auth:
        return auth

    cat = get_object_or_404(Category, pk=pk)
    if request.method == 'POST':
        cat.name = request.POST.get('name', cat.name).strip()
        cat.name_en = request.POST.get('name_en', '').strip()
        cat.description = request.POST.get('description', '')
        cat.section = request.POST.get('section', cat.section)
        cat.display_order = request.POST.get('display_order', 0) or 0
        cat.is_active = request.POST.get('is_active', 'on') == 'on'
        parent_id = request.POST.get('parent')
        cat.parent_id = int(parent_id) if parent_id else None
        if 'image' in request.FILES:
            cat.image = request.FILES['image']
        cat.save()
        messages.success(request, f'分类 "{cat.name}" 已更新')
        return redirect('marketplace:admin_categories')

    parent_categories = Category.objects.filter(parent__isnull=True, is_active=True).exclude(pk=pk)
    context = {'category': cat, 'parent_categories': parent_categories, 'name': request.session.get("name", "Admin")}
    return render(request, 'marketplace/admin/category_form.html', context)


def admin_category_delete(request, pk):
    auth = _admin_required(request)
    if auth:
        return auth

    if request.method == 'POST':
        cat = get_object_or_404(Category, pk=pk)
        name = cat.name
        cat.delete()
        messages.success(request, f'分类 "{name}" 已删除')
    return redirect('marketplace:admin_categories')


# ─── Orders ───────────────────────────────────────────────────────────────────

def admin_orders(request):
    auth = _admin_required(request)
    if auth:
        return auth

    orders = MarketplaceOrder.objects.prefetch_related('items').all()
    status_filter = request.GET.get('status', '')
    payment_status_filter = request.GET.get('payment_status', '')
    search_query = request.GET.get('search', '')

    if status_filter:
        orders = orders.filter(status=status_filter)
    if payment_status_filter:
        orders = orders.filter(payment_status=payment_status_filter)
    if search_query:
        orders = orders.filter(
            Q(order_number__icontains=search_query) |
            Q(user_name__icontains=search_query) |
            Q(user_email__icontains=search_query) |
            Q(customer_phone__icontains=search_query)
        )

    orders = orders.order_by('-created_at')

    # Statistics
    all_orders = MarketplaceOrder.objects.all()
    total_orders = all_orders.count()
    pending_orders = all_orders.filter(status='pending').count()
    completed_orders = all_orders.filter(payment_status='completed').count()
    total_revenue = all_orders.filter(payment_status='completed').aggregate(
        total=Sum('total_amount')
    )['total'] or 0

    paginator = Paginator(orders, 20)
    page = paginator.get_page(request.GET.get('page', 1))
    context = {
        'orders': page,
        'current_status': status_filter,
        'current_payment_status': payment_status_filter,
        'current_search': search_query,
        'total_orders': total_orders,
        'pending_orders': pending_orders,
        'completed_orders': completed_orders,
        'total_revenue': total_revenue,
        'status_choices': MarketplaceOrder.STATUS_CHOICES,
        'payment_status_choices': MarketplaceOrder.PAYMENT_STATUS_CHOICES,
        'name': request.session.get("name", "Admin"),
    }
    return render(request, 'marketplace/admin/orders.html', context)


def admin_order_detail(request, pk):
    """Admin marketplace order detail view"""
    auth = _admin_required(request)
    if auth:
        return auth

    order = get_object_or_404(MarketplaceOrder, pk=pk)
    order_items = order.items.all()

    context = {
        'order': order,
        'order_items': order_items,
        'status_choices': MarketplaceOrder.STATUS_CHOICES,
        'payment_status_choices': MarketplaceOrder.PAYMENT_STATUS_CHOICES,
        'name': request.session.get("name", "Admin"),
    }
    return render(request, 'marketplace/admin/order_detail.html', context)


@require_POST
def admin_update_order_status(request):
    """Update marketplace order status via AJAX"""
    if not request.session.get("name"):
        return JsonResponse({'success': False, 'message': '请先登录'})

    try:
        order_id = request.POST.get('order_id')
        new_status = request.POST.get('status')
        admin_notes = request.POST.get('admin_notes', '')

        order = get_object_or_404(MarketplaceOrder, id=order_id)
        old_status = order.status

        order.status = new_status
        if admin_notes:
            order.admin_notes = admin_notes
        order.save()

        status_dict = dict(MarketplaceOrder.STATUS_CHOICES)
        return JsonResponse({
            'success': True,
            'message': f'订单状态已从 "{status_dict[old_status]}" 更新为 "{status_dict[new_status]}"',
            'new_status': new_status,
            'new_status_display': status_dict[new_status],
            'new_status_color': order.get_status_color()
        })
    except Exception:
        return JsonResponse({'success': False, 'message': '更新失败，请重试'})


@require_POST
def admin_update_payment_status(request):
    """Update marketplace order payment status via AJAX"""
    if not request.session.get("name"):
        return JsonResponse({'success': False, 'message': '请先登录'})

    try:
        order_id = request.POST.get('order_id')
        new_payment_status = request.POST.get('payment_status')
        transaction_id = request.POST.get('transaction_id', '')

        order = get_object_or_404(MarketplaceOrder, id=order_id)
        old_payment_status = order.payment_status

        if new_payment_status == 'completed':
            # Route through the shared pipeline (shipment creation,
            # confirmation email, inventory deduction) instead of just
            # flipping the field.
            from manager.payments.views import _update_order_status
            _update_order_status(order, 'SUCCESSFUL', transaction_id=transaction_id or None)
        else:
            order.payment_status = new_payment_status
            if transaction_id:
                order.payment_transaction_id = transaction_id
            order.save()

        payment_dict = dict(MarketplaceOrder.PAYMENT_STATUS_CHOICES)
        status_dict = dict(MarketplaceOrder.STATUS_CHOICES)
        return JsonResponse({
            'success': True,
            'message': f'支付状态已从 "{payment_dict[old_payment_status]}" 更新为 "{payment_dict[new_payment_status]}"',
            'new_payment_status': new_payment_status,
            'new_payment_status_display': payment_dict[new_payment_status],
            'new_payment_status_color': order.get_payment_status_color(),
            'order_status': order.status,
            'order_status_display': status_dict[order.status],
            'order_status_color': order.get_status_color()
        })
    except Exception:
        return JsonResponse({'success': False, 'message': '更新失败，请重试'})


@require_POST
def admin_delete_order(request, pk):
    """Delete marketplace order via AJAX"""
    if not request.session.get("name"):
        return JsonResponse({'success': False, 'message': '请先登录'})

    try:
        order = get_object_or_404(MarketplaceOrder, pk=pk)

        if order.status == 'delivered':
            return JsonResponse({'success': False, 'message': '已送达的订单不能删除'})

        if order.payment_status == 'completed':
            return JsonResponse({'success': False, 'message': '已完成支付的订单不能删除，请先处理退款'})

        order_number = order.order_number
        user_name = order.user_name
        order.delete()

        return JsonResponse({
            'success': True,
            'message': f'订单 {order_number} (客户: {user_name}) 已成功删除'
        })
    except MarketplaceOrder.DoesNotExist:
        return JsonResponse({'success': False, 'message': '订单不存在'})
    except Exception as e:
        return JsonResponse({'success': False, 'message': f'删除失败：{str(e)}'})


# ─── Vendor Helper ────────────────────────────────────────────────────────────

def _vendor_required(request):
    """Return vendor object or redirect response (aligned with manager._get_vendor)."""
    from manager.models import Vendor

    admin_access = request.session.get('name')
    vendor = None

    vendor_id = request.session.get('vendor_id')
    if vendor_id:
        vendor = Vendor.objects.filter(id=vendor_id, is_active=True).first()
        if not vendor:
            request.session.pop('vendor_id', None)
            request.session.pop('vendor_name', None)

    if not vendor:
        site_user_id = request.session.get('site_user_id')
        if site_user_id:
            vendor = Vendor.objects.filter(user_id=site_user_id, is_active=True).first()
            if vendor and vendor.status == 'approved':
                request.session['vendor_id'] = vendor.id
                request.session['vendor_name'] = vendor.company_name

    if not vendor and admin_access:
        vid = (request.GET.get('vendor_id') or request.POST.get('vendor_id') or '').strip()
        if vid:
            vendor = Vendor.objects.filter(pk=vid, is_active=True).first()

    if not vendor:
        return None, redirect('/manager/vendor/login/')

    if vendor.status == 'rejected' and not admin_access:
        return None, redirect('/manager/vendor/login/')

    return vendor, None


# ─── Vendor Dashboard ────────────────────────────────────────────────────────

def vendor_dashboard(request):
    """Former product-center dashboard merged into manager seller hub."""
    vendor, redir = _vendor_required(request)
    if redir:
        return redir
    return redirect(reverse('manager:vendor_dashboard'))


def _vendor_marketplace_order_ids(vendor):
    pids = list(Product.objects.filter(vendor=vendor).values_list('id', flat=True))
    cids = list(Course.objects.filter(vendor=vendor).values_list('id', flat=True))
    sids = list(SupermarketItem.objects.filter(vendor=vendor).values_list('id', flat=True))
    if not pids and not cids and not sids:
        return []
    q_filter = Q()
    if pids:
        q_filter |= Q(item_type='product', item_id__in=pids)
    if cids:
        q_filter |= Q(item_type='course', item_id__in=cids)
    if sids:
        q_filter |= Q(item_type='supermarket', item_id__in=sids)
    return list(
        MarketplaceOrderItem.objects.filter(q_filter)
        .values_list('order_id', flat=True)
        .distinct()
    )


def _vendor_mkt_order_can_update_fulfillment(order):
    """Vendors may update status/payment unless the order is closed."""
    return order.status not in ('cancelled', 'refunded')


# 'shipped'/'delivered' are deliberately excluded — those now require the
# shipment-based flow (manager:vendor_shipment_action) which enforces
# tracking info on ship and never lets the vendor self-report delivery.
VENDOR_MKT_ORDER_ALLOWED_STATUSES = frozenset({'processing'})


def _vendor_mkt_order_customer_editable(order):
    return order.status not in ('cancelled', 'refunded')


def vendor_marketplace_orders(request):
    """Marketplace orders that include this vendor's products or courses."""
    vendor, redir = _vendor_required(request)
    if redir:
        return redir

    oid_list = _vendor_marketplace_order_ids(vendor)
    orders = MarketplaceOrder.objects.filter(id__in=oid_list).order_by('-created_at')

    status_filter = request.GET.get('status', '')
    payment_filter = request.GET.get('payment_status', '')
    search_q = request.GET.get('search', '').strip()
    if status_filter:
        orders = orders.filter(status=status_filter)
    if payment_filter:
        orders = orders.filter(payment_status=payment_filter)
    if search_q:
        orders = orders.filter(
            Q(order_number__icontains=search_q)
            | Q(user_name__icontains=search_q)
            | Q(user_email__icontains=search_q)
            | Q(customer_phone__icontains=search_q)
        )

    base = MarketplaceOrder.objects.filter(id__in=oid_list)
    total_orders = base.count()
    pending_pay = base.filter(payment_status='pending').count()
    paid_completed = base.filter(payment_status='completed').count()

    paginator = Paginator(orders, 20)
    page = paginator.get_page(request.GET.get('page', 1))

    context = {
        'vendor': vendor,
        'orders': page,
        'status_choices': MarketplaceOrder.STATUS_CHOICES,
        'payment_status_choices': MarketplaceOrder.PAYMENT_STATUS_CHOICES,
        'current_status': status_filter,
        'current_payment_status': payment_filter,
        'current_search': search_q,
        'total_orders': total_orders,
        'pending_pay': pending_pay,
        'paid_completed': paid_completed,
        'fulfillment_statuses': [(k, v) for k, v in MarketplaceOrder.STATUS_CHOICES if k in VENDOR_MKT_ORDER_ALLOWED_STATUSES],
    }
    return render(request, 'marketplace/vendor/vendor_marketplace_orders.html', context)


def vendor_marketplace_order_detail(request, pk):
    vendor, redir = _vendor_required(request)
    if redir:
        return redir

    allowed_ids = set(_vendor_marketplace_order_ids(vendor))
    order = get_object_or_404(MarketplaceOrder, pk=pk)
    if order.id not in allowed_ids:
        raise Http404('Order not found')

    pids = list(Product.objects.filter(vendor=vendor).values_list('id', flat=True))
    cids = list(Course.objects.filter(vendor=vendor).values_list('id', flat=True))
    sids = list(SupermarketItem.objects.filter(vendor=vendor).values_list('id', flat=True))
    q_items = None
    if pids:
        q_items = Q(item_type='product', item_id__in=pids)
    if cids:
        cq = Q(item_type='course', item_id__in=cids)
        q_items = cq if q_items is None else (q_items | cq)
    if sids:
        sq = Q(item_type='supermarket', item_id__in=sids)
        q_items = sq if q_items is None else (q_items | sq)
    vendor_items = list(order.items.filter(q_items).select_related()) if q_items is not None else []

    vendor_subtotal = sum((it.subtotal for it in vendor_items), Decimal('0'))
    from manager.models import Shipment
    vendor_shipment = Shipment.objects.filter(
        order_source='marketplace', order_id=order.id, vendor=vendor,
    ).first()
    suggested_delivery_date = None
    if vendor_shipment and vendor_shipment.fulfillment_status in ('accepted', 'packing'):
        from manager.fulfillment_service import suggested_delivery_date as _suggest
        suggested_delivery_date = _suggest(vendor_shipment)

    context = {
        'vendor': vendor,
        'order': order,
        'vendor_items': vendor_items,
        'vendor_subtotal': vendor_subtotal,
        'shipment': vendor_shipment,
        'suggested_delivery_date': suggested_delivery_date,
        'can_update_fulfillment': _vendor_mkt_order_can_update_fulfillment(order),
        'fulfillment_statuses': [(k, v) for k, v in MarketplaceOrder.STATUS_CHOICES if k in VENDOR_MKT_ORDER_ALLOWED_STATUSES],
        'status_choices': MarketplaceOrder.STATUS_CHOICES,
        'payment_status_choices': MarketplaceOrder.PAYMENT_STATUS_CHOICES,
        'can_edit_customer': _vendor_mkt_order_customer_editable(order),
    }
    return render(request, 'marketplace/vendor/vendor_marketplace_order_detail.html', context)


@require_POST
def vendor_marketplace_order_update_status(request):
    vendor, redir = _vendor_required(request)
    if redir:
        return JsonResponse({'success': False, 'message': '请以卖家身份登录'}, status=403)

    order_id = request.POST.get('order_id')
    new_status = request.POST.get('status', '').strip()
    note = request.POST.get('vendor_note', '').strip()

    if new_status not in VENDOR_MKT_ORDER_ALLOWED_STATUSES:
        return JsonResponse({'success': False, 'message': '不允许的状态'})

    allowed_ids = set(_vendor_marketplace_order_ids(vendor))
    order = get_object_or_404(MarketplaceOrder, id=order_id)
    if order.id not in allowed_ids:
        return JsonResponse({'success': False, 'message': '无权操作此订单'})

    if not _vendor_mkt_order_can_update_fulfillment(order):
        return JsonResponse({'success': False, 'message': '订单已关闭，无法更新状态'})

    order.status = new_status
    if note:
        prefix = '[Vendor %s] ' % vendor.company_name[:40]
        order.admin_notes = (prefix + note + '\n' + (order.admin_notes or '')).strip()
    order.save(update_fields=['status', 'admin_notes', 'updated_at'])

    status_dict = dict(MarketplaceOrder.STATUS_CHOICES)
    return JsonResponse({
        'success': True,
        'message': '已更新',
        'new_status': new_status,
        'new_status_display': status_dict.get(new_status, new_status),
        'new_status_color': order.get_status_color(),
    })


@require_POST
def vendor_marketplace_order_update_customer(request, pk):
    vendor, redir = _vendor_required(request)
    if redir:
        return JsonResponse({'success': False, 'message': str(_('请以卖家身份登录'))}, status=403)

    order_id = request.POST.get('order_id') or pk
    allowed_ids = set(_vendor_marketplace_order_ids(vendor))
    order = get_object_or_404(MarketplaceOrder, id=order_id)
    if order.id not in allowed_ids:
        return JsonResponse({'success': False, 'message': str(_('无权操作此订单'))}, status=403)
    if not _vendor_mkt_order_customer_editable(order):
        return JsonResponse({'success': False, 'message': str(_('订单已关闭，无法修改联系信息'))})

    user_name = request.POST.get('user_name', '').strip()
    user_email = request.POST.get('user_email', '').strip()
    phone = request.POST.get('customer_phone', '').strip()
    country = request.POST.get('country', '').strip() or order.country
    shipping_address = request.POST.get('shipping_address', '').strip()
    customer_notes = request.POST.get('customer_notes', '').strip()

    if not user_email:
        return JsonResponse({'success': False, 'message': str(_('邮箱不能为空'))})

    order.user_name = user_name[:100]
    order.user_email = user_email[:254]
    order.customer_phone = phone[:20]
    order.country = country[:50]
    order.shipping_address = shipping_address
    order.customer_notes = customer_notes
    order.save(update_fields=[
        'user_name', 'user_email', 'customer_phone', 'country',
        'shipping_address', 'customer_notes', 'updated_at',
    ])
    return JsonResponse({'success': True, 'message': str(_('客户与地址信息已保存'))})


# ─── Vendor Products ─────────────────────────────────────────────────────────

def vendor_products(request):
    """List vendor's products."""
    vendor, redir = _vendor_required(request)
    if redir:
        return redir

    all_products = Product.objects.filter(vendor=vendor)
    products = all_products.order_by('-created_at')
    q = request.GET.get('q', '').strip()
    if q:
        # The search box promises "name, SKU, or category" — it only ever
        # matched name/SKU before, silently dropping category matches.
        products = products.filter(
            Q(name__icontains=q) | Q(sku__icontains=q) | Q(category__name__icontains=q)
        )

    # Stats
    total_products = all_products.count()
    active_products = all_products.filter(is_active=True).count()
    total_sales = all_products.aggregate(s=Sum('sales_count'))['s'] or 0
    total_stock = all_products.aggregate(s=Sum('stock'))['s'] or 0

    paginator = Paginator(products, 15)
    page = paginator.get_page(request.GET.get('page', 1))

    context = {
        'vendor': vendor,
        'products': page,
        'search_query': q,
        'total_products': total_products,
        'active_products': active_products,
        'total_sales': total_sales,
        'total_stock': total_stock,
    }
    return render(request, 'marketplace/vendor/products.html', context)


def _ensure_vendor_for_site_user(site_user):
    if not site_user:
        return None
    site_user.promote_to_seller()
    vendor, created = Vendor.objects.get_or_create(
        user=site_user,
        defaults={
            'company_name': site_user.name,
            'contact_name': site_user.name,
            'email': site_user.email,
            'phone': site_user.phone or '',
            'password': site_user.password,
            'description': '',
            'status': 'approved',
            'is_active': True,
        }
    )
    changed = False
    if not vendor.phone and site_user.phone:
        vendor.phone = site_user.phone
        changed = True
    if vendor.status != 'approved':
        vendor.status = 'approved'
        changed = True
    if not vendor.is_active:
        vendor.is_active = True
        changed = True
    if changed:
        vendor.save()
    return vendor


def vendor_publish_product(request):
    """Public publish flow that auto-promotes buyer to seller."""
    user_id = request.session.get('site_user_id')
    if not user_id:
        messages.error(request, 'Veuillez vous connecter pour publier une annonce.')
        return redirect('manager:public_login')

    site_user = SiteUser.objects.filter(pk=user_id, is_active=True).first()
    if not site_user:
        messages.error(request, 'Session utilisateur invalide. Veuillez vous reconnecter.')
        return redirect('manager:public_login')

    vendor = _ensure_vendor_for_site_user(site_user)
    request.session['user_role'] = 'seller'

    if request.method == 'POST':
        return _handle_vendor_product_form_submission(
            request, vendor, redirect_name='marketplace:vendor_publish_product', min_images=2,
        )

    categories = Category.objects.filter(section='products', is_active=True)
    context = {
        'vendor': vendor,
        'categories': categories,
        'public_publish_mode': True,
        'seller_phone': site_user.phone or vendor.phone or '',
        'seller_name': site_user.name or vendor.contact_name,
    }
    return render(request, 'marketplace/vendor/product_form.html', context)


def _handle_vendor_product_form_submission(request, vendor, redirect_name='marketplace:vendor_products', min_images=1):
    title = _required_text(request, 'name', '商品标题', min_length=3)
    phone = _required_text(request, 'seller_phone', '卖家电话', min_length=6)
    description = _required_text(request, 'description', '商品描述', min_length=12)
    if description:
        description = description[:850]
    image_count = sum(1 for key in ['image', 'image_2', 'image_3'] if request.FILES.get(key))

    categories = Category.objects.filter(section='products', is_active=True)
    form_state = _build_marketplace_form_state(request)

    if not title or not phone or not description or not _validate_marketplace_business_rules(request, require_images=min_images):
        context = _form_context_with_pricing({'vendor': vendor, 'product': None, 'categories': categories, 'form_state': _build_marketplace_form_state(request)}, None)
        return render(request, 'marketplace/vendor/product_form.html', context)
    if len(title) > 70:
        _add_field_error(request, 'name', 'Le titre ne doit pas dépasser 70 caractères.')
        context = _form_context_with_pricing({'vendor': vendor, 'product': None, 'categories': categories, 'form_state': _build_marketplace_form_state(request)}, None)
        return render(request, 'marketplace/vendor/product_form.html', context)
    if image_count < min_images:
        _add_field_error(request, 'image', 'Veuillez ajouter au moins 2 photos.' if min_images >= 2 else 'Veuillez ajouter au moins une photo.')
        context = _form_context_with_pricing({'vendor': vendor, 'categories': categories, 'form_state': _build_marketplace_form_state(request)}, None)
        return render(request, 'marketplace/vendor/product_form.html', context)

    category = _required_category(request, 'products', redirect_name)
    if not category:
        context = _form_context_with_pricing({'vendor': vendor, 'categories': categories, 'form_state': _build_marketplace_form_state(request)}, None)
        return render(request, 'marketplace/vendor/product_form.html', context)

    from manager.views import _parse_delivery_days_override
    delivery_days_min, delivery_days_max = _parse_delivery_days_override(request.POST)

    with transaction.atomic():
        product = Product(
            vendor_id=vendor.pk,
            slug=slugify(title) or f'product-{uuid.uuid4().hex[:8]}',
            price=request.POST.get('price', 0) or 0,
            original_price=request.POST.get('original_price') or None,
            stock=request.POST.get('stock', 1) or 1,
            min_order_quantity=_positive_int(request.POST.get('min_order_quantity'), 1),
            max_order_quantity=_optional_positive_int(request.POST.get('max_order_quantity')),
            quantity_step=_positive_int(request.POST.get('quantity_step'), 1),
            pricing_rules=_pricing_rules_from_post(request),
            brand=request.POST.get('brand', '').strip(),
            condition=request.POST.get('condition', 'new'),
            weight=request.POST.get('weight') or None,
            is_featured=False,
            is_active=request.POST.get('is_active', 'on') == 'on',
            category=category,
            delivery_days_min=delivery_days_min,
            delivery_days_max=delivery_days_max,
        )
        # name/description are django-modeltranslation fields — passing them
        # as constructor kwargs above silently drops them (the library skips
        # populating the per-language column while _mt_init is set during
        # __init__), so they must be assigned as plain attributes instead.
        product.name = title
        product.description = description
        if request.FILES.get('image'):
            product.image = request.FILES['image']
        if request.FILES.get('image_2'):
            product.image_2 = request.FILES['image_2']
        if request.FILES.get('image_3'):
            product.image_3 = request.FILES['image_3']
        _apply_uploaded_media(product, request)

        base_slug = product.slug
        counter = 1
        while Product.objects.filter(slug=product.slug).exists():
            product.slug = f'{base_slug}-{counter}'
            counter += 1
        product.save()

        dynamic_fields = {
            'location': 'Emplacement',
            'brand': 'Marque',
            'item_type': 'Type',
            'gender': 'Sexe',
            'material': 'Matériel',
            'size_text': 'Taille',
            'color_text': 'Couleur',
            'style': 'Style',
            'length_style': 'Longueur',
            'fit': 'Coupe',
            'neckline': 'Encolure',
            'details_text': 'Détails',
            'season': 'Saison',
            'closure': 'Fermeture',
            'sub_type': 'Sous-type',
            'youtube_url': 'Vidéo YouTube',
            'seller_name': 'Nom du vendeur',
            'negotiation': 'Négociation',
            'bulk_min_qty': 'Qté gros min',
            'bulk_unit_price': 'Prix gros unitaire',
            'delivery_available': 'Livraison',
        }
        for field_name, label in dynamic_fields.items():
            raw_value = request.POST.get(field_name, '')
            value = raw_value.strip() if isinstance(raw_value, str) else str(raw_value).strip()
            if value:
                ProductAttribute.objects.create(product=product, name=label, value=value)

        for field_name, label in [('is_handmade', 'Fait main'), ('has_warranty', 'Garantie')]:
            if request.POST.get(field_name):
                ProductAttribute.objects.create(product=product, name=label, value='Oui')

        attr_names = request.POST.getlist('attr_name')
        attr_values = request.POST.getlist('attr_value')
        for a_name, a_val in zip(attr_names, attr_values):
            a_name, a_val = a_name.strip(), a_val.strip()
            if a_name and a_val:
                ProductAttribute.objects.create(product=product, name=a_name, value=a_val)

        if vendor.phone != phone:
            vendor.phone = phone
            vendor.save(update_fields=['phone'])
        if vendor.user and vendor.user.phone != phone:
            vendor.user.phone = phone
            vendor.user.save(update_fields=['phone', 'updated_at'])

    messages.success(request, f'Annonce "{title}" publiée avec succès')
    return redirect('marketplace:vendor_products')


def vendor_product_add(request):
    """Add a new product."""
    vendor, redir = _vendor_required(request)
    if redir:
        return redir
    if vendor.status == 'suspended':
        messages.warning(request, _('您的店铺当前处于暂停状态，暂时不能发布新商品。'))
        return redirect('marketplace:vendor_products')

    if request.method == 'POST':
        return _handle_vendor_product_form_submission(request, vendor, redirect_name='marketplace:vendor_product_add', min_images=1)

    categories = Category.objects.filter(section='products', is_active=True)
    context = _form_context_with_pricing({
        'vendor': vendor,
        'product': None,
        'categories': categories,
        'form_state': _build_marketplace_form_state(request),
        'seller_phone': vendor.phone or '',
        'seller_name': vendor.contact_name or vendor.company_name,
    }, None)
    return render(request, 'marketplace/vendor/product_form.html', context)


def vendor_product_edit(request, pk):
    """Edit vendor's product."""
    vendor, redir = _vendor_required(request)
    if redir:
        return redir

    product = get_object_or_404(Product, pk=pk, vendor=vendor)

    if request.method == 'POST':
        product.name = request.POST.get('name', product.name).strip()
        product.name_en = request.POST.get('name_en', '').strip()
        product.description = request.POST.get('description', '')
        product.price = request.POST.get('price', product.price)
        product.original_price = request.POST.get('original_price') or None
        product.stock = request.POST.get('stock', product.stock)
        product.min_order_quantity = _positive_int(request.POST.get('min_order_quantity'), product.min_order_quantity)
        product.max_order_quantity = _optional_positive_int(request.POST.get('max_order_quantity'))
        product.quantity_step = _positive_int(request.POST.get('quantity_step'), product.quantity_step)
        product.pricing_rules = _pricing_rules_from_post(request)
        product.brand = request.POST.get('brand', '').strip()
        product.condition = request.POST.get('condition', 'new')
        product.weight = request.POST.get('weight') or None
        product.is_active = request.POST.get('is_active', 'on') == 'on'
        from manager.views import _parse_delivery_days_override
        product.delivery_days_min, product.delivery_days_max = _parse_delivery_days_override(request.POST)
        category = _required_category(request, 'products', 'marketplace:vendor_product_edit', pk=product.pk)
        if not category:
            categories = Category.objects.filter(section='products', is_active=True)
            context = _form_context_with_pricing({'vendor': vendor, 'product': product, 'categories': categories, 'form_state': _build_marketplace_form_state(request, product)}, product)
            return render(request, 'marketplace/vendor/product_form.html', context)
        product.category = category
        if 'image' in request.FILES:
            product.image = request.FILES['image']
        if 'image_2' in request.FILES:
            product.image_2 = request.FILES['image_2']
        if 'image_3' in request.FILES:
            product.image_3 = request.FILES['image_3']
        _apply_uploaded_media(product, request)
        product.save()

        product.attributes.all().delete()
        attr_names = request.POST.getlist('attr_name')
        attr_values = request.POST.getlist('attr_value')
        for a_name, a_val in zip(attr_names, attr_values):
            a_name, a_val = a_name.strip(), a_val.strip()
            if a_name and a_val:
                ProductAttribute.objects.create(product=product, name=a_name, value=a_val)

        messages.success(request, f'商品 "{product.name}" 已更新')
        return redirect('marketplace:vendor_products')

    categories = Category.objects.filter(section='products', is_active=True)
    context = _form_context_with_pricing({'vendor': vendor, 'product': product, 'categories': categories, 'form_state': {}}, product)
    return render(request, 'marketplace/vendor/product_form.html', context)


@require_POST
def vendor_product_delete(request, pk):
    """Delete vendor's product."""
    vendor, redir = _vendor_required(request)
    if redir:
        return redir
    product = get_object_or_404(Product, pk=pk, vendor=vendor)
    name = product.name
    product.delete()
    messages.success(request, f'商品 "{name}" 已删除')
    return redirect('marketplace:vendor_products')


@require_POST
def vendor_product_toggle(request, pk):
    """Toggle active status."""
    vendor, redir = _vendor_required(request)
    if redir:
        return redir
    product = get_object_or_404(Product, pk=pk, vendor=vendor)
    product.is_active = not product.is_active
    product.save(update_fields=['is_active'])
    return JsonResponse({'success': True, 'is_active': product.is_active})


# ─── Vendor Courses ──────────────────────────────────────────────────────────

def vendor_courses(request):
    """List vendor's courses."""
    vendor, redir = _vendor_required(request)
    if redir:
        return redir

    courses = Course.objects.filter(vendor=vendor).order_by('-created_at')
    q = request.GET.get('q', '').strip()
    if q:
        # The search box promises "title, instructor, or keyword" — it only
        # ever matched title before, silently dropping instructor/description
        # matches despite what the placeholder tells the vendor to expect.
        courses = courses.filter(
            Q(title__icontains=q) | Q(instructor__icontains=q) | Q(description__icontains=q)
        )

    paginator = Paginator(courses, 15)
    page = paginator.get_page(request.GET.get('page', 1))

    context = {'vendor': vendor, 'courses': page, 'search_query': q}
    return render(request, 'marketplace/vendor/courses.html', context)


def vendor_course_add(request):
    """Add a new course."""
    vendor, redir = _vendor_required(request)
    if redir:
        return redir

    if request.method == 'POST':
        title = _required_text(request, 'title', '课程标题', min_length=3)
        description = _required_text(request, 'description', '课程描述', min_length=12)
        instructor = _required_text(request, 'instructor', '讲师姓名', min_length=2)
        category = _required_category(request, 'courses', 'marketplace:vendor_course_add')
        if not title or not description or not instructor or not category or not _validate_marketplace_business_rules(request, require_images=1):
            categories = Category.objects.filter(section='courses', is_active=True)
            context = {'vendor': vendor, 'categories': categories, 'form_state': _build_marketplace_form_state(request)}
            return render(request, 'marketplace/vendor/course_form.html', context)

        course = Course(
            vendor_id=vendor.pk,
            title_en=request.POST.get('title_en', '').strip(),
            slug=slugify(title) or f'course-{uuid.uuid4().hex[:8]}',
            price=request.POST.get('price', 0),
            original_price=request.POST.get('original_price') or None,
            instructor=instructor,
            duration_hours=request.POST.get('duration_hours', 0) or 0,
            lessons_count=request.POST.get('lessons_count', 0) or 0,
            level=request.POST.get('level', 'all'),
            language=request.POST.get('language', '中文'),
            preview_url=request.POST.get('preview_url', ''),
            is_featured=False,
            is_active=request.POST.get('is_active', 'on') == 'on',
        )
        # title/description are django-modeltranslation fields — passing them
        # as constructor kwargs above silently drops them (the library skips
        # populating the per-language column while _mt_init is set during
        # __init__), so they must be assigned as plain attributes instead.
        course.title = title
        course.description = description
        cat_id = request.POST.get('category')
        if cat_id:
            course.category_id = int(cat_id)
        if 'image' in request.FILES:
            course.image = request.FILES['image']

        base_slug = course.slug
        counter = 1
        while Course.objects.filter(slug=course.slug).exists():
            course.slug = f'{base_slug}-{counter}'
            counter += 1
        course.save()

        messages.success(request, f'课程 "{title}" 已添加')
        return redirect('marketplace:vendor_courses')

    categories = Category.objects.filter(section='courses', is_active=True)
    context = {
        'vendor': vendor,
        'course': None,
        'categories': categories,
        'form_state': _build_marketplace_form_state(request),
    }
    return render(request, 'marketplace/vendor/course_form.html', context)


def vendor_course_edit(request, pk):
    """Edit vendor's course."""
    vendor, redir = _vendor_required(request)
    if redir:
        return redir

    course = get_object_or_404(Course, pk=pk, vendor=vendor)

    if request.method == 'POST':
        course_title = _required_text(request, 'title', '课程标题', min_length=3)
        course_description = _required_text(request, 'description', '课程描述', min_length=12)
        instructor = _required_text(request, 'instructor', '讲师姓名', min_length=2)
        category = _required_category(request, 'courses', 'marketplace:vendor_course_edit', pk=course.pk)
        if not course_title or not course_description or not instructor or not category or not _validate_marketplace_business_rules(request, require_images=0, allow_existing_images=bool(course.image)):
            categories = Category.objects.filter(section='courses', is_active=True)
            context = {'vendor': vendor, 'course': course, 'categories': categories, 'form_state': _build_marketplace_form_state(request, course)}
            return render(request, 'marketplace/vendor/course_form.html', context)
        course.title = course_title
        course.title_en = request.POST.get('title_en', '').strip()
        course.description = course_description
        course.price = request.POST.get('price', course.price)
        course.original_price = request.POST.get('original_price') or None
        course.instructor = instructor
        course.duration_hours = request.POST.get('duration_hours', 0) or 0
        course.lessons_count = request.POST.get('lessons_count', 0) or 0
        course.level = request.POST.get('level', 'all')
        course.language = request.POST.get('language', '中文')
        course.preview_url = request.POST.get('preview_url', '')
        course.is_active = request.POST.get('is_active', 'on') == 'on'
        cat_id = request.POST.get('category')
        course.category_id = int(cat_id) if cat_id else None
        if 'image' in request.FILES:
            course.image = request.FILES['image']
        course.save()

        messages.success(request, f'课程 "{course.title}" 已更新')
        return redirect('marketplace:vendor_courses')

    categories = Category.objects.filter(section='courses', is_active=True)
    context = {'vendor': vendor, 'course': course, 'categories': categories, 'form_state': {}}
    return render(request, 'marketplace/vendor/course_form.html', context)


@require_POST
def vendor_course_delete(request, pk):
    """Delete vendor's course."""
    vendor, redir = _vendor_required(request)
    if redir:
        return redir
    course = get_object_or_404(Course, pk=pk, vendor=vendor)
    name = course.title
    course.delete()
    messages.success(request, f'课程 "{name}" 已删除')
    return redirect('marketplace:vendor_courses')


@require_POST
def vendor_course_toggle(request, pk):
    """Toggle course active status."""
    vendor, redir = _vendor_required(request)
    if redir:
        return redir
    course = get_object_or_404(Course, pk=pk, vendor=vendor)
    course.is_active = not course.is_active
    course.save(update_fields=['is_active'])
    return JsonResponse({'success': True, 'is_active': course.is_active})


# ─── Vendor Course Content Management ────────────────────────────────────────

def vendor_course_content(request, pk):
    """Manage sections and lessons for a vendor's course."""
    vendor, redir = _vendor_required(request)
    if redir:
        return redir
    course = get_object_or_404(Course, pk=pk, vendor=vendor)
    sections = course.sections.prefetch_related('lessons').all()
    context = {
        'course': course,
        'sections': sections,
        'vendor': vendor,
    }
    return render(request, 'marketplace/vendor/course_content.html', context)


@require_POST
def vendor_section_add(request, course_pk):
    """Add a new section to a vendor's course."""
    vendor, redir = _vendor_required(request)
    if redir:
        return JsonResponse({'success': False, 'message': '未登录'}, status=403)
    course = get_object_or_404(Course, pk=course_pk, vendor=vendor)
    title = request.POST.get('title', '').strip()
    title_en = request.POST.get('title_en', '').strip()
    if not title:
        return JsonResponse({'success': False, 'message': '章节标题不能为空'})
    max_order = course.sections.count()
    section = CourseSection.objects.create(
        course=course, title=title, title_en=title_en, order=max_order,
    )
    return JsonResponse({
        'success': True, 'message': f'章节 "{title}" 已添加',
        'section': {'id': section.id, 'title': section.title, 'title_en': section.title_en, 'order': section.order}
    })


@require_POST
def vendor_section_edit(request, pk):
    """Edit a section belonging to a vendor's course."""
    vendor, redir = _vendor_required(request)
    if redir:
        return JsonResponse({'success': False, 'message': '未登录'}, status=403)
    section = get_object_or_404(CourseSection, pk=pk, course__vendor=vendor)
    title = request.POST.get('title', '').strip()
    if not title:
        return JsonResponse({'success': False, 'message': '章节标题不能为空'})
    section.title = title
    section.title_en = request.POST.get('title_en', '').strip()
    order = request.POST.get('order')
    if order is not None:
        section.order = int(order)
    section.save()
    return JsonResponse({'success': True, 'message': f'章节 "{title}" 已更新'})


@require_POST
def vendor_section_delete(request, pk):
    """Delete a section belonging to a vendor's course."""
    vendor, redir = _vendor_required(request)
    if redir:
        return JsonResponse({'success': False, 'message': '未登录'}, status=403)
    section = get_object_or_404(CourseSection, pk=pk, course__vendor=vendor)
    name = section.title
    section.delete()
    return JsonResponse({'success': True, 'message': f'章节 "{name}" 已删除'})


@require_POST
def vendor_lesson_add(request, section_pk):
    """Add a new lesson to a section of a vendor's course."""
    vendor, redir = _vendor_required(request)
    if redir:
        return JsonResponse({'success': False, 'message': '未登录'}, status=403)
    section = get_object_or_404(CourseSection, pk=section_pk, course__vendor=vendor)
    title = request.POST.get('title', '').strip()
    if not title:
        return JsonResponse({'success': False, 'message': '课时标题不能为空'})
    max_order = section.lessons.count()
    lesson = CourseLesson(
        section=section, title=title,
        title_en=request.POST.get('title_en', '').strip(),
        description=request.POST.get('description', ''),
        video_url=request.POST.get('video_url', ''),
        duration_minutes=int(request.POST.get('duration_minutes', 0) or 0),
        order=max_order,
        is_free=request.POST.get('is_free') == 'on',
    )
    if 'video_file' in request.FILES:
        lesson.video_file = request.FILES['video_file']
    if 'pdf_file' in request.FILES:
        lesson.pdf_file = request.FILES['pdf_file']
    if 'resource_file' in request.FILES:
        lesson.resource_file = request.FILES['resource_file']
    lesson.save()
    return JsonResponse({
        'success': True, 'message': f'课时 "{title}" 已添加',
        'lesson': {
            'id': lesson.id, 'title': lesson.title,
            'duration_minutes': lesson.duration_minutes, 'is_free': lesson.is_free,
            'has_video': bool(lesson.video_file or lesson.video_url),
            'has_pdf': bool(lesson.pdf_file),
            'has_resource': bool(lesson.resource_file),
        }
    })


@require_POST
def vendor_lesson_edit(request, pk):
    """Edit a lesson belonging to a vendor's course."""
    vendor, redir = _vendor_required(request)
    if redir:
        return JsonResponse({'success': False, 'message': '未登录'}, status=403)
    lesson = get_object_or_404(CourseLesson, pk=pk, section__course__vendor=vendor)
    title = request.POST.get('title', '').strip()
    if not title:
        return JsonResponse({'success': False, 'message': '课时标题不能为空'})
    lesson.title = title
    lesson.title_en = request.POST.get('title_en', '').strip()
    lesson.description = request.POST.get('description', '')
    lesson.video_url = request.POST.get('video_url', '')
    lesson.duration_minutes = int(request.POST.get('duration_minutes', 0) or 0)
    lesson.is_free = request.POST.get('is_free') == 'on'
    order = request.POST.get('order')
    if order is not None:
        lesson.order = int(order)
    section_id = request.POST.get('section_id')
    if section_id:
        lesson.section_id = int(section_id)
    if 'video_file' in request.FILES:
        lesson.video_file = request.FILES['video_file']
    if request.POST.get('clear_video_file') == '1':
        lesson.video_file = None
    if 'pdf_file' in request.FILES:
        lesson.pdf_file = request.FILES['pdf_file']
    if request.POST.get('clear_pdf_file') == '1':
        lesson.pdf_file = None
    if 'resource_file' in request.FILES:
        lesson.resource_file = request.FILES['resource_file']
    if request.POST.get('clear_resource_file') == '1':
        lesson.resource_file = None
    lesson.save()
    return JsonResponse({'success': True, 'message': f'课时 "{title}" 已更新'})


@require_POST
def vendor_lesson_delete(request, pk):
    """Delete a lesson belonging to a vendor's course."""
    vendor, redir = _vendor_required(request)
    if redir:
        return JsonResponse({'success': False, 'message': '未登录'}, status=403)
    lesson = get_object_or_404(CourseLesson, pk=pk, section__course__vendor=vendor)
    name = lesson.title
    lesson.delete()
    return JsonResponse({'success': True, 'message': f'课时 "{name}" 已删除'})


# ─── Vendor Supermarket (seller-owned grocery SKUs) ───────────────────────────

def vendor_supermarket(request):
    vendor, redir = _vendor_required(request)
    if redir:
        return redir

    base = SupermarketItem.objects.filter(vendor=vendor)
    total_items = base.count()
    active_items = base.filter(is_active=True).count()
    qs = base.order_by('-created_at')
    q = request.GET.get('q', '').strip()
    if q:
        # The search box promises "name, brand, or origin" — it only ever
        # matched name/brand before, silently dropping origin matches.
        qs = qs.filter(Q(name__icontains=q) | Q(brand__icontains=q) | Q(origin__icontains=q))
    paginator = Paginator(qs, 15)
    page = paginator.get_page(request.GET.get('page', 1))

    context = {
        'vendor': vendor,
        'items': page,
        'search_query': q,
        'total_items': total_items,
        'active_items': active_items,
    }
    return render(request, 'marketplace/vendor/supermarket.html', context)


def vendor_supermarket_add(request):
    vendor, redir = _vendor_required(request)
    if redir:
        return redir
    if vendor.status == 'suspended':
        messages.warning(request, _('您的店铺当前处于暂停状态，暂时不能发布新的超市商品。'))
        return redirect('marketplace:vendor_supermarket')

    if request.method == 'POST':
        name = _required_text(request, 'name', '商品名称', min_length=3)
        description = _required_text(request, 'description', '商品描述', min_length=12)
        category = _required_category(request, 'supermarket', 'marketplace:vendor_supermarket_add')
        if not name or not description or not category or not _validate_marketplace_business_rules(request, require_images=1):
            categories = Category.objects.filter(section='supermarket', is_active=True)
            context = _form_context_with_pricing({'vendor': vendor, 'item': None, 'categories': categories, 'unit_choices': SupermarketItem.UNIT_CHOICES, 'form_state': _build_marketplace_form_state(request)}, None)
            return render(request, 'marketplace/vendor/supermarket_form.html', context)

        from manager.views import _parse_delivery_days_override
        delivery_days_min, delivery_days_max = _parse_delivery_days_override(request.POST)

        item = SupermarketItem(
            vendor_id=vendor.pk,
            name_en=request.POST.get('name_en', '').strip(),
            slug=slugify(name) or f'sm-{uuid.uuid4().hex[:8]}',
            price=request.POST.get('price', 0),
            original_price=request.POST.get('original_price') or None,
            stock=request.POST.get('stock', 0),
            min_order_quantity=_positive_int(request.POST.get('min_order_quantity'), 1),
            max_order_quantity=_optional_positive_int(request.POST.get('max_order_quantity')),
            quantity_step=_positive_int(request.POST.get('quantity_step'), 1),
            pricing_rules=_pricing_rules_from_post(request),
            unit=request.POST.get('unit', 'piece'),
            brand=request.POST.get('brand', '').strip(),
            origin=request.POST.get('origin', '').strip(),
            is_organic=request.POST.get('is_organic') == 'on',
            is_featured=False,
            is_active=request.POST.get('is_active', 'on') == 'on',
            delivery_days_min=delivery_days_min,
            delivery_days_max=delivery_days_max,
        )
        # name/description are django-modeltranslation fields — passing them
        # as constructor kwargs above silently drops them (the library skips
        # populating the per-language column while _mt_init is set during
        # __init__), so they must be assigned as plain attributes instead.
        item.name = name
        item.description = request.POST.get('description', '')
        item.category = category
        if 'image' in request.FILES:
            item.image = request.FILES['image']
        if 'image_2' in request.FILES:
            item.image_2 = request.FILES['image_2']
        if 'image_3' in request.FILES:
            item.image_3 = request.FILES['image_3']
        _apply_uploaded_media(item, request)

        base_slug = item.slug
        counter = 1
        while SupermarketItem.objects.filter(slug=item.slug).exists():
            item.slug = f'{base_slug}-{counter}'
            counter += 1

        item.save()

        attr_names = request.POST.getlist('attr_name')
        attr_values = request.POST.getlist('attr_value')
        for a_name, a_val in zip(attr_names, attr_values):
            a_name = a_name.strip()
            a_val = a_val.strip()
            if a_name and a_val:
                SupermarketItemAttribute.objects.create(item=item, name=a_name, value=a_val)

        messages.success(request, _('超市商品已添加'))
        return redirect('marketplace:vendor_supermarket')

    categories = Category.objects.filter(section='supermarket', is_active=True)
    context = _form_context_with_pricing({
        'vendor': vendor,
        'item': None,
        'categories': categories,
        'unit_choices': SupermarketItem.UNIT_CHOICES,
        'form_state': _build_marketplace_form_state(request),
    }, None)
    return render(request, 'marketplace/vendor/supermarket_form.html', context)


def vendor_supermarket_edit(request, pk):
    vendor, redir = _vendor_required(request)
    if redir:
        return redir

    item = get_object_or_404(SupermarketItem, pk=pk, vendor=vendor)

    if request.method == 'POST':
        item.name = request.POST.get('name', item.name).strip()
        item.name_en = request.POST.get('name_en', '').strip()
        item.description = request.POST.get('description', '')
        item.price = request.POST.get('price', item.price)
        item.original_price = request.POST.get('original_price') or None
        item.stock = request.POST.get('stock', item.stock)
        item.min_order_quantity = _positive_int(request.POST.get('min_order_quantity'), item.min_order_quantity)
        item.max_order_quantity = _optional_positive_int(request.POST.get('max_order_quantity'))
        item.quantity_step = _positive_int(request.POST.get('quantity_step'), item.quantity_step)
        item.pricing_rules = _pricing_rules_from_post(request)
        item.unit = request.POST.get('unit', item.unit)
        item.brand = request.POST.get('brand', '').strip()
        item.origin = request.POST.get('origin', '').strip()
        item.is_organic = request.POST.get('is_organic') == 'on'
        item.is_active = request.POST.get('is_active', 'on') == 'on'
        from manager.views import _parse_delivery_days_override
        item.delivery_days_min, item.delivery_days_max = _parse_delivery_days_override(request.POST)
        category = _required_category(request, 'supermarket', 'marketplace:vendor_supermarket_edit', pk=item.pk)
        if not category:
            categories = Category.objects.filter(section='supermarket', is_active=True)
            context = _form_context_with_pricing({'vendor': vendor, 'categories': categories, 'item': item, 'unit_choices': SupermarketItem.UNIT_CHOICES, 'form_state': _build_marketplace_form_state(request, item)}, item)
            return render(request, 'marketplace/vendor/supermarket_form.html', context)
        item.category = category
        if 'image' in request.FILES:
            item.image = request.FILES['image']
        if 'image_2' in request.FILES:
            item.image_2 = request.FILES['image_2']
        if 'image_3' in request.FILES:
            item.image_3 = request.FILES['image_3']
        _apply_uploaded_media(item, request)
        item.save()

        item.attributes.all().delete()
        attr_names = request.POST.getlist('attr_name')
        attr_values = request.POST.getlist('attr_value')
        for a_name, a_val in zip(attr_names, attr_values):
            a_name = a_name.strip()
            a_val = a_val.strip()
            if a_name and a_val:
                SupermarketItemAttribute.objects.create(item=item, name=a_name, value=a_val)

        messages.success(request, _('超市商品已更新'))
        return redirect('marketplace:vendor_supermarket')

    categories = Category.objects.filter(section='supermarket', is_active=True)
    context = _form_context_with_pricing({
        'vendor': vendor,
        'categories': categories,
        'item': item,
        'unit_choices': SupermarketItem.UNIT_CHOICES,
        'form_state': {},
    }, item)
    return render(request, 'marketplace/vendor/supermarket_form.html', context)


@require_POST
def vendor_supermarket_delete(request, pk):
    vendor, redir = _vendor_required(request)
    if redir:
        return redir
    item = get_object_or_404(SupermarketItem, pk=pk, vendor=vendor)
    item.delete()
    messages.success(request, _('超市商品已删除'))
    return redirect('marketplace:vendor_supermarket')


@require_POST
def vendor_supermarket_toggle(request, pk):
    vendor, redir = _vendor_required(request)
    if redir:
        return JsonResponse({'success': False}, status=403)
    item = get_object_or_404(SupermarketItem, pk=pk, vendor=vendor)
    item.is_active = not item.is_active
    item.save(update_fields=['is_active'])
    return JsonResponse({'success': True, 'is_active': item.is_active})


def listing_reviews_api(request, kind, listing_id):
    if request.method != 'GET':
        return JsonResponse({'error': 'method'}, status=405)
    try:
        lid = int(listing_id)
    except (TypeError, ValueError):
        return JsonResponse({'error': 'invalid'}, status=400)
    fl = (request.GET.get('filter') or 'all').lower()
    offset = max(int(request.GET.get('offset', 0)), 0)
    limit = min(max(int(request.GET.get('limit', 15)), 1), 50)
    qs = filter_reviews(reviews_for_listing(kind, lid), fl)
    total = qs.count()
    rows = list(qs[offset : offset + limit])
    return JsonResponse({'total': total, 'reviews': [serialize_review(r) for r in rows]})


def vendor_post_reviews(request):
    vendor, redir = _vendor_required(request)
    if redir:
        return redir
    from manager import models as mgr_models

    pids = list(Product.objects.filter(vendor=vendor).values_list('id', flat=True))
    cids = list(Course.objects.filter(vendor=vendor).values_list('id', flat=True))
    sids = list(SupermarketItem.objects.filter(vendor=vendor).values_list('id', flat=True))
    bids = list(
        mgr_models.VendorBook.objects.filter(vendor=vendor, is_active=True).values_list('book_id', flat=True)
    )
    q = (
        Q(listing_kind='product', listing_id__in=pids)
        | Q(listing_kind='course', listing_id__in=cids)
        | Q(listing_kind='supermarket', listing_id__in=sids)
        | Q(listing_kind='book', listing_id__in=bids)
    )
    reviews = list(
        PostDeliveryReview.objects.filter(q)
        .select_related('site_user')
        .order_by('-created_at')[:200]
    )
    return render(
        request,
        'marketplace/vendor/post_reviews_readonly.html',
        {'vendor': vendor, 'reviews': reviews},
    )


def admin_post_reviews(request):
    gate = _admin_required(request)
    if gate:
        return gate
    reviews = PostDeliveryReview.objects.select_related('site_user').order_by('-created_at')[:500]
    return render(
        request,
        'marketplace/admin/post_reviews_readonly.html',
        {'reviews': reviews},
    )
