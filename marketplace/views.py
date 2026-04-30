from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse, FileResponse
from django.db.models import Q, Sum, Count, Avg
from django.core.paginator import Paginator
from django.contrib import messages
from django.utils.text import slugify
from django.utils import timezone
from django.views.decorators.http import require_POST
from django.views.decorators.clickjacking import xframe_options_sameorigin
from .models import (
    Category, Product, Course, SupermarketItem,
    MarketplaceOrder, MarketplaceOrderItem,
    MarketplaceCartItem, CourseSection, CourseLesson, CourseProgress,
    ProductAttribute, SupermarketItemAttribute,
)
from .utils import build_attribute_groups, validate_selected_attributes, normalize_selected_attributes
from book_Project.payment_config import build_payment_options
from decimal import Decimal
import uuid
import json


# ─── Helper ───────────────────────────────────────────────────────────────────

def _admin_required(request):
    """Check if admin is logged in via session."""
    if not request.session.get("name"):
        return redirect('/manager/login/')
    return None


# ═══════════════════════════════════════════════════════════════════════════════
#  PUBLIC VIEWS
# ═══════════════════════════════════════════════════════════════════════════════

def marketplace_home(request):
    """Marketplace landing page with featured items from all sections."""
    featured_products = Product.objects.filter(is_active=True, is_featured=True)[:4]
    featured_courses = Course.objects.filter(is_active=True, is_featured=True)[:4]
    featured_supermarket = SupermarketItem.objects.filter(is_active=True, is_featured=True)[:4]

    # Fallback if not enough featured items
    if featured_products.count() < 4:
        featured_products = Product.objects.filter(is_active=True)[:4]
    if featured_courses.count() < 4:
        featured_courses = Course.objects.filter(is_active=True)[:4]
    if featured_supermarket.count() < 4:
        featured_supermarket = SupermarketItem.objects.filter(is_active=True)[:4]

    product_count = Product.objects.filter(is_active=True).count()
    course_count = Course.objects.filter(is_active=True).count()
    supermarket_count = SupermarketItem.objects.filter(is_active=True).count()

    context = {
        'featured_products': featured_products,
        'featured_courses': featured_courses,
        'featured_supermarket': featured_supermarket,
        'product_count': product_count,
        'course_count': course_count,
        'supermarket_count': supermarket_count,
    }
    return render(request, 'marketplace/home.html', context)


def product_list(request):
    """Browse all products with search and category filter."""
    products = Product.objects.filter(is_active=True).select_related('category')
    categories = Category.objects.filter(section='products', is_active=True)

    q = request.GET.get('q', '').strip()
    cat = request.GET.get('category', '')
    sort = request.GET.get('sort', '-created_at')

    if q:
        products = products.filter(Q(name__icontains=q) | Q(description__icontains=q) | Q(brand__icontains=q))
    if cat:
        products = products.filter(category__slug=cat)
    if sort in ['price', '-price', '-sales_count', '-created_at', 'name']:
        products = products.order_by(sort)

    paginator = Paginator(products, 12)
    page = paginator.get_page(request.GET.get('page', 1))

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
    Product.objects.filter(pk=product.pk).update(views_count=product.views_count + 1)
    related = Product.objects.filter(
        is_active=True, category=product.category
    ).exclude(pk=product.pk)[:4] if product.category else Product.objects.none()
    attribute_context = build_attribute_groups(product.attributes.all())

    context = {
        'product': product,
        'related_products': related,
        'attribute_groups': attribute_context['groups'],
        'selectable_attributes': attribute_context['selectable_groups'],
        'specification_attributes': attribute_context['specification_groups'],
    }
    return render(request, 'marketplace/product_detail.html', context)


def course_list(request):
    """Browse all courses with search and filter."""
    courses = Course.objects.filter(is_active=True).select_related('category')
    categories = Category.objects.filter(section='courses', is_active=True)

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
    if sort in ['price', '-price', '-enrollment_count', '-rating', '-created_at']:
        courses = courses.order_by(sort)

    paginator = Paginator(courses, 12)
    page = paginator.get_page(request.GET.get('page', 1))

    context = {
        'courses': page,
        'categories': categories,
        'query': q,
        'current_category': cat,
        'current_level': level,
        'current_sort': sort,
    }
    return render(request, 'marketplace/courses.html', context)


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

    context = {
        'course': course,
        'sections': sections,
        'related_courses': related,
        'completed_ids': completed_ids,
        'total_lessons': total_lessons,
        'completed_count': completed_count,
        'progress_percent': progress_percent,
        'current_lesson': current_lesson,
    }
    return render(request, 'marketplace/course_detail.html', context)


def supermarket_list(request):
    """Browse supermarket items with search and filter."""
    items = SupermarketItem.objects.filter(is_active=True).select_related('category')
    categories = Category.objects.filter(section='supermarket', is_active=True)

    q = request.GET.get('q', '').strip()
    cat = request.GET.get('category', '')
    sort = request.GET.get('sort', '-created_at')

    if q:
        items = items.filter(Q(name__icontains=q) | Q(description__icontains=q) | Q(brand__icontains=q))
    if cat:
        items = items.filter(category__slug=cat)
    if sort in ['price', '-price', '-sales_count', '-created_at', 'name']:
        items = items.order_by(sort)

    paginator = Paginator(items, 16)
    page = paginator.get_page(request.GET.get('page', 1))

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

    context = {
        'item': item,
        'related_items': related,
        'attribute_groups': attribute_context['groups'],
        'selectable_attributes': attribute_context['selectable_groups'],
        'specification_attributes': attribute_context['specification_groups'],
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
            if quantity > item.stock:
                return JsonResponse({'success': False, 'message': f'库存不足！当前库存：{item.stock}'})
            item_name = item.name
        elif item_type == 'course':
            item = get_object_or_404(Course, pk=item_id, is_active=True)
            quantity = 1  # Courses always qty 1
            item_name = item.title
        elif item_type == 'supermarket':
            item = get_object_or_404(SupermarketItem, pk=item_id, is_active=True)
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
            if item_type == 'product' and new_qty > item.stock:
                return JsonResponse({'success': False, 'message': f'库存不足！购物车已有{cart_item.quantity}件'})
            if item_type == 'supermarket' and new_qty > item.stock:
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
            if ci.item_type in ('product', 'supermarket') and item and quantity > item.stock:
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


def checkout(request):
    """Checkout page with payment methods."""
    session_key = _get_session_key(request)
    cart_items = MarketplaceCartItem.objects.filter(session_key=session_key)

    if not cart_items.exists():
        messages.warning(request, '购物车为空')
        return redirect('marketplace:home')

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
                'selected_attributes': ci.selected_attributes or {},
            })

    if request.method == 'POST':
        try:
            country = request.POST.get('country', 'China')
            payment_method = request.POST.get('payment_method', 'wechat_pay')
            available_methods = {
                option['method']
                for region_options in build_payment_options(country).values()
                for option in region_options
            }
            if payment_method not in available_methods:
                messages.error(request, '当前国家暂不支持该支付方式，请重新选择。')
                return redirect('marketplace:checkout')

            order = MarketplaceOrder(
                user_name=request.POST.get('customer_name', ''),
                user_email=request.POST.get('customer_email', ''),
                customer_phone=request.POST.get('customer_phone', ''),
                country=country,
                payment_method=payment_method,
                total_amount=total_amount,
                shipping_address=request.POST.get('shipping_address', ''),
                notes=request.POST.get('notes', ''),
            )
            order.save()

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
                )

                # Update stock/sales
                item = detail['item']
                if ci.item_type == 'product':
                    item.stock = max(0, item.stock - ci.quantity)
                    item.sales_count += ci.quantity
                    item.save()
                elif ci.item_type == 'supermarket':
                    item.stock = max(0, item.stock - ci.quantity)
                    item.sales_count += ci.quantity
                    item.save()
                elif ci.item_type == 'course':
                    item.enrollment_count += 1
                    item.save()

            cart_items.delete()
            return redirect('marketplace:order_confirmation', order_number=order.order_number)

        except Exception as e:
            messages.error(request, '订单创建失败，请重试')

    payment_methods = build_payment_options()

    context = {
        'cart_items': items_with_details,
        'total_amount': total_amount,
        'total_price': total_amount,
        'total_quantity': total_qty,
        'total_count': len(items_with_details),
        'payment_methods': payment_methods,
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
    response = FileResponse(lesson.pdf_file.open('rb'), content_type='application/pdf')
    response['Content-Disposition'] = 'inline'
    return response


# ═══════════════════════════════════════════════════════════════════════════════
#  ADMIN VIEWS
# ═══════════════════════════════════════════════════════════════════════════════

def admin_dashboard(request):
    """Marketplace admin dashboard with stats."""
    auth = _admin_required(request)
    if auth:
        return auth

    context = {
        'product_count': Product.objects.count(),
        'course_count': Course.objects.count(),
        'supermarket_count': SupermarketItem.objects.count(),
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

        product = Product(
            name=name,
            name_en=request.POST.get('name_en', '').strip(),
            slug=slugify(name) or f'product-{uuid.uuid4().hex[:8]}',
            description=request.POST.get('description', ''),
            price=request.POST.get('price', 0),
            original_price=request.POST.get('original_price') or None,
            stock=request.POST.get('stock', 0),
            brand=request.POST.get('brand', '').strip(),
            condition=request.POST.get('condition', 'new'),
            weight=request.POST.get('weight') or None,
            is_featured=request.POST.get('is_featured') == 'on',
            is_active=request.POST.get('is_active', 'on') == 'on',
        )
        cat_id = request.POST.get('category')
        if cat_id:
            product.category_id = int(cat_id)
        if 'image' in request.FILES:
            product.image = request.FILES['image']
        if 'image_2' in request.FILES:
            product.image_2 = request.FILES['image_2']
        if 'image_3' in request.FILES:
            product.image_3 = request.FILES['image_3']

        # Ensure unique slug
        base_slug = product.slug
        counter = 1
        while Product.objects.filter(slug=product.slug).exists():
            product.slug = f'{base_slug}-{counter}'
            counter += 1

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
    context = {'categories': categories, 'name': request.session.get("name", "Admin")}
    return render(request, 'marketplace/admin/product_form.html', context)


def admin_product_edit(request, pk):
    auth = _admin_required(request)
    if auth:
        return auth

    product = get_object_or_404(Product, pk=pk)
    if request.method == 'POST':
        product.name = request.POST.get('name', product.name).strip()
        product.name_en = request.POST.get('name_en', '').strip()
        product.description = request.POST.get('description', '')
        product.price = request.POST.get('price', product.price)
        product.original_price = request.POST.get('original_price') or None
        product.stock = request.POST.get('stock', product.stock)
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
        product.save()

        # Update dynamic attributes: clear old, save new
        product.attributes.all().delete()
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
    context = {'product': product, 'categories': categories, 'name': request.session.get("name", "Admin")}
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
            title=title,
            title_en=request.POST.get('title_en', '').strip(),
            slug=slugify(title) or f'course-{uuid.uuid4().hex[:8]}',
            description=request.POST.get('description', ''),
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
        course.title = request.POST.get('title', course.title).strip()
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

        item = SupermarketItem(
            name=name,
            name_en=request.POST.get('name_en', '').strip(),
            slug=slugify(name) or f'item-{uuid.uuid4().hex[:8]}',
            description=request.POST.get('description', ''),
            price=request.POST.get('price', 0),
            original_price=request.POST.get('original_price') or None,
            stock=request.POST.get('stock', 0),
            unit=request.POST.get('unit', 'piece'),
            brand=request.POST.get('brand', '').strip(),
            origin=request.POST.get('origin', '').strip(),
            is_organic=request.POST.get('is_organic') == 'on',
            is_featured=request.POST.get('is_featured') == 'on',
            is_active=request.POST.get('is_active', 'on') == 'on',
        )
        cat_id = request.POST.get('category')
        if cat_id:
            item.category_id = int(cat_id)
        if 'image' in request.FILES:
            item.image = request.FILES['image']

        base_slug = item.slug
        counter = 1
        while SupermarketItem.objects.filter(slug=item.slug).exists():
            item.slug = f'{base_slug}-{counter}'
            counter += 1

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
    context = {'categories': categories, 'name': request.session.get("name", "Admin")}
    return render(request, 'marketplace/admin/supermarket_form.html', context)


def admin_supermarket_edit(request, pk):
    auth = _admin_required(request)
    if auth:
        return auth

    item = get_object_or_404(SupermarketItem, pk=pk)
    if request.method == 'POST':
        item.name = request.POST.get('name', item.name).strip()
        item.name_en = request.POST.get('name_en', '').strip()
        item.description = request.POST.get('description', '')
        item.price = request.POST.get('price', item.price)
        item.original_price = request.POST.get('original_price') or None
        item.stock = request.POST.get('stock', item.stock)
        item.unit = request.POST.get('unit', 'piece')
        item.brand = request.POST.get('brand', '').strip()
        item.origin = request.POST.get('origin', '').strip()
        item.is_organic = request.POST.get('is_organic') == 'on'
        item.is_featured = request.POST.get('is_featured') == 'on'
        item.is_active = request.POST.get('is_active', 'on') == 'on'
        cat_id = request.POST.get('category')
        item.category_id = int(cat_id) if cat_id else None
        if 'image' in request.FILES:
            item.image = request.FILES['image']
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
    context = {'item': item, 'categories': categories, 'name': request.session.get("name", "Admin")}
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
            name=name,
            name_en=request.POST.get('name_en', '').strip(),
            slug=slugify(name) or f'cat-{uuid.uuid4().hex[:8]}',
            description=request.POST.get('description', ''),
            section=request.POST.get('section', 'products'),
            display_order=request.POST.get('display_order', 0) or 0,
            is_active=request.POST.get('is_active', 'on') == 'on',
        )
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

        order.payment_status = new_payment_status
        if transaction_id:
            order.payment_transaction_id = transaction_id

        if new_payment_status == 'completed':
            order.payment_completed_at = timezone.now()
            if order.status == 'pending':
                order.status = 'paid'

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
    """Return vendor object or redirect response."""
    from manager.models import Vendor
    vendor_id = request.session.get('vendor_id')
    if not vendor_id:
        return None, redirect('/manager/vendor/login/')
    try:
        vendor = Vendor.objects.get(id=vendor_id, is_active=True, status='approved')
        return vendor, None
    except Vendor.DoesNotExist:
        return None, redirect('/manager/vendor/login/')


# ─── Vendor Dashboard ────────────────────────────────────────────────────────

def vendor_dashboard(request):
    """Vendor dashboard with data insights."""
    vendor, redir = _vendor_required(request)
    if redir:
        return redir

    from manager.models import OrderItem, CartItem
    from datetime import timedelta

    # Vendor's marketplace items
    vendor_products = Product.objects.filter(vendor=vendor)
    vendor_courses = Course.objects.filter(vendor=vendor)

    product_count = vendor_products.count()
    course_count = vendor_courses.count()
    active_products = vendor_products.filter(is_active=True).count()
    active_courses = vendor_courses.filter(is_active=True).count()

    total_product_sales = vendor_products.aggregate(s=Sum('sales_count'))['s'] or 0
    total_enrollments = vendor_courses.aggregate(s=Sum('enrollment_count'))['s'] or 0

    # Revenue from marketplace orders
    product_ids = list(vendor_products.values_list('id', flat=True))
    course_ids = list(vendor_courses.values_list('id', flat=True))

    product_order_items = MarketplaceOrderItem.objects.filter(
        item_type='product', item_id__in=product_ids,
        order__status__in=['paid', 'processing', 'shipped', 'delivered']
    ) if product_ids else MarketplaceOrderItem.objects.none()

    course_order_items = MarketplaceOrderItem.objects.filter(
        item_type='course', item_id__in=course_ids,
        order__status__in=['paid', 'processing', 'shipped', 'delivered']
    ) if course_ids else MarketplaceOrderItem.objects.none()

    product_revenue = product_order_items.aggregate(s=Sum('subtotal'))['s'] or 0
    course_revenue = course_order_items.aggregate(s=Sum('subtotal'))['s'] or 0
    total_revenue = product_revenue + course_revenue

    # Last 7 days daily revenue for chart
    daily_labels = []
    daily_product_data = []
    daily_course_data = []
    for i in range(6, -1, -1):
        day = (timezone.now() - timedelta(days=i)).date()
        daily_labels.append(day.strftime('%m/%d'))
        p_rev = product_order_items.filter(order__created_at__date=day).aggregate(s=Sum('subtotal'))['s'] or 0
        c_rev = course_order_items.filter(order__created_at__date=day).aggregate(s=Sum('subtotal'))['s'] or 0
        daily_product_data.append(float(p_rev))
        daily_course_data.append(float(c_rev))

    # Top products by sales
    top_products = vendor_products.order_by('-sales_count')[:5]

    # Recent orders involving vendor items
    all_item_ids = product_ids + course_ids
    recent_order_ids = MarketplaceOrderItem.objects.filter(
        Q(item_type='product', item_id__in=product_ids) |
        Q(item_type='course', item_id__in=course_ids)
    ).values_list('order_id', flat=True).distinct()[:20] if all_item_ids else []

    recent_orders = MarketplaceOrder.objects.filter(
        id__in=recent_order_ids
    ).order_by('-created_at')[:10]

    # Category distribution for products
    cat_data = vendor_products.values('category__name').annotate(
        cnt=Count('id')
    ).order_by('-cnt')[:6]
    cat_labels = [c['category__name'] or '未分类' for c in cat_data]
    cat_counts = [c['cnt'] for c in cat_data]

    context = {
        'vendor': vendor,
        'product_count': product_count,
        'course_count': course_count,
        'active_products': active_products,
        'active_courses': active_courses,
        'total_product_sales': total_product_sales,
        'total_enrollments': total_enrollments,
        'total_revenue': total_revenue,
        'product_revenue': product_revenue,
        'course_revenue': course_revenue,
        'daily_labels': json.dumps(daily_labels),
        'daily_product_data': json.dumps(daily_product_data),
        'daily_course_data': json.dumps(daily_course_data),
        'top_products': top_products,
        'recent_orders': recent_orders,
        'cat_labels': json.dumps(cat_labels),
        'cat_counts': json.dumps(cat_counts),
    }
    return render(request, 'marketplace/vendor/dashboard.html', context)


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
        products = products.filter(Q(name__icontains=q) | Q(sku__icontains=q))

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


def vendor_product_add(request):
    """Add a new product."""
    vendor, redir = _vendor_required(request)
    if redir:
        return redir

    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        if not name:
            messages.error(request, '商品名称不能为空')
            return redirect('marketplace:vendor_product_add')

        product = Product(
            vendor_id=vendor.pk,
            name=name,
            name_en=request.POST.get('name_en', '').strip(),
            slug=slugify(name) or f'product-{uuid.uuid4().hex[:8]}',
            description=request.POST.get('description', ''),
            price=request.POST.get('price', 0),
            original_price=request.POST.get('original_price') or None,
            stock=request.POST.get('stock', 0),
            brand=request.POST.get('brand', '').strip(),
            condition=request.POST.get('condition', 'new'),
            weight=request.POST.get('weight') or None,
            is_featured=False,
            is_active=request.POST.get('is_active', 'on') == 'on',
        )
        cat_id = request.POST.get('category')
        if cat_id:
            product.category_id = int(cat_id)
        if 'image' in request.FILES:
            product.image = request.FILES['image']
        if 'image_2' in request.FILES:
            product.image_2 = request.FILES['image_2']
        if 'image_3' in request.FILES:
            product.image_3 = request.FILES['image_3']

        base_slug = product.slug
        counter = 1
        while Product.objects.filter(slug=product.slug).exists():
            product.slug = f'{base_slug}-{counter}'
            counter += 1
        product.save()

        attr_names = request.POST.getlist('attr_name')
        attr_values = request.POST.getlist('attr_value')
        for a_name, a_val in zip(attr_names, attr_values):
            a_name, a_val = a_name.strip(), a_val.strip()
            if a_name and a_val:
                ProductAttribute.objects.create(product=product, name=a_name, value=a_val)

        messages.success(request, f'商品 "{name}" 已添加')
        return redirect('marketplace:vendor_products')

    categories = Category.objects.filter(section='products', is_active=True)
    context = {'vendor': vendor, 'categories': categories}
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
        product.brand = request.POST.get('brand', '').strip()
        product.condition = request.POST.get('condition', 'new')
        product.weight = request.POST.get('weight') or None
        product.is_active = request.POST.get('is_active', 'on') == 'on'
        cat_id = request.POST.get('category')
        product.category_id = int(cat_id) if cat_id else None
        if 'image' in request.FILES:
            product.image = request.FILES['image']
        if 'image_2' in request.FILES:
            product.image_2 = request.FILES['image_2']
        if 'image_3' in request.FILES:
            product.image_3 = request.FILES['image_3']
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
    context = {'vendor': vendor, 'product': product, 'categories': categories}
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
        courses = courses.filter(Q(title__icontains=q))

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
        title = request.POST.get('title', '').strip()
        if not title:
            messages.error(request, '课程标题不能为空')
            return redirect('marketplace:vendor_course_add')

        course = Course(
            vendor_id=vendor.pk,
            title=title,
            title_en=request.POST.get('title_en', '').strip(),
            slug=slugify(title) or f'course-{uuid.uuid4().hex[:8]}',
            description=request.POST.get('description', ''),
            price=request.POST.get('price', 0),
            original_price=request.POST.get('original_price') or None,
            instructor=request.POST.get('instructor', vendor.company_name),
            duration_hours=request.POST.get('duration_hours', 0) or 0,
            lessons_count=request.POST.get('lessons_count', 0) or 0,
            level=request.POST.get('level', 'all'),
            language=request.POST.get('language', '中文'),
            preview_url=request.POST.get('preview_url', ''),
            is_featured=False,
            is_active=request.POST.get('is_active', 'on') == 'on',
        )
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
    context = {'vendor': vendor, 'categories': categories}
    return render(request, 'marketplace/vendor/course_form.html', context)


def vendor_course_edit(request, pk):
    """Edit vendor's course."""
    vendor, redir = _vendor_required(request)
    if redir:
        return redir

    course = get_object_or_404(Course, pk=pk, vendor=vendor)

    if request.method == 'POST':
        course.title = request.POST.get('title', course.title).strip()
        course.title_en = request.POST.get('title_en', '').strip()
        course.description = request.POST.get('description', '')
        course.price = request.POST.get('price', course.price)
        course.original_price = request.POST.get('original_price') or None
        course.instructor = request.POST.get('instructor', course.instructor)
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
    context = {'vendor': vendor, 'course': course, 'categories': categories}
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
    lesson.save()
    return JsonResponse({
        'success': True, 'message': f'课时 "{title}" 已添加',
        'lesson': {
            'id': lesson.id, 'title': lesson.title,
            'duration_minutes': lesson.duration_minutes, 'is_free': lesson.is_free,
            'has_video': bool(lesson.video_file or lesson.video_url),
            'has_pdf': bool(lesson.pdf_file),
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
