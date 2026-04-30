from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse, HttpResponse, HttpResponseNotAllowed, FileResponse
from django.contrib import messages
from django.db import transaction
from django.views.decorators.http import require_http_methods, require_POST
from django.db.models import Sum, Avg, Q, Count, Max, F, Prefetch
from django.utils import timezone
from decimal import Decimal
from datetime import timedelta
from django.core.paginator import Paginator
import uuid
import json
from . import models
import csv
from openpyxl import Workbook
from openpyxl.styles import Font, Alignment, PatternFill
import io
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from plotly.utils import PlotlyJSONEncoder

from django.utils.text import slugify
from django.core.mail import send_mail
from django.conf import settings as django_settings
from django.views.decorators.csrf import csrf_protect, ensure_csrf_cookie
from django.core.cache import cache

# Marketplace imports for unified cart
from marketplace.models import (
    Product, Course, SupermarketItem, MarketplaceCartItem,
    MarketplaceOrder, MarketplaceOrderItem, CourseProgress, CourseLesson, CourseSection
)
from marketplace.utils import (
    build_attribute_groups,
    normalize_selected_attributes,
    validate_selected_attributes,
)
from book_Project.payment_config import build_payment_options
import hashlib
import logging

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Simple IP-based brute-force guard (no extra packages needed).
# Limits: 5 failed attempts per 5 minutes per IP.
# ---------------------------------------------------------------------------
_LOGIN_MAX_ATTEMPTS = 5
_LOGIN_WINDOW_SECONDS = 300  # 5 minutes


def _get_client_ip(request):
    """Return the real client IP, honouring X-Forwarded-For behind a proxy."""
    x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
    if x_forwarded_for:
        return x_forwarded_for.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR", "0.0.0.0")


def _is_rate_limited(ip: str) -> bool:
    """Return True when the IP has exceeded the login failure threshold."""
    key = f"login_fail:{ip}"
    failures = cache.get(key, 0)
    return failures >= _LOGIN_MAX_ATTEMPTS


def _record_login_failure(ip: str) -> int:
    """Increment failure counter; returns current count."""
    key = f"login_fail:{ip}"
    try:
        return cache.incr(key)
    except ValueError:
        cache.set(key, 1, _LOGIN_WINDOW_SECONDS)
        return 1


def _reset_login_failures(ip: str) -> None:
    cache.delete(f"login_fail:{ip}")


# 方法实现（数据库操作和页面跳转）
# ====================   默认跳转  ===========================
def index(request):
    return redirect("/manager/login")


# ====================   管理员登录  ===========================
def manager_login(request):
    """Admin login with PBKDF2 password check and IP-based rate limiting."""
    if request.method == "GET":
        return render(request, "admin/admin.html")

    if request.method == "POST":
        ip = _get_client_ip(request)

        # --- Rate-limit check ---
        if _is_rate_limited(ip):
            return render(
                request,
                "admin/admin.html",
                {"error": "登录尝试次数过多，请5分钟后再试。"},
                status=429,
            )

        number = request.POST.get("number", "").strip()
        password = request.POST.get("password", "")

        if not number or not password:
            _record_login_failure(ip)
            return render(request, "admin/admin.html", {"error": "账号和密码不能为空"})

        try:
            manager = models.Manager.objects.get(number=number)
        except models.Manager.DoesNotExist:
            _record_login_failure(ip)
            return render(request, "admin/admin.html", {"error": "账号或密码错误"})

        if not manager.check_password(password):
            _record_login_failure(ip)
            return render(request, "admin/admin.html", {"error": "账号或密码错误"})

        # Successful login
        _reset_login_failures(ip)
        request.session.cycle_key()          # prevent session fixation
        request.session["name"] = manager.name
        request.session["manager_id"] = manager.id
        request.session["is_admin"] = manager.is_admin
        return redirect("/manager/dashboard/")

    return redirect("/manager/login")


# ====================   管理员登出  ===========================
def manager_logout(request):
    """Manager logout — clears session and redirects to login page."""
    request.session.flush()   # flush() deletes AND regenerates the key
    return redirect("/manager/login")


# Keep the old logout function for backward compatibility
def logout(request):
    """Legacy logout function — delegates to manager_logout."""
    return manager_logout(request)


# ====================   一、出版社模块  ===========================
# 01添加出版社
def add_publisher(request):
    # 登录判断
    if "name" not in request.session:
        return redirect("/manager/login")
    # 直接访问（get请求），跳转界面
    if request.method == "GET":
        return render(request, 'publisher/add_publisher.html', {"name": request.session["name"]})
    # 提交表单请求（POST）,处理数据库,跳转到列表页面
    if request.method == "POST":
        # 1.获取请求参数
        publisher_name = request.POST.get("publisher_name")
        publisher_address = request.POST.get("publisher_address")
        # 2.将数据保存到数据库中（insert）
        models.Publisher.objects.create(
            publisher_name=publisher_name,
            publisher_address=publisher_address,
        )
        # 3.重添加成功，返回出版社列表
        return redirect("/manager/publisher_list")


# 02查询所有出版社信息
def publisher_list(request):
    # 登录判断
    if "name" not in request.session:
        return redirect("/manager/login")
    # 查询数据库中的所以信息（select * from）
    publisher_list = models.Publisher.objects.all()
    # 跳转到publisher_list页面，传入publisher_list数据
    return render(request, "publisher/publisher_list.html",
                  {"publisher_obj_list": publisher_list, "name": request.session["name"]})


# 03修改出版社信息
def edit_publisher(request):
    # 登录判断
    if "name" not in request.session:
        return redirect("/manager/login")
    # 1获取到的是表单提交过来的内容（POST），获取对应的值
    if request.method == "POST":
        id = request.POST.get('id')
        publisher_name = request.POST.get("publisher_name")
        publisher_address = request.POST.get("publisher_address")
        # 2根据id去数据库查找对象（where id = id）
        publisher_obj = models.Publisher.objects.get(id=id)
        # 3修改
        publisher_obj.publisher_name = publisher_name
        publisher_obj.publisher_address = publisher_address
        # 04更新数据库（update）
        publisher_obj.save()
        # 4重定向到出版社列表
        return redirect('/manager/publisher_list/')
    # get请求跳转界面（获取原始数据）
    else:
        # 1获取id
        id = request.GET.get('id')
        # 2去数据库中查找相应的数据
        publisher_obj = models.Publisher.objects.get(id=id)
        publisher_obj_list = models.Publisher.objects.all()
        # 3返回页面
        return render(request, "publisher/edit_publisher.html",
                      {"publisher_obj": publisher_obj, "publisher_obj_list": publisher_obj_list,
                       "name": request.session["name"]})


# 04删除出版社信息
def delete_publisher(request):
    if "name" not in request.session:
        return redirect("/manager/login")
    if request.method != 'POST':
        return HttpResponseNotAllowed(['POST'])
    pub_id = request.POST.get('id')
    models.Publisher.objects.filter(id=pub_id).delete()
    return redirect('/manager/publisher_list')


# ============================  二、图书模块操作   ===============================
# 01获取所有图书信息
def book_list(request):
    # 登录判断
    if "name" not in request.session:
        return redirect("/manager/login")
    # 1获取图书信息(select *)
    book_obj_list = models.Book.objects.select_related('publisher', 'category').all()
    # 2将数据渲染到页面上
    return render(request, 'book/book_list.html', {'book_obj_list': book_obj_list, "name": request.session["name"]})


# 02添加图书
def add_book(request):
    # 登录判断
    if "name" not in request.session:
        return redirect("/manager/login")

    # Handle inline creation of new publisher
    if request.method == 'POST' and request.POST.get('action') == 'create_publisher':
        pub_name = request.POST.get('publisher_name', '').strip()
        pub_address = request.POST.get('publisher_address', '').strip()
        if pub_name:
            pub = models.Publisher.objects.create(publisher_name=pub_name, publisher_address=pub_address)
            return JsonResponse({'success': True, 'id': pub.id, 'name': pub.publisher_name})
        return JsonResponse({'success': False, 'message': '出版社名称不能为空'})

    # Handle inline creation of new author
    if request.method == 'POST' and request.POST.get('action') == 'create_author':
        author_name = request.POST.get('author_name', '').strip()
        if author_name:
            author = models.Author.objects.create(name=author_name)
            return JsonResponse({'success': True, 'id': author.id, 'name': author.name})
        return JsonResponse({'success': False, 'message': '作者名称不能为空'})

    if request.method == 'POST':
        # 1获取表单提交过来的内容
        name = request.POST.get('name')
        description = request.POST.get('description', '')
        price = request.POST.get('price')
        inventory = request.POST.get('inventory')
        sale_num = request.POST.get('sale_num')
        publisher_id = request.POST.get('publisher_id')
        category_id = request.POST.get('category_id') or None
        author_ids = request.POST.getlist('author_ids')
        cover_image = request.FILES.get('cover_image')
        book_file = request.FILES.get('book_file')
        download_link = request.POST.get('download_link', '').strip()
        
        # 2保存到数据库（insert）
        book = models.Book.objects.create(
            name=name, 
            description=description,
            price=price, 
            inventory=inventory, 
            sale_num=sale_num,
            publisher_id=publisher_id,
            category_id=category_id,
        )
        
        # Handle image upload or auto-generate cover
        if cover_image:
            book.cover_image = cover_image
        else:
            # Auto-generate a stylish cover
            try:
                from manager.cover_generator import generate_cover_image
                book.cover_image = generate_cover_image(book.name, book.id)
            except Exception:
                pass
        
        # Handle book file upload
        if book_file:
            book.book_file = book_file
        
        # Handle download link
        if download_link:
            book.download_link = download_link
            
        book.save()

        # Associate authors with the book
        if author_ids:
            authors = models.Author.objects.filter(id__in=author_ids)
            for author in authors:
                author.book.add(book)
        
        # 3重定向到图书列表页面
        return redirect('/manager/book_list/')
    else:
        # 1获取所有的出版社（点击添加图书按钮时，得到所有出版社信息供用户选择）
        publisher_obj_list = models.Publisher.objects.all()
        author_obj_list = models.Author.objects.all()
        category_obj_list = models.BookCategory.objects.filter(is_active=True)
        # 2返回html页面（在页面中遍历出版社对象列表）
        return render(request, 'book/add_book.html', {
            'publisher_obj_list': publisher_obj_list,
            'author_obj_list': author_obj_list,
            'category_obj_list': category_obj_list,
            'name': request.session['name'],
        })


# 03修改图书信息
def edit_book(request):
    # 登录判断
    if "name" not in request.session:
        return redirect("/manager/login")
    # 点击修改图书（获取要修改图书的原本信息）
    if request.method == 'GET':
        id = request.GET.get('id')
        book_obj = models.Book.objects.select_related('category').get(id=id)
        publisher_obj_list = models.Publisher.objects.all()
        category_obj_list = models.BookCategory.objects.filter(is_active=True)
        book_obj_list = models.Book.objects.all()
        return render(request, "book/edit_book.html",
                      {"book_obj": book_obj, "book_obj_list": book_obj_list, "publisher_obj_list": publisher_obj_list,
                       "category_obj_list": category_obj_list, "name": request.session["name"]})
    # 修改图书信息（POST表单）
    else:
        id = request.POST.get('id')
        name = request.POST.get('name')
        description = request.POST.get('description', '')
        inventory = request.POST.get('inventory')
        price = request.POST.get('price')
        sale_num = request.POST.get('sale_num')
        publisher_id = request.POST.get('publisher_id')
        category_id = request.POST.get('category_id') or None
        cover_image = request.FILES.get('cover_image')
        book_file = request.FILES.get('book_file')
        download_link = request.POST.get('download_link', '').strip()
        
        # 获取要更新的图书对象
        book = models.Book.objects.get(id=id)
        
        # 数据库中更新图书信息
        book.name = name
        book.description = description
        book.inventory = inventory
        book.price = price
        book.sale_num = sale_num
        book.publisher_id = publisher_id
        book.category_id = category_id
        
        # Handle image upload
        if cover_image:
            book.cover_image = cover_image
        
        # Handle book file upload
        if book_file:
            book.book_file = book_file
        
        # Handle download link
        if download_link:
            book.download_link = download_link
        elif 'clear_download_link' in request.POST:
            book.download_link = None
            
        book.save()
        return redirect("/manager/book_list/")


# 04删除图书
def delete_book(request):
    if "name" not in request.session:
        return redirect("/manager/login")
    if request.method != 'POST':
        return HttpResponseNotAllowed(['POST'])
    book_id = request.POST.get('id')
    models.Book.objects.filter(id=book_id).delete()
    return redirect('/manager/book_list')


# ================================  三、作者操作模块  =============================
# 01作者列表
def author_list(request):
    if "name" not in request.session:
        return redirect("/manager/login")
    # Use prefetch_related to avoid N+1 queries when accessing author.book.all()
    author_obj_list = models.Author.objects.prefetch_related('book').all()
    ret_list = [
        {'author_obj': author, 'book_list': author.book.all()}
        for author in author_obj_list
    ]
    return render(request, 'author/author_list.html', {'ret_list': ret_list, "name": request.session["name"]})


# 02添加作家
def add_author(request):
    # 登录判断
    if "name" not in request.session:
        return redirect("/manager/login")
    # 添加作家页面
    if request.method == 'GET':
        # 1获取所有的图书
        book_obj_list = models.Book.objects.all()
        # 2返回页面
        return render(request, 'author/add_author.html',
                      {'book_obj_list': book_obj_list, "name": request.session["name"]})
    # 数据库处理添加
    else:
        # 1.获取表单提交过来的数据
        name = request.POST.get('name')
        book_ids = request.POST.getlist('books')
        # 2 保存数据库
        author_obj = models.Author.objects.create(name=name)  # 创建对象
        author_obj.book.set(book_ids)  # 设置关系
        # 3 重定向到列表页面
        return redirect('/manager/author_list/')


# 03修改作者信息
def edit_author(request):
    # 登录判断
    if "name" not in request.session:
        return redirect("/manager/login")
    
    # 跳转修改界面
    if request.method == 'GET':
        id = request.GET.get('id')
        try:
            author_obj = models.Author.objects.get(id=id)
            book_obj_list = models.Book.objects.all()
            # Get currently associated books
            current_books = author_obj.book.all()
            return render(request, 'author/edit_author.html',
                          {
                              'author_obj': author_obj, 
                              'book_obj_list': book_obj_list,
                              'current_books': current_books,
                              "name": request.session["name"]
                          })
        except models.Author.DoesNotExist:
            return redirect('/manager/author_list/')
    
    # 提交修改表单
    else:
        id = request.POST.get('id')
        name = request.POST.get('name')
        book_ids = request.POST.getlist('books')  # Get list of selected book IDs
        
        try:
            # 找到作者对象
            author_obj = models.Author.objects.filter(id=id).first()
            if author_obj:
                author_obj.name = name
                # Clear existing relationships and set new ones
                author_obj.book.set(book_ids)  # This handles the many-to-many relationship
                author_obj.save()
            return redirect('/manager/author_list/')
        except Exception as e:
            # Handle any errors gracefully
            return redirect(f'/manager/edit_author/?id={id}')

# 04 删除作者
def delete_author(request):
    if "name" not in request.session:
        return redirect("/manager/login")
    if request.method != 'POST':
        return HttpResponseNotAllowed(['POST'])
    author_id = request.POST.get('id')
    models.Author.objects.filter(id=author_id).delete()
    return redirect('/manager/author_list')


# ====================   PUBLIC USER INTERFACE  ===========================

def public_home(request):
    """Public homepage with platform statistics and featured content"""
    book_count = models.Book.objects.filter(is_active=True).count()
    author_count = models.Author.objects.count()
    publisher_count = models.Publisher.objects.count()
    
    # Marketplace stats & featured content
    featured_products = []
    featured_courses = []
    flash_sales = []
    flash_sale_end = None
    try:
        from marketplace.models import Product, Course, SupermarketItem, FlashSale
        from django.utils import timezone as tz
        product_count = Product.objects.filter(is_active=True).count()
        course_count = Course.objects.filter(is_active=True).count()
        vendor_count = models.Vendor.objects.filter(is_active=True).count()
        featured_products = list(Product.objects.filter(is_active=True).select_related('category').order_by('-sales_count')[:6])
        featured_courses = list(Course.objects.filter(is_active=True).order_by('-enrollment_count')[:6])
        now = tz.now()
        flash_sales = list(FlashSale.objects.filter(
            is_active=True, start_time__lte=now, end_time__gte=now
        ).select_related('product', 'course', 'supermarket_item').order_by('end_time')[:10])
        if flash_sales:
            flash_sale_end = flash_sales[0].end_time
    except Exception:
        product_count = 0
        course_count = 0
        vendor_count = 0
    
    # Get featured books (top 6 by sales)
    featured_books = models.Book.objects.filter(is_active=True).select_related('publisher', 'category').order_by('-sale_num')[:6]
    
    # Recent books (last 8 added)
    recent_books = models.Book.objects.filter(is_active=True).select_related('publisher', 'category').order_by('-id')[:8]
    book_categories = models.BookCategory.objects.filter(is_active=True, parent__isnull=True)[:12]
    
    context = {
        'book_count': book_count,
        'author_count': author_count,
        'publisher_count': publisher_count,
        'product_count': product_count,
        'course_count': course_count,
        'vendor_count': vendor_count,
        'featured_books': featured_books,
        'featured_products': featured_products,
        'featured_courses': featured_courses,
        'recent_books': recent_books,
        'book_categories': book_categories,
        'flash_sales': flash_sales,
        'flash_sale_end': flash_sale_end,
    }
    return render(request, 'public/home.html', context)


def public_messages(request):
    """Messages page: buyer/vendor direct discussions plus support chatbot entries."""
    user_id = request.session.get('site_user_id')
    user = None
    user_messages = []
    direct_conversations = []
    if user_id:
        try:
            user = models.SiteUser.objects.get(pk=user_id)
            user_messages = list(models.ContactMessage.objects.filter(
                email=user.email
            ).order_by('-created_at')[:20])
            direct_conversations = list(models.Conversation.objects.filter(
                buyer=user
            ).select_related('vendor').prefetch_related('direct_messages')[:30])
        except models.SiteUser.DoesNotExist:
            pass
    # Also include messages by session key
    if not request.session.session_key:
        request.session.save()
    session_key = request.session.session_key or ''
    if session_key:
        session_msgs = list(models.ContactMessage.objects.filter(
            session_key=session_key
        ).order_by('-created_at')[:10])
        seen_ids = {m.id for m in user_messages}
        for m in session_msgs:
            if m.id not in seen_ids:
                user_messages.append(m)
        user_messages.sort(key=lambda m: m.created_at, reverse=True)
    unread_count = len([m for m in user_messages if not m.is_read])
    context = {
        'site_user': user,
        'user_messages': user_messages,
        'direct_conversations': direct_conversations,
        'unread_count': unread_count,
    }
    return render(request, 'public/messages.html', context)


def start_conversation(request):
    """Create/open a buyer-seller conversation from product pages."""
    if not request.session.get('site_user_id'):
        return redirect('manager:user_login')
    user = get_object_or_404(models.SiteUser, pk=request.session['site_user_id'])
    item_type = request.GET.get('item_type', 'support')
    item_id = request.GET.get('item_id')
    vendor = None
    subject = request.GET.get('subject', '')
    try:
        if request.GET.get('vendor_id'):
            vendor = models.Vendor.objects.filter(pk=request.GET.get('vendor_id'), is_active=True).first()
        elif item_type == 'product':
            from marketplace.models import Product
            item = Product.objects.select_related('vendor').filter(pk=item_id).first()
            vendor = item.vendor if item else None
            subject = subject or (item.name if item else '')
        elif item_type == 'course':
            from marketplace.models import Course
            item = Course.objects.select_related('vendor').filter(pk=item_id).first()
            vendor = item.vendor if item else None
            subject = subject or (item.title if item else '')
        elif item_type == 'supermarket':
            from marketplace.models import SupermarketItem
            item = SupermarketItem.objects.filter(pk=item_id).first()
            subject = subject or (item.name if item else '')
    except Exception:
        vendor = None
    conversation_type = 'buyer_seller' if vendor else 'support'
    conversation, _ = models.Conversation.objects.get_or_create(
        buyer=user,
        vendor=vendor,
        conversation_type=conversation_type,
        ref_item_type=item_type,
        ref_item_id=item_id or None,
        defaults={'subject': subject[:200] or 'Support'}
    )
    return redirect(f"{request.build_absolute_uri('/manager/public/messages/')}?conversation={conversation.id}")


def public_send_message(request):
    """AJAX: send a support or direct message from the messages page."""
    from django.http import JsonResponse
    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': '无效请求'})
    user_id = request.session.get('site_user_id')
    message_text = request.POST.get('message', request.POST.get('content', '')).strip()
    if not message_text:
        return JsonResponse({'success': False, 'message': '消息不能为空'})
    conversation_id = request.POST.get('conversation_id')
    if conversation_id:
        if not user_id:
            return JsonResponse({'success': False, 'message': '请先登录'}, status=401)
        conversation = get_object_or_404(models.Conversation, pk=conversation_id, buyer_id=user_id)
        models.DirectMessage.objects.create(
            conversation=conversation,
            sender_type='buyer',
            sender_name=request.session.get('site_user_name', ''),
            content=message_text
        )
        conversation.save(update_fields=['updated_at'])
        return JsonResponse({'success': True, 'message': '消息已发送'})
    try:
        user = models.SiteUser.objects.get(pk=user_id) if user_id else None
        name = user.name if user else request.POST.get('name', 'Guest')
        email = user.email if user else request.POST.get('email', '')
        if not email:
            return JsonResponse({'success': False, 'message': '请先登录或提供邮箱'})
        if not request.session.session_key:
            request.session.save()
        msg = models.ContactMessage.objects.create(
            name=name,
            email=email,
            subject='来自消息页面',
            message=message_text,
            session_key=request.session.session_key or '',
        )
        return JsonResponse({'success': True, 'message': '消息已发送', 'id': msg.id,
                             'created_at': msg.created_at.strftime('%H:%M')})
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)})


def api_conversations(request):
    """API: list all conversations for the logged-in user."""
    user_id = request.session.get('site_user_id')
    if not user_id:
        return JsonResponse({'conversations': [], 'error': 'not_logged_in'})
    convos = models.Conversation.objects.filter(
        buyer_id=user_id
    ).select_related('vendor').prefetch_related('direct_messages').order_by('-updated_at')
    result = []
    for c in convos:
        last_msg = c.direct_messages.order_by('-created_at').first()
        unread = c.direct_messages.filter(is_read=False).exclude(sender_type='buyer').count()
        vendor_name = c.vendor.company_name if c.vendor else 'Support'
        vendor_avatar = c.vendor.company_name[0].upper() if c.vendor and c.vendor.company_name else 'S'
        result.append({
            'id': c.id,
            'type': c.conversation_type,
            'vendor_name': vendor_name,
            'vendor_avatar': vendor_avatar,
            'vendor_id': c.vendor_id,
            'subject': c.subject,
            'last_message': last_msg.content[:80] if last_msg else '',
            'last_time': last_msg.created_at.strftime('%H:%M') if last_msg else '',
            'last_date': last_msg.created_at.strftime('%Y-%m-%d') if last_msg else '',
            'unread': unread,
            'is_closed': c.is_closed,
        })
    return JsonResponse({'conversations': result})


def api_conversation_messages(request, conversation_id):
    """API: get messages for a specific conversation."""
    user_id = request.session.get('site_user_id')
    if not user_id:
        return JsonResponse({'messages': [], 'error': 'not_logged_in'})
    convo = get_object_or_404(models.Conversation, pk=conversation_id, buyer_id=user_id)
    msgs = convo.direct_messages.order_by('created_at')
    msgs.filter(is_read=False).exclude(sender_type='buyer').update(is_read=True)
    result = []
    for m in msgs:
        result.append({
            'id': m.id,
            'sender_type': m.sender_type,
            'sender_name': m.sender_name,
            'content': m.content,
            'time': m.created_at.strftime('%H:%M'),
            'date': m.created_at.strftime('%Y-%m-%d'),
            'is_read': m.is_read,
        })
    vendor_name = convo.vendor.company_name if convo.vendor else 'Support'
    return JsonResponse({
        'messages': result,
        'conversation': {
            'id': convo.id,
            'vendor_name': vendor_name,
            'subject': convo.subject,
            'type': convo.conversation_type,
            'is_closed': convo.is_closed,
        }
    })


def api_vendor_conversations(request):
    """API: list conversations for the logged-in vendor."""
    vendor_id = request.session.get('vendor_id')
    if not vendor_id:
        return JsonResponse({'conversations': [], 'error': 'not_logged_in'})
    convos = models.Conversation.objects.filter(
        vendor_id=vendor_id
    ).select_related('buyer').prefetch_related('direct_messages').order_by('-updated_at')
    result = []
    for c in convos:
        last_msg = c.direct_messages.order_by('-created_at').first()
        unread = c.direct_messages.filter(is_read=False).exclude(sender_type='vendor').count()
        buyer_name = c.buyer.name if c.buyer else 'Unknown'
        result.append({
            'id': c.id,
            'buyer_name': buyer_name,
            'buyer_avatar': buyer_name[0].upper() if buyer_name else 'U',
            'buyer_id': c.buyer_id,
            'subject': c.subject,
            'last_message': last_msg.content[:80] if last_msg else '',
            'last_time': last_msg.created_at.strftime('%H:%M') if last_msg else '',
            'last_date': last_msg.created_at.strftime('%Y-%m-%d') if last_msg else '',
            'unread': unread,
            'is_closed': c.is_closed,
        })
    return JsonResponse({'conversations': result})


def api_vendor_conversation_messages(request, conversation_id):
    """API: get messages for a vendor conversation."""
    vendor_id = request.session.get('vendor_id')
    if not vendor_id:
        return JsonResponse({'messages': [], 'error': 'not_logged_in'})
    convo = get_object_or_404(models.Conversation, pk=conversation_id, vendor_id=vendor_id)
    msgs = convo.direct_messages.order_by('created_at')
    msgs.filter(is_read=False).exclude(sender_type='vendor').update(is_read=True)
    result = []
    for m in msgs:
        result.append({
            'id': m.id,
            'sender_type': m.sender_type,
            'sender_name': m.sender_name,
            'content': m.content,
            'time': m.created_at.strftime('%H:%M'),
            'date': m.created_at.strftime('%Y-%m-%d'),
            'is_read': m.is_read,
        })
    buyer_name = convo.buyer.name if convo.buyer else 'Unknown'
    return JsonResponse({
        'messages': result,
        'conversation': {
            'id': convo.id,
            'buyer_name': buyer_name,
            'subject': convo.subject,
            'type': convo.conversation_type,
            'is_closed': convo.is_closed,
        }
    })


def vendor_send_message(request):
    """Vendor sends a message in a conversation."""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': 'Invalid method'})
    vendor_id = request.session.get('vendor_id')
    if not vendor_id:
        return JsonResponse({'success': False, 'message': '请先登录'}, status=401)
    conversation_id = request.POST.get('conversation_id')
    content = request.POST.get('content', '').strip()
    if not content:
        return JsonResponse({'success': False, 'message': '消息不能为空'})
    convo = get_object_or_404(models.Conversation, pk=conversation_id, vendor_id=vendor_id)
    vendor = get_object_or_404(models.Vendor, pk=vendor_id)
    msg = models.DirectMessage.objects.create(
        conversation=convo,
        sender_type='vendor',
        sender_name=vendor.company_name,
        content=content
    )
    convo.save(update_fields=['updated_at'])
    return JsonResponse({
        'success': True,
        'message': {
            'id': msg.id,
            'sender_type': 'vendor',
            'sender_name': vendor.company_name,
            'content': content,
            'time': msg.created_at.strftime('%H:%M'),
            'date': msg.created_at.strftime('%Y-%m-%d'),
        }
    })


def vendor_messages_page(request):
    """Vendor messaging dashboard page."""
    vendor_id = request.session.get('vendor_id')
    if not vendor_id:
        return redirect('manager:vendor_login')
    vendor = get_object_or_404(models.Vendor, pk=vendor_id)
    return render(request, 'public/vendor_messages.html', {'vendor': vendor})


def public_my_profile(request):
    """PWA 'My' tab — shows login prompt if not logged in, else full profile."""
    from django.db.models import Sum, Count
    user_id = request.session.get('site_user_id')
    if not user_id:
        return render(request, 'public/my_profile.html', {'site_user': None})
    try:
        user = models.SiteUser.objects.get(pk=user_id)
    except models.SiteUser.DoesNotExist:
        return render(request, 'public/my_profile.html', {'site_user': None})

    # Loyalty
    try:
        loyalty = models.LoyaltyPoints.objects.get(user=user)
    except Exception:
        loyalty = None

    # Orders
    orders = models.Order.objects.filter(customer_email=user.email).order_by('-created_at')[:5]

    # Followed shops
    followed_shops = models.UserFollowedShop.objects.filter(user=user).select_related('publisher')[:20]
    followed_vendors = models.UserFollowedVendor.objects.filter(user=user).select_related('vendor')[:20]

    # Wishlist books for feed
    from django.db.models import Q
    wishlist_books = models.Book.objects.filter(
        wishlist_items__user=user
    ).select_related('publisher')[:20]

    # Recent books feed
    feed_books = models.Book.objects.select_related('publisher').order_by('-id')[:20]

    context = {
        'site_user': user,
        'loyalty': loyalty,
        'orders': orders,
        'followed_shops': followed_shops,
        'followed_vendors': followed_vendors,
        'following_count': len(followed_shops) + len(followed_vendors),
        'wishlist_books': wishlist_books,
        'feed_books': feed_books,
    }
    return render(request, 'public/my_profile.html', context)


def follow_publisher(request, publisher_id):
    """AJAX: toggle follow/unfollow a publisher."""
    from django.http import JsonResponse
    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': '无效请求'})
    user_id = request.session.get('site_user_id')
    if not user_id:
        return JsonResponse({'success': False, 'message': '请先登录', 'login_required': True}, status=401)
    try:
        user = models.SiteUser.objects.get(pk=user_id)
        publisher = models.Publisher.objects.get(pk=publisher_id)
        follow_obj, created = models.UserFollowedShop.objects.get_or_create(
            user=user, publisher=publisher
        )
        if not created:
            follow_obj.delete()
            return JsonResponse({'success': True, 'following': False, 'message': f'已取消关注 {publisher.publisher_name}'})
        return JsonResponse({'success': True, 'following': True, 'message': f'已关注 {publisher.publisher_name}'})
    except models.Publisher.DoesNotExist:
        return JsonResponse({'success': False, 'message': '店铺不存在'}, status=404)
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)}, status=500)


def follow_vendor(request, vendor_id):
    """AJAX: toggle follow/unfollow a marketplace vendor."""
    from django.http import JsonResponse
    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': '无效请求'})
    user_id = request.session.get('site_user_id')
    if not user_id:
        return JsonResponse({'success': False, 'message': '请先登录', 'login_required': True}, status=401)
    try:
        user = models.SiteUser.objects.get(pk=user_id)
        vendor = models.Vendor.objects.get(pk=vendor_id, is_active=True)
        follow_obj, created = models.UserFollowedVendor.objects.get_or_create(
            user=user, vendor=vendor
        )
        if not created:
            follow_obj.delete()
            return JsonResponse({'success': True, 'following': False, 'message': f'已取消关注 {vendor.company_name}'})
        return JsonResponse({'success': True, 'following': True, 'message': f'已关注 {vendor.company_name}'})
    except models.Vendor.DoesNotExist:
        return JsonResponse({'success': False, 'message': '卖家不存在'}, status=404)
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)}, status=500)


def public_books(request):
    """Public book listing with search, category filter and pagination."""
    search_query = request.GET.get('search', request.GET.get('q', '')).strip()
    sort_by = request.GET.get('sort', 'name')
    if sort_by == 'new':
        sort_by = 'newest'
    category_slug = request.GET.get('category', '').strip()
    min_price = request.GET.get('min_price', '').strip()
    max_price = request.GET.get('max_price', '').strip()
    
    books = models.Book.objects.filter(is_active=True).select_related('publisher', 'category')
    
    if search_query:
        books = books.filter(
            Q(name__icontains=search_query) |
            Q(description__icontains=search_query) |
            Q(publisher__publisher_name__icontains=search_query)
        )
    if category_slug:
        books = books.filter(category__slug=category_slug)
    if min_price:
        try:
            books = books.filter(price__gte=min_price)
        except Exception:
            pass
    if max_price:
        try:
            books = books.filter(price__lte=max_price)
        except Exception:
            pass
    
    if sort_by == 'price_low':
        books = books.order_by('price')
    elif sort_by == 'price_high':
        books = books.order_by('-price')
    elif sort_by in ('popular', '-sale_num'):
        books = books.order_by('-sale_num')
    elif sort_by == 'newest':
        books = books.order_by('-id')
    else:
        books = books.order_by('name')
    
    paginator = Paginator(books, 20)
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)
    categories = models.BookCategory.objects.filter(is_active=True, parent__isnull=True)

    if request.GET.get('format') == 'json':
        data_books = []
        for book in page_obj:
            data_books.append({
                'id': book.id,
                'name': book.name,
                'price': str(book.price),
                'cover_url': book.get_cover_url(),
                'url': f'/manager/public/books/{book.id}/',
            })
        return JsonResponse({
            'books': data_books,
            'page': page_obj.number,
            'has_more': page_obj.has_next(),
        })

    context = {
        'books': page_obj,
        'page_obj': page_obj,
        'categories': categories,
        'search_query': search_query,
        'query': search_query,
        'sort_by': sort_by,
        'current_sort': sort_by,
        'current_category': category_slug,
        'active_category': category_slug,
        'min_price': min_price,
        'max_price': max_price,
    }
    return render(request, 'public/books.html', context)

def public_book_detail(request, book_id):
    """Public book detail view"""
    book = get_object_or_404(models.Book.objects.select_related('publisher', 'category'), id=book_id, is_active=True)
    authors = book.author_set.all()
    
    # Related books by same publisher
    related_books = models.Book.objects.filter(
        publisher=book.publisher
    ).exclude(id=book.id)[:4]
    
    context = {
        'book': book,
        'authors': authors,
        'related_books': related_books,
    }
    return render(request, 'public/book_detail.html', context)

def public_authors(request):
    """Public authors listing"""
    search_query = request.GET.get('search', '')
    
    authors = models.Author.objects.prefetch_related('book').all()
    
    if search_query:
        authors = authors.filter(name__icontains=search_query)
    
    authors = authors.order_by('name')

    # Use aggregate instead of per-author Python loop to avoid N+1
    from django.db.models import Count
    total_authors = authors.count()
    total_books = models.Book.objects.filter(author__in=authors).distinct().count()
    
    paginator = Paginator(authors, 20)
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)

    context = {
        'authors': page_obj,
        'page_obj': page_obj,
        'search_query': search_query,
        'total_authors': total_authors,
        'total_books': total_books,
    }
    return render(request, 'public/authors.html', context)

def public_author_detail(request, author_id):
    """Public author detail view"""
    author = get_object_or_404(models.Author, id=author_id)
    # Fix: Use 'book' instead of 'book_set' for ManyToMany relationship
    books = author.book.select_related('publisher').all()
    
    # Calculate statistics
    total_sales = sum(book.sale_num for book in books)
    total_inventory = sum(book.inventory for book in books)
    avg_price = sum(book.price for book in books) / len(books) if books else 0
    
    context = {
        'author': author,
        'books': books,
        'total_sales': total_sales,
        'total_inventory': total_inventory,
        'avg_price': avg_price,
    }
    return render(request, 'public/author_detail.html', context)

def public_publishers(request):
    """Public publishers listing"""
    search_query = request.GET.get('search', '')
    
    publishers = models.Publisher.objects.all()
    
    if search_query:
        publishers = publishers.filter(publisher_name__icontains=search_query)
    
    publishers = publishers.order_by('publisher_name')

    # Use aggregate instead of per-publisher Python loop to avoid N+1
    from django.db.models import Count
    total_publishers = publishers.count()
    total_books = models.Book.objects.filter(publisher__in=publishers).count()
    
    paginator = Paginator(publishers, 20)
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)

    context = {
        'publishers': page_obj,
        'page_obj': page_obj,
        'search_query': search_query,
        'total_publishers': total_publishers,
        'total_books': total_books,
    }
    return render(request, 'public/publishers.html', context)

def public_publisher_detail(request, publisher_id):
    """Public publisher detail view"""
    publisher = get_object_or_404(models.Publisher, id=publisher_id)
    books = models.Book.objects.filter(publisher=publisher).order_by('name')
    
    # Calculate statistics
    total_sales = sum(book.sale_num for book in books)
    total_inventory = sum(book.inventory for book in books)
    avg_price = sum(book.price for book in books) / len(books) if books else 0
    total_revenue = sum(book.price * book.sale_num for book in books)
    
    # Count unique authors
    author_count = models.Author.objects.filter(book__publisher=publisher).distinct().count()
    
    context = {
        'publisher': publisher,
        'books': books,
        'total_sales': total_sales,
        'total_inventory': total_inventory,
        'avg_price': avg_price,
        'total_revenue': total_revenue,
        'author_count': author_count,
    }
    return render(request, 'public/publisher_detail.html', context)

# ==================== E-COMMERCE FUNCTIONALITY ====================

def get_session_key(request):
    """Get or create session key for cart functionality"""
    if not request.session.session_key:
        request.session.create()
    return request.session.session_key


def _get_marketplace_item(item_type, item_id):
    """Helper to resolve a marketplace item from its type and ID."""
    if item_type == 'product':
        return Product.objects.filter(pk=item_id, is_active=True).first()
    elif item_type == 'course':
        return Course.objects.filter(pk=item_id, is_active=True).first()
    elif item_type == 'supermarket':
        return SupermarketItem.objects.filter(pk=item_id, is_active=True).first()
    return None


def _get_marketplace_attribute_context(item):
    if not item or not hasattr(item, 'attributes'):
        return {'groups': [], 'selectable_groups': [], 'specification_groups': []}
    return build_attribute_groups(item.attributes.all())


def _build_unified_cart(session_key):
    """Build a unified cart list merging books and marketplace items."""
    items = []

    # Book cart items
    book_items = models.CartItem.objects.filter(session_key=session_key).select_related('book', 'book__publisher')
    for ci in book_items:
        items.append({
            'id': ci.id,
            'item_type': 'book',
            'item_id': ci.book.id,
            'name': ci.book.name,
            'price': ci.book.price,
            'quantity': ci.quantity,
            'image_url': ci.book.get_cover_url() if hasattr(ci.book, 'get_cover_url') else (ci.book.cover_image.url if ci.book.cover_image else ''),
            'total_price': ci.get_total_price(),
            'publisher': ci.book.publisher.publisher_name if ci.book.publisher else '',
            'inventory': ci.book.inventory,
            'item_obj': ci.book,
            'cart_item': ci,
        })

    # Marketplace cart items
    mkt_items = MarketplaceCartItem.objects.filter(session_key=session_key).order_by('-created_at')
    for ci in mkt_items:
        item = ci.get_item()
        if item:
            items.append({
                'id': ci.id,
                'item_type': ci.item_type,
                'item_id': ci.item_id,
                'name': ci.get_item_name(),
                'price': ci.get_item_price(),
                'quantity': ci.quantity,
                'image_url': ci.get_item_image_url(),
                'total_price': ci.get_total_price(),
                'publisher': getattr(item, 'brand', '') or '',
                'inventory': getattr(item, 'stock', 999),
                'item_obj': item,
                'cart_item': ci,
                'selected_attributes': ci.selected_attributes or {},
                'selected_attribute_list': ci.get_selected_attributes_display(),
            })

    return items


@require_POST
def add_to_cart(request, book_id):
    """Add book to shopping cart"""
    try:
        book = get_object_or_404(models.Book, id=book_id)
        quantity = int(request.POST.get('quantity', 1))
        session_key = get_session_key(request)
        
        # Validate quantity
        if quantity > book.inventory:
            return JsonResponse({
                'success': False,
                'message': f'库存不足！当前库存：{book.inventory}本'
            })
        
        # Get or create cart item
        cart_item, created = models.CartItem.objects.get_or_create(
            session_key=session_key,
            book=book,
            defaults={'quantity': quantity}
        )
        
        if not created:
            new_quantity = cart_item.quantity + quantity
            if new_quantity > book.inventory:
                return JsonResponse({
                    'success': False,
                    'message': f'库存不足！当前库存：{book.inventory}本，购物车中已有：{cart_item.quantity}本'
                })
            cart_item.quantity = new_quantity
            cart_item.save()
        
        # Get total unified cart count
        cart_count = _get_unified_cart_count(session_key)
        
        return JsonResponse({
            'success': True,
            'message': f'已将《{book.name}》添加到购物车',
            'cart_count': cart_count,
            'item_quantity': cart_item.quantity
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': '添加到购物车失败，请重试'
        })


@require_POST
def add_marketplace_item_to_cart(request):
    """Add marketplace item (product/course/supermarket) to unified cart."""
    try:
        item_type = request.POST.get('item_type')
        item_id = int(request.POST.get('item_id'))
        quantity = int(request.POST.get('quantity', 1))
        session_key = get_session_key(request)

        if item_type not in ('product', 'course', 'supermarket'):
            return JsonResponse({'success': False, 'message': '无效的商品类型'})

        item = _get_marketplace_item(item_type, item_id)
        if not item:
            return JsonResponse({'success': False, 'message': '商品不存在或已下架'})

        # Validate stock
        if item_type in ('product', 'supermarket') and quantity > item.stock:
            return JsonResponse({'success': False, 'message': f'库存不足！当前库存：{item.stock}'})
        if item_type == 'course':
            quantity = 1

        selected_attributes = {}
        if item_type in ('product', 'supermarket'):
            validation = validate_selected_attributes(
                _get_marketplace_attribute_context(item),
                request.POST.get('selected_attributes', '{}')
            )
            if not validation['is_valid']:
                return JsonResponse({'success': False, 'message': validation['errors'][0]})
            selected_attributes = validation['cleaned']

        item_name = item.title if item_type == 'course' else item.name

        cart_item = MarketplaceCartItem.objects.filter(
            session_key=session_key,
            item_type=item_type,
            item_id=item_id,
            selected_attributes=selected_attributes,
        ).first()
        created = cart_item is None
        if created:
            cart_item = MarketplaceCartItem.objects.create(
                session_key=session_key,
                item_type=item_type,
                item_id=item_id,
                quantity=quantity,
                selected_attributes=selected_attributes,
            )

        if not created:
            if item_type == 'course':
                return JsonResponse({'success': False, 'message': '该课程已在购物车中'})
            new_qty = cart_item.quantity + quantity
            if item_type in ('product', 'supermarket') and new_qty > item.stock:
                return JsonResponse({'success': False, 'message': f'库存不足！购物车已有{cart_item.quantity}件'})
            cart_item.quantity = new_qty
            cart_item.save()

        cart_count = _get_unified_cart_count(session_key)
        return JsonResponse({
            'success': True,
            'message': f'已将「{item_name}」添加到购物车',
            'cart_count': cart_count,
        })
    except Exception as e:
        return JsonResponse({'success': False, 'message': '添加失败，请重试'})


def _get_unified_cart_count(session_key):
    """Get total count of items in both carts."""
    book_count = models.CartItem.objects.filter(session_key=session_key).count()
    mkt_count = MarketplaceCartItem.objects.filter(session_key=session_key).count()
    return book_count + mkt_count


@ensure_csrf_cookie
def view_cart(request):
    """Display unified shopping cart (books + marketplace)"""
    session_key = get_session_key(request)
    unified_items = _build_unified_cart(session_key)
    
    total_amount = sum(item['total_price'] for item in unified_items)
    total_items = sum(item['quantity'] for item in unified_items)
    
    context = {
        'cart_items': unified_items,
        'total_amount': total_amount,
        'total_items': total_items,
    }
    
    return render(request, 'public/cart.html', context)

@require_POST
def update_cart(request):
    """Update cart item quantities via AJAX - handles both books and marketplace items"""
    try:
        data = json.loads(request.body)
        item_id = data.get('item_id')
        item_type = data.get('item_type', 'book')
        quantity = int(data.get('quantity', 1))
        session_key = get_session_key(request)
        
        item_name = ''

        if item_type == 'book':
            cart_item = get_object_or_404(models.CartItem, id=item_id, session_key=session_key)
            if quantity > cart_item.book.inventory:
                return JsonResponse({
                    'success': False,
                    'message': f'库存不足！最大可购买：{cart_item.book.inventory}本'
                })
            item_name = cart_item.book.name
            if quantity <= 0:
                cart_item.delete()
            else:
                cart_item.quantity = quantity
                cart_item.save()
            item_total = float(cart_item.get_total_price()) if quantity > 0 else 0
        else:
            cart_item = MarketplaceCartItem.objects.filter(
                id=item_id, session_key=session_key
            ).first()
            if not cart_item:
                return JsonResponse({'success': False, 'message': '商品不在购物车中'})

            item = cart_item.get_item()
            if item_type in ('product', 'supermarket') and item and quantity > item.stock:
                return JsonResponse({'success': False, 'message': f'库存不足！最大可购买：{item.stock}'})
            
            item_name = cart_item.get_item_name()
            if quantity <= 0:
                cart_item.delete()
            else:
                cart_item.quantity = quantity
                cart_item.save()
            item_total = float(cart_item.get_total_price()) if quantity > 0 else 0
        
        # Recalculate unified totals
        unified_items = _build_unified_cart(session_key)
        total_amount = sum(i['total_price'] for i in unified_items)
        total_items = sum(i['quantity'] for i in unified_items)
        
        message = f'已更新「{item_name}」数量' if quantity > 0 else f'已移除「{item_name}」'
        
        return JsonResponse({
            'success': True,
            'message': message,
            'item_total': item_total,
            'cart_total': float(total_amount),
            'total_items': total_items
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': '更新购物车失败'
        })

def remove_from_cart(request, item_id):
    """Remove item from cart - handles both books and marketplace items"""
    session_key = get_session_key(request)
    item_type = request.POST.get('item_type', request.GET.get('item_type', 'book'))

    item_name = ''
    if item_type == 'book':
        cart_item = get_object_or_404(models.CartItem, id=item_id, session_key=session_key)
        item_name = cart_item.book.name
        cart_item.delete()
    else:
        cart_item = MarketplaceCartItem.objects.filter(
            id=item_id, session_key=session_key
        ).first()
        if cart_item:
            item_name = cart_item.get_item_name()
            cart_item.delete()

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.method == 'POST':
        unified_items = _build_unified_cart(session_key)
        total_amount = sum(i['total_price'] for i in unified_items)
        total_items = sum(i['quantity'] for i in unified_items)
        cart_count = len(unified_items)
        return JsonResponse({
            'success': True,
            'message': f'已移除「{item_name}」',
            'cart_total': float(total_amount),
            'total_items': total_items,
            'cart_count': cart_count,
        })

    messages.success(request, f'已移除「{item_name}」')
    return redirect('manager:view_cart')


def clear_cart(request):
    """Clear all items from both carts"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Method not allowed'}, status=405)
    session_key = get_session_key(request)
    models.CartItem.objects.filter(session_key=session_key).delete()
    MarketplaceCartItem.objects.filter(session_key=session_key).delete()
    return JsonResponse({'success': True, 'message': '购物车已清空'})

def get_cart_count(request):
    """Get unified cart item count"""
    session_key = get_session_key(request)
    cart_count = _get_unified_cart_count(session_key)
    return JsonResponse({'cart_count': cart_count})

@require_POST
def buy_now(request, book_id):
    """Direct purchase without cart"""
    try:
        book = get_object_or_404(models.Book, id=book_id)
        quantity = int(request.POST.get('quantity', 1))
        session_key = get_session_key(request)
        
        if quantity > book.inventory:
            messages.error(request, f'库存不足！当前库存：{book.inventory}本')
            return redirect('manager:public_book_detail', book_id=book_id)
        
        # Clear book cart items only
        models.CartItem.objects.filter(session_key=session_key).delete()
        MarketplaceCartItem.objects.filter(session_key=session_key).delete()
        
        models.CartItem.objects.create(
            session_key=session_key,
            book=book,
            quantity=quantity
        )
        
        return redirect('manager:checkout')
        
    except Exception as e:
        messages.error(request, '购买失败，请重试')
        return redirect('manager:public_book_detail', book_id=book_id)

def checkout(request):
    """Unified checkout - handles books and marketplace items together"""
    session_key = get_session_key(request)
    unified_items = _build_unified_cart(session_key)
    
    if not unified_items:
        messages.warning(request, '购物车为空，请先添加商品')
        return redirect('manager:public_books')
    
    # Separate items by type
    book_items = [i for i in unified_items if i['item_type'] == 'book']
    marketplace_items = [i for i in unified_items if i['item_type'] != 'book']
    
    # Calculate totals - books use actual price, marketplace uses item price
    total_amount = sum(i['total_price'] for i in unified_items)
    total_items_count = sum(i['quantity'] for i in unified_items)
    
    if request.method == 'POST':
        try:
            payment_confirmed = request.POST.get('payment_confirmed', 'no')
            if payment_confirmed == 'yes':
                initial_status = 'processing'
                payment_status = 'pending'
            else:
                initial_status = 'payment_pending'
                payment_status = 'pending'
            
            customer_name = request.POST.get('customer_name')
            customer_email = request.POST.get('customer_email')
            customer_phone = request.POST.get('customer_phone')
            country = request.POST.get('country', 'China')
            payment_method = request.POST.get('payment_method')
            customer_notes = request.POST.get('customer_notes', '')

            available_methods = {
                option['method']
                for region_options in build_payment_options(country).values()
                for option in region_options
            }
            if payment_method not in available_methods:
                messages.error(request, '当前国家暂不支持该支付方式，请重新选择。')
                return redirect('manager:checkout')

            book_order = None
            mkt_order = None

            # Create book order if there are book items
            if book_items:
                book_total = sum(i['total_price'] for i in book_items)
                book_order = models.Order.objects.create(
                    customer_name=customer_name,
                    customer_email=customer_email,
                    customer_phone=customer_phone,
                    country=country,
                    payment_method=payment_method,
                    total_amount=book_total,
                    status=initial_status,
                    payment_status=payment_status,
                    customer_notes=customer_notes
                )
                for item in book_items:
                    models.OrderItem.objects.create(
                        order=book_order,
                        book=item['item_obj'],
                        quantity=item['quantity'],
                        unit_price=item['price'],
                        total_price=item['total_price']
                    )
                    book = item['item_obj']
                    book.inventory -= item['quantity']
                    book.sale_num += item['quantity']
                    book.save()
                
                # Clear book cart
                models.CartItem.objects.filter(session_key=session_key).delete()
                
                create_notification(
                    'new_order',
                    f'新订单 {book_order.order_number}',
                    f'{book_order.customer_name} 下了一个新订单，共 ¥{book_order.total_amount}',
                    icon='fas fa-shopping-bag',
                    color='#10b981',
                    link=f'/manager/order_detail/{book_order.id}/',
                    related_id=book_order.id,
                )

            # Create marketplace order if there are marketplace items
            if marketplace_items:
                mkt_total = sum(i['total_price'] for i in marketplace_items)
                mkt_order = MarketplaceOrder(
                    user_name=customer_name,
                    user_email=customer_email,
                    customer_phone=customer_phone,
                    country=country,
                    payment_method=payment_method,
                    total_amount=mkt_total,
                    status=initial_status,
                    payment_status=payment_status,
                    shipping_address=request.POST.get('shipping_address', ''),
                    notes=customer_notes,
                    customer_notes=customer_notes,
                )
                mkt_order.save()

                for item in marketplace_items:
                    MarketplaceOrderItem.objects.create(
                        order=mkt_order,
                        item_type=item['item_type'],
                        item_id=item['item_id'],
                        item_name=item['name'],
                        item_image=item['image_url'],
                        quantity=item['quantity'],
                        unit_price=item['price'],
                        selected_attributes=item.get('selected_attributes', {}),
                    )
                    # Update stock/sales
                    obj = item['item_obj']
                    if item['item_type'] == 'product':
                        obj.stock = max(0, obj.stock - item['quantity'])
                        obj.sales_count += item['quantity']
                        obj.save()
                    elif item['item_type'] == 'supermarket':
                        obj.stock = max(0, obj.stock - item['quantity'])
                        obj.sales_count += item['quantity']
                        obj.save()
                    elif item['item_type'] == 'course':
                        obj.enrollment_count += 1
                        obj.save()
                
                # Clear marketplace cart
                MarketplaceCartItem.objects.filter(session_key=session_key).delete()

            # Grant access via session before redirecting
            if book_order:
                _accessible = request.session.get('accessible_orders', [])
                _order_key = str(book_order.order_number)
                if _order_key not in _accessible:
                    _accessible.append(_order_key)
                request.session['accessible_orders'] = _accessible
                return redirect('manager:order_confirmation', order_number=book_order.order_number)
            elif mkt_order:
                _accessible = request.session.get('accessible_orders', [])
                _order_key = str(mkt_order.order_number)
                if _order_key not in _accessible:
                    _accessible.append(_order_key)
                request.session['accessible_orders'] = _accessible
                return redirect('manager:order_confirmation', order_number=mkt_order.order_number)
            
        except Exception as e:
            messages.error(request, '订单创建失败，请重试')
    
    payment_methods_by_region = build_payment_options()

    context = {
        'cart_items': unified_items,
        'book_items': book_items,
        'marketplace_items': marketplace_items,
        'total_amount': total_amount,
        'total_items': total_items_count,
        'payment_methods_by_region': payment_methods_by_region,
    }
    
    return render(request, 'public/checkout.html', context)

def order_confirmation(request, order_number):
    """Order confirmation page - handles both book and marketplace orders"""
    # Ownership check: order_number must be in the session's accessible list
    # (granted at checkout or after email-verified track_order lookup).
    accessible = request.session.get('accessible_orders', [])
    if str(order_number) not in accessible:
        messages.warning(request, '请通过订单查询验证您的身份后查看订单详情')
        return redirect('manager:track_order')
    book_order = None
    book_order_items = []
    mkt_order = None
    mkt_order_items = []

    # Try book order first
    try:
        book_order = models.Order.objects.get(order_number=order_number)
        book_order_items = models.OrderItem.objects.filter(order=book_order).select_related('book')
    except models.Order.DoesNotExist:
        pass

    # Try marketplace order
    if not book_order:
        try:
            mkt_order = MarketplaceOrder.objects.get(order_number=order_number)
            mkt_order_items = mkt_order.items.all()
        except MarketplaceOrder.DoesNotExist:
            pass

    if not book_order and not mkt_order:
        messages.error(request, '订单不存在')
        return redirect('manager:public_home')

    resolved_order = book_order or mkt_order
    payment_time_remaining = None
    payment_time_remaining_seconds = 0
    if hasattr(resolved_order, 'get_payment_time_remaining'):
        payment_time_remaining = resolved_order.get_payment_time_remaining()
        if payment_time_remaining:
            payment_time_remaining_seconds = max(int(payment_time_remaining.total_seconds()), 0)

    context = {
        'order': resolved_order,
        'book_order': book_order,
        'book_order_items': book_order_items,
        'mkt_order': mkt_order,
        'mkt_order_items': mkt_order_items,
        'order_items': book_order_items,  # backward compat
        'payment_time_remaining_seconds': payment_time_remaining_seconds,
    }
    
    return render(request, 'public/order_confirmation.html', context)

def track_order(request):
    """Order tracking page - Search by order number or email"""
    order = None
    orders = None
    mkt_order = None
    mkt_orders = None
    has_downloadable_books = False
    
    if request.method == 'POST':
        search_type = request.POST.get('search_type', 'order_number')
        
        if search_type == 'email':
            # Search by email - return all orders from both systems
            customer_email = request.POST.get('customer_email')
            if customer_email:
                orders = models.Order.objects.filter(
                    customer_email=customer_email
                ).order_by('-created_at')
                
                # Also search marketplace orders
                try:
                    mkt_orders = MarketplaceOrder.objects.filter(
                        user_email=customer_email
                    ).order_by('-created_at')
                    if not mkt_orders.exists():
                        mkt_orders = None
                except Exception:
                    mkt_orders = None
                
                if not orders.exists() and not mkt_orders:
                    messages.error(request, f'未找到与邮箱 {customer_email} 相关的订单')
                    orders = None
                else:
                    # Grant session access to all orders verified by email
                    _accessible = request.session.get('accessible_orders', [])
                    for _o in (orders if orders.exists() else []):
                        if str(_o.order_number) not in _accessible:
                            _accessible.append(str(_o.order_number))
                    for _o in (mkt_orders or []):
                        if str(_o.order_number) not in _accessible:
                            _accessible.append(str(_o.order_number))
                    request.session['accessible_orders'] = _accessible
        else:
            # Search by order number - return single order
            order_number = request.POST.get('order_number')
            if order_number:
                # Try book order first
                try:
                    order = models.Order.objects.get(order_number=order_number)
                    # Check if payment window expired and auto-cancel
                    if order.status == 'payment_pending':
                        order.auto_cancel_if_expired()

                    # Grant session access for order found by order_number
                    _accessible = request.session.get('accessible_orders', [])
                    if str(order.order_number) not in _accessible:
                        _accessible.append(str(order.order_number))
                    request.session['accessible_orders'] = _accessible

                    # Check if any books have downloads available
                    has_downloadable_books = any(
                        item.book.has_download 
                        for item in order.orderitem_set.all()
                    )
                except models.Order.DoesNotExist:
                    # Try marketplace order
                    try:
                        mkt_order = MarketplaceOrder.objects.get(order_number=order_number)
                        if mkt_order.status in ['pending', 'payment_pending']:
                            mkt_order.auto_cancel_if_expired()
                    except MarketplaceOrder.DoesNotExist:
                        messages.error(request, '订单号不存在')
    
    context = {
        'order': order,
        'orders': orders,
        'mkt_order': mkt_order,
        'mkt_orders': mkt_orders,
        'has_downloadable_books': has_downloadable_books
    }
    return render(request, 'public/track_order.html', context)

def download_book(request, order_id, book_id):
    """Download purchased ebook - supports files and external links"""
    import os

    # Verify order and book
    order = get_object_or_404(models.Order, id=order_id)
    book = get_object_or_404(models.Book, id=book_id)

    # Ownership check — order_number must be in session's accessible list
    accessible = request.session.get('accessible_orders', [])
    if str(order.order_number) not in accessible:
        messages.error(request, '您没有权限下载此文件，请先通过订单查询验证您的身份')
        return redirect('manager:track_order')
    
    # Check if order status allows download (shipped or delivered means payment is done)
    valid_statuses = ['paid', 'confirmed', 'processing', 'shipped', 'delivered']
    if order.status not in valid_statuses:
        messages.error(request, '订单尚未完成支付，无法下载')
        return redirect('manager:order_confirmation', order_number=order.order_number)
    
    # Additional check: if status is shipped/delivered, payment must be completed
    # (For backwards compatibility, we allow download if status is shipped regardless of payment_status)
    if order.status not in ['shipped', 'delivered'] and order.payment_status != 'completed':
        messages.error(request, '订单支付未完成，无法下载')
        return redirect('manager:order_confirmation', order_number=order.order_number)
    
    # Check if this book is in the order
    order_item = models.OrderItem.objects.filter(order=order, book=book).first()
    if not order_item:
        messages.error(request, '此订单不包含该图书')
        return redirect('manager:order_confirmation', order_number=order.order_number)
    
    # Check if book has download available
    if not book.has_download():
        messages.error(request, '该图书暂无下载文件')
        return redirect('manager:order_confirmation', order_number=order.order_number)
    
    # If book has a file, serve it directly
    if book.book_file:
        try:
            response = FileResponse(book.book_file.open('rb'))
            file_name = os.path.basename(book.book_file.name)
            response['Content-Disposition'] = f'attachment; filename="{file_name}"'
            return response
        except Exception as e:
            messages.error(request, f'文件下载失败: {str(e)}')
            return redirect('manager:order_confirmation', order_number=order.order_number)
    
    # If book has external download link, redirect to it
    elif book.download_link:
        return redirect(book.download_link)
    
    # Fallback: Create a placeholder PDF with book information
    try:
        from reportlab.pdfgen import canvas
        from reportlab.lib.pagesizes import letter
        from io import BytesIO
        
        buffer = BytesIO()
        p = canvas.Canvas(buffer, pagesize=letter)
        
        # Add content to PDF
        p.setFont("Helvetica-Bold", 24)
        p.drawString(100, 750, f"{book.name}")
        
        p.setFont("Helvetica", 12)
        p.drawString(100, 720, f"Publisher: {book.publisher.publisher_name}")
        p.drawString(100, 700, f"Order Number: {order.order_number}")
        p.drawString(100, 680, f"Customer: {order.customer_name}")
        
        p.setFont("Helvetica-Oblique", 10)
        p.drawString(100, 650, "Thank you for your purchase!")
        p.drawString(100, 630, "This is a sample ebook file.")
        p.drawString(100, 610, "Please contact support to get the actual ebook file.")
        
        p.showPage()
        p.save()
        
        buffer.seek(0)
        
        response = FileResponse(buffer, content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="{book.name}.pdf"'
        
        return response
        
    except ImportError:
        # If reportlab is not installed, return a simple text file
        content = f"""
        电子书信息
        ==========
        
        书名: {book.name}
        出版社: {book.publisher.publisher_name}
        订单号: {order.order_number}
        客户: {order.customer_name}
        
        感谢您的购买！
        
        注意: 这是一个示例文件。实际生产环境中，这里应该提供真实的电子书文件。
        """
        
        response = HttpResponse(content, content_type='text/plain; charset=utf-8')
        response['Content-Disposition'] = f'attachment; filename="{book.name}.txt"'
        return response


# ====================   API Views for Order Actions  ===========================
def api_cancel_order(request):
    """API endpoint to cancel an order"""
    from django.http import JsonResponse
    import json
    
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            order_number = data.get('order_number')
            
            order = models.Order.objects.get(order_number=order_number)
            
            # Only allow cancellation for pending or payment_pending orders
            if order.status in ['pending', 'payment_pending']:
                order.status = 'cancelled'
                order.save()
                return JsonResponse({'success': True, 'message': '订单已取消'})
            else:
                return JsonResponse({'success': False, 'message': '此订单状态无法取消'})
                
        except models.Order.DoesNotExist:
            return JsonResponse({'success': False, 'message': '订单不存在'})
        except Exception as e:
            return JsonResponse({'success': False, 'message': str(e)})
    
    return JsonResponse({'success': False, 'message': '无效请求'})


def api_confirm_payment(request):
    """API endpoint to confirm payment"""
    from django.http import JsonResponse
    import json
    
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            order_number = data.get('order_number')
            
            order = models.Order.objects.get(order_number=order_number)
            
            # Update order status to processing
            if order.status == 'payment_pending':
                order.status = 'processing'
                order.payment_status = 'pending'
                order.save()
                create_notification(
                    'order_paid',
                    f'订单 {order.order_number} 确认付款',
                    f'{order.customer_name} 确认了订单付款，金额 ¥{order.total_amount}',
                    icon='fas fa-credit-card',
                    color='#10b981',
                    link=f'/manager/order_detail/{order.id}/',
                    related_id=order.id,
                )
                return JsonResponse({'success': True, 'message': '支付确认成功'})
            else:
                return JsonResponse({'success': False, 'message': '订单状态无法确认支付'})
                
        except models.Order.DoesNotExist:
            return JsonResponse({'success': False, 'message': '订单不存在'})
        except Exception as e:
            return JsonResponse({'success': False, 'message': str(e)})
    
    return JsonResponse({'success': False, 'message': '无效请求'})


def api_home_feed(request):
    """Paginated feed API for infinite scroll on homepage.
    Returns mixed books + products, 12 per page."""
    try:
        page = max(1, int(request.GET.get('page', 1)))
    except ValueError:
        page = 1
    feed_type = request.GET.get('feed', 'mixed')
    PER_PAGE = 12
    offset = (page - 1) * PER_PAGE

    items = []
    # Books
    book_limit = PER_PAGE if feed_type == 'books' else PER_PAGE // 2
    book_count = models.Book.objects.filter(is_active=True).count()
    book_offset = offset % book_count if book_count else 0
    books_qs = models.Book.objects.filter(is_active=True).select_related('publisher').order_by('-sale_num')
    books = list(books_qs[book_offset:book_offset + book_limit])
    if book_count and len(books) < book_limit:
        books += list(books_qs[:book_limit - len(books)])
    for b in books:
        items.append({
            'type': 'book',
            'type_label': '图书',
            'name': b.name[:30],
            'price': str(b.price),
            'image': b.get_cover_url(),
            'url': f'/manager/public/books/{b.id}/',
        })

    if feed_type != 'books':
        try:
            from marketplace.models import Product
            product_limit = PER_PAGE // 2
            product_qs = Product.objects.filter(is_active=True).order_by('-sales_count')
            product_count = product_qs.count()
            product_offset = offset % product_count if product_count else 0
            products = list(product_qs[product_offset:product_offset + product_limit])
            if product_count and len(products) < product_limit:
                products += list(product_qs[:product_limit - len(products)])
            for p in products:
                items.append({
                    'type': 'product',
                    'type_label': '商品',
                    'name': p.name[:30],
                    'price': str(p.price),
                    'image': p.get_image_url(),
                    'url': f'/marketplace/products/{p.slug}/',
                })
        except Exception:
            pass

    return JsonResponse({'items': items, 'page': page, 'has_more': len(items) > 0})


def api_unified_search(request):
    """Unified search across books, products, courses, and supermarket items."""
    query = request.GET.get('q', '').strip()
    if not query:
        return JsonResponse({'results': [], 'query': '', 'total': 0, 'suggestions': []})

    from marketplace.models import Product, Course, SupermarketItem, Category as MktCategory
    results = []
    MAX_PER_TYPE = 8

    books = models.Book.objects.filter(
        Q(name__icontains=query) | Q(description__icontains=query) |
        Q(publisher__publisher_name__icontains=query) |
        Q(category__name__icontains=query),
        is_active=True
    ).select_related('publisher', 'category')[:MAX_PER_TYPE]
    for b in books:
        results.append({
            'type': 'book', 'type_label': '图书',
            'name': b.name, 'price': str(b.price),
            'image': b.get_cover_url(),
            'url': f'/manager/public/books/{b.id}/',
            'desc': (b.description or '')[:80],
        })

    products = Product.objects.filter(
        Q(name__icontains=query) | Q(description__icontains=query) |
        Q(category__name__icontains=query),
        is_active=True
    ).select_related('category')[:MAX_PER_TYPE]
    for p in products:
        results.append({
            'type': 'product', 'type_label': '商品',
            'name': p.name, 'price': str(p.price),
            'image': p.get_image_url(),
            'url': f'/marketplace/products/{p.slug}/',
            'desc': (p.description or '')[:80],
        })

    courses = Course.objects.filter(
        Q(title__icontains=query) | Q(description__icontains=query),
        is_active=True
    )[:MAX_PER_TYPE]
    for c in courses:
        results.append({
            'type': 'course', 'type_label': '课程',
            'name': c.title, 'price': str(c.price),
            'image': c.get_image_url(),
            'url': f'/marketplace/courses/{c.slug}/',
            'desc': (c.description or '')[:80],
        })

    supermarket = SupermarketItem.objects.filter(
        Q(name__icontains=query) | Q(description__icontains=query) |
        Q(category__name__icontains=query),
        is_active=True
    ).select_related('category')[:MAX_PER_TYPE]
    for s in supermarket:
        results.append({
            'type': 'supermarket', 'type_label': '超市',
            'name': s.name, 'price': str(s.price),
            'image': s.get_image_url(),
            'url': f'/marketplace/supermarket/{s.slug}/',
            'desc': (s.description or '')[:80],
        })

    suggestions = []
    if not results:
        suggest_books = models.Book.objects.filter(is_active=True).order_by('-sale_num')[:4]
        suggest_products = Product.objects.filter(is_active=True).order_by('-sales_count')[:4]
        for b in suggest_books:
            suggestions.append({
                'type': 'book', 'type_label': '图书',
                'name': b.name, 'price': str(b.price),
                'image': b.get_cover_url(),
                'url': f'/manager/public/books/{b.id}/',
            })
        for p in suggest_products:
            suggestions.append({
                'type': 'product', 'type_label': '商品',
                'name': p.name, 'price': str(p.price),
                'image': p.get_image_url(),
                'url': f'/marketplace/products/{p.slug}/',
            })

    return JsonResponse({
        'results': results,
        'query': query,
        'total': len(results),
        'suggestions': suggestions,
    })


def public_search(request):
    """Full-page unified search results."""
    query = request.GET.get('q', '').strip()
    return render(request, 'public/search_results.html', {'query': query})


def api_spin_wheel(request):
    """Daily spin wheel — awards 10-100 random points once per day per user."""
    import random
    from datetime import date

    if not request.session.get('site_user_id'):
        return JsonResponse({'success': False, 'message': '请先登录', 'code': 'login_required'})

    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': '无效请求'})

    user_id = request.session['site_user_id']
    try:
        user = models.SiteUser.objects.get(pk=user_id)
        loyalty, created = models.LoyaltyPoints.objects.get_or_create(user=user)

        today = date.today()
        if loyalty.last_spin == today:
            return JsonResponse({'success': False, 'message': '今天已经转过了，明天再来！', 'code': 'already_spun'})

        pts = random.choice([10, 20, 30, 50, 80, 100])
        loyalty.points_balance += pts
        loyalty.lifetime_points += pts
        loyalty.last_spin = today
        loyalty.update_tier()
        loyalty.save()

        models.PointTransaction.objects.create(
            user=user, points=pts, reason='daily_spin',
            description=f'每日转盘获得 {pts} 积分'
        )
        return JsonResponse({
            'success': True,
            'points_won': pts,
            'new_balance': loyalty.points_balance,
            'tier': loyalty.get_tier_display(),
        })
    except models.SiteUser.DoesNotExist:
        return JsonResponse({'success': False, 'message': '用户不存在'})
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)})


# ====================   订单管理模块  ===========================
def order_list(request):
    """Admin order list view"""
    # 登录判断
    if "name" not in request.session:
        return redirect("/manager/login")
    
    # Get filter parameters
    status_filter = request.GET.get('status', '')
    payment_status_filter = request.GET.get('payment_status', '')
    search_query = request.GET.get('search', '')
    
    # Start with all orders
    orders = models.Order.objects.all().select_related().prefetch_related('orderitem_set__book')
    
    # Apply filters
    if status_filter:
        orders = orders.filter(status=status_filter)
    if payment_status_filter:
        orders = orders.filter(payment_status=payment_status_filter)
    if search_query:
        orders = orders.filter(
            Q(order_number__icontains=search_query) |
            Q(customer_name__icontains=search_query) |
            Q(customer_email__icontains=search_query) |
            Q(customer_phone__icontains=search_query)
        )
      # Order by creation date (newest first)
    orders = orders.order_by('-created_at')
    
    # Get statistics
    total_orders = models.Order.objects.count()
    pending_orders = models.Order.objects.filter(status='pending').count()
    completed_orders = models.Order.objects.filter(payment_status='completed').count()
    total_revenue = models.Order.objects.filter(payment_status='completed').aggregate(
        total=Sum('total_amount')
    )['total'] or 0
    
    context = {
        'orders': orders,
        'name': request.session["name"],
        'status_choices': models.ORDER_STATUS_CHOICES,
        'payment_status_choices': models.PAYMENT_STATUS_CHOICES,
        'current_status_filter': status_filter,
        'current_payment_status_filter': payment_status_filter,
        'current_search': search_query,
        'total_orders': total_orders,
        'pending_orders': pending_orders,
        'completed_orders': completed_orders,
        'total_revenue': total_revenue,
    }
    
    return render(request, 'order/order_list.html', context)


def order_detail(request, order_id):
    """Admin order detail view"""
    # 登录判断
    if "name" not in request.session:
        return redirect("/manager/login")
    
    order = get_object_or_404(models.Order, id=order_id)
    order_items = models.OrderItem.objects.filter(order=order).select_related('book')
    
    context = {
        'order': order,
        'order_items': order_items,
        'name': request.session["name"],
        'status_choices': models.ORDER_STATUS_CHOICES,
        'payment_status_choices': models.PAYMENT_STATUS_CHOICES,
    }
    
    return render(request, 'order/order_detail.html', context)


@require_POST
def update_order_status(request):
    """Update order status via AJAX"""
    # 登录判断
    if "name" not in request.session:
        return JsonResponse({'success': False, 'message': '请先登录'})
    
    try:
        order_id = request.POST.get('order_id')
        new_status = request.POST.get('status')
        admin_notes = request.POST.get('admin_notes', '')
        
        order = get_object_or_404(models.Order, id=order_id)
        old_status = order.status
        
        order.status = new_status
        if admin_notes:
            order.admin_notes = admin_notes
        order.save()
        
        # Log the status change
        return JsonResponse({
            'success': True, 
            'message': f'订单状态已从 "{dict(models.ORDER_STATUS_CHOICES)[old_status]}" 更新为 "{dict(models.ORDER_STATUS_CHOICES)[new_status]}"',
            'new_status': new_status,
            'new_status_display': dict(models.ORDER_STATUS_CHOICES)[new_status],
            'new_status_color': order.get_status_color()
        })
        
    except Exception as e:
        return JsonResponse({'success': False, 'message': '更新失败，请重试'})


@require_POST
def update_payment_status(request):
    """Update payment status via AJAX"""
    # 登录判断
    if "name" not in request.session:
        return JsonResponse({'success': False, 'message': '请先登录'})
    
    try:
        order_id = request.POST.get('order_id')
        new_payment_status = request.POST.get('payment_status')
        transaction_id = request.POST.get('transaction_id', '')
        
        order = get_object_or_404(models.Order, id=order_id)
        old_payment_status = order.payment_status
        
        order.payment_status = new_payment_status
        if transaction_id:
            order.payment_transaction_id = transaction_id
        
        # If payment is completed, also update payment completion time
        if new_payment_status == 'completed':
            order.payment_completed_at = timezone.now()
            # Also update order status if it's still pending
            if order.status == 'pending':
                order.status = 'paid'
        
        order.save()
        
        return JsonResponse({
            'success': True, 
            'message': f'支付状态已从 "{dict(models.PAYMENT_STATUS_CHOICES)[old_payment_status]}" 更新为 "{dict(models.PAYMENT_STATUS_CHOICES)[new_payment_status]}"',
            'new_payment_status': new_payment_status,
            'new_payment_status_display': dict(models.PAYMENT_STATUS_CHOICES)[new_payment_status],
            'new_payment_status_color': order.get_payment_status_color(),
            'order_status': order.status,
            'order_status_display': dict(models.ORDER_STATUS_CHOICES)[order.status],
            'order_status_color': order.get_status_color()
        })
        
    except Exception as e:
        return JsonResponse({'success': False, 'message': '更新失败，请重试'})

@require_http_methods(["GET"])
def export_orders(request):
    """Export orders to CSV or Excel format"""
    # 登录判断
    if "name" not in request.session:
        return redirect("/manager/login")
    
    export_format = request.GET.get('format', 'csv')  # csv or excel
    status_filter = request.GET.get('status', '')
    payment_status_filter = request.GET.get('payment_status', '')
    search_filter = request.GET.get('search', '')
    date_from = request.GET.get('date_from', '')
    date_to = request.GET.get('date_to', '')
    
    # Build queryset with filters
    orders = models.Order.objects.all().order_by('-created_at')
    
    if status_filter:
        orders = orders.filter(status=status_filter)
    
    if payment_status_filter:
        orders = orders.filter(payment_status=status_filter)
    
    if search_filter:
        orders = orders.filter(
            Q(order_number__icontains=search_filter) |
            Q(customer_name__icontains=search_filter) |
            Q(customer_email__icontains=search_filter) |
            Q(customer_phone__icontains=search_filter)
        )
    
    if date_from:
        try:
            from_date = timezone.datetime.strptime(date_from, '%Y-%m-%d').date()
            orders = orders.filter(created_at__date__gte=from_date)
        except ValueError:
            pass
    
    if date_to:
        try:
            to_date = timezone.datetime.strptime(date_to, '%Y-%m-%d').date()
            orders = orders.filter(created_at__date__lte=to_date)
        except ValueError:
            pass
    
    if export_format == 'excel':
        return export_orders_excel(orders)
    else:
        return export_orders_csv(orders)


def export_orders_csv(orders):
    """Export orders to CSV format"""
    response = HttpResponse(content_type='text/csv; charset=utf-8')
    response['Content-Disposition'] = f'attachment; filename="orders_export_{timezone.now().strftime("%Y%m%d_%H%M%S")}.csv"'
    
    # Add BOM for UTF-8 to ensure proper encoding in Excel
    response.write('\ufeff')
    
    writer = csv.writer(response)
    
    # Write header
    writer.writerow([
        '订单号', '客户姓名', '客户邮箱', '客户电话', '收货地址', '城市', '省份',
        '支付方式', '订单状态', '支付状态', '总金额', '商品数量', '创建时间', '客户备注', '管理员备注'
    ])
    
    # Write data
    for order in orders:
        writer.writerow([
            order.order_number,
            order.customer_name,
            order.customer_email,
            order.customer_phone,
            order.shipping_address,
            order.shipping_city,
            order.shipping_state,
            order.get_payment_method_display(),
            order.get_status_display(),
            order.get_payment_status_display(),
            f'¥{order.total_amount}',
            order.orderitem_set.count(),
            order.created_at.strftime('%Y-%m-%d %H:%M:%S'),
            order.customer_notes or '',
            order.admin_notes or ''
        ])
    
    return response


def export_orders_excel(orders):
    """Export orders to Excel format"""
    # Create workbook and worksheet
    wb = Workbook()
    ws = wb.active
    ws.title = "订单导出"
    
    # Define styles
    header_font = Font(bold=True, color="FFFFFF")
    header_fill = PatternFill(start_color="366092", end_color="366092", fill_type="solid")
    header_alignment = Alignment(horizontal="center", vertical="center")
    
    # Headers
    headers = [
        '订单号', '客户姓名', '客户邮箱', '客户电话', '收货地址', '城市', '省份',
        '支付方式', '订单状态', '支付状态', '总金额', '商品数量', '创建时间', '客户备注', '管理员备注'
    ]
    
    # Write headers
    for col_num, header in enumerate(headers, 1):
        cell = ws.cell(row=1, column=col_num, value=header)
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = header_alignment
    
    # Write data
    for row_num, order in enumerate(orders, 2):
        data = [
            order.order_number,
            order.customer_name,
            order.customer_email,
            order.customer_phone,
            order.shipping_address,
            order.shipping_city,
            order.shipping_state,
            order.get_payment_method_display(),
            order.get_status_display(),
            order.get_payment_status_display(),
            float(order.total_amount),
            order.orderitem_set.count(),
            order.created_at.strftime('%Y-%m-%d %H:%M:%S'),
            order.customer_notes or '',
            order.admin_notes or ''
        ]
        
        for col_num, value in enumerate(data, 1):
            ws.cell(row=row_num, column=col_num, value=value)
    
    # Auto-adjust column widths
    for column in ws.columns:
        max_length = 0
        column_letter = column[0].column_letter
        for cell in column:
            try:
                if len(str(cell.value)) > max_length:
                    max_length = len(str(cell.value))
            except:
                pass
        adjusted_width = min(max_length + 2, 50)
        ws.column_dimensions[column_letter].width = adjusted_width
    
    # Save to BytesIO
    excel_file = io.BytesIO()
    wb.save(excel_file)
    excel_file.seek(0)
    
    # Create response
    response = HttpResponse(
        excel_file.read(),
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    response['Content-Disposition'] = f'attachment; filename="orders_export_{timezone.now().strftime("%Y%m%d_%H%M%S")}.xlsx"'
    
    return response


@require_http_methods(["GET"])
def order_analytics(request):
    """Get order analytics data"""
    if not request.session.get('is_login'):
        return JsonResponse({'error': '请先登录'}, status=401)
    
    # Date range for analytics (default: last 30 days)
    end_date = timezone.now().date()
    start_date = end_date - timedelta(days=30)
    
    # Get date range from request
    date_from = request.GET.get('date_from')
    date_to = request.GET.get('date_to')
    
    if date_from:
        try:
            start_date = timezone.datetime.strptime(date_from, '%Y-%m-%d').date()
        except ValueError:
            pass
    
    if date_to:
        try:
            end_date = timezone.datetime.strptime(date_to, '%Y-%m-%d').date()
        except ValueError:
            pass
    
    # Analytics queries
    orders_in_range = models.Order.objects.filter(
        created_at__date__range=[start_date, end_date]
    )
    
    # Daily order counts
    daily_orders = []
    current_date = start_date
    while current_date <= end_date:
        count = orders_in_range.filter(created_at__date=current_date).count()
        revenue = orders_in_range.filter(
            created_at__date=current_date,
            payment_status='paid'
        ).aggregate(total=Sum('total_amount'))['total'] or 0
        
        daily_orders.append({
            'date': current_date.strftime('%Y-%m-%d'),
            'orders': count,
            'revenue': float(revenue)
        })
        current_date += timedelta(days=1)
    
    # Status distribution
    status_counts = {}
    for status, label in models.ORDER_STATUS_CHOICES:
        count = orders_in_range.filter(status=status).count()
        status_counts[label] = count
    
    # Payment status distribution
    payment_status_counts = {}
    for status, label in models.PAYMENT_STATUS_CHOICES:
        count = orders_in_range.filter(payment_status=status).count()
        payment_status_counts[label] = count
    
    # Top customers
    top_customers = orders_in_range.values('customer_name', 'customer_email').annotate(
        order_count=models.Count('id'),
        total_spent=Sum('total_amount')
    ).order_by('-total_spent')[:10]
    
    return JsonResponse({
        'success': True,
        'data': {
            'date_range': {
                'start': start_date.strftime('%Y-%m-%d'),
                'end': end_date.strftime('%Y-%m-%d')
            },
            'daily_orders': daily_orders,
            'status_distribution': status_counts,
            'payment_status_distribution': payment_status_counts,
            'top_customers': list(top_customers),
            'summary': {
                'total_orders': orders_in_range.count(),                'total_revenue': float(orders_in_range.filter(payment_status='paid').aggregate(
                    total=Sum('total_amount'))['total'] or 0),
                'average_order_value': float(orders_in_range.aggregate(
                    avg=Avg('total_amount'))['avg'] or 0),
                'completion_rate': round(
                    (orders_in_range.filter(status='delivered').count() / 
                     max(orders_in_range.count(), 1)) * 100, 2
                )
            }
        }
    })

# ====================   MANAGER DASHBOARD  ===========================
def manager_dashboard(request):
    """Professional dashboard for managers with statistics and analytics"""
    # 登录判断
    if "name" not in request.session:
        return redirect("/manager/login")
    
    from datetime import datetime, timedelta
    from django.utils import timezone
    from django.db.models import Sum, Count, Q
    import json
    
    # Get current date ranges
    now = timezone.now()
    current_month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    last_month = (current_month - timedelta(days=1)).replace(day=1)
    last_7_days = now.date() - timedelta(days=7)
    
    # ==== BASIC STATISTICS ====
    total_books = models.Book.objects.count()
    total_publishers = models.Publisher.objects.count()
    total_authors = models.Author.objects.count()
    
    # Books added this month - Real dynamic calculation
    new_books_this_month = models.Book.objects.filter(
        created_at__gte=current_month
    ).count() if hasattr(models.Book, 'created_at') else 0
    
    # ==== ORDER STATISTICS ====
    try:
        total_orders = models.Order.objects.count()
        orders_this_month = models.Order.objects.filter(created_at__gte=current_month).count()
        
        # Order status counts
        pending_orders = models.Order.objects.filter(status='payment_pending').count()
        processing_orders = models.Order.objects.filter(status='processing').count()
        shipped_orders = models.Order.objects.filter(status='shipped').count()
        completed_orders = models.Order.objects.filter(status='delivered').count()
        cancelled_orders = models.Order.objects.filter(status='cancelled').count()
        
        # Revenue calculations
        total_revenue = models.Order.objects.filter(
            payment_status__in=['completed', 'pending']
        ).aggregate(Sum('total_amount'))['total_amount__sum'] or 0
        
        revenue_this_month = models.Order.objects.filter(
            created_at__gte=current_month,
            payment_status__in=['completed', 'pending']
        ).aggregate(Sum('total_amount'))['total_amount__sum'] or 0
        
    except Exception as e:
        total_orders = 0
        orders_this_month = 0
        pending_orders = 0
        processing_orders = 0
        shipped_orders = 0
        completed_orders = 0
        cancelled_orders = 0
        total_revenue = 0
        revenue_this_month = 0
    
    # ==== INVENTORY STATISTICS ====
    low_inventory_books = models.Book.objects.filter(inventory__lt=10).count()
    total_inventory = models.Book.objects.aggregate(Sum('inventory'))['inventory__sum'] or 0
    total_sales = models.Book.objects.aggregate(Sum('sale_num'))['sale_num__sum'] or 0
    
    # Top selling books
    top_books = models.Book.objects.order_by('-sale_num')[:5]
    
    # Recent orders (if available)
    try:
        recent_orders = models.Order.objects.order_by('-created_at')[:5]
    except:
        recent_orders = []
    
    # ==== CHART DATA ==== 
    # Daily sales for the last 7 days
    daily_sales = []
    for i in range(6, -1, -1):  # Reverse order to show oldest to newest
        date = (now.date() - timedelta(days=i))
        try:
            day_orders = models.Order.objects.filter(
                created_at__date=date
            ).count()
            day_revenue = models.Order.objects.filter(
                created_at__date=date,
                payment_status__in=['completed', 'pending']
            ).aggregate(Sum('total_amount'))['total_amount__sum'] or 0
        except:
            day_orders = 0
            day_revenue = 0
        
        daily_sales.append({
            'date': date.strftime('%m-%d'),
            'orders': day_orders,
            'revenue': float(day_revenue)
        })
    
    # Publisher distribution
    publisher_stats = []
    for publisher in models.Publisher.objects.all()[:5]:
        book_count = models.Book.objects.filter(publisher=publisher).count()
        publisher_stats.append({
            'name': publisher.publisher_name,
            'books': book_count
        })
    
    # Add default data if no publishers
    if not publisher_stats:
        publisher_stats = [{'name': '暂无数据', 'books': 1}]

    # ==== ADDITIONAL CHART DATA ====
    # Top 5 books: sales vs inventory comparison
    top_books_comparison = []
    for book in models.Book.objects.order_by('-sale_num')[:5]:
        top_books_comparison.append({
            'name': book.name[:12],
            'sales': book.sale_num,
            'inventory': book.inventory,
        })
    if not top_books_comparison:
        top_books_comparison = [{'name': '暂无数据', 'sales': 0, 'inventory': 0}]

    # Price range distribution
    price_ranges = {
        '0-20': models.Book.objects.filter(price__lte=20).count(),
        '20-50': models.Book.objects.filter(price__gt=20, price__lte=50).count(),
        '50-100': models.Book.objects.filter(price__gt=50, price__lte=100).count(),
        '100-200': models.Book.objects.filter(price__gt=100, price__lte=200).count(),
        '200+': models.Book.objects.filter(price__gt=200).count(),
    }
    price_distribution = [{'range': k, 'count': v} for k, v in price_ranges.items()]

    # Monthly order trend (last 6 months)
    monthly_orders = []
    for i in range(5, -1, -1):
        month_start = (now.replace(day=1) - timedelta(days=i * 30)).replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        if i > 0:
            next_month = (month_start + timedelta(days=32)).replace(day=1)
        else:
            next_month = now
        try:
            month_count = models.Order.objects.filter(
                created_at__gte=month_start, created_at__lt=next_month
            ).count()
            month_rev = float(models.Order.objects.filter(
                created_at__gte=month_start, created_at__lt=next_month,
                payment_status__in=['completed', 'pending']
            ).aggregate(Sum('total_amount'))['total_amount__sum'] or 0)
        except Exception:
            month_count = 0
            month_rev = 0
        monthly_orders.append({
            'month': month_start.strftime('%Y-%m'),
            'orders': month_count,
            'revenue': month_rev,
        })

    # ==== MARKETPLACE STATS ====
    total_products = 0
    total_courses = 0
    total_supermarket = 0
    mkt_order_count = 0
    mkt_revenue = 0
    try:
        from marketplace.models import Product, Course, SupermarketItem, MarketplaceOrder as MktOrder
        total_products = Product.objects.filter(is_active=True).count()
        total_courses = Course.objects.filter(is_active=True).count()
        total_supermarket = SupermarketItem.objects.filter(is_active=True).count()
        _mkt_qs = MktOrder.objects.all()
        mkt_order_count = _mkt_qs.count()
        mkt_revenue = float(_mkt_qs.filter(payment_status='completed').aggregate(Sum('total_amount'))['total_amount__sum'] or 0)
    except Exception:
        pass

    context = {
        'name': request.session["name"],
        'current_date': f'{now.year}年{now.month:02d}月{now.day:02d}日',
        
        # Basic stats
        'total_books': total_books,
        'total_publishers': total_publishers,
        'total_authors': total_authors,
        'new_books_this_month': new_books_this_month,
        'total_customers': 0,  # Default value
        'new_customers_this_month': 0,  # Default value
        
        # Order stats
        'total_orders': total_orders,
        'orders_this_month': orders_this_month,
        'pending_orders': pending_orders,
        'processing_orders': processing_orders,
        'shipped_orders': shipped_orders,
        'completed_orders': completed_orders,
        'cancelled_orders': cancelled_orders,
        'total_revenue': total_revenue,
        'revenue_this_month': revenue_this_month,
        
        # Inventory stats
        'low_inventory_books': low_inventory_books,
        'total_inventory': total_inventory,
        'total_sales': total_sales,
        
        # Lists
        'top_books': top_books,
        'recent_orders': recent_orders,
        'recent_activities': [],  # Default empty list
        
        # Marketplace stats
        'total_products': total_products,
        'total_courses': total_courses,
        'total_supermarket': total_supermarket,
        'mkt_order_count': mkt_order_count,
        'mkt_revenue': mkt_revenue,

        # Chart data (as JSON)
        'daily_sales_json': json.dumps(daily_sales),
        'publisher_stats_json': json.dumps(publisher_stats),
        'top_books_comparison_json': json.dumps(top_books_comparison),
        'price_distribution_json': json.dumps(price_distribution),
        'monthly_orders_json': json.dumps(monthly_orders),
    }
    
    return render(request, 'manager/dashboard.html', context)

@require_http_methods(["GET"])
def dashboard_analytics_api(request):
    """API endpoint for dashboard analytics data"""
    if "name" not in request.session:
        return JsonResponse({'error': 'Unauthorized'}, status=401)
    
    # Return analytics data for AJAX requests
    return JsonResponse({
        'success': True,
        'data': {
            'total_books': models.Book.objects.count(),
            'total_orders': models.Order.objects.count() if hasattr(models, 'Order') else 0,
            'low_inventory': models.Book.objects.filter(inventory__lt=10).count(),
        }
    })

@require_POST
def delete_order(request, order_id):
    """Delete an order via AJAX"""
    # 登录判断
    if "name" not in request.session:
        return JsonResponse({'success': False, 'message': '请先登录'})
    
    try:
        order = get_object_or_404(models.Order, id=order_id)
        
        # Check if order can be deleted (business rules)
        if order.status == 'delivered':
            return JsonResponse({
                'success': False, 
                'message': '已送达的订单不能删除'
            })
        
        if order.payment_status == 'completed':
            return JsonResponse({
                'success': False, 
                'message': '已完成支付的订单不能删除，请先处理退款'
            })
        
        # Store order info for response
        order_number = order.order_number
        customer_name = order.customer_name
        
        # Delete the order (cascade will delete related OrderItems)
        order.delete()
        
        return JsonResponse({
            'success': True, 
            'message': f'订单 {order_number} (客户: {customer_name}) 已成功删除'
        })
        
    except models.Order.DoesNotExist:
        return JsonResponse({
            'success': False, 
            'message': '订单不存在'
        })
    except Exception as e:
        return JsonResponse({
            'success': False, 
            'message': f'删除失败：{str(e)}'
        })


# ====================   Public Static Pages  ===========================
def public_about(request):
    """About Us page"""
    context = {
        'book_count': models.Book.objects.count(),
        'author_count': models.Author.objects.count(),
        'publisher_count': models.Publisher.objects.count(),
        'total_sales': models.Book.objects.aggregate(total=Sum('sale_num'))['total'] or 0,
    }
    return render(request, 'public/about.html', context)


def public_services(request):
    """Services page"""
    return render(request, 'public/services.html')


@csrf_protect
def public_contact(request):
    """Contact Us page with email sending via configured EmailAccount(s)"""
    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        email = request.POST.get('email', '').strip()
        subject = request.POST.get('subject', '').strip()
        message = request.POST.get('message', '').strip()

        if not name or not email or not message:
            return JsonResponse({'success': False, 'error': 'Please fill in all required fields.'}, status=400)

        # Save to database first (never lose a message)
        contact_msg = models.ContactMessage.objects.create(
            name=name, email=email, subject=subject, message=message
        )

        # Create admin notification for contact form message
        create_notification(
            'contact_message',
            f'新联系消息 - {name}',
            f'{subject or "无主题"}: {message[:80]}',
            icon='fas fa-envelope-open-text',
            color='#10b981',
            link=f'/manager/email/?folder=contact',
            related_id=contact_msg.id,
        )

        # Build notification email content
        email_subject = f'[Contact Form] {subject or "No Subject"} - from {name}'
        email_body = (
            f'New message from the contact form\n'
            f'{"-" * 40}\n\n'
            f'Name:    {name}\n'
            f'Email:   {email}\n'
            f'Subject: {subject or "N/A"}\n\n'
            f'Message:\n{message}\n\n'
            f'{"-" * 40}\n'
            f'Sent from DUNO 360 contact form\n'
        )

        # Send notification to all active email accounts (or default)
        sent_ok = False
        accounts = models.EmailAccount.objects.filter(is_active=True)
        if accounts.exists():
            # Use default account to send, deliver to all active account addresses
            sender_account = accounts.filter(is_default=True).first() or accounts.first()
            recipient_emails = list(accounts.values_list('email_address', flat=True))
            try:
                _send_email(
                    account=sender_account,
                    to=', '.join(recipient_emails),
                    subject=email_subject,
                    body=email_body,
                )
                sent_ok = True
            except Exception as e:
                logger.warning(f'Contact form email via EmailAccount failed (msg #{contact_msg.id}): {e}')

        # Fallback to Django send_mail if no EmailAccount configured or sending failed
        if not sent_ok:
            try:
                send_mail(
                    subject=email_subject,
                    message=email_body,
                    from_email=django_settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[django_settings.CONTACT_EMAIL],
                    fail_silently=False,
                )
                sent_ok = True
            except Exception as e:
                logger.warning(f'Contact form Django email failed (msg #{contact_msg.id}): {e}')

        if sent_ok:
            contact_msg.email_sent = True
            contact_msg.save(update_fields=['email_sent'])

        return JsonResponse({'success': True})

    return render(request, 'public/contact.html')


# ====================   Public Blog  ===========================
def public_blog(request):
    """Blog listing page"""
    search = request.GET.get('search', '')
    category_slug = request.GET.get('category', '')

    posts = models.BlogPost.objects.filter(status='published').select_related('category')

    if search:
        posts = posts.filter(Q(title__icontains=search) | Q(content__icontains=search))

    if category_slug:
        posts = posts.filter(category__slug=category_slug)

    categories = models.BlogCategory.objects.annotate(
        post_count=Count('posts', filter=Q(posts__status='published'))
    )
    featured_posts = models.BlogPost.objects.filter(
        status='published', is_featured=True
    ).select_related('category')[:3]

    context = {
        'posts': posts,
        'categories': categories,
        'featured_posts': featured_posts,
        'search_query': search,
        'current_category': category_slug,
    }
    return render(request, 'public/blog.html', context)


def public_blog_detail(request, slug):
    """Blog post detail page"""
    post = get_object_or_404(models.BlogPost, slug=slug, status='published')
    # Increment views
    models.BlogPost.objects.filter(pk=post.pk).update(views_count=F('views_count') + 1)
    post.refresh_from_db()

    related_posts = models.BlogPost.objects.filter(
        status='published', category=post.category
    ).exclude(id=post.id)[:3] if post.category else models.BlogPost.objects.filter(
        status='published'
    ).exclude(id=post.id)[:3]

    context = {
        'post': post,
        'related_posts': related_posts,
    }
    return render(request, 'public/blog_detail.html', context)


# ====================   Admin Blog Management  ===========================
def blog_list(request):
    """Admin blog post list"""
    if "name" not in request.session:
        return redirect('/manager/login/')

    search = request.GET.get('search', '')
    status_filter = request.GET.get('status', '')

    posts = models.BlogPost.objects.select_related('category').all()

    if search:
        posts = posts.filter(Q(title__icontains=search) | Q(content__icontains=search))
    if status_filter:
        posts = posts.filter(status=status_filter)

    categories = models.BlogCategory.objects.all()

    context = {
        'posts': posts,
        'categories': categories,
        'search_query': search,
        'status_filter': status_filter,
    }
    return render(request, 'blog/blog_list.html', context)


def add_blog_post(request):
    """Admin add blog post"""
    if "name" not in request.session:
        return redirect('/manager/login/')

    if request.method == 'POST':
        title = request.POST.get('title', '').strip()
        content = request.POST.get('content', '').strip()
        excerpt = request.POST.get('excerpt', '').strip()
        category_id = request.POST.get('category')
        author_name = request.POST.get('author_name', 'Admin').strip()
        status = request.POST.get('status', 'draft')
        is_featured = request.POST.get('is_featured') == 'on'

        if not title or not content:
            messages.error(request, '标题和内容不能为空')
            return redirect('/manager/add_blog/')

        # Generate unique slug
        base_slug = slugify(title, allow_unicode=True)
        if not base_slug:
            base_slug = hashlib.md5(title.encode()).hexdigest()[:12]
        slug = base_slug
        counter = 1
        while models.BlogPost.objects.filter(slug=slug).exists():
            slug = f"{base_slug}-{counter}"
            counter += 1

        post = models.BlogPost(
            title=title,
            slug=slug,
            content=content,
            excerpt=excerpt,
            author_name=author_name,
            status=status,
            is_featured=is_featured,
        )

        if category_id:
            try:
                post.category = models.BlogCategory.objects.get(id=category_id)
            except models.BlogCategory.DoesNotExist:
                pass

        if 'cover_image' in request.FILES:
            post.cover_image = request.FILES['cover_image']

        if status == 'published':
            post.published_at = timezone.now()

        post.save()
        messages.success(request, f'文章 "{title}" 创建成功！')
        return redirect('/manager/blog_list/')

    categories = models.BlogCategory.objects.all()
    return render(request, 'blog/add_blog.html', {'categories': categories})


def edit_blog_post(request):
    """Admin edit blog post"""
    if "name" not in request.session:
        return redirect('/manager/login/')

    if request.method == 'GET':
        post_id = request.GET.get('id')
        post = get_object_or_404(models.BlogPost, id=post_id)
        categories = models.BlogCategory.objects.all()
        return render(request, 'blog/edit_blog.html', {'post': post, 'categories': categories})

    if request.method == 'POST':
        post_id = request.POST.get('id')
        post = get_object_or_404(models.BlogPost, id=post_id)

        post.title = request.POST.get('title', '').strip()
        post.content = request.POST.get('content', '').strip()
        post.excerpt = request.POST.get('excerpt', '').strip()
        post.author_name = request.POST.get('author_name', 'Admin').strip()
        post.is_featured = request.POST.get('is_featured') == 'on'

        new_status = request.POST.get('status', 'draft')
        if new_status == 'published' and post.status != 'published':
            post.published_at = timezone.now()
        post.status = new_status

        category_id = request.POST.get('category')
        if category_id:
            try:
                post.category = models.BlogCategory.objects.get(id=category_id)
            except models.BlogCategory.DoesNotExist:
                post.category = None
        else:
            post.category = None

        if 'cover_image' in request.FILES:
            post.cover_image = request.FILES['cover_image']

        post.save()
        messages.success(request, f'文章 "{post.title}" 更新成功！')
        return redirect('/manager/blog_list/')


def delete_blog_post(request):
    """Admin delete blog post"""
    if "name" not in request.session:
        return redirect('/manager/login/')

    post_id = request.GET.get('id')
    post = get_object_or_404(models.BlogPost, id=post_id)
    title = post.title
    post.delete()
    messages.success(request, f'文章 "{title}" 已删除')
    return redirect('/manager/blog_list/')


def manage_blog_categories(request):
    """Admin blog category management"""
    if "name" not in request.session:
        return redirect('/manager/login/')

    if request.method == 'POST':
        action = request.POST.get('action')

        if action == 'add':
            name = request.POST.get('name', '').strip()
            description = request.POST.get('description', '').strip()
            icon = request.POST.get('icon', 'fas fa-folder').strip()
            if name:
                base_slug = slugify(name, allow_unicode=True)
                if not base_slug:
                    base_slug = hashlib.md5(name.encode()).hexdigest()[:12]
                slug = base_slug
                counter = 1
                while models.BlogCategory.objects.filter(slug=slug).exists():
                    slug = f"{base_slug}-{counter}"
                    counter += 1
                models.BlogCategory.objects.create(
                    name=name, slug=slug, description=description, icon=icon
                )
                messages.success(request, f'分类 "{name}" 创建成功！')

        elif action == 'delete':
            cat_id = request.POST.get('category_id')
            try:
                cat = models.BlogCategory.objects.get(id=cat_id)
                name = cat.name
                cat.delete()
                messages.success(request, f'分类 "{name}" 已删除')
            except models.BlogCategory.DoesNotExist:
                messages.error(request, '分类不存在')

        return redirect('/manager/blog_categories/')

    categories = models.BlogCategory.objects.annotate(
        post_count=Count('posts')
    )
    return render(request, 'blog/blog_categories.html', {'categories': categories})


def manage_book_categories(request):
    """Admin book category management used by public mobile and desktop filters."""
    if "name" not in request.session:
        return redirect('/manager/login/')

    if request.method == 'POST':
        action = request.POST.get('action')

        if action == 'add':
            name = request.POST.get('name', '').strip()
            name_en = request.POST.get('name_en', '').strip()
            name_fr = request.POST.get('name_fr', '').strip()
            description = request.POST.get('description', '').strip()
            icon = request.POST.get('icon', 'fas fa-book').strip() or 'fas fa-book'
            color = request.POST.get('color', '#667eea').strip() or '#667eea'
            display_order = request.POST.get('display_order') or 0
            if name:
                base_slug = slugify(request.POST.get('slug', '').strip() or name, allow_unicode=True)
                if not base_slug:
                    base_slug = hashlib.md5(name.encode()).hexdigest()[:12]
                slug = base_slug
                counter = 1
                while models.BookCategory.objects.filter(slug=slug).exists():
                    slug = f"{base_slug}-{counter}"
                    counter += 1
                models.BookCategory.objects.create(
                    name=name,
                    name_en=name_en,
                    name_fr=name_fr,
                    slug=slug,
                    description=description,
                    icon=icon,
                    color=color,
                    display_order=display_order,
                    is_active=bool(request.POST.get('is_active', 'on')),
                )
                messages.success(request, f'图书分类 "{name}" 创建成功！')

        elif action == 'delete':
            cat_id = request.POST.get('category_id')
            try:
                cat = models.BookCategory.objects.get(id=cat_id)
                name = cat.name
                cat.delete()
                messages.success(request, f'图书分类 "{name}" 已删除')
            except models.BookCategory.DoesNotExist:
                messages.error(request, '分类不存在')

        elif action == 'toggle':
            cat_id = request.POST.get('category_id')
            try:
                cat = models.BookCategory.objects.get(id=cat_id)
                cat.is_active = not cat.is_active
                cat.save(update_fields=['is_active'])
                messages.success(request, f'图书分类 "{cat.name}" 状态已更新')
            except models.BookCategory.DoesNotExist:
                messages.error(request, '分类不存在')

        return redirect('/manager/book_categories/')

    categories = models.BookCategory.objects.filter(parent__isnull=True).annotate(
        book_count=Count('books')
    )
    return render(request, 'book/book_categories.html', {'categories': categories, 'name': request.session["name"]})


# ====================   Admin Contact Messages  ===========================

def admin_messages(request):
    """Redirect to unified mail management"""
    return redirect('/manager/email/')


def admin_message_detail(request, msg_id):
    """Admin: view single message detail — auto marks as read"""
    if "name" not in request.session:
        return redirect('/manager/login/')

    msg = get_object_or_404(models.ContactMessage, id=msg_id)
    if not msg.is_read:
        msg.is_read = True
        msg.save(update_fields=['is_read'])

    unread_count = models.ContactMessage.objects.filter(is_read=False).count()
    accounts = models.EmailAccount.objects.filter(is_active=True)
    labels = models.EmailLabel.objects.all()
    name = request.session["name"]
    return render(request, 'admin/admin_message_detail.html', {
        'msg': msg,
        'unread_count': unread_count,
        'accounts': accounts,
        'labels': labels,
        'name': name,
    })


def admin_message_toggle_read(request):
    """AJAX: toggle is_read status for a message"""
    if "name" not in request.session:
        return JsonResponse({'success': False, 'error': 'Unauthorized'}, status=403)
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Method not allowed'}, status=405)

    msg_id = request.POST.get('id')
    try:
        msg = models.ContactMessage.objects.get(id=msg_id)
        msg.is_read = not msg.is_read
        msg.save(update_fields=['is_read'])
        unread_count = models.ContactMessage.objects.filter(is_read=False).count()
        return JsonResponse({'success': True, 'is_read': msg.is_read, 'unread_count': unread_count})
    except models.ContactMessage.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Not found'}, status=404)


def admin_message_delete(request):
    """Admin: delete a contact message"""
    if "name" not in request.session:
        return JsonResponse({'success': False, 'error': 'Unauthorized'}, status=403)
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Method not allowed'}, status=405)

    msg_id = request.POST.get('id')
    try:
        msg = models.ContactMessage.objects.get(id=msg_id)
        msg.delete()
        unread_count = models.ContactMessage.objects.filter(is_read=False).count()
        return JsonResponse({'success': True, 'unread_count': unread_count})
    except models.ContactMessage.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Not found'}, status=404)


def admin_message_bulk_action(request):
    """Admin: bulk mark read or bulk delete messages"""
    if "name" not in request.session:
        return JsonResponse({'success': False, 'error': 'Unauthorized'}, status=403)
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Method not allowed'}, status=405)

    action = request.POST.get('action')
    ids_raw = request.POST.get('ids', '')
    try:
        ids = [int(i) for i in ids_raw.split(',') if i.strip().isdigit()]
    except ValueError:
        return JsonResponse({'success': False, 'error': 'Invalid IDs'}, status=400)

    if not ids:
        return JsonResponse({'success': False, 'error': 'No IDs provided'}, status=400)

    if action == 'mark_read':
        models.ContactMessage.objects.filter(id__in=ids).update(is_read=True)
    elif action == 'mark_unread':
        models.ContactMessage.objects.filter(id__in=ids).update(is_read=False)
    elif action == 'delete':
        models.ContactMessage.objects.filter(id__in=ids).delete()
    else:
        return JsonResponse({'success': False, 'error': 'Unknown action'}, status=400)

    unread_count = models.ContactMessage.objects.filter(is_read=False).count()
    return JsonResponse({'success': True, 'unread_count': unread_count})


def reply_to_contact(request, msg_id):
    """Reply to a contact message using a configured email account"""
    if "name" not in request.session:
        return JsonResponse({'success': False, 'error': 'Unauthorized'}, status=403)
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'POST required'}, status=405)

    msg = get_object_or_404(models.ContactMessage, id=msg_id)
    account_id = request.POST.get('account_id')
    reply_body = request.POST.get('body', '').strip()

    if not reply_body:
        return JsonResponse({'success': False, 'error': '回复内容不能为空'})
    if not account_id:
        return JsonResponse({'success': False, 'error': '请选择发送账户'})

    account = get_object_or_404(models.EmailAccount, id=account_id, is_active=True)
    subject = f'Re: {msg.subject or "(无主题)"}'

    # Build reply with original message quoted
    full_body = (
        f'{reply_body}\n\n'
        f'--- 原始消息 ---\n'
        f'发件人: {msg.name} <{msg.email}>\n'
        f'时间: {msg.created_at.strftime("%Y-%m-%d %H:%M")}\n'
        f'主题: {msg.subject or "(无主题)"}\n\n'
        f'{msg.message}'
    )

    try:
        _send_email(
            account=account,
            to=msg.email,
            subject=subject,
            body=full_body,
        )

        # Save as sent EmailMessage for record
        models.EmailMessage.objects.create(
            account=account,
            sender_name=account.name,
            sender_email=account.email_address,
            recipients=msg.email,
            subject=subject,
            body_text=full_body,
            folder='sent',
            is_read=True,
            sent_at=timezone.now(),
        )

        msg.replied = True
        msg.replied_at = timezone.now()
        msg.admin_reply = reply_body
        msg.save(update_fields=['replied', 'replied_at', 'admin_reply'])

        return JsonResponse({'success': True, 'message': f'回复已发送至 {msg.email}'})
    except Exception as e:
        logger.error(f'Reply to contact #{msg_id} failed: {e}')
        return JsonResponse({'success': False, 'error': f'发送失败: {str(e)}'})


def contact_label_action(request):
    """Add/remove labels on contact messages"""
    if "name" not in request.session:
        return JsonResponse({'success': False, 'error': 'Unauthorized'}, status=403)
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'POST required'}, status=405)

    action = request.POST.get('action', '')
    ids_raw = request.POST.get('ids', '')
    label_id = request.POST.get('label_id')

    try:
        ids = [int(i) for i in ids_raw.split(',') if i.strip().isdigit()]
    except ValueError:
        return JsonResponse({'success': False, 'error': 'Invalid IDs'}, status=400)

    if not ids or not label_id:
        return JsonResponse({'success': False, 'error': 'Missing parameters'}, status=400)

    label = get_object_or_404(models.EmailLabel, id=label_id)
    msgs = models.ContactMessage.objects.filter(id__in=ids)

    if action == 'add_label':
        for m in msgs:
            m.labels.add(label)
    elif action == 'remove_label':
        for m in msgs:
            m.labels.remove(label)
    else:
        return JsonResponse({'success': False, 'error': 'Unknown action'}, status=400)

    return JsonResponse({'success': True})


# ====================   Email Management System  ===========================

import imaplib
import smtplib
import email as email_lib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from email.utils import parseaddr, formataddr, parsedate_to_datetime
from email.header import decode_header


def _decode_header_value(value):
    """Decode email header value (handles encoded words)"""
    if not value:
        return ''
    decoded_parts = []
    for part, charset in decode_header(value):
        if isinstance(part, bytes):
            decoded_parts.append(part.decode(charset or 'utf-8', errors='replace'))
        else:
            decoded_parts.append(part)
    return ''.join(decoded_parts)


def _apply_auto_rules(email_obj):
    """Apply auto-rules to a newly received email"""
    rules = models.EmailAutoRule.objects.filter(is_active=True).order_by('-priority')
    if email_obj.account_id:
        rules = rules.filter(
            Q(apply_to_account__isnull=True) | Q(apply_to_account=email_obj.account)
        )

    for rule in rules:
        matched = False
        pattern = rule.match_pattern.lower()
        fields_to_check = []

        if rule.match_field == 'from':
            fields_to_check = [email_obj.sender_email.lower(), email_obj.sender_name.lower()]
        elif rule.match_field == 'to':
            fields_to_check = [email_obj.recipients.lower()]
        elif rule.match_field == 'subject':
            fields_to_check = [email_obj.subject.lower()]
        elif rule.match_field == 'body':
            fields_to_check = [email_obj.body_text.lower()]
        else:  # 'any'
            fields_to_check = [
                email_obj.sender_email.lower(), email_obj.sender_name.lower(),
                email_obj.recipients.lower(), email_obj.subject.lower(),
                email_obj.body_text.lower()
            ]

        for field_val in fields_to_check:
            if pattern in field_val:
                matched = True
                break

        if matched:
            if rule.action == 'label' and rule.action_label:
                email_obj.labels.add(rule.action_label)
            elif rule.action == 'star':
                email_obj.is_starred = True
                email_obj.save(update_fields=['is_starred'])
            elif rule.action == 'archive':
                email_obj.folder = 'archive'
                email_obj.save(update_fields=['folder'])
            elif rule.action == 'delete':
                email_obj.folder = 'trash'
                email_obj.save(update_fields=['folder'])
            elif rule.action == 'mark_read':
                email_obj.is_read = True
                email_obj.save(update_fields=['is_read'])
            elif rule.action == 'auto_reply':
                try:
                    _send_email(
                        account=email_obj.account,
                        to=email_obj.sender_email,
                        subject=rule.auto_reply_subject or f'Re: {email_obj.subject}',
                        body=rule.auto_reply_body,
                        in_reply_to=email_obj.message_uid,
                    )
                except Exception as e:
                    logger.error(f'Auto-reply failed for rule {rule.name}: {e}')
            elif rule.action == 'forward' and rule.action_forward_to:
                try:
                    _send_email(
                        account=email_obj.account,
                        to=rule.action_forward_to,
                        subject=f'Fwd: {email_obj.subject}',
                        body=f'---------- Forwarded message ----------\nFrom: {email_obj.sender_name} <{email_obj.sender_email}>\nDate: {email_obj.received_at}\nSubject: {email_obj.subject}\n\n{email_obj.body_text}',
                    )
                except Exception as e:
                    logger.error(f'Forward failed for rule {rule.name}: {e}')


def _send_email(account, to, subject, body, cc='', bcc='', html_body='', in_reply_to='', attachments=None):
    """Send email through an account's SMTP settings"""
    msg = MIMEMultipart('alternative')
    msg['From'] = formataddr((account.name, account.email_address))
    msg['To'] = to
    msg['Subject'] = subject
    if cc:
        msg['Cc'] = cc
    if in_reply_to:
        msg['In-Reply-To'] = in_reply_to

    msg.attach(MIMEText(body, 'plain', 'utf-8'))
    if html_body:
        msg.attach(MIMEText(html_body, 'html', 'utf-8'))

    if attachments:
        for att in attachments:
            part = MIMEBase('application', 'octet-stream')
            part.set_payload(att.read())
            encoders.encode_base64(part)
            part.add_header('Content-Disposition', f'attachment; filename="{att.name}"')
            msg.attach(part)

    all_recipients = [r.strip() for r in to.split(',') if r.strip()]
    if cc:
        all_recipients += [r.strip() for r in cc.split(',') if r.strip()]
    if bcc:
        all_recipients += [r.strip() for r in bcc.split(',') if r.strip()]

    server = None
    try:
        if account.smtp_use_tls:
            server = smtplib.SMTP(account.smtp_host, account.smtp_port, timeout=30)
            server.starttls()
        else:
            server = smtplib.SMTP_SSL(account.smtp_host, account.smtp_port, timeout=30)

        server.login(account.username, account.password)
        server.send_message(msg, to_addrs=all_recipients)
        return msg['Message-ID'] or ''
    finally:
        if server:
            try:
                server.quit()
            except Exception:
                pass


def email_dashboard(request):
    """Unified mail/message management dashboard"""
    if "name" not in request.session:
        return redirect('/manager/login/')

    folder = request.GET.get('folder', 'inbox')
    account_id = request.GET.get('account', '')
    label_id = request.GET.get('label', '')
    search = request.GET.get('search', '').strip()
    starred_only = request.GET.get('starred', '') == '1'

    accounts = models.EmailAccount.objects.filter(is_active=True)
    labels = models.EmailLabel.objects.all()

    contact_messages = None

    if folder == 'contact':
        # Show contact form messages
        cqs = models.ContactMessage.objects.prefetch_related('labels').order_by('-created_at')
        if search:
            cqs = cqs.filter(
                Q(name__icontains=search) | Q(email__icontains=search) |
                Q(subject__icontains=search) | Q(message__icontains=search)
            )
        if label_id:
            cqs = cqs.filter(labels__id=label_id)
        contact_messages = cqs
        emails = models.EmailMessage.objects.none()
    else:
        qs = models.EmailMessage.objects.select_related('account')

        if account_id:
            qs = qs.filter(account_id=account_id)
        if folder:
            qs = qs.filter(folder=folder)
        if label_id:
            qs = qs.filter(labels__id=label_id)
        if starred_only:
            qs = qs.filter(is_starred=True)
        if search:
            qs = qs.filter(
                Q(subject__icontains=search) |
                Q(sender_name__icontains=search) |
                Q(sender_email__icontains=search) |
                Q(body_text__icontains=search) |
                Q(recipients__icontains=search)
            )

        emails = qs.order_by('-received_at', '-created_at')

    # Counts per folder
    base_qs = models.EmailMessage.objects.all()
    if account_id:
        base_qs = base_qs.filter(account_id=account_id)

    contact_unread = models.ContactMessage.objects.filter(is_read=False).count()
    contact_total = models.ContactMessage.objects.count()

    folder_counts = {
        'inbox': base_qs.filter(folder='inbox').count(),
        'sent': base_qs.filter(folder='sent').count(),
        'draft': base_qs.filter(folder='draft').count(),
        'trash': base_qs.filter(folder='trash').count(),
        'archive': base_qs.filter(folder='archive').count(),
        'starred': base_qs.filter(is_starred=True).count(),
        'contact': contact_total,
    }
    unread_count = base_qs.filter(folder='inbox', is_read=False).count() + contact_unread

    context = {
        'emails': emails,
        'contact_messages': contact_messages,
        'accounts': accounts,
        'labels': labels,
        'current_folder': folder,
        'current_account': account_id,
        'current_label': label_id,
        'search': search,
        'starred_only': starred_only,
        'folder_counts': folder_counts,
        'unread_count': unread_count,
        'contact_unread': contact_unread,
        'name': request.session.get('name', ''),
    }
    return render(request, 'admin/email_management.html', context)


def email_detail(request, email_id):
    """View a single email"""
    if "name" not in request.session:
        return redirect('/manager/login/')

    email_obj = get_object_or_404(models.EmailMessage, id=email_id)
    if not email_obj.is_read:
        email_obj.is_read = True
        email_obj.save(update_fields=['is_read'])

    # Get thread
    thread = models.EmailMessage.objects.filter(
        account=email_obj.account,
        subject__in=[email_obj.subject, f'Re: {email_obj.subject}', email_obj.subject.replace('Re: ', '', 1)]
    ).exclude(id=email_obj.id).order_by('received_at', 'created_at')[:10]

    # JSON response for reading pane
    if request.GET.get('format') == 'json':
        date_str = ''
        if email_obj.received_at:
            date_str = email_obj.received_at.strftime('%Y-%m-%d %H:%M')
        elif email_obj.sent_at:
            date_str = email_obj.sent_at.strftime('%Y-%m-%d %H:%M')
        elif email_obj.created_at:
            date_str = email_obj.created_at.strftime('%Y-%m-%d %H:%M')

        labels_data = [{'name': l.name, 'color': l.color} for l in email_obj.labels.all()]
        attachments_data = [{'filename': a.filename, 'url': a.file.url} for a in email_obj.attachments.all() if a.file]

        return JsonResponse({
            'id': email_obj.id,
            'subject': email_obj.subject,
            'sender_name': email_obj.sender_name,
            'sender_email': email_obj.sender_email,
            'recipients': email_obj.recipients,
            'cc': email_obj.cc,
            'body_text': email_obj.body_text,
            'body_html': email_obj.body_html,
            'date': date_str,
            'message_uid': email_obj.message_uid,
            'is_starred': email_obj.is_starred,
            'folder': email_obj.folder,
            'labels': labels_data,
            'attachments': attachments_data,
        })

    context = {
        'email': email_obj,
        'thread': thread,
        'accounts': models.EmailAccount.objects.filter(is_active=True),
    }

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return render(request, 'admin/email_detail_partial.html', context)
    return render(request, 'admin/email_detail.html', context)


def email_compose(request):
    """Compose and send a new email"""
    if "name" not in request.session:
        return redirect('/manager/login/')

    if request.method == 'POST':
        account_id = request.POST.get('account_id')
        to = request.POST.get('to', '').strip()
        cc = request.POST.get('cc', '').strip()
        bcc = request.POST.get('bcc', '').strip()
        subject = request.POST.get('subject', '').strip()
        body = request.POST.get('body', '').strip()
        html_body = request.POST.get('html_body', '').strip()
        is_draft = request.POST.get('save_draft') == '1'
        in_reply_to = request.POST.get('in_reply_to', '').strip()

        if not account_id:
            return JsonResponse({'success': False, 'error': '请选择发送账户'})

        account = get_object_or_404(models.EmailAccount, id=account_id)

        email_obj = models.EmailMessage.objects.create(
            account=account,
            sender_name=account.name,
            sender_email=account.email_address,
            recipients=to,
            cc=cc,
            bcc=bcc,
            subject=subject or '(无主题)',
            body_text=body,
            body_html=html_body,
            folder='draft' if is_draft else 'sent',
            is_read=True,
            in_reply_to=in_reply_to,
            sent_at=None if is_draft else timezone.now(),
        )

        if not is_draft:
            try:
                attachments = request.FILES.getlist('attachments')
                _send_email(
                    account=account,
                    to=to,
                    subject=subject,
                    body=body,
                    cc=cc,
                    bcc=bcc,
                    html_body=html_body,
                    in_reply_to=in_reply_to,
                    attachments=attachments if attachments else None,
                )

                for att_file in attachments:
                    models.EmailAttachment.objects.create(
                        email=email_obj,
                        filename=att_file.name,
                        content_type=att_file.content_type or '',
                        file=att_file,
                        size=att_file.size,
                    )

                return JsonResponse({'success': True, 'message': '邮件发送成功'})
            except Exception as e:
                logger.error(f'Email send failed: {e}')
                email_obj.folder = 'draft'
                email_obj.sent_at = None
                email_obj.save()
                return JsonResponse({'success': False, 'error': f'发送失败: {str(e)}'})
        else:
            return JsonResponse({'success': True, 'message': '草稿已保存'})

    # GET: return compose data
    accounts = models.EmailAccount.objects.filter(is_active=True)
    reply_to = request.GET.get('reply_to', '')
    reply_email = None
    if reply_to:
        try:
            reply_email = models.EmailMessage.objects.get(id=reply_to)
        except models.EmailMessage.DoesNotExist:
            pass

    context = {
        'accounts': accounts,
        'reply_email': reply_email,
    }

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return render(request, 'admin/email_compose_partial.html', context)
    return JsonResponse({'accounts': list(accounts.values('id', 'name', 'email_address'))})


def email_sync(request):
    """Sync emails from IMAP server(s)"""
    if "name" not in request.session:
        return redirect('/manager/login/')

    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'POST required'}, status=405)

    account_id = request.POST.get('account_id', '')
    if account_id:
        accounts = models.EmailAccount.objects.filter(id=account_id, is_active=True)
    else:
        accounts = models.EmailAccount.objects.filter(is_active=True)

    total_new = 0
    errors = []

    for account in accounts:
        try:
            new_count = _fetch_emails_imap(account)
            total_new += new_count
            account.last_sync = timezone.now()
            account.save(update_fields=['last_sync'])
        except Exception as e:
            logger.error(f'IMAP sync failed for {account.email_address}: {e}')
            errors.append(f'{account.email_address}: {str(e)}')

    return JsonResponse({
        'success': True,
        'new_emails': total_new,
        'errors': errors,
        'message': f'同步完成，共 {total_new} 封新邮件' + (f'，{len(errors)} 个错误' if errors else ''),
    })


def _fetch_emails_imap(account, folder='INBOX', max_emails=50):
    """Fetch emails from IMAP for a single account with incremental sync"""
    if account.imap_use_ssl:
        mail = imaplib.IMAP4_SSL(account.imap_host, account.imap_port, timeout=30)
    else:
        mail = imaplib.IMAP4(account.imap_host, account.imap_port, timeout=30)

    mail.login(account.username, account.password)
    mail.select(folder)

    existing_uids = set(
        models.EmailMessage.objects.filter(account=account)
        .exclude(message_uid='')
        .values_list('message_uid', flat=True)
    )

    # Incremental sync: only fetch emails since last sync date
    search_criteria = 'ALL'
    if account.last_sync:
        since_date = account.last_sync.strftime('%d-%b-%Y')
        search_criteria = f'(SINCE {since_date})'

    status, data = mail.search(None, search_criteria)
    if status != 'OK':
        mail.logout()
        return 0

    email_ids = data[0].split()
    if not email_ids:
        mail.logout()
        return 0

    recent_ids = email_ids[-max_emails:]
    new_count = 0

    for eid in recent_ids:
        status, msg_data = mail.fetch(eid, '(RFC822 FLAGS)')
        if status != 'OK':
            continue

        raw_email = msg_data[0][1]
        msg = email_lib.message_from_bytes(raw_email)

        msg_uid = msg.get('Message-ID', '')
        if msg_uid in existing_uids:
            continue

        subject = _decode_header_value(msg.get('Subject', ''))
        from_raw = msg.get('From', '')
        from_name, from_email_addr = parseaddr(from_raw)
        from_name = _decode_header_value(from_name) or from_email_addr
        to_raw = _decode_header_value(msg.get('To', ''))
        cc_raw = _decode_header_value(msg.get('Cc', ''))

        date_str = msg.get('Date', '')
        received_at = None
        if date_str:
            try:
                received_at = parsedate_to_datetime(date_str)
            except Exception:
                received_at = timezone.now()
        else:
            received_at = timezone.now()

        body_text = ''
        body_html = ''
        if msg.is_multipart():
            for part in msg.walk():
                content_type = part.get_content_type()
                content_disp = str(part.get('Content-Disposition', ''))
                if 'attachment' in content_disp:
                    continue
                payload = part.get_payload(decode=True)
                if payload:
                    charset = part.get_content_charset() or 'utf-8'
                    text = payload.decode(charset, errors='replace')
                    if content_type == 'text/plain':
                        body_text = text
                    elif content_type == 'text/html':
                        body_html = text
        else:
            payload = msg.get_payload(decode=True)
            if payload:
                charset = msg.get_content_charset() or 'utf-8'
                body_text = payload.decode(charset, errors='replace')

        flags_raw = msg_data[0][0] if isinstance(msg_data[0], tuple) else b''
        is_read = b'\\Seen' in flags_raw
        in_reply_to = msg.get('In-Reply-To', '')

        email_obj = models.EmailMessage.objects.create(
            account=account,
            message_uid=msg_uid,
            sender_name=from_name,
            sender_email=from_email_addr,
            recipients=to_raw,
            cc=cc_raw,
            subject=subject or '(无主题)',
            body_text=body_text,
            body_html=body_html,
            folder='inbox',
            is_read=is_read,
            received_at=received_at,
            in_reply_to=in_reply_to,
        )

        if msg.is_multipart():
            for part in msg.walk():
                content_disp = str(part.get('Content-Disposition', ''))
                if 'attachment' in content_disp:
                    filename = _decode_header_value(part.get_filename() or 'attachment')
                    payload = part.get_payload(decode=True)
                    if payload:
                        from django.core.files.base import ContentFile
                        att = models.EmailAttachment(
                            email=email_obj,
                            filename=filename,
                            content_type=part.get_content_type() or '',
                            size=len(payload),
                        )
                        att.file.save(filename, ContentFile(payload), save=True)

        _apply_auto_rules(email_obj)
        new_count += 1

    mail.logout()
    return new_count


def email_action(request):
    """AJAX: perform actions on emails"""
    if "name" not in request.session:
        return JsonResponse({'success': False, 'error': 'Not authenticated'}, status=401)

    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'POST required'}, status=405)

    action = request.POST.get('action', '')
    email_ids_raw = request.POST.get('ids', '')

    try:
        email_ids = [int(i) for i in email_ids_raw.split(',') if i.strip().isdigit()]
    except ValueError:
        return JsonResponse({'success': False, 'error': 'Invalid IDs'}, status=400)

    if not email_ids:
        return JsonResponse({'success': False, 'error': 'No emails selected'}, status=400)

    qs = models.EmailMessage.objects.filter(id__in=email_ids)

    if action == 'mark_read':
        qs.update(is_read=True)
    elif action == 'mark_unread':
        qs.update(is_read=False)
    elif action == 'star':
        qs.update(is_starred=True)
    elif action == 'unstar':
        qs.update(is_starred=False)
    elif action == 'toggle_star':
        for e in qs:
            e.is_starred = not e.is_starred
            e.save(update_fields=['is_starred'])
    elif action == 'trash':
        qs.update(folder='trash')
    elif action == 'archive':
        qs.update(folder='archive')
    elif action == 'move_inbox':
        qs.update(folder='inbox')
    elif action == 'delete':
        qs.delete()
    elif action == 'add_label':
        label_id = request.POST.get('label_id')
        if label_id:
            label = get_object_or_404(models.EmailLabel, id=label_id)
            for e in qs:
                e.labels.add(label)
    elif action == 'remove_label':
        label_id = request.POST.get('label_id')
        if label_id:
            label = get_object_or_404(models.EmailLabel, id=label_id)
            for e in qs:
                e.labels.remove(label)
    else:
        return JsonResponse({'success': False, 'error': 'Unknown action'}, status=400)

    unread = models.EmailMessage.objects.filter(folder='inbox', is_read=False).count()
    return JsonResponse({'success': True, 'unread_count': unread})


# ---- Email Account Management ----

def email_accounts(request):
    """Manage email accounts"""
    if "name" not in request.session:
        return redirect('/manager/login/')

    if request.method == 'POST':
        action = request.POST.get('action', '')

        if action == 'add':
            account = models.EmailAccount(
                name=request.POST.get('name', '').strip(),
                email_address=request.POST.get('email_address', '').strip(),
                imap_host=request.POST.get('imap_host', 'imap.gmail.com').strip(),
                imap_port=int(request.POST.get('imap_port', 993)),
                imap_use_ssl=request.POST.get('imap_use_ssl') == 'on',
                smtp_host=request.POST.get('smtp_host', 'smtp.gmail.com').strip(),
                smtp_port=int(request.POST.get('smtp_port', 587)),
                smtp_use_tls=request.POST.get('smtp_use_tls') == 'on',
                username=request.POST.get('username', '').strip(),
                password=request.POST.get('password', '').strip(),
                is_active=True,
                is_default=request.POST.get('is_default') == 'on',
            )
            account.save()
            if account.is_default:
                models.EmailAccount.objects.exclude(id=account.id).update(is_default=False)
            return JsonResponse({'success': True, 'message': '账户添加成功', 'id': account.id})

        elif action == 'edit':
            acc_id = request.POST.get('id')
            account = get_object_or_404(models.EmailAccount, id=acc_id)
            account.name = request.POST.get('name', account.name).strip()
            account.email_address = request.POST.get('email_address', account.email_address).strip()
            account.imap_host = request.POST.get('imap_host', account.imap_host).strip()
            account.imap_port = int(request.POST.get('imap_port', account.imap_port))
            account.imap_use_ssl = request.POST.get('imap_use_ssl') == 'on'
            account.smtp_host = request.POST.get('smtp_host', account.smtp_host).strip()
            account.smtp_port = int(request.POST.get('smtp_port', account.smtp_port))
            account.smtp_use_tls = request.POST.get('smtp_use_tls') == 'on'
            account.username = request.POST.get('username', account.username).strip()
            pwd = request.POST.get('password', '').strip()
            if pwd:
                account.password = pwd
            account.is_default = request.POST.get('is_default') == 'on'
            account.is_active = request.POST.get('is_active', 'on') == 'on'
            account.save()
            if account.is_default:
                models.EmailAccount.objects.exclude(id=account.id).update(is_default=False)
            return JsonResponse({'success': True, 'message': '账户更新成功'})

        elif action == 'delete':
            acc_id = request.POST.get('id')
            models.EmailAccount.objects.filter(id=acc_id).delete()
            return JsonResponse({'success': True, 'message': '账户已删除'})

        elif action == 'test':
            acc_id = request.POST.get('id')
            account = get_object_or_404(models.EmailAccount, id=acc_id)
            errors = []
            try:
                if account.imap_use_ssl:
                    m = imaplib.IMAP4_SSL(account.imap_host, account.imap_port, timeout=15)
                else:
                    m = imaplib.IMAP4(account.imap_host, account.imap_port, timeout=15)
                m.login(account.username, account.password)
                m.logout()
            except Exception as e:
                errors.append(f'IMAP: {str(e)}')
            try:
                if account.smtp_use_tls:
                    s = smtplib.SMTP(account.smtp_host, account.smtp_port, timeout=15)
                    s.starttls()
                else:
                    s = smtplib.SMTP_SSL(account.smtp_host, account.smtp_port, timeout=15)
                s.login(account.username, account.password)
                s.quit()
            except Exception as e:
                errors.append(f'SMTP: {str(e)}')

            if errors:
                return JsonResponse({'success': False, 'error': '; '.join(errors)})
            return JsonResponse({'success': True, 'message': '连接测试成功'})

    accounts = models.EmailAccount.objects.all()
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({
            'accounts': list(accounts.values(
                'id', 'name', 'email_address', 'imap_host', 'imap_port',
                'smtp_host', 'smtp_port', 'is_active', 'is_default', 'last_sync'
            ))
        })
    return render(request, 'admin/email_accounts.html', {'accounts': accounts})


# ---- Email Labels Management ----

def email_labels(request):
    """Manage email labels"""
    if "name" not in request.session:
        return JsonResponse({'success': False, 'error': 'Not authenticated'}, status=401)

    if request.method == 'POST':
        action = request.POST.get('action', '')
        if action == 'add':
            label = models.EmailLabel.objects.create(
                name=request.POST.get('name', '').strip(),
                color=request.POST.get('color', '#667eea').strip(),
                icon=request.POST.get('icon', 'fa-tag').strip(),
            )
            return JsonResponse({'success': True, 'id': label.id, 'message': '标签创建成功'})
        elif action == 'edit':
            label = get_object_or_404(models.EmailLabel, id=request.POST.get('id'))
            label.name = request.POST.get('name', label.name).strip()
            label.color = request.POST.get('color', label.color).strip()
            label.icon = request.POST.get('icon', label.icon).strip()
            label.save()
            return JsonResponse({'success': True, 'message': '标签更新成功'})
        elif action == 'delete':
            models.EmailLabel.objects.filter(id=request.POST.get('id')).delete()
            return JsonResponse({'success': True, 'message': '标签已删除'})

    labels = models.EmailLabel.objects.all()
    return JsonResponse({'labels': list(labels.values('id', 'name', 'color', 'icon'))})


# ---- Email Auto-Rules Management ----

def email_rules(request):
    """Manage email auto-rules"""
    if "name" not in request.session:
        return redirect('/manager/login/')

    if request.method == 'POST':
        action = request.POST.get('action', '')

        if action == 'add':
            label_id = request.POST.get('action_label')
            account_id = request.POST.get('apply_to_account')
            rule = models.EmailAutoRule.objects.create(
                name=request.POST.get('name', '').strip(),
                is_active=request.POST.get('is_active', 'on') == 'on',
                match_field=request.POST.get('match_field', 'any'),
                match_pattern=request.POST.get('match_pattern', '').strip(),
                action=request.POST.get('rule_action', 'label'),
                action_label_id=int(label_id) if label_id else None,
                action_forward_to=request.POST.get('action_forward_to', '').strip(),
                auto_reply_subject=request.POST.get('auto_reply_subject', '').strip(),
                auto_reply_body=request.POST.get('auto_reply_body', '').strip(),
                apply_to_account_id=int(account_id) if account_id else None,
                priority=int(request.POST.get('priority', 0)),
            )
            return JsonResponse({'success': True, 'id': rule.id, 'message': '规则创建成功'})

        elif action == 'edit':
            rule = get_object_or_404(models.EmailAutoRule, id=request.POST.get('id'))
            rule.name = request.POST.get('name', rule.name).strip()
            rule.is_active = request.POST.get('is_active', 'on') == 'on'
            rule.match_field = request.POST.get('match_field', rule.match_field)
            rule.match_pattern = request.POST.get('match_pattern', rule.match_pattern).strip()
            rule.action = request.POST.get('rule_action', rule.action)
            label_id = request.POST.get('action_label')
            rule.action_label_id = int(label_id) if label_id else None
            rule.action_forward_to = request.POST.get('action_forward_to', '').strip()
            rule.auto_reply_subject = request.POST.get('auto_reply_subject', '').strip()
            rule.auto_reply_body = request.POST.get('auto_reply_body', '').strip()
            account_id = request.POST.get('apply_to_account')
            rule.apply_to_account_id = int(account_id) if account_id else None
            rule.priority = int(request.POST.get('priority', rule.priority))
            rule.save()
            return JsonResponse({'success': True, 'message': '规则更新成功'})

        elif action == 'delete':
            models.EmailAutoRule.objects.filter(id=request.POST.get('id')).delete()
            return JsonResponse({'success': True, 'message': '规则已删除'})

        elif action == 'toggle':
            rule = get_object_or_404(models.EmailAutoRule, id=request.POST.get('id'))
            rule.is_active = not rule.is_active
            rule.save(update_fields=['is_active'])
            return JsonResponse({'success': True, 'is_active': rule.is_active})

    rules = models.EmailAutoRule.objects.select_related('action_label', 'apply_to_account').all()
    labels = models.EmailLabel.objects.all()
    accounts = models.EmailAccount.objects.filter(is_active=True)

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({
            'rules': list(rules.values(
                'id', 'name', 'is_active', 'match_field', 'match_pattern',
                'action', 'action_label__name', 'action_forward_to',
                'auto_reply_subject', 'priority'
            ))
        })
    return render(request, 'admin/email_rules.html', {
        'rules': rules, 'labels': labels, 'accounts': accounts
    })


# ==========================================
# Site User Authentication Views
# ==========================================

def _hash_password(password):
    """Hash password with SHA-256 + salt"""
    salt = 'book_project_salt_2024'
    return hashlib.sha256(f'{salt}{password}'.encode()).hexdigest()


import random
import string


def _generate_pin():
    """Generate a 6-digit PIN code"""
    return ''.join(random.choices(string.digits, k=6))


def _send_verification_email(email, pin_code, name):
    """Send verification PIN code via Django's email backend"""
    subject = 'DUNO 360 - 邮箱验证码 / Email Verification'
    html_body = f'''
    <div style="font-family:'Segoe UI',Arial,sans-serif;max-width:520px;margin:0 auto;background:#fff;border-radius:16px;overflow:hidden;box-shadow:0 4px 24px rgba(0,0,0,0.08);">
        <div style="background:linear-gradient(135deg,#667eea 0%,#764ba2 100%);padding:32px 28px;text-align:center;">
            <h1 style="color:#fff;margin:0;font-size:1.5rem;">📚 ScholarQuest</h1>
            <p style="color:rgba(255,255,255,0.85);margin:8px 0 0;font-size:0.95rem;">邮箱验证 / Email Verification</p>
        </div>
        <div style="padding:32px 28px;">
            <p style="color:#333;font-size:1rem;margin:0 0 8px;">你好，<strong>{name}</strong>！</p>
            <p style="color:#666;font-size:0.93rem;line-height:1.7;margin:0 0 24px;">
                感谢您注册我们的图书平台。请使用以下验证码完成注册：<br>
                Thank you for registering. Please use the PIN code below to verify your account:
            </p>
            <div style="background:linear-gradient(135deg,rgba(102,126,234,0.08),rgba(118,75,162,0.08));border:2px dashed #667eea;border-radius:14px;padding:24px;text-align:center;margin:0 0 24px;">
                <span style="font-size:2.5rem;font-weight:800;letter-spacing:12px;color:#667eea;">{pin_code}</span>
            </div>
            <p style="color:#999;font-size:0.85rem;text-align:center;margin:0;">
                ⏰ 验证码有效期为 <strong>15分钟</strong> / This code expires in <strong>15 minutes</strong>
            </p>
        </div>
        <div style="background:#f8f9ff;padding:16px 28px;text-align:center;border-top:1px solid #eee;">
            <p style="color:#aaa;font-size:0.8rem;margin:0;">如果您没有注册，请忽略此邮件。<br>If you did not register, please ignore this email.</p>
        </div>
    </div>
    '''
    plain_body = f'你好 {name}，你的验证码是: {pin_code}。有效期15分钟。\nHi {name}, your verification code is: {pin_code}. Valid for 15 minutes.'

    try:
        from django.core.mail import EmailMultiAlternatives
        msg = EmailMultiAlternatives(subject, plain_body, django_settings.DEFAULT_FROM_EMAIL, [email])
        msg.attach_alternative(html_body, 'text/html')
        msg.send(fail_silently=False)
        return True
    except Exception as e:
        logger.error(f'Failed to send verification email to {email}: {e}')
        return False


def user_register(request):
    """Public user registration - Step 1: collect info & send PIN"""
    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        email = request.POST.get('email', '').strip()
        password = request.POST.get('password', '').strip()
        password2 = request.POST.get('password2', '').strip()

        if not all([name, email, password]):
            return JsonResponse({'success': False, 'message': '请填写所有必填字段'})
        if password != password2:
            return JsonResponse({'success': False, 'message': '两次密码不一致'})
        if len(password) < 6:
            return JsonResponse({'success': False, 'message': '密码至少6位'})
        if models.SiteUser.objects.filter(email=email).exists():
            return JsonResponse({'success': False, 'message': '该邮箱已注册'})

        # Generate PIN and store pending registration
        pin_code = _generate_pin()
        expires_at = timezone.now() + timedelta(minutes=15)

        # Delete any previous pending verifications for this email
        models.EmailVerification.objects.filter(email=email, is_verified=False).delete()

        models.EmailVerification.objects.create(
            email=email,
            pin_code=pin_code,
            name=name,
            password=_hash_password(password),
            phone=request.POST.get('phone', '').strip(),
            expires_at=expires_at,
        )

        # Send PIN via email
        sent = _send_verification_email(email, pin_code, name)
        if not sent:
            return JsonResponse({'success': False, 'message': '验证邮件发送失败，请稍后重试'})

        return JsonResponse({
            'success': True,
            'message': '验证码已发送到您的邮箱',
            'redirect': f'/manager/public/user/verify-email/?email={email}',
        })

    return render(request, 'public/user_register.html')


def verify_email_pin(request):
    """Step 2: User enters PIN to complete registration"""
    email = request.GET.get('email', '') or request.POST.get('email', '')

    if request.method == 'POST':
        pin = request.POST.get('pin', '').strip()
        email = request.POST.get('email', '').strip()

        if not pin or not email:
            return JsonResponse({'success': False, 'message': '请输入验证码'})

        try:
            verification = models.EmailVerification.objects.get(
                email=email, is_verified=False
            )
        except models.EmailVerification.DoesNotExist:
            return JsonResponse({'success': False, 'message': '验证记录不存在，请重新注册'})

        if verification.is_expired():
            return JsonResponse({'success': False, 'message': '验证码已过期，请重新发送'})

        if verification.pin_code != pin:
            return JsonResponse({'success': False, 'message': '验证码不正确'})

        # PIN is correct — create the actual user account
        if models.SiteUser.objects.filter(email=email).exists():
            return JsonResponse({'success': False, 'message': '该邮箱已注册'})

        user = models.SiteUser.objects.create(
            name=verification.name,
            email=verification.email,
            password=verification.password,
            phone=verification.phone,
        )
        verification.is_verified = True
        verification.save(update_fields=['is_verified'])

        # Create notification for new user
        create_notification(
            'new_user',
            f'新用户注册: {user.name}',
            f'{user.name} ({user.email}) 完成了注册',
            icon='fas fa-user-plus',
            color='#10b981',
            link='/manager/admin/users/',
            related_id=user.id,
        )

        # Auto-login
        request.session['site_user_id'] = user.id
        request.session['site_user_name'] = user.name

        return JsonResponse({
            'success': True,
            'message': '验证成功，注册完成！',
            'redirect': '/manager/public/user/profile/',
        })

    return render(request, 'public/verify_email.html', {'email': email})


def resend_verification_pin(request):
    """Resend a new PIN code for pending registration"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': 'Invalid request'})

    email = request.POST.get('email', '').strip()
    if not email:
        return JsonResponse({'success': False, 'message': '缺少邮箱'})

    try:
        verification = models.EmailVerification.objects.get(email=email, is_verified=False)
    except models.EmailVerification.DoesNotExist:
        return JsonResponse({'success': False, 'message': '没有找到待验证记录，请重新注册'})

    # Generate new PIN
    new_pin = _generate_pin()
    verification.pin_code = new_pin
    verification.expires_at = timezone.now() + timedelta(minutes=15)
    verification.save(update_fields=['pin_code', 'expires_at'])

    sent = _send_verification_email(email, new_pin, verification.name)
    if not sent:
        return JsonResponse({'success': False, 'message': '邮件发送失败，请稍后重试'})

    return JsonResponse({'success': True, 'message': '新验证码已发送'})


def user_login(request):
    """Public user login"""
    if request.method == 'POST':
        email = request.POST.get('email', '').strip()
        password = request.POST.get('password', '').strip()

        if not all([email, password]):
            return JsonResponse({'success': False, 'message': '请输入邮箱和密码'})

        try:
            user = models.SiteUser.objects.get(email=email, is_active=True)
        except models.SiteUser.DoesNotExist:
            return JsonResponse({'success': False, 'message': '邮箱或密码错误'})

        if user.password != _hash_password(password):
            return JsonResponse({'success': False, 'message': '邮箱或密码错误'})

        request.session['site_user_id'] = user.id
        request.session['site_user_name'] = user.name
        next_url = request.POST.get('next') or '/manager/public/my-profile/'
        return JsonResponse({'success': True, 'message': '登录成功', 'redirect': next_url})

    return render(request, 'public/user_login.html')


def user_logout(request):
    """Public user logout"""
    request.session.pop('site_user_id', None)
    request.session.pop('site_user_name', None)
    return redirect('/manager/public/')


def user_profile(request):
    """User profile page with orders, favorites, and course progress"""
    user_id = request.session.get('site_user_id')
    if not user_id:
        return redirect('/manager/public/user/login/')

    user = get_object_or_404(models.SiteUser, id=user_id, is_active=True)

    if request.method == 'POST':
        user.name = request.POST.get('name', user.name).strip()
        user.phone = request.POST.get('phone', '').strip()
        if 'avatar' in request.FILES:
            user.avatar = request.FILES['avatar']
        user.save()
        request.session['site_user_name'] = user.name
        return JsonResponse({'success': True, 'message': '资料已更新'})

    # Get book orders
    book_orders = models.Order.objects.filter(
        customer_email=user.email
    ).prefetch_related('orderitem_set__book').order_by('-created_at')[:10]

    # Get marketplace orders
    mkt_orders = list(MarketplaceOrder.objects.filter(
        user_email=user.email
    ).order_by('-created_at')[:10])

    # Merge and sort all orders
    all_orders = []
    for o in book_orders:
        all_orders.append({
            'type': 'book',
            'order': o,
            'order_number': o.order_number,
            'created_at': o.created_at,
            'total_amount': o.total_amount,
            'status_display': o.get_status_display(),
            'items': list(o.orderitem_set.all()),
        })
    for o in mkt_orders:
        all_orders.append({
            'type': 'marketplace',
            'order': o,
            'order_number': o.order_number,
            'created_at': o.created_at,
            'total_amount': o.total_amount,
            'status_display': o.get_status_display(),
            'items': list(o.items.all()),
        })
    all_orders.sort(key=lambda x: x['created_at'], reverse=True)

    # Wishlists - all types
    wishlists = models.Wishlist.objects.filter(user=user).select_related('book')
    wishlist_data = []
    for w in wishlists:
        if w.item_type == 'book' and w.book:
            wishlist_data.append({
                'id': w.id,
                'item_type': 'book',
                'item_id': w.book.id,
                'name': w.book.name,
                'price': w.book.price,
                'image_url': w.book.get_cover_url() if hasattr(w.book, 'get_cover_url') else '',
                'detail_url': f'/manager/public/books/{w.book.id}/',
            })
        else:
            item = w.get_item()
            if item:
                if w.item_type == 'course':
                    detail_url = f'/marketplace/courses/{item.slug}/'
                elif w.item_type == 'product':
                    detail_url = f'/marketplace/products/{item.slug}/'
                elif w.item_type == 'supermarket':
                    detail_url = f'/marketplace/supermarket/{item.slug}/'
                else:
                    detail_url = '#'
                wishlist_data.append({
                    'id': w.id,
                    'item_type': w.item_type,
                    'item_id': w.item_id,
                    'name': w.get_item_name(),
                    'price': w.get_item_price(),
                    'image_url': w.get_item_image_url(),
                    'detail_url': detail_url,
                })

    # Course progress
    session_key = get_session_key(request)
    courses_progress = []
    try:
        # Get all courses the user has progress in
        progress_records = CourseProgress.objects.filter(
            session_key=session_key
        ).select_related('course', 'lesson')

        course_ids = set(p.course_id for p in progress_records)
        for course_id in course_ids:
            course = Course.objects.filter(pk=course_id).first()
            if not course:
                continue
            total_lessons = CourseLesson.objects.filter(
                section__course=course
            ).count()
            completed_lessons = progress_records.filter(
                course_id=course_id, completed=True
            ).count()
            progress_pct = int((completed_lessons / total_lessons * 100)) if total_lessons > 0 else 0
            courses_progress.append({
                'course': course,
                'total_lessons': total_lessons,
                'completed_lessons': completed_lessons,
                'progress_pct': progress_pct,
                'detail_url': f'/marketplace/courses/{course.slug}/',
            })
    except Exception:
        pass

    context = {
        'site_user': user,
        'orders': book_orders,  # backward compat
        'all_orders': all_orders,
        'wishlists': wishlists,  # backward compat
        'wishlist_data': wishlist_data,
        'courses_progress': courses_progress,
    }
    # Loyalty / gamification
    try:
        loyalty = models.LoyaltyPoints.objects.filter(user=user).first()
        point_transactions = models.PointTransaction.objects.filter(
            user=user
        ).order_by('-created_at')[:15] if loyalty else []
        context['loyalty'] = loyalty
        context['point_transactions'] = list(point_transactions)
    except Exception:
        context['loyalty'] = None
        context['point_transactions'] = []
    return render(request, 'public/user_profile.html', context)


def user_toggle_wishlist(request):
    """Toggle item in wishlist via AJAX - supports books and marketplace items"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': 'Invalid request'})

    user_id = request.session.get('site_user_id')
    if not user_id:
        return JsonResponse({'success': False, 'message': '请先登录', 'login_required': True})

    item_type = request.POST.get('item_type', 'book')
    item_id = request.POST.get('item_id') or request.POST.get('book_id')
    if not item_id:
        return JsonResponse({'success': False, 'message': '缺少参数'})

    item_id = int(item_id)

    if item_type == 'book':
        book = get_object_or_404(models.Book, id=item_id)
        wish, created = models.Wishlist.objects.get_or_create(
            user_id=user_id, book=book, item_type='book',
            defaults={'item_id': item_id}
        )
    else:
        # Marketplace item - verify it exists
        item = _get_marketplace_item(item_type, item_id)
        if not item:
            return JsonResponse({'success': False, 'message': '商品不存在'})
        wish, created = models.Wishlist.objects.get_or_create(
            user_id=user_id, item_type=item_type, item_id=item_id,
            defaults={'book': None}
        )

    if not created:
        wish.delete()
        return JsonResponse({'success': True, 'wishlisted': False, 'message': '已取消收藏'})
    return JsonResponse({'success': True, 'wishlisted': True, 'message': '已添加到收藏'})


def user_check_wishlist(request):
    """Check if an item is in the user's wishlist"""
    user_id = request.session.get('site_user_id')
    if not user_id:
        return JsonResponse({'wishlisted': False})

    item_type = request.GET.get('item_type', 'book')
    item_id = request.GET.get('item_id') or request.GET.get('book_id')

    if item_type == 'book':
        wishlisted = models.Wishlist.objects.filter(user_id=user_id, book_id=item_id, item_type='book').exists()
    else:
        wishlisted = models.Wishlist.objects.filter(user_id=user_id, item_type=item_type, item_id=int(item_id)).exists()

    return JsonResponse({'wishlisted': wishlisted})


# Admin CRUD for site users
def admin_site_users(request):
    """Admin view to manage site users"""
    if "name" not in request.session:
        return redirect('/manager/login/')

    users = models.SiteUser.objects.all()
    search = request.GET.get('search', '')
    status_filter = request.GET.get('status', '')
    if search:
        users = users.filter(Q(name__icontains=search) | Q(email__icontains=search) | Q(phone__icontains=search))
    if status_filter == 'active':
        users = users.filter(is_active=True)
    elif status_filter == 'inactive':
        users = users.filter(is_active=False)

    context = {
        'users': users,
        'search_query': search,
        'status_filter': status_filter,
        'total_users': models.SiteUser.objects.count(),
        'name': request.session.get('name', ''),
    }
    return render(request, 'admin/site_users.html', context)


def admin_toggle_user(request):
    """Toggle user active status"""
    if "name" not in request.session:
        return JsonResponse({'success': False, 'message': '未授权'})
    if request.method == 'POST':
        user = get_object_or_404(models.SiteUser, id=request.POST.get('id'))
        user.is_active = not user.is_active
        user.save(update_fields=['is_active'])
        return JsonResponse({'success': True, 'is_active': user.is_active})
    return JsonResponse({'success': False})


def admin_delete_user(request):
    """Delete a site user"""
    if "name" not in request.session:
        return JsonResponse({'success': False, 'message': '未授权'})
    if request.method == 'POST':
        models.SiteUser.objects.filter(id=request.POST.get('id')).delete()
        return JsonResponse({'success': True, 'message': '用户已删除'})
    return JsonResponse({'success': False})


# ==========================================
# Vendor / Seller Views
# ==========================================

def vendor_register(request):
    """Vendor registration page - Step 1: collect info & send PIN"""
    if request.method == 'POST':
        company_name = request.POST.get('company_name', '').strip()
        contact_name = request.POST.get('contact_name', '').strip()
        email = request.POST.get('email', '').strip()
        password = request.POST.get('password', '').strip()
        password2 = request.POST.get('password2', '').strip()

        if not all([company_name, contact_name, email, password]):
            return JsonResponse({'success': False, 'message': '请填写所有必填字段'})
        if password != password2:
            return JsonResponse({'success': False, 'message': '两次密码不一致'})
        if len(password) < 6:
            return JsonResponse({'success': False, 'message': '密码至少6位'})
        if models.Vendor.objects.filter(email=email).exists():
            return JsonResponse({'success': False, 'message': '该邮箱已注册为卖家'})

        pin_code = _generate_pin()
        expires_at = timezone.now() + timedelta(minutes=15)

        # Clean old unverified records for this email
        models.EmailVerification.objects.filter(email=email, is_verified=False).delete()

        models.EmailVerification.objects.create(
            email=email,
            pin_code=pin_code,
            name=contact_name,
            password=_hash_password(password),
            phone=request.POST.get('phone', '').strip(),
            verification_type='vendor',
            company_name=company_name,
            description=request.POST.get('description', '').strip(),
            expires_at=expires_at,
        )

        # Handle logo: store temporarily in session
        if 'logo' in request.FILES:
            logo_file = request.FILES['logo']
            import os
            from django.conf import settings as django_conf_settings
            tmp_dir = os.path.join(django_conf_settings.MEDIA_ROOT, 'tmp_vendor_logos')
            os.makedirs(tmp_dir, exist_ok=True)
            tmp_path = os.path.join(tmp_dir, f'{email}_{logo_file.name}')
            with open(tmp_path, 'wb') as f:
                for chunk in logo_file.chunks():
                    f.write(chunk)
            request.session['vendor_tmp_logo'] = tmp_path
            request.session['vendor_tmp_logo_name'] = logo_file.name

        sent = _send_verification_email(email, pin_code, contact_name)
        if not sent:
            return JsonResponse({'success': False, 'message': '验证邮件发送失败，请稍后重试'})

        return JsonResponse({
            'success': True,
            'message': '验证码已发送到您的邮箱',
            'redirect': f'/manager/vendor/verify-email/?email={email}',
        })

    return render(request, 'public/vendor_register.html')


def verify_vendor_pin(request):
    """Step 2: Vendor enters PIN to complete registration"""
    email = request.GET.get('email', '') or request.POST.get('email', '')

    if request.method == 'POST':
        pin = request.POST.get('pin', '').strip()
        email = request.POST.get('email', '').strip()

        if not pin or not email:
            return JsonResponse({'success': False, 'message': '请输入验证码'})

        try:
            verification = models.EmailVerification.objects.get(
                email=email, is_verified=False, verification_type='vendor'
            )
        except models.EmailVerification.DoesNotExist:
            return JsonResponse({'success': False, 'message': '验证记录不存在，请重新注册'})

        if verification.is_expired():
            return JsonResponse({'success': False, 'message': '验证码已过期，请重新发送'})

        if verification.pin_code != pin:
            return JsonResponse({'success': False, 'message': '验证码不正确'})

        if models.Vendor.objects.filter(email=email).exists():
            return JsonResponse({'success': False, 'message': '该邮箱已注册为卖家'})

        vendor = models.Vendor.objects.create(
            company_name=verification.company_name,
            contact_name=verification.name,
            email=verification.email,
            password=verification.password,
            phone=verification.phone,
            description=verification.description,
        )

        # Handle temporary logo file
        tmp_logo = request.session.pop('vendor_tmp_logo', None)
        tmp_logo_name = request.session.pop('vendor_tmp_logo_name', None)
        if tmp_logo and tmp_logo_name:
            import os
            if os.path.exists(tmp_logo):
                from django.core.files import File
                with open(tmp_logo, 'rb') as f:
                    vendor.logo.save(tmp_logo_name, File(f), save=True)
                os.remove(tmp_logo)

        verification.is_verified = True
        verification.save(update_fields=['is_verified'])

        create_notification(
            'vendor_registered',
            f'新卖家注册: {vendor.company_name}',
            f'{vendor.company_name} ({vendor.email}) 完成邮箱验证并注册了卖家账户，等待审核',
            icon='fas fa-store',
            color='#667eea',
            link='/manager/admin/vendors/',
            related_id=vendor.id,
        )

        request.session['vendor_id'] = vendor.id
        request.session['vendor_name'] = vendor.company_name

        return JsonResponse({
            'success': True,
            'message': '验证成功，注册完成！请等待审核',
            'redirect': '/manager/vendor/dashboard/',
        })

    return render(request, 'public/verify_vendor_email.html', {'email': email})


def vendor_login(request):
    """Vendor login"""
    if request.method == 'POST':
        email = request.POST.get('email', '').strip()
        password = request.POST.get('password', '').strip()

        if not all([email, password]):
            return JsonResponse({'success': False, 'message': '请输入邮箱和密码'})

        try:
            vendor = models.Vendor.objects.get(email=email, is_active=True)
        except models.Vendor.DoesNotExist:
            return JsonResponse({'success': False, 'message': '邮箱或密码错误'})

        if vendor.password != _hash_password(password):
            return JsonResponse({'success': False, 'message': '邮箱或密码错误'})

        request.session['vendor_id'] = vendor.id
        request.session['vendor_name'] = vendor.company_name
        return JsonResponse({'success': True, 'message': '登录成功', 'redirect': '/manager/vendor/dashboard/'})

    return render(request, 'public/vendor_login.html')


def vendor_logout(request):
    """Vendor logout"""
    request.session.pop('vendor_id', None)
    request.session.pop('vendor_name', None)
    return redirect('/manager/public/')


# ==========================================
# Forgot Password / Password Reset
# ==========================================

def _send_reset_email(email, pin_code, name):
    """Send password reset PIN code"""
    subject = 'DUNO 360 - 密码重置验证码 / Password Reset'
    html_body = f'''
    <div style="font-family:'Segoe UI',Arial,sans-serif;max-width:520px;margin:0 auto;background:#fff;border-radius:16px;overflow:hidden;box-shadow:0 4px 24px rgba(0,0,0,0.08);">
        <div style="background:linear-gradient(135deg,#667eea 0%,#764ba2 100%);padding:32px 28px;text-align:center;">
            <h1 style="color:#fff;margin:0;font-size:1.5rem;">🔐 DUNO 360</h1>
            <p style="color:rgba(255,255,255,0.85);margin:8px 0 0;font-size:0.95rem;">密码重置 / Password Reset</p>
        </div>
        <div style="padding:32px 28px;">
            <p style="color:#333;font-size:1rem;margin:0 0 8px;">你好，<strong>{name}</strong>！</p>
            <p style="color:#666;font-size:0.93rem;line-height:1.7;margin:0 0 24px;">
                您申请了密码重置，请使用以下验证码：<br>
                You requested a password reset. Use the code below:
            </p>
            <div style="background:linear-gradient(135deg,rgba(102,126,234,0.08),rgba(118,75,162,0.08));border:2px dashed #667eea;border-radius:14px;padding:24px;text-align:center;margin:0 0 24px;">
                <span style="font-size:2.5rem;font-weight:800;letter-spacing:12px;color:#667eea;">{pin_code}</span>
            </div>
            <p style="color:#999;font-size:0.85rem;text-align:center;margin:0;">
                ⏰ 验证码有效期为 <strong>15分钟</strong> / This code expires in <strong>15 minutes</strong>
            </p>
        </div>
        <div style="background:#f8f9ff;padding:16px 28px;text-align:center;border-top:1px solid #eee;">
            <p style="color:#aaa;font-size:0.8rem;margin:0;">如果您没有申请密码重置，请忽略此邮件。<br>If you did not request a password reset, please ignore this email.</p>
        </div>
    </div>
    '''
    plain_body = f'你好 {name}，你的密码重置验证码是: {pin_code}。有效期15分钟。\nHi {name}, your password reset code is: {pin_code}. Valid for 15 minutes.'

    try:
        from django.core.mail import EmailMultiAlternatives
        msg = EmailMultiAlternatives(subject, plain_body, django_settings.DEFAULT_FROM_EMAIL, [email])
        msg.attach_alternative(html_body, 'text/html')
        msg.send(fail_silently=False)
        return True
    except Exception as e:
        logger.error(f'Failed to send reset email to {email}: {e}')
        return False


def forgot_password(request):
    """Step 1: User/Vendor enters email to receive reset PIN"""
    account_type = request.GET.get('type', 'user')  # 'user' or 'vendor'

    if request.method == 'POST':
        email = request.POST.get('email', '').strip()
        account_type = request.POST.get('account_type', 'user')

        if not email:
            return JsonResponse({'success': False, 'message': '请输入邮箱'})

        # Check if account exists
        name = ''
        if account_type == 'vendor':
            try:
                vendor = models.Vendor.objects.get(email=email, is_active=True)
                name = vendor.contact_name
            except models.Vendor.DoesNotExist:
                return JsonResponse({'success': False, 'message': '未找到该邮箱对应的卖家账户'})
        else:
            try:
                user = models.SiteUser.objects.get(email=email, is_active=True)
                name = user.name
            except models.SiteUser.DoesNotExist:
                return JsonResponse({'success': False, 'message': '未找到该邮箱对应的用户账户'})

        # Clean old reset verifications for this email
        models.EmailVerification.objects.filter(
            email=email, verification_type='password_reset', is_verified=False
        ).delete()

        # Create reset verification
        pin_code = _generate_pin()
        models.EmailVerification.objects.create(
            email=email,
            pin_code=pin_code,
            name=name,
            password='',  # Not used for reset
            verification_type='password_reset',
            company_name=account_type,  # Reuse field to store account type
            expires_at=timezone.now() + timezone.timedelta(minutes=15),
        )

        sent = _send_reset_email(email, pin_code, name)
        if sent:
            return JsonResponse({'success': True, 'message': '验证码已发送到您的邮箱', 'email': email, 'account_type': account_type})
        else:
            return JsonResponse({'success': True, 'message': '验证码已生成（开发模式：' + pin_code + '）', 'email': email, 'account_type': account_type})

    return render(request, 'public/forgot_password.html', {'account_type': account_type})


def reset_password_verify(request):
    """Step 2: Verify PIN and set new password"""
    if request.method == 'POST':
        email = request.POST.get('email', '').strip()
        pin_code = request.POST.get('pin_code', '').strip()
        new_password = request.POST.get('new_password', '').strip()
        account_type = request.POST.get('account_type', 'user')

        if not all([email, pin_code, new_password]):
            return JsonResponse({'success': False, 'message': '请填写所有字段'})

        if len(new_password) < 6:
            return JsonResponse({'success': False, 'message': '密码长度至少6个字符'})

        # Find the verification record
        try:
            verification = models.EmailVerification.objects.get(
                email=email,
                pin_code=pin_code,
                verification_type='password_reset',
                is_verified=False,
            )
        except models.EmailVerification.DoesNotExist:
            return JsonResponse({'success': False, 'message': '验证码无效'})

        if verification.is_expired():
            verification.delete()
            return JsonResponse({'success': False, 'message': '验证码已过期，请重新获取'})

        # Update password
        hashed = _hash_password(new_password)
        if account_type == 'vendor':
            updated = models.Vendor.objects.filter(email=email, is_active=True).update(password=hashed)
        else:
            updated = models.SiteUser.objects.filter(email=email, is_active=True).update(password=hashed)

        if updated:
            verification.is_verified = True
            verification.save()
            redirect_url = '/manager/vendor/login/' if account_type == 'vendor' else '/manager/public/user/login/'
            return JsonResponse({'success': True, 'message': '密码重置成功！请用新密码登录', 'redirect': redirect_url})
        else:
            return JsonResponse({'success': False, 'message': '账户不存在或已被禁用'})

    return JsonResponse({'success': False, 'message': '无效请求'})


def _get_vendor(request):
    """Get the currently logged-in vendor or None"""
    vendor_id = request.session.get('vendor_id')
    if not vendor_id:
        return None
    try:
        return models.Vendor.objects.get(id=vendor_id, is_active=True)
    except models.Vendor.DoesNotExist:
        return None


def vendor_dashboard(request):
    """Vendor dashboard"""
    # Allow admin to access any vendor dashboard
    admin_access = request.session.get("name")
    vendor = _get_vendor(request)

    if not vendor and not admin_access:
        return redirect('/manager/vendor/login/')

    # If admin is viewing, allow seeing any vendor via query param
    if admin_access and not vendor:
        vendor_id = request.GET.get('vendor_id')
        if vendor_id:
            vendor = get_object_or_404(models.Vendor, id=vendor_id)
        else:
            # Show vendor list for admin
            vendors = models.Vendor.objects.all()
            return render(request, 'admin/vendor_list.html', {
                'vendors': vendors,
                'total_vendors': vendors.count(),
            })

    vendor_books = models.VendorBook.objects.filter(vendor=vendor).select_related('book', 'book__publisher')
    total_sales = sum(vb.book.sale_num for vb in vendor_books)
    total_revenue = sum(vb.vendor_price * vb.book.sale_num for vb in vendor_books)
    active_books = sum(1 for vb in vendor_books if vb.is_active)
    inactive_books = vendor_books.count() - active_books
    avg_price = sum(vb.vendor_price for vb in vendor_books) / vendor_books.count() if vendor_books.count() > 0 else 0
    best_seller = max(vendor_books, key=lambda vb: vb.book.sale_num) if vendor_books.exists() else None
    total_inventory = sum(vb.book.inventory for vb in vendor_books)

    # --- Customer behavior analytics ---
    vendor_book_ids = [vb.book_id for vb in vendor_books]

    # Purchases: customers who bought vendor's books (from completed orders)
    purchase_data = []
    if vendor_book_ids:
        purchased_items = models.OrderItem.objects.filter(
            book_id__in=vendor_book_ids,
            order__status__in=['paid', 'confirmed', 'processing', 'shipped', 'delivered']
        ).select_related('order', 'book').order_by('-order__created_at')[:50]
        for item in purchased_items:
            purchase_data.append({
                'book_name': item.book.name,
                'customer_name': item.order.customer_name,
                'customer_email': item.order.customer_email,
                'quantity': item.quantity,
                'total_price': item.total_price,
                'date': item.order.created_at,
                'status': item.order.get_status_display(),
            })

    # Cart abandonment: items in cart for vendor's books
    cart_data = []
    if vendor_book_ids:
        cart_items = models.CartItem.objects.filter(
            book_id__in=vendor_book_ids
        ).select_related('book').order_by('-updated_at')[:50]
        for ci in cart_items:
            cart_data.append({
                'book_name': ci.book.name,
                'quantity': ci.quantity,
                'session_key': ci.session_key[:8] + '...',
                'added_at': ci.created_at,
                'updated_at': ci.updated_at,
            })

    # Wishlist/Favorites: users who favorited vendor's books
    wishlist_data = []
    if vendor_book_ids:
        wishlists = models.Wishlist.objects.filter(
            book_id__in=vendor_book_ids
        ).select_related('user', 'book').order_by('-created_at')[:50]
        for w in wishlists:
            wishlist_data.append({
                'book_name': w.book.name,
                'user_name': w.user.name,
                'user_email': w.user.email,
                'added_at': w.created_at,
            })

    # Summary counts
    total_purchases = len(purchase_data)
    total_cart_items = len(cart_data)
    total_wishlists = len(wishlist_data)

    context = {
        'vendor': vendor,
        'vendor_books': vendor_books,
        'total_books': vendor_books.count(),
        'total_sales': total_sales,
        'total_revenue': total_revenue,
        'active_books': active_books,
        'inactive_books': inactive_books,
        'avg_price': avg_price,
        'best_seller': best_seller,
        'total_inventory': total_inventory,
        'admin_access': admin_access,
        # Customer behavior
        'purchase_data': purchase_data,
        'cart_data': cart_data,
        'wishlist_data': wishlist_data,
        'total_purchases': total_purchases,
        'total_cart_items': total_cart_items,
        'total_wishlists': total_wishlists,
    }
    return render(request, 'public/vendor_dashboard.html', context)


# ==========================================
# AI Chatbot System
# ==========================================


# Cache for platform context (avoids rebuilding on every message)
_platform_context_cache = {'text': None, 'stats': None, 'ts': 0}
_CONTEXT_CACHE_TTL = 60  # seconds


def _build_platform_context():
    """Build a detailed system prompt with real-time platform data. Cached for 60s."""
    import time
    now = time.time()
    if _platform_context_cache['text'] and (now - _platform_context_cache['ts']) < _CONTEXT_CACHE_TTL:
        return _platform_context_cache['text'], _platform_context_cache['stats']

    from django.db.models import Avg, Sum, Count, Q

    # --- Books ---
    books = models.Book.objects.select_related('publisher').prefetch_related('author_set').all()
    total_books = books.count()
    book_lines = []
    for b in books[:80]:  # cap for token budget
        authors = ', '.join(a.name for a in b.author_set.all()[:3])
        pub = b.publisher.publisher_name if b.publisher else '—'
        desc = b.get_short_description(60) if hasattr(b, 'get_short_description') else ''
        book_lines.append(
            f"  • 《{b.name}》| 价格: ¥{b.price} | 库存: {b.inventory} | "
            f"销量: {b.sale_num} | 作者: {authors or '—'} | 出版社: {pub}"
            + (f" | 简介: {desc}" if desc and desc != '暂无描述' else '')
        )
    book_section = '\n'.join(book_lines) if book_lines else '  （暂无图书数据）'

    # --- Authors ---
    authors_qs = models.Author.objects.prefetch_related('book').all()
    total_authors = authors_qs.count()
    author_lines = []
    for a in authors_qs[:40]:
        book_count = a.book.count()
        book_titles = '、'.join(b.name for b in a.book.all()[:3])
        author_lines.append(f"  • {a.name} | 作品({book_count}): {book_titles or '—'}")
    author_section = '\n'.join(author_lines) if author_lines else '  （暂无作者数据）'

    # --- Publishers ---
    publishers = models.Publisher.objects.annotate(book_count=Count('book')).all()
    total_publishers = publishers.count()
    pub_lines = []
    for p in publishers[:30]:
        pub_lines.append(f"  • {p.publisher_name} | 地址: {p.publisher_address} | 图书数: {p.book_count}")
    pub_section = '\n'.join(pub_lines) if pub_lines else '  （暂无出版社数据）'

    # --- Stats ---
    stats = books.aggregate(
        avg_price=Avg('price'),
        total_sales=Sum('sale_num'),
        total_inventory=Sum('inventory'),
    )
    avg_price = round(stats['avg_price'] or 0, 2)
    total_sales = stats['total_sales'] or 0
    total_inventory = stats['total_inventory'] or 0

    # --- Book Orders ---
    order_count = 0
    recent_order_info = ''
    try:
        order_qs = models.Order.objects.all()
        order_count = order_qs.count()
        recent_orders = order_qs.order_by('-created_at')[:5]
        order_lines = []
        for o in recent_orders:
            order_lines.append(f"  • 订单 {o.order_number} | ¥{o.total_amount} | 状态: {o.get_status_display()}")
        recent_order_info = '\n'.join(order_lines) if order_lines else '  （暂无订单）'
    except Exception:
        recent_order_info = '  （订单模块未启用）'

    # --- Bestsellers ---
    bestsellers = books.order_by('-sale_num')[:5]
    best_lines = []
    for i, b in enumerate(bestsellers, 1):
        best_lines.append(f"  {i}. 《{b.name}》— 销量 {b.sale_num}")
    bestseller_section = '\n'.join(best_lines) if best_lines else '  （暂无销量数据）'

    # --- Marketplace Data ---
    mkt_product_section = '  （市场模块未启用）'
    mkt_course_section = '  （课程模块未启用）'
    mkt_supermarket_section = '  （超市模块未启用）'
    mkt_order_section = '  （市场订单模块未启用）'
    total_products = 0
    total_courses = 0
    total_supermarket = 0
    mkt_order_count = 0

    try:
        from marketplace.models import Product, Course, SupermarketItem, MarketplaceOrder

        # Products
        products = Product.objects.filter(is_active=True)
        total_products = products.count()
        prod_lines = []
        for p in products[:30]:
            prod_lines.append(
                f"  • {p.name} | 价格: ¥{p.price} | 库存: {p.stock} | "
                f"品牌: {p.brand or '—'} | 销量: {p.sales_count}"
            )
        mkt_product_section = '\n'.join(prod_lines) if prod_lines else '  （暂无商品）'

        # Courses
        courses = Course.objects.filter(is_active=True)
        total_courses = courses.count()
        course_lines = []
        for c in courses[:20]:
            course_lines.append(
                f"  • {c.title} | 价格: ¥{c.price} | 讲师: {c.instructor} | "
                f"时长: {c.duration_hours}h | 级别: {c.get_level_display()} | 注册: {c.enrollment_count}"
            )
        mkt_course_section = '\n'.join(course_lines) if course_lines else '  （暂无课程）'

        # Supermarket
        supermarket = SupermarketItem.objects.filter(is_active=True)
        total_supermarket = supermarket.count()
        sm_lines = []
        for s in supermarket[:30]:
            sm_lines.append(
                f"  • {s.name} | 价格: ¥{s.price} | 库存: {s.stock} | "
                f"品牌: {s.brand or '—'} | 产地: {s.origin or '—'}"
            )
        mkt_supermarket_section = '\n'.join(sm_lines) if sm_lines else '  （暂无超市商品）'

        # Marketplace Orders
        mkt_orders = MarketplaceOrder.objects.all()
        mkt_order_count = mkt_orders.count()
        recent_mkt = mkt_orders.order_by('-created_at')[:5]
        mkt_order_lines = []
        for o in recent_mkt:
            mkt_order_lines.append(
                f"  • 订单 {o.order_number} | ¥{o.total_amount} | 状态: {o.get_status_display()} | 支付: {o.get_payment_status_display()}"
            )
        mkt_order_section = '\n'.join(mkt_order_lines) if mkt_order_lines else '  （暂无市场订单）'

    except Exception:
        pass  # Marketplace not available

    context_text = f"""===== 综合平台实时数据 =====
（以下数据来自数据库，实时更新）

【平台概况】
  图书数: {total_books} | 作者数: {total_authors} | 出版社数: {total_publishers}
  市场商品: {total_products} | 在线课程: {total_courses} | 超市商品: {total_supermarket}
  图书均价: ¥{avg_price} | 图书总销量: {total_sales} | 图书库存: {total_inventory}
  图书订单数: {order_count} | 市场订单数: {mkt_order_count}

【图书热销排行 TOP 5】
{bestseller_section}

【图书目录】
{book_section}

【作者列表】
{author_section}

【出版社列表】
{pub_section}

【市场商品】
{mkt_product_section}

【在线课程】
{mkt_course_section}

【超市商品】
{mkt_supermarket_section}

【最近图书订单】
{recent_order_info}

【最近市场订单】
{mkt_order_section}

【平台功能说明】
  • 图书商店：浏览、搜索、购买电子书，付款后可直接下载
  • 综合市场：包含商品、在线课程、生鲜超市三大板块
  • 统一购物车：图书和市场商品共享同一购物车和结算流程
  • 订单跟踪：支持通过订单号或邮箱查询订单状态（图书和市场订单均可）
  • 支付方式：微信支付、支付宝、PayPal、信用卡、MTN Money、Orange Money、Airtel Money、银行转账
  • AI智能助手：本聊天机器人，可回答平台相关问题
  • 多语言：支持中文、英文、法文三种语言
  • 收藏夹/心愿单：用户可收藏喜欢的图书
  • 博客系统：平台资讯和文章
  • 联系我们：可通过网站表单、邮件、微信、WhatsApp联系
  • 导航结构：首页、图书（下拉菜单含图书目录/作者/出版社）、市场、跟踪订单、博客、更多（下拉菜单含关于我们/服务/联系我们）
===== 数据结束 ====="""
    stats = {
        'total_books': total_books,
        'total_authors': total_authors,
        'total_publishers': total_publishers,
        'total_sales': total_sales,
        'avg_price': avg_price,
        'order_count': order_count,
        'total_products': total_products,
        'total_courses': total_courses,
        'total_supermarket': total_supermarket,
        'mkt_order_count': mkt_order_count,
    }
    # Update cache
    import time
    _platform_context_cache['text'] = context_text
    _platform_context_cache['stats'] = stats
    _platform_context_cache['ts'] = time.time()
    return context_text, stats

def _get_or_create_chat_session(request):
    """Get or create a ChatSession for this browser session."""
    config = models.ChatbotConfig.objects.filter(is_active=True).first()
    session_key = request.session.session_key
    if not session_key:
        request.session.create()
        session_key = request.session.session_key

    session, created = models.ChatSession.objects.get_or_create(
        session_key=session_key,
        defaults={'config': config},
    )
    # Link to user if logged in
    user_id = request.session.get('user_id')
    if user_id and not session.user_id:
        try:
            session.user = models.SiteUser.objects.get(id=user_id)
            session.save(update_fields=['user'])
        except models.SiteUser.DoesNotExist:
            pass
    return session


def _call_ai_api(config, messages_history):
    """
    Call the configured AI provider API.
    Returns (reply_text, tokens_used, error_message)
    """
    import urllib.request
    import urllib.error
    import ssl

    if not config or not config.api_key:
        return None, 0, '未配置 API Key，请在管理后台设置'

    provider = config.provider
    api_key = config.api_key
    model = config.get_default_model()
    max_tokens = config.max_tokens
    temperature = config.temperature

    # Build message list including system prompt + platform context
    platform_ctx, _ = _build_platform_context()
    base_prompt = config.system_prompt or (
        '你是一个友好、专业的综合平台智能助手。我们的平台集合了图书商店（电子书购买和下载）、'
        '综合市场（商品、在线视频课程、生鲜超市）、博客系统于一体。你帮助用户了解图书、课程、'
        '商品信息，回答关于购物、支付、订单跟踪等问题。用户可以通过订单号或邮箱查询图书和市场的订单。'
        '支付方式包含微信支付、支付宝、PayPal、信用卡、MTN/Orange/Airtel Money、银行转账等。'
        '请用简洁、友好的语言回答。如果用户的问题与平台数据有关，请基于下方提供的实时数据来回答。'
    )
    # Auto language detection instruction
    lang_instruction = (
        '\n\nIMPORTANT LANGUAGE RULE: You MUST detect the language of the user\'s message and '
        'reply in the SAME language. If the user writes in English, reply in English. '
        'If the user writes in French, reply in French. If the user writes in Chinese, reply in Chinese. '
        'If the user writes in any other language, reply in that language. '
        'Always match the user\'s language automatically.'
    )
    full_system_prompt = f"{base_prompt}{lang_instruction}\n\n{platform_ctx}"

    msgs = [{'role': 'system', 'content': full_system_prompt}]
    msgs.extend(messages_history)

    # --- OpenAI-compatible providers (OpenAI, DeepSeek, Qwen, OpenRouter, Custom) ---
    if provider in ('openai', 'deepseek', 'qwen', 'openrouter', 'custom'):
        if provider == 'openai':
            endpoint = config.api_endpoint or 'https://api.openai.com/v1/chat/completions'
        elif provider == 'deepseek':
            endpoint = config.api_endpoint or 'https://api.deepseek.com/chat/completions'
        elif provider == 'qwen':
            endpoint = config.api_endpoint or 'https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions'
        elif provider == 'openrouter':
            endpoint = config.api_endpoint or 'https://openrouter.ai/api/v1/chat/completions'
        else:
            endpoint = config.api_endpoint
            if not endpoint:
                return None, 0, '自定义 API 需要填写 API 地址'

        payload = {
            'model': model,
            'messages': msgs,
            'max_tokens': max_tokens,
            'temperature': temperature,
            'stream': False,
        }
        headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {api_key}',
        }
        if provider == 'openrouter':
            headers['HTTP-Referer'] = 'http://localhost:8000'
            headers['X-Title'] = 'DUNO 360'
        try:
            ctx = ssl.create_default_context()
            data = json.dumps(payload).encode('utf-8')
            req = urllib.request.Request(endpoint, data=data, headers=headers, method='POST')
            with urllib.request.urlopen(req, timeout=30, context=ctx) as resp:
                result = json.loads(resp.read().decode('utf-8'))
            text = result['choices'][0]['message']['content']
            tokens = result.get('usage', {}).get('total_tokens', 0)
            return text, tokens, None
        except urllib.error.HTTPError as e:
            body = e.read().decode('utf-8', errors='replace')
            return None, 0, f'API 错误 {e.code}: {body[:200]}'
        except Exception as e:
            return None, 0, f'请求失败: {str(e)[:200]}'

    # --- Anthropic Claude ---
    elif provider == 'anthropic':
        endpoint = config.api_endpoint or 'https://api.anthropic.com/v1/messages'
        # Anthropic uses system as separate field
        system_content = full_system_prompt
        user_msgs = [m for m in messages_history]  # without system
        payload = {
            'model': model,
            'max_tokens': max_tokens,
            'system': system_content,
            'messages': user_msgs,
        }
        headers = {
            'Content-Type': 'application/json',
            'x-api-key': api_key,
            'anthropic-version': '2023-06-01',
        }
        try:
            ctx = ssl.create_default_context()
            data = json.dumps(payload).encode('utf-8')
            req = urllib.request.Request(endpoint, data=data, headers=headers, method='POST')
            with urllib.request.urlopen(req, timeout=30, context=ctx) as resp:
                result = json.loads(resp.read().decode('utf-8'))
            text = result['content'][0]['text']
            tokens = result.get('usage', {}).get('input_tokens', 0) + result.get('usage', {}).get('output_tokens', 0)
            return text, tokens, None
        except urllib.error.HTTPError as e:
            body = e.read().decode('utf-8', errors='replace')
            return None, 0, f'API 错误 {e.code}: {body[:200]}'
        except Exception as e:
            return None, 0, f'请求失败: {str(e)[:200]}'

    # --- Google Gemini ---
    elif provider == 'google':
        endpoint = config.api_endpoint or f'https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent'
        # Convert messages to Gemini format
        gemini_msgs = []
        for m in messages_history:
            role = 'user' if m['role'] == 'user' else 'model'
            gemini_msgs.append({'role': role, 'parts': [{'text': m['content']}]})
        payload = {
            'contents': gemini_msgs,
            'generationConfig': {
                'maxOutputTokens': max_tokens,
                'temperature': temperature,
            },
            'systemInstruction': {'parts': [{'text': full_system_prompt}]},
        }
        url = f'{endpoint}?key={api_key}'
        headers = {'Content-Type': 'application/json'}
        try:
            ctx = ssl.create_default_context()
            data = json.dumps(payload).encode('utf-8')
            req = urllib.request.Request(url, data=data, headers=headers, method='POST')
            with urllib.request.urlopen(req, timeout=30, context=ctx) as resp:
                result = json.loads(resp.read().decode('utf-8'))
            text = result['candidates'][0]['content']['parts'][0]['text']
            tokens = result.get('usageMetadata', {}).get('totalTokenCount', 0)
            return text, tokens, None
        except urllib.error.HTTPError as e:
            body = e.read().decode('utf-8', errors='replace')
            return None, 0, f'API 错误 {e.code}: {body[:200]}'
        except Exception as e:
            return None, 0, f'请求失败: {str(e)[:200]}'

    return None, 0, f'不支持的 AI 提供商: {provider}'


def chatbot_send(request):
    """Handle user message, call AI, return response."""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': '仅支持 POST'})

    user_message = request.POST.get('message', '').strip()
    if not user_message:
        return JsonResponse({'success': False, 'message': '请输入消息'})
    if len(user_message) > 2000:
        return JsonResponse({'success': False, 'message': '消息太长（最多2000字符）'})

    config = models.ChatbotConfig.objects.filter(is_active=True).first()
    if not config:
        return JsonResponse({'success': False, 'message': '聊天机器人暂未配置'})

    session = _get_or_create_chat_session(request)

    # Check rate limit
    if session.message_count >= config.max_messages_per_session:
        return JsonResponse({'success': False, 'message': '本次会话消息已达上限，请刷新页面开始新会话'})

    # Save user message
    models.ChatMessage.objects.create(session=session, role='user', content=user_message)

    # Build history (last 10 turns = 20 messages)
    recent_msgs = list(models.ChatMessage.objects.filter(
        session=session, role__in=['user', 'assistant']
    ).order_by('-created_at')[:20])
    recent_msgs.reverse()
    history = [{'role': m.role, 'content': m.content} for m in recent_msgs]

    # Call AI
    reply, tokens_used, error = _call_ai_api(config, history)

    if error:
        return JsonResponse({'success': False, 'message': error})

    # Save assistant response
    models.ChatMessage.objects.create(session=session, role='assistant', content=reply, tokens_used=tokens_used)
    session.message_count += 2
    session.save(update_fields=['message_count', 'last_active'])

    return JsonResponse({
        'success': True,
        'reply': reply,
        'message_count': session.message_count,
    })


def chatbot_send_stream(request):
    """Stream AI response via Server-Sent Events for lower perceived latency."""
    from django.http import StreamingHttpResponse
    import urllib.request
    import urllib.error
    import ssl

    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': 'POST only'})

    user_message = request.POST.get('message', '').strip()
    if not user_message:
        return JsonResponse({'success': False, 'message': 'Empty message'})
    if len(user_message) > 2000:
        return JsonResponse({'success': False, 'message': 'Message too long'})

    config = models.ChatbotConfig.objects.filter(is_active=True).first()
    if not config:
        return JsonResponse({'success': False, 'message': 'Chatbot not configured'})

    session = _get_or_create_chat_session(request)
    if session.message_count >= config.max_messages_per_session:
        return JsonResponse({'success': False, 'message': 'Session limit reached'})

    # Save user message
    models.ChatMessage.objects.create(session=session, role='user', content=user_message)

    # Build history
    recent_msgs = list(models.ChatMessage.objects.filter(
        session=session, role__in=['user', 'assistant']
    ).order_by('-created_at')[:20])
    recent_msgs.reverse()
    history = [{'role': m.role, 'content': m.content} for m in recent_msgs]

    # Build system prompt
    platform_ctx, _ = _build_platform_context()
    base_prompt = config.system_prompt or (
        '你是一个友好、专业的综合平台智能助手。我们的平台集合了图书商店（电子书购买和下载）、'
        '综合市场（商品、在线视频课程、生鲜超市）、博客系统于一体。你帮助用户了解图书、课程、'
        '商品信息，回答关于购物、支付、订单跟踪等问题。用户可以通过订单号或邮箱查询图书和市场的订单。'
        '支付方式包含微信支付、支付宝、PayPal、信用卡、MTN/Orange/Airtel Money、银行转账等。'
        '请用简洁、友好的语言回答。如果用户的问题与平台数据有关，请基于下方提供的实时数据来回答。'
    )
    lang_instruction = (
        '\n\nIMPORTANT LANGUAGE RULE: You MUST detect the language of the user\'s message and '
        'reply in the SAME language. If the user writes in English, reply in English. '
        'If the user writes in French, reply in French. If the user writes in Chinese, reply in Chinese. '
        'If the user writes in any other language, reply in that language. '
        'Always match the user\'s language automatically.'
    )
    full_system_prompt = f"{base_prompt}{lang_instruction}\n\n{platform_ctx}"

    provider = config.provider
    api_key = config.api_key
    model = config.get_default_model()

    # Only OpenAI-compatible providers support streaming
    if provider not in ('openai', 'deepseek', 'qwen', 'openrouter', 'custom'):
        # Fallback to non-streaming
        reply, tokens_used, error = _call_ai_api(config, history)
        if error:
            return JsonResponse({'success': False, 'message': error})
        models.ChatMessage.objects.create(session=session, role='assistant', content=reply, tokens_used=tokens_used)
        session.message_count += 2
        session.save(update_fields=['message_count', 'last_active'])
        return JsonResponse({'success': True, 'reply': reply, 'message_count': session.message_count})

    # Streaming for OpenAI-compatible APIs
    endpoints = {
        'openai': 'https://api.openai.com/v1/chat/completions',
        'deepseek': 'https://api.deepseek.com/chat/completions',
        'qwen': 'https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions',
        'openrouter': 'https://openrouter.ai/api/v1/chat/completions',
    }
    endpoint = config.api_endpoint or endpoints.get(provider, '')
    if not endpoint:
        return JsonResponse({'success': False, 'message': 'No API endpoint configured'})

    msgs = [{'role': 'system', 'content': full_system_prompt}] + history
    payload = {
        'model': model,
        'messages': msgs,
        'max_tokens': config.max_tokens,
        'temperature': config.temperature,
        'stream': True,
    }
    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {api_key}',
    }
    if provider == 'openrouter':
        headers['HTTP-Referer'] = 'http://localhost:8000'
        headers['X-Title'] = 'DUNO 360'

    _session_ref = session  # closure reference

    def event_stream():
        full_reply = []
        try:
            ctx = ssl.create_default_context()
            data = json.dumps(payload).encode('utf-8')
            req = urllib.request.Request(endpoint, data=data, headers=headers, method='POST')
            resp = urllib.request.urlopen(req, timeout=60, context=ctx)

            # Read in larger chunks for efficiency, split on newlines
            leftover = b''
            while True:
                chunk = resp.read(4096)
                if not chunk:
                    break
                chunk = leftover + chunk
                parts = chunk.split(b'\n')
                leftover = parts.pop()  # may be incomplete line
                for raw_line in parts:
                    line = raw_line.decode('utf-8', errors='replace').strip()
                    if not line or not line.startswith('data: '):
                        continue
                    data_str = line[6:]
                    if data_str == '[DONE]':
                        leftover = b''
                        break
                    try:
                        obj = json.loads(data_str)
                        delta = obj.get('choices', [{}])[0].get('delta', {})
                        token = delta.get('content', '')
                        if token:
                            full_reply.append(token)
                            yield f"data: {json.dumps({'token': token})}\n\n"
                    except (json.JSONDecodeError, IndexError, KeyError):
                        continue
            resp.close()
        except Exception as e:
            yield f"data: {json.dumps({'error': str(e)[:200]})}\n\n"

        # Save complete reply
        complete_text = ''.join(full_reply)
        if complete_text:
            models.ChatMessage.objects.create(
                session=_session_ref, role='assistant',
                content=complete_text, tokens_used=0
            )
            _session_ref.message_count += 2
            _session_ref.save(update_fields=['message_count', 'last_active'])
        yield f"data: {json.dumps({'done': True})}\n\n"

    response = StreamingHttpResponse(event_stream(), content_type='text/event-stream')
    response['Cache-Control'] = 'no-cache'
    response['X-Accel-Buffering'] = 'no'
    return response


def chatbot_config_api(request):
    """Return public chatbot config (non-sensitive)."""
    config = models.ChatbotConfig.objects.filter(is_active=True).first()
    if not config:
        return JsonResponse({'active': False})
    return JsonResponse({
        'active': True,
        'widget_title': config.widget_title,
        'widget_subtitle': config.widget_subtitle,
        'welcome_message': config.welcome_message,
        'show_on_public': config.show_on_public,
        'show_on_admin': config.show_on_admin,
        'provider': config.get_provider_display(),
        'model': config.get_default_model(),
    })


def chatbot_history(request):
    """Return chat history for current session."""
    session_key = request.session.session_key
    if not session_key:
        return JsonResponse({'messages': []})
    try:
        session = models.ChatSession.objects.get(session_key=session_key)
        msgs = list(session.messages.filter(role__in=['user', 'assistant']).order_by('created_at')[:50].values(
            'role', 'content', 'created_at'
        ))
        for m in msgs:
            m['created_at'] = m['created_at'].strftime('%H:%M')
        return JsonResponse({'messages': msgs})
    except models.ChatSession.DoesNotExist:
        return JsonResponse({'messages': []})


# ==========================================
# Admin Chatbot Management
# ==========================================

def admin_chatbot_config(request):
    """Admin chatbot configuration page."""
    if 'name' not in request.session:
        return redirect('/manager/login/')

    config = models.ChatbotConfig.objects.filter(is_active=True).first()
    if not config:
        config = models.ChatbotConfig.objects.create()

    if request.method == 'POST':
        action = request.POST.get('action', 'save')

        if action == 'save':
            config.name = request.POST.get('name', config.name)
            config.provider = request.POST.get('provider', config.provider)
            new_key = request.POST.get('api_key', '').strip()
            if new_key and '*' not in new_key:
                config.api_key = new_key
            config.model_name = request.POST.get('model_name', '').strip()
            config.api_endpoint = request.POST.get('api_endpoint', '').strip()
            config.system_prompt = request.POST.get('system_prompt', '').strip()
            config.widget_title = request.POST.get('widget_title', config.widget_title)
            config.widget_subtitle = request.POST.get('widget_subtitle', config.widget_subtitle)
            config.welcome_message = request.POST.get('welcome_message', config.welcome_message)
            config.show_on_public = request.POST.get('show_on_public') == 'on'
            config.show_on_admin = request.POST.get('show_on_admin') == 'on'
            config.is_active = request.POST.get('is_active') == 'on'
            try:
                config.max_tokens = int(request.POST.get('max_tokens', config.max_tokens))
                config.temperature = float(request.POST.get('temperature', config.temperature))
                config.max_messages_per_session = int(request.POST.get('max_messages_per_session', config.max_messages_per_session))
            except (ValueError, TypeError):
                pass
            config.save()
            return JsonResponse({'success': True, 'message': '配置已保存'})

        elif action == 'test':
            test_msg = request.POST.get('test_message', '你好，请介绍一下自己。')
            reply, tokens, error = _call_ai_api(config, [{'role': 'user', 'content': test_msg}])
            if error:
                return JsonResponse({'success': False, 'message': error})
            return JsonResponse({'success': True, 'reply': reply, 'tokens': tokens})

        elif action == 'get_context':
            ctx_text, _ = _build_platform_context()
            return JsonResponse({'success': True, 'context': ctx_text})

        elif action == 'clear_sessions':
            models.ChatSession.objects.all().delete()
            return JsonResponse({'success': True, 'message': '已清除所有聊天会话'})

    # Platform stats
    _, platform_stats = _build_platform_context()
    total_sessions = models.ChatSession.objects.count()
    total_messages = models.ChatMessage.objects.count()
    active_sessions = models.ChatSession.objects.filter(is_closed=False).count()
    tokens_used = models.ChatMessage.objects.aggregate(t=Sum('tokens_used'))['t'] or 0
    recent_sessions = models.ChatSession.objects.order_by('-last_active')[:20]

    # Free API providers list
    free_providers = [
        {'name': 'OpenRouter', 'models': 'Llama 3.3, Nemotron, Qwen3, Mistral, Gemma…', 'note': '聚合网关，1 个 Key 访问 20+ 免费模型', 'url': 'https://openrouter.ai/keys'},
        {'name': 'Google AI Studio', 'models': 'Gemini 2.0 Flash, Gemini 1.5 Pro', 'note': '免费额度丰富，1500 次/天', 'url': 'https://aistudio.google.com/apikey'},
        {'name': 'Groq', 'models': 'Llama 3.3 70B, Mixtral, Gemma 2', 'note': '超快推理，免费每天 14400 请求', 'url': 'https://console.groq.com/keys'},
        {'name': 'Together AI', 'models': 'Llama 3, Mixtral, CodeLlama', 'note': '注册送 $25 免费额度', 'url': 'https://api.together.xyz/settings/api-keys'},
        {'name': 'DeepSeek', 'models': 'DeepSeek-V3, DeepSeek-R1', 'note': '价格极低，注册送 ¥10', 'url': 'https://platform.deepseek.com/api_keys'},
        {'name': 'Alibaba Qwen', 'models': 'Qwen-Plus, Qwen-Turbo, Qwen-Max', 'note': '中文优化，阿里云免费额度', 'url': 'https://dashscope.console.aliyun.com/apiKey'},
        {'name': 'Mistral AI', 'models': 'Mistral Small, Codestral', 'note': '欧洲 AI，免费试用', 'url': 'https://console.mistral.ai/api-keys/'},
        {'name': 'GitHub Models', 'models': 'GPT-4o, Llama 3, Phi-4', 'note': 'GitHub 账号免费使用', 'url': 'https://github.com/marketplace/models'},
    ]

    # Free OpenRouter models
    free_models_list = [
        ('nvidia/nemotron-3-super-120b-a12b:free', 'NVIDIA Nemotron 3 Super 120B', '高质量通用模型，推荐'),
        ('qwen/qwen3-next-80b-a3b-instruct:free', 'Qwen3 Next 80B', '中文优化，适合中文平台'),
        ('mistralai/mistral-small-3.1-24b-instruct:free', 'Mistral Small 3.1 24B', '快速响应，欧洲 AI'),
        ('qwen/qwen3-coder:free', 'Qwen3 Coder 480B', '编程与技术问答'),
        ('nvidia/nemotron-3-nano-30b-a3b:free', 'NVIDIA Nemotron Nano 30B', '轻量快速'),
        ('minimax/minimax-m2.5:free', 'MiniMax M2.5', '多语言支持'),
        ('stepfun/step-3.5-flash:free', 'StepFun Step 3.5 Flash', '超快推理'),
        ('openai/gpt-oss-120b:free', 'OpenAI GPT-OSS 120B', '开源 GPT 模型'),
        ('google/gemma-3n-e4b-it:free', 'Google Gemma 3n 4B', '轻量 Google 模型'),
    ]

    context = {
        'config': config,
        'total_sessions': total_sessions,
        'total_messages': total_messages,
        'active_sessions': active_sessions,
        'tokens_used': f'{tokens_used:,}',
        'recent_sessions': recent_sessions,
        'ai_providers': models.AI_PROVIDER_CHOICES,
        'free_providers': free_providers,
        'free_models_list': free_models_list,
        'total_books': platform_stats['total_books'],
        'total_authors': platform_stats['total_authors'],
        'total_publishers': platform_stats['total_publishers'],
        'total_products': platform_stats.get('total_products', 0),
        'total_courses': platform_stats.get('total_courses', 0),
        'total_supermarket': platform_stats.get('total_supermarket', 0),
        'mkt_order_count': platform_stats.get('mkt_order_count', 0),
        'name': request.session.get('name', ''),
    }
    return render(request, 'admin/chatbot_config.html', context)


def chatbot_contact_send(request):
    """User sends a customer service message from the chatbot widget"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': 'POST required'})

    name = request.POST.get('name', '').strip() or '匿名用户'
    email = request.POST.get('email', '').strip() or 'anonymous@chat.local'
    message = request.POST.get('message', '').strip()

    if not message:
        return JsonResponse({'success': False, 'message': '消息内容不能为空'})

    # Use session key to group messages from the same user
    if not request.session.session_key:
        request.session.create()
    session_key = request.session.session_key

    contact_msg = models.ContactMessage.objects.create(
        name=name,
        email=email,
        subject='[客服聊天] ' + message[:50],
        message=message,
        session_key=session_key,
    )

    # Create admin notification for CS chat message
    create_notification(
        'cs_chat',
        f'客服消息 - {name}',
        f'{message[:80]}',
        icon='fas fa-headset',
        color='#667eea',
        link=f'/manager/email/?folder=contact',
        related_id=contact_msg.id,
    )

    return JsonResponse({'success': True, 'message': '消息已发送，客服将尽快回复您'})


def chatbot_contact_replies(request):
    """User polls for admin replies to their customer service messages"""
    if not request.session.session_key:
        return JsonResponse({'success': True, 'replies': []})

    session_key = request.session.session_key
    # Get messages from this session that have admin replies
    replied_msgs = models.ContactMessage.objects.filter(
        session_key=session_key,
        replied=True,
    ).exclude(admin_reply='').order_by('replied_at')

    # Return only replies not yet seen (tracked via query param)
    last_seen = request.GET.get('after', '')
    if last_seen:
        try:
            from datetime import datetime
            last_dt = datetime.fromisoformat(last_seen)
            if timezone.is_naive(last_dt):
                last_dt = timezone.make_aware(last_dt)
            replied_msgs = replied_msgs.filter(replied_at__gt=last_dt)
        except (ValueError, TypeError):
            pass

    replies = [{
        'id': m.id,
        'original_message': m.message[:100],
        'reply': m.admin_reply,
        'replied_at': m.replied_at.isoformat() if m.replied_at else '',
    } for m in replied_msgs[:20]]

    return JsonResponse({'success': True, 'replies': replies})


def admin_contact_quick_reply(request):
    """Admin quick-replies to a contact message (text stored, no email sent)"""
    if "name" not in request.session:
        return JsonResponse({'success': False, 'message': '未授权'})
    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': 'POST required'})

    msg_id = request.POST.get('id')
    reply_text = request.POST.get('reply', '').strip()
    if not reply_text:
        return JsonResponse({'success': False, 'message': '回复内容不能为空'})

    msg = get_object_or_404(models.ContactMessage, id=msg_id)
    msg.admin_reply = reply_text
    msg.replied = True
    msg.replied_at = timezone.now()
    msg.is_read = True
    msg.save(update_fields=['admin_reply', 'replied', 'replied_at', 'is_read'])

    return JsonResponse({'success': True, 'message': '回复已发送'})


def vendor_add_book(request):
    """Vendor adds a book to sell"""
    vendor = _get_vendor(request)
    admin_access = request.session.get("name")
    if not vendor and not admin_access:
        return redirect('/manager/vendor/login/')

    # Handle inline creation of new publisher
    if request.method == 'POST' and request.POST.get('action') == 'create_publisher':
        pub_name = request.POST.get('publisher_name', '').strip()
        pub_address = request.POST.get('publisher_address', '').strip()
        if pub_name:
            pub = models.Publisher.objects.create(publisher_name=pub_name, publisher_address=pub_address)
            return JsonResponse({'success': True, 'id': pub.id, 'name': pub.publisher_name})
        return JsonResponse({'success': False, 'message': '出版社名称不能为空'})

    # Handle inline creation of new author
    if request.method == 'POST' and request.POST.get('action') == 'create_author':
        author_name = request.POST.get('author_name', '').strip()
        if author_name:
            author = models.Author.objects.create(name=author_name)
            return JsonResponse({'success': True, 'id': author.id, 'name': author.name})
        return JsonResponse({'success': False, 'message': '作者名称不能为空'})

    if request.method == 'POST':
        if admin_access and not vendor:
            vendor = get_object_or_404(models.Vendor, id=request.POST.get('vendor_id'))

        name = request.POST.get('name', '').strip()
        price = request.POST.get('price', '0')
        vendor_price = request.POST.get('vendor_price', price)
        inventory = request.POST.get('inventory', '0')
        description = request.POST.get('description', '').strip()
        publisher_id = request.POST.get('publisher_id')
        author_ids = request.POST.getlist('author_ids')
        book_file = request.FILES.get('book_file')
        download_link = request.POST.get('download_link', '').strip()

        if not name:
            return JsonResponse({'success': False, 'message': '请填写图书名称'})

        book = models.Book.objects.create(
            name=name,
            price=Decimal(price),
            inventory=int(inventory),
            sale_num=0,
            description=description,
            publisher_id=int(publisher_id) if publisher_id else None,
        )
        if 'cover_image' in request.FILES:
            book.cover_image = request.FILES['cover_image']
        else:
            # Auto-generate a stylish cover
            try:
                from manager.cover_generator import generate_cover_image
                book.cover_image = generate_cover_image(book.name, book.id)
            except Exception:
                pass

        if book_file:
            book.book_file = book_file
        if download_link:
            book.download_link = download_link

        book.save()

        # Associate authors with the book
        if author_ids:
            authors = models.Author.objects.filter(id__in=author_ids)
            for author in authors:
                author.book.add(book)

        models.VendorBook.objects.create(
            vendor=vendor,
            book=book,
            vendor_price=Decimal(vendor_price),
        )
        return JsonResponse({'success': True, 'message': '图书已上架'})

    publishers = models.Publisher.objects.all()
    authors = models.Author.objects.all()
    context = {
        'vendor': vendor,
        'publishers': publishers,
        'authors': authors,
        'admin_access': admin_access,
    }
    return render(request, 'public/vendor_add_book.html', context)


def vendor_toggle_book(request):
    """Toggle a vendor book active status"""
    vendor = _get_vendor(request)
    admin_access = request.session.get("name")
    if not vendor and not admin_access:
        return JsonResponse({'success': False, 'message': '未授权'})

    if request.method == 'POST':
        vb = get_object_or_404(models.VendorBook, id=request.POST.get('id'))
        if not admin_access and vb.vendor != vendor:
            return JsonResponse({'success': False, 'message': '无权限'})
        vb.is_active = not vb.is_active
        vb.save(update_fields=['is_active'])
        return JsonResponse({'success': True, 'is_active': vb.is_active})
    return JsonResponse({'success': False})


def vendor_edit_book(request):
    """Vendor edits an existing book"""
    vendor = _get_vendor(request)
    admin_access = request.session.get("name")
    if not vendor and not admin_access:
        return redirect('/manager/vendor/login/')

    if request.method == 'GET':
        vb_id = request.GET.get('id')
        vb = get_object_or_404(models.VendorBook, id=vb_id)
        if not admin_access and vb.vendor != vendor:
            return JsonResponse({'success': False, 'message': '无权限'})
        book = vb.book
        authors = models.Author.objects.all()
        book_author_ids = list(book.author_set.values_list('id', flat=True))
        publishers = models.Publisher.objects.all()
        return render(request, 'public/vendor_edit_book.html', {
            'vendor': vendor or vb.vendor,
            'vb': vb,
            'book': book,
            'publishers': publishers,
            'authors': authors,
            'book_author_ids': book_author_ids,
            'admin_access': admin_access,
        })

    if request.method == 'POST':
        # Handle inline creation of new publisher
        if request.POST.get('action') == 'create_publisher':
            pub_name = request.POST.get('publisher_name', '').strip()
            pub_address = request.POST.get('publisher_address', '').strip()
            if pub_name:
                pub = models.Publisher.objects.create(publisher_name=pub_name, publisher_address=pub_address)
                return JsonResponse({'success': True, 'id': pub.id, 'name': pub.publisher_name})
            return JsonResponse({'success': False, 'message': '出版社名称不能为空'})

        # Handle inline creation of new author
        if request.POST.get('action') == 'create_author':
            author_name = request.POST.get('author_name', '').strip()
            if author_name:
                author = models.Author.objects.create(name=author_name)
                return JsonResponse({'success': True, 'id': author.id, 'name': author.name})
            return JsonResponse({'success': False, 'message': '作者名称不能为空'})

        vb_id = request.POST.get('vb_id')
        vb = get_object_or_404(models.VendorBook, id=vb_id)
        if not admin_access and vb.vendor != vendor:
            return JsonResponse({'success': False, 'message': '无权限'})

        book = vb.book
        name = request.POST.get('name', '').strip()
        price = request.POST.get('price', '0')
        vendor_price = request.POST.get('vendor_price', price)
        inventory = request.POST.get('inventory', '0')
        description = request.POST.get('description', '').strip()
        publisher_id = request.POST.get('publisher_id')
        author_ids = request.POST.getlist('author_ids')

        if not name:
            return JsonResponse({'success': False, 'message': '请填写图书名称'})

        book.name = name
        book.price = Decimal(price)
        book.inventory = int(inventory)
        book.description = description
        if publisher_id:
            book.publisher_id = int(publisher_id)
        if 'cover_image' in request.FILES:
            book.cover_image = request.FILES['cover_image']
        if 'book_file' in request.FILES:
            book.book_file = request.FILES['book_file']
        download_link = request.POST.get('download_link', '').strip()
        if download_link:
            book.download_link = download_link
        elif request.POST.get('clear_download_link') == '1':
            book.download_link = ''
        book.save()

        # Update author associations
        book.author_set.clear()
        if author_ids:
            authors = models.Author.objects.filter(id__in=author_ids)
            for author in authors:
                author.book.add(book)

        vb.vendor_price = Decimal(vendor_price)
        vb.save(update_fields=['vendor_price'])

        return JsonResponse({'success': True, 'message': '图书信息已更新'})

    return JsonResponse({'success': False})


def vendor_delete_book(request):
    """Vendor removes a book from their listings"""
    vendor = _get_vendor(request)
    admin_access = request.session.get("name")
    if not vendor and not admin_access:
        return JsonResponse({'success': False, 'message': '未授权'})

    if request.method == 'POST':
        vb_id = request.POST.get('id')
        vb = get_object_or_404(models.VendorBook, id=vb_id)
        if not admin_access and vb.vendor != vendor:
            return JsonResponse({'success': False, 'message': '无权限'})
        vb.delete()
        return JsonResponse({'success': True, 'message': '图书已从您的店铺中移除'})
    return JsonResponse({'success': False})


# Admin vendor management
def admin_vendor_list(request):
    """Admin view all vendors with marketplace metrics"""
    if "name" not in request.session:
        return redirect('/manager/login/')

    vendors = models.Vendor.objects.all()
    search = request.GET.get('search', '')
    status_filter = request.GET.get('status', '')
    if search:
        vendors = vendors.filter(Q(company_name__icontains=search) | Q(email__icontains=search) | Q(contact_name__icontains=search))
    if status_filter in dict(models.VENDOR_STATUS_CHOICES):
        vendors = vendors.filter(status=status_filter)

    # Annotate vendors with marketplace metrics
    from django.db.models import Sum, Count, Avg
    vendors = vendors.annotate(
        product_count=Count('products', distinct=True),
        course_count=Count('courses', distinct=True),
        mp_total_sales=Sum('products__sales_count'),
        mp_total_stock=Sum('products__stock'),
        mp_total_enrollments=Sum('courses__enrollment_count'),
    )

    # Global marketplace metrics
    all_vendors = models.Vendor.objects.all()
    total_mp_products = Product.objects.filter(vendor__isnull=False).count()
    total_mp_courses = Course.objects.filter(vendor__isnull=False).count()
    total_mp_sales = Product.objects.filter(vendor__isnull=False).aggregate(s=Sum('sales_count'))['s'] or 0
    total_mp_enrollments = Course.objects.filter(vendor__isnull=False).aggregate(s=Sum('enrollment_count'))['s'] or 0
    total_mp_revenue = MarketplaceOrderItem.objects.filter(
        order__status__in=['paid', 'processing', 'shipped', 'delivered']
    ).aggregate(s=Sum('subtotal'))['s'] or 0

    # Top selling products across all vendors
    top_products = Product.objects.filter(
        vendor__isnull=False, sales_count__gt=0
    ).select_related('vendor', 'category').order_by('-sales_count')[:5]

    # Top vendors by product sales
    top_vendors = models.Vendor.objects.annotate(
        total_sales=Sum('products__sales_count')
    ).filter(total_sales__gt=0).order_by('-total_sales')[:5]

    # Vendor being viewed in detail (read-only)
    view_vendor_id = request.GET.get('view_vendor')
    viewed_vendor = None
    vendor_products_list = []
    vendor_courses_list = []
    vendor_books_list = []
    if view_vendor_id:
        viewed_vendor = models.Vendor.objects.filter(id=view_vendor_id).first()
        if viewed_vendor:
            vendor_products_list = Product.objects.filter(vendor=viewed_vendor).select_related('category').order_by('-created_at')[:50]
            vendor_courses_list = Course.objects.filter(vendor=viewed_vendor).select_related('category').order_by('-created_at')[:50]
            vendor_books_list = models.VendorBook.objects.filter(vendor=viewed_vendor).select_related('book', 'book__publisher').order_by('-created_at')[:50]

    return render(request, 'admin/vendor_list.html', {
        'vendors': vendors,
        'total_vendors': models.Vendor.objects.count(),
        'search_query': search,
        'status_filter': status_filter,
        'name': request.session.get('name', ''),
        'total_mp_products': total_mp_products,
        'total_mp_courses': total_mp_courses,
        'total_mp_sales': total_mp_sales,
        'total_mp_enrollments': total_mp_enrollments,
        'total_mp_revenue': total_mp_revenue,
        'top_products': top_products,
        'top_vendors': top_vendors,
        'viewed_vendor': viewed_vendor,
        'vendor_products_list': vendor_products_list,
        'vendor_courses_list': vendor_courses_list,
        'vendor_books_list': vendor_books_list,
    })


def admin_vendor_status(request):
    """Admin approve/reject/suspend vendor"""
    if "name" not in request.session:
        return JsonResponse({'success': False, 'message': '未授权'})
    if request.method == 'POST':
        vendor = get_object_or_404(models.Vendor, id=request.POST.get('id'))
        new_status = request.POST.get('status')
        if new_status in dict(models.VENDOR_STATUS_CHOICES):
            vendor.status = new_status
            vendor.save(update_fields=['status'])
            return JsonResponse({'success': True, 'message': f'状态已更新为 {vendor.get_status_display()}'})
    return JsonResponse({'success': False})


def admin_delete_vendor_item(request):
    """Admin delete a vendor's product or course from the platform"""
    if "name" not in request.session:
        return JsonResponse({'success': False, 'message': '未授权'})
    if request.method == 'POST':
        item_type = request.POST.get('type')
        item_id = request.POST.get('id')
        if item_type == 'product':
            item = get_object_or_404(Product, id=item_id)
            name = item.name
            item.delete()
            return JsonResponse({'success': True, 'message': f'商品 "{name}" 已删除'})
        elif item_type == 'course':
            item = get_object_or_404(Course, id=item_id)
            name = item.title
            item.delete()
            return JsonResponse({'success': True, 'message': f'课程 "{name}" 已删除'})
        elif item_type == 'book':
            item = get_object_or_404(models.VendorBook, id=item_id)
            name = item.book.name
            item.delete()
            return JsonResponse({'success': True, 'message': f'图书 "{name}" 已从卖家下架'})
    return JsonResponse({'success': False, 'message': '无效请求'})


# ==========================================
# Notification System
# ==========================================

def create_notification(ntype, title, message, icon='fas fa-bell', color='#667eea', link='', related_id=None):
    """Helper to create an admin notification"""
    models.AdminNotification.objects.create(
        notification_type=ntype,
        title=title,
        message=message,
        icon=icon,
        color=color,
        link=link,
        related_id=related_id,
    )


def check_and_create_notifications(request):
    """Generate notifications for pending events (called periodically)"""
    now = timezone.now()

    # 1. Incomplete registrations (PIN expired, not verified)
    expired_cutoff = now - timedelta(hours=1)
    expired_regs = models.EmailVerification.objects.filter(
        is_verified=False,
        expires_at__lt=now,
        created_at__gte=expired_cutoff,
    )
    for reg in expired_regs:
        exists = models.AdminNotification.objects.filter(
            notification_type='incomplete_registration',
            related_id=reg.id,
        ).exists()
        if not exists:
            create_notification(
                'incomplete_registration',
                f'用户 {reg.name} 注册未完成',
                f'{reg.email} 在注册时未在规定时间内完成验证（验证码已过期）',
                icon='fas fa-user-clock',
                color='#f59e0b',
                related_id=reg.id,
            )

    # 2. Abandoned carts (items in cart for > 30 minutes, no order)
    cart_cutoff = now - timedelta(minutes=30)
    stale_carts = models.CartItem.objects.filter(
        updated_at__lt=cart_cutoff,
    ).values('session_key').annotate(
        item_count=Count('id'),
        latest=Max('updated_at'),
    )
    for cart in stale_carts:
        exists = models.AdminNotification.objects.filter(
            notification_type='abandoned_cart',
            message__contains=cart['session_key'][:16],
            created_at__gte=now - timedelta(hours=2),
        ).exists()
        if not exists:
            items = models.CartItem.objects.filter(session_key=cart['session_key']).select_related('book')
            book_names = ', '.join([ci.book.name for ci in items[:3]])
            create_notification(
                'abandoned_cart',
                f'有顾客可能要下单（{cart["item_count"]}件商品）',
                f'购物车包含: {book_names}... 会话: {cart["session_key"][:16]}',
                icon='fas fa-shopping-cart',
                color='#06b6d4',
                link='/manager/order_list/',
            )


def admin_notifications_api(request):
    """API endpoint for notifications"""
    if "name" not in request.session:
        return JsonResponse({'success': False, 'message': '未授权'})

    if request.method == 'GET':
        # Check for new events first
        check_and_create_notifications(request)

        notifications = models.AdminNotification.objects.filter(is_dismissed=False)[:50]
        unread_count = models.AdminNotification.objects.filter(is_read=False, is_dismissed=False).count()

        data = [{
            'id': n.id,
            'type': n.notification_type,
            'type_display': n.get_notification_type_display(),
            'title': n.title,
            'message': n.message,
            'icon': n.icon,
            'color': n.color,
            'link': n.link,
            'is_read': n.is_read,
            'created_at': n.created_at.strftime('%Y-%m-%d %H:%M'),
            'time_ago': _time_ago(n.created_at),
        } for n in notifications]

        return JsonResponse({'success': True, 'notifications': data, 'unread_count': unread_count})

    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'mark_read':
            nid = request.POST.get('id')
            if nid:
                models.AdminNotification.objects.filter(id=nid).update(is_read=True)
            return JsonResponse({'success': True})
        elif action == 'mark_all_read':
            models.AdminNotification.objects.filter(is_read=False).update(is_read=True)
            return JsonResponse({'success': True})
        elif action == 'delete':
            nid = request.POST.get('id')
            if nid:
                models.AdminNotification.objects.filter(id=nid).delete()
            return JsonResponse({'success': True})
        elif action == 'clear_all':
            models.AdminNotification.objects.filter(is_read=True).update(is_dismissed=True)
            return JsonResponse({'success': True})

    return JsonResponse({'success': False})


def _time_ago(dt):
    """Return human-readable time ago string"""
    now = timezone.now()
    diff = now - dt
    seconds = diff.total_seconds()
    if seconds < 60:
        return '刚刚'
    elif seconds < 3600:
        return f'{int(seconds // 60)} 分钟前'
    elif seconds < 86400:
        return f'{int(seconds // 3600)} 小时前'
    elif seconds < 604800:
        return f'{int(seconds // 86400)} 天前'
    else:
        return dt.strftime('%m-%d %H:%M')


def admin_notifications_page(request):
    """Full notification management page"""
    if "name" not in request.session:
        return redirect('/manager/login/')

    # Generate any pending notifications
    check_and_create_notifications(request)

    notifications = models.AdminNotification.objects.all()

    # Filters
    type_filter = request.GET.get('type', '')
    read_filter = request.GET.get('read', '')
    if type_filter:
        notifications = notifications.filter(notification_type=type_filter)
    if read_filter == 'unread':
        notifications = notifications.filter(is_read=False)
    elif read_filter == 'read':
        notifications = notifications.filter(is_read=True)

    total = models.AdminNotification.objects.count()
    unread = models.AdminNotification.objects.filter(is_read=False).count()

    notif_list = []
    for n in notifications[:200]:
        notif_list.append({
            'id': n.id,
            'type': n.notification_type,
            'type_display': n.get_notification_type_display(),
            'title': n.title,
            'message': n.message,
            'icon': n.icon,
            'color': n.color,
            'link': n.link,
            'is_read': n.is_read,
            'related_id': n.related_id,
            'created_at': n.created_at,
            'time_ago': _time_ago(n.created_at),
        })

    context = {
        'notifications': notif_list,
        'total': total,
        'unread': unread,
        'read_count': total - unread,
        'type_filter': type_filter,
        'read_filter': read_filter,
        'notification_types': models.NOTIFICATION_TYPE_CHOICES,
        'name': request.session.get('name', ''),
    }
    return render(request, 'admin/notifications.html', context)


# ==========================================
# Enhanced Admin User Management (CRUD)
# ==========================================

def admin_edit_user(request):
    """Admin edit user"""
    if "name" not in request.session:
        return JsonResponse({'success': False, 'message': '未授权'})

    if request.method == 'GET':
        uid = request.GET.get('id')
        user = get_object_or_404(models.SiteUser, id=uid)
        return JsonResponse({
            'success': True,
            'user': {
                'id': user.id,
                'name': user.name,
                'email': user.email,
                'phone': user.phone,
                'is_active': user.is_active,
            }
        })

    if request.method == 'POST':
        uid = request.POST.get('id')
        user = get_object_or_404(models.SiteUser, id=uid)
        user.name = request.POST.get('name', user.name).strip()
        user.email = request.POST.get('email', user.email).strip()
        user.phone = request.POST.get('phone', user.phone).strip()
        is_active = request.POST.get('is_active')
        if is_active is not None:
            user.is_active = is_active == 'true'
        user.save()
        return JsonResponse({'success': True, 'message': '用户信息已更新'})

    return JsonResponse({'success': False})


def admin_add_user(request):
    """Admin add user manually"""
    if "name" not in request.session:
        return JsonResponse({'success': False, 'message': '未授权'})

    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        email = request.POST.get('email', '').strip()
        phone = request.POST.get('phone', '').strip()
        password = request.POST.get('password', '').strip()

        if not all([name, email, password]):
            return JsonResponse({'success': False, 'message': '姓名、邮箱和密码为必填项'})

        if models.SiteUser.objects.filter(email=email).exists():
            return JsonResponse({'success': False, 'message': '该邮箱已被注册'})

        user = models.SiteUser.objects.create(
            name=name,
            email=email,
            phone=phone,
            password=_hash_password(password),
            is_active=True,
        )
        create_notification(
            'new_user', f'管理员添加了用户 {name}',
            f'管理员手动添加了用户 {name} ({email})',
            icon='fas fa-user-plus', color='#10b981',
            link='/manager/admin/users/', related_id=user.id,
        )
        return JsonResponse({'success': True, 'message': f'用户 {name} 已创建'})

    return JsonResponse({'success': False})


# ==========================================
# Enhanced Admin Vendor Management (CRUD)
# ==========================================

def admin_edit_vendor(request):
    """Admin edit vendor"""
    if "name" not in request.session:
        return JsonResponse({'success': False, 'message': '未授权'})

    if request.method == 'GET':
        vid = request.GET.get('id')
        vendor = get_object_or_404(models.Vendor, id=vid)
        return JsonResponse({
            'success': True,
            'vendor': {
                'id': vendor.id,
                'company_name': vendor.company_name,
                'contact_name': vendor.contact_name,
                'email': vendor.email,
                'phone': vendor.phone,
                'description': vendor.description,
                'commission_rate': str(vendor.commission_rate),
                'status': vendor.status,
                'is_active': vendor.is_active,
            }
        })

    if request.method == 'POST':
        vid = request.POST.get('id')
        vendor = get_object_or_404(models.Vendor, id=vid)
        vendor.company_name = request.POST.get('company_name', vendor.company_name).strip()
        vendor.contact_name = request.POST.get('contact_name', vendor.contact_name).strip()
        vendor.email = request.POST.get('email', vendor.email).strip()
        vendor.phone = request.POST.get('phone', vendor.phone).strip()
        vendor.description = request.POST.get('description', vendor.description).strip()
        commission = request.POST.get('commission_rate')
        if commission:
            vendor.commission_rate = Decimal(commission)
        status = request.POST.get('status')
        if status and status in dict(models.VENDOR_STATUS_CHOICES):
            vendor.status = status
        is_active = request.POST.get('is_active')
        if is_active is not None:
            vendor.is_active = is_active == 'true'
        if 'logo' in request.FILES:
            vendor.logo = request.FILES['logo']
        vendor.save()
        return JsonResponse({'success': True, 'message': '卖家信息已更新'})

    return JsonResponse({'success': False})


def admin_add_vendor(request):
    """Admin add vendor manually"""
    if "name" not in request.session:
        return JsonResponse({'success': False, 'message': '未授权'})

    if request.method == 'POST':
        company_name = request.POST.get('company_name', '').strip()
        contact_name = request.POST.get('contact_name', '').strip()
        email = request.POST.get('email', '').strip()
        phone = request.POST.get('phone', '').strip()
        password = request.POST.get('password', '').strip()
        description = request.POST.get('description', '').strip()
        status = request.POST.get('status', 'approved')

        if not all([company_name, contact_name, email, password]):
            return JsonResponse({'success': False, 'message': '店铺名、联系人、邮箱和密码为必填项'})

        if models.Vendor.objects.filter(email=email).exists():
            return JsonResponse({'success': False, 'message': '该邮箱已被注册'})

        vendor = models.Vendor.objects.create(
            company_name=company_name,
            contact_name=contact_name,
            email=email,
            phone=phone,
            password=_hash_password(password),
            description=description,
            status=status,
        )
        if 'logo' in request.FILES:
            vendor.logo = request.FILES['logo']
            vendor.save()

        create_notification(
            'vendor_registered', f'管理员添加了卖家 {company_name}',
            f'管理员手动添加了卖家 {company_name} ({email})',
            icon='fas fa-store', color='#667eea',
            link='/manager/admin/vendors/', related_id=vendor.id,
        )
        return JsonResponse({'success': True, 'message': f'卖家 {company_name} 已创建'})

    return JsonResponse({'success': False})


def admin_delete_vendor(request):
    """Admin delete vendor"""
    if "name" not in request.session:
        return JsonResponse({'success': False, 'message': '未授权'})
    if request.method == 'POST':
        vid = request.POST.get('id')
        vendor = models.Vendor.objects.filter(id=vid).first()
        if vendor:
            name = vendor.company_name
            vendor.delete()
            return JsonResponse({'success': True, 'message': f'卖家 {name} 已删除'})
        return JsonResponse({'success': False, 'message': '卖家不存在'})
    return JsonResponse({'success': False})
