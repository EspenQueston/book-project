from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse, HttpResponse
from django.contrib import messages
from django.db import transaction
from django.views.decorators.http import require_http_methods, require_POST
from django.db.models import Sum, Avg, Q, Count, Max, F
from django.utils import timezone
from decimal import Decimal
from datetime import timedelta
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
import hashlib
import logging

logger = logging.getLogger(__name__)

# 方法实现（数据库操作和页面跳转）
# ====================   默认跳转  ===========================
def index(request):
    return redirect("/manager/login")


# ====================   管理员登录  ===========================
def manager_login(request):
    # 直接访问（get请求），原地跳转
    if request.method == "GET":
        return render(request, "admin/admin.html")
    # 提交表单请求（POST）
    if request.method == "POST":
        # 1.获取请求参数
        number = request.POST.get("number")
        password = request.POST.get("password")
        # 2.将数据保存到数据库中（insert）
        manager = models.Manager.objects.filter(number=number, password=password)
        if manager.exists():
            name = manager.first().name
            request.session["name"] = name
            # Redirect to dashboard instead of book list
            return redirect("/manager/dashboard/")
        return redirect("/manager/login")


# ====================   管理员登出  ===========================
def manager_logout(request):
    """Manager logout function - renamed from logout to avoid conflicts"""
    request.session.clear()
    return render(request, "admin/admin.html")


# Keep the old logout function for backward compatibility
def logout(request):
    """Legacy logout function - redirects to manager_logout"""
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
    # 登录判断
    if "name" not in request.session:
        return redirect("/manager/login")
    # 1获取要删除图书的id
    id = request.GET.get('id')
    # 2根据id删除数据库中的记录（delete）
    models.Publisher.objects.filter(id=id).delete()
    return redirect('/manager/publisher_list')


# ============================  二、图书模块操作   ===============================
# 01获取所有图书信息
def book_list(request):
    # 登录判断
    if "name" not in request.session:
        return redirect("/manager/login")
    # 1获取图书信息(select *)
    book_obj_list = models.Book.objects.all()
    # 2将数据渲染到页面上
    return render(request, 'book/book_list.html', {'book_obj_list': book_obj_list, "name": request.session["name"]})


# 02添加图书
def add_book(request):
    # 登录判断
    if "name" not in request.session:
        return redirect("/manager/login")
    if request.method == 'POST':
        # 1获取表单提交过来的内容
        name = request.POST.get('name')
        description = request.POST.get('description', '')
        price = request.POST.get('price')
        inventory = request.POST.get('inventory')
        sale_num = request.POST.get('sale_num')
        publisher_id = request.POST.get('publisher_id')
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
            publisher_id=publisher_id
        )
        
        # Handle image upload
        if cover_image:
            book.cover_image = cover_image
        
        # Handle book file upload
        if book_file:
            book.book_file = book_file
        
        # Handle download link
        if download_link:
            book.download_link = download_link
            
        book.save()
        
        # 3重定向到图书列表页面
        return redirect('/manager/book_list/')
    else:
        # 1获取所有的出版社（点击添加图书按钮时，得到所有出版社信息供用户选择）
        publisher_obj_list = models.Publisher.objects.all()
        # 2返回html页面（在页面中遍历出版社对象列表）
        return render(request, 'book/add_book.html', locals())


# 03修改图书信息
def edit_book(request):
    # 登录判断
    if "name" not in request.session:
        return redirect("/manager/login")
    # 点击修改图书（获取要修改图书的原本信息）
    if request.method == 'GET':
        id = request.GET.get('id')
        book_obj = models.Book.objects.get(id=id)
        publisher_obj_list = models.Publisher.objects.all()
        book_obj_list = models.Book.objects.all()
        return render(request, "book/edit_book.html",
                      {"book_obj": book_obj, "book_obj_list": book_obj_list, "publisher_obj_list": publisher_obj_list,
                       "name": request.session["name"]})
    # 修改图书信息（POST表单）
    else:
        id = request.POST.get('id')
        name = request.POST.get('name')
        description = request.POST.get('description', '')
        inventory = request.POST.get('inventory')
        price = request.POST.get('price')
        sale_num = request.POST.get('sale_num')
        publisher_id = request.POST.get('publisher_id')
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
    # 登录判断
    if "name" not in request.session:
        return redirect("/manager/login")
    id = request.GET.get('id')
    models.Book.objects.filter(id=id).delete()
    return redirect('/manager/book_list')


# ================================  三、作者操作模块  =============================
# 01作者列表
def author_list(request):
    # 登录判断
    if "name" not in request.session:
        return redirect("/manager/login")
    # 列表存储作者和图书（一个作者可能有多本书）
    ret_list = []
    # 获取作者列表信息
    author_obj_list = models.Author.objects.all()
    for author_obj in author_obj_list:
        book_obj_list = author_obj.book.all()
        # 定义字典存储
        ret_dic = {'author_obj': author_obj, 'book_list': book_obj_list}
        ret_list.append(ret_dic)
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
    # 登录判断
    if "name" not in request.session:
        return redirect("/manager/login")
    # 1获取id
    id = request.GET.get('id')
    # 2删除作者
    models.Author.objects.filter(id=id).delete()
    # 3重定向作者列表 - Fixed URL
    return redirect('/manager/author_list')


# ====================   PUBLIC USER INTERFACE  ===========================

def public_home(request):
    """Public homepage with book statistics and featured content"""
    book_count = models.Book.objects.count()
    author_count = models.Author.objects.count()
    publisher_count = models.Publisher.objects.count()
    
    # Get featured books (top 6 by sales)
    featured_books = models.Book.objects.select_related('publisher').order_by('-sale_num')[:6]
    
    # Recent books (last 8 added)
    recent_books = models.Book.objects.select_related('publisher').order_by('-id')[:8]
    
    context = {
        'book_count': book_count,
        'author_count': author_count,
        'publisher_count': publisher_count,
        'featured_books': featured_books,
        'recent_books': recent_books,
    }
    return render(request, 'public/home.html', context)

def public_books(request):
    """Public book listing with search and pagination"""
    search_query = request.GET.get('search', '')
    sort_by = request.GET.get('sort', 'name')
    
    books = models.Book.objects.select_related('publisher')
    
    if search_query:
        books = books.filter(name__icontains=search_query)
    
    # Sorting options
    if sort_by == 'price_low':
        books = books.order_by('price')
    elif sort_by == 'price_high':
        books = books.order_by('-price')
    elif sort_by == 'popular':
        books = books.order_by('-sale_num')
    else:
        books = books.order_by('name')
    
    context = {
        'books': books,
        'search_query': search_query,
        'sort_by': sort_by,
    }
    return render(request, 'public/books.html', context)

def public_book_detail(request, book_id):
    """Public book detail view"""
    book = get_object_or_404(models.Book.objects.select_related('publisher'), id=book_id)
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
    
    # Fix: Use 'book' instead of 'book_set' for ManyToMany relationship
    authors = models.Author.objects.prefetch_related('book').all()
    
    if search_query:
        authors = authors.filter(name__icontains=search_query)
    
    authors = authors.order_by('name')
    
    context = {
        'authors': authors,
        'search_query': search_query,
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
    
    context = {
        'publishers': publishers,
        'search_query': search_query,
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
            # Update existing cart item
            new_quantity = cart_item.quantity + quantity
            if new_quantity > book.inventory:
                return JsonResponse({
                    'success': False,
                    'message': f'库存不足！当前库存：{book.inventory}本，购物车中已有：{cart_item.quantity}本'
                })
            cart_item.quantity = new_quantity
            cart_item.save()
        
        # Get total cart count
        cart_count = models.CartItem.objects.filter(session_key=session_key).count()
        
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

@ensure_csrf_cookie
def view_cart(request):
    """Display shopping cart"""
    session_key = get_session_key(request)
    cart_items = models.CartItem.objects.filter(session_key=session_key).select_related('book')
    
    total_amount = sum(item.get_total_price() for item in cart_items)
    total_items = sum(item.quantity for item in cart_items)
    
    context = {
        'cart_items': cart_items,
        'total_amount': total_amount,
        'total_items': total_items,
    }
    
    return render(request, 'public/cart.html', context)

@require_POST
def update_cart(request):
    """Update cart item quantities via AJAX"""
    try:
        data = json.loads(request.body)
        item_id = data.get('item_id')
        quantity = int(data.get('quantity', 1))
        session_key = get_session_key(request)
        
        cart_item = get_object_or_404(models.CartItem, id=item_id, session_key=session_key)
        
        # Validate quantity
        if quantity > cart_item.book.inventory:
            return JsonResponse({
                'success': False,
                'message': f'库存不足！最大可购买：{cart_item.book.inventory}本'
            })
        
        if quantity <= 0:
            cart_item.delete()
            message = f'已从购物车移除《{cart_item.book.name}》'
        else:
            cart_item.quantity = quantity
            cart_item.save()
            message = f'已更新《{cart_item.book.name}》数量为：{quantity}本'
        
        # Recalculate totals
        cart_items = models.CartItem.objects.filter(session_key=session_key)
        total_amount = sum(item.get_total_price() for item in cart_items)
        total_items = sum(item.quantity for item in cart_items)
        
        return JsonResponse({
            'success': True,
            'message': message,
            'item_total': float(cart_item.get_total_price()) if quantity > 0 else 0,
            'cart_total': float(total_amount),
            'total_items': total_items
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': '更新购物车失败'
        })

def remove_from_cart(request, item_id):
    """Remove item from cart - returns JSON for AJAX or redirects for regular requests"""
    session_key = get_session_key(request)
    cart_item = get_object_or_404(models.CartItem, id=item_id, session_key=session_key)
    book_name = cart_item.book.name
    cart_item.delete()

    # Check if AJAX request
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.method == 'POST':
        cart_items = models.CartItem.objects.filter(session_key=session_key)
        total_amount = sum(item.get_total_price() for item in cart_items)
        total_items = sum(item.quantity for item in cart_items)
        cart_count = cart_items.count()
        return JsonResponse({
            'success': True,
            'message': f'已从购物车移除《{book_name}》',
            'cart_total': float(total_amount),
            'total_items': total_items,
            'cart_count': cart_count,
        })

    messages.success(request, f'已从购物车移除《{book_name}》')
    return redirect('manager:view_cart')


def clear_cart(request):
    """Clear all items from cart"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Method not allowed'}, status=405)
    session_key = get_session_key(request)
    models.CartItem.objects.filter(session_key=session_key).delete()
    return JsonResponse({'success': True, 'message': '购物车已清空'})

def get_cart_count(request):
    """Get cart item count for AJAX requests"""
    session_key = get_session_key(request)
    cart_count = models.CartItem.objects.filter(session_key=session_key).count()
    return JsonResponse({'cart_count': cart_count})

@require_POST
def buy_now(request, book_id):
    """Direct purchase without cart"""
    try:
        book = get_object_or_404(models.Book, id=book_id)
        quantity = int(request.POST.get('quantity', 1))
        session_key = get_session_key(request)
        
        # Validate quantity
        if quantity > book.inventory:
            messages.error(request, f'库存不足！当前库存：{book.inventory}本')
            return redirect('manager:public_book_detail', book_id=book_id)
        
        # Clear any existing cart items for this session (optional)
        models.CartItem.objects.filter(session_key=session_key).delete()
        
        # Add to cart for checkout
        models.CartItem.objects.create(
            session_key=session_key,
            book=book,
            quantity=quantity
        )
        
        # Redirect to checkout
        return redirect('manager:checkout')
        
    except Exception as e:
        messages.error(request, '购买失败，请重试')
        return redirect('manager:public_book_detail', book_id=book_id)

def checkout(request):
    """Checkout process - Fixed price ¥6.99 per book"""
    session_key = get_session_key(request)
    cart_items = models.CartItem.objects.filter(session_key=session_key).select_related('book')
    
    if not cart_items.exists():
        messages.warning(request, '购物车为空，请先添加商品')
        return redirect('manager:public_books')
    
    # Fixed price per book
    FIXED_PRICE = Decimal('6.99')
    
    if request.method == 'POST':
        try:
            # Calculate total with fixed price
            total_items_count = sum(item.quantity for item in cart_items)
            total_amount = FIXED_PRICE * total_items_count
            
            # Determine initial status based on payment confirmation
            payment_confirmed = request.POST.get('payment_confirmed', 'no')
            if payment_confirmed == 'yes':
                initial_status = 'processing'  # 处理中
                payment_status = 'pending'
            else:
                initial_status = 'payment_pending'  # 待付款
                payment_status = 'pending'
            
            # Create order (Digital Product - no shipping address needed)
            order = models.Order.objects.create(
                customer_name=request.POST.get('customer_name'),
                customer_email=request.POST.get('customer_email'),
                customer_phone=request.POST.get('customer_phone'),
                country=request.POST.get('country', 'China'),
                payment_method=request.POST.get('payment_method'),
                total_amount=total_amount,
                status=initial_status,
                payment_status=payment_status,
                customer_notes=request.POST.get('customer_notes', '')
            )
            
            # Create order items and update inventory
            for cart_item in cart_items:
                models.OrderItem.objects.create(
                    order=order,
                    book=cart_item.book,
                    quantity=cart_item.quantity,
                    unit_price=cart_item.book.price,
                    total_price=cart_item.get_total_price()
                )
                
                # Update book inventory and sales
                book = cart_item.book
                book.inventory -= cart_item.quantity
                book.sale_num += cart_item.quantity
                book.save()
            
            # Clear cart
            cart_items.delete()
            
            return redirect('manager:order_confirmation', order_number=order.order_number)
            
        except Exception as e:
            messages.error(request, '订单创建失败，请重试')
    
    # Calculate with fixed price
    total_items = sum(item.quantity for item in cart_items)
    total_amount = FIXED_PRICE * total_items
    
    # Payment methods grouped by region
    payment_methods_by_region = {
        'africa': [
            ('mtn_money', 'MTN Money'),
            ('orange_money', 'Orange Money'),
            ('airtel_money', 'Airtel Money'),
        ],
        'china': [
            ('wechat_pay', '微信支付'),
            ('alipay', '支付宝'),
        ],
        'others': [
            ('paypal', 'PayPal'),
            ('credit_card', '信用卡'),
            ('bank_transfer', '银行转账'),
        ]
    }
    
    context = {
        'cart_items': cart_items,
        'total_amount': total_amount,
        'total_items': total_items,
        'fixed_price': FIXED_PRICE,
        'payment_methods_by_region': payment_methods_by_region,
    }
    
    return render(request, 'public/checkout.html', context)

def order_confirmation(request, order_number):
    """Order confirmation page"""
    order = get_object_or_404(models.Order, order_number=order_number)
    order_items = models.OrderItem.objects.filter(order=order).select_related('book')
    
    context = {
        'order': order,
        'order_items': order_items,
    }
    
    return render(request, 'public/order_confirmation.html', context)

def track_order(request):
    """Order tracking page - Search by order number or email"""
    order = None
    orders = None
    has_downloadable_books = False
    
    if request.method == 'POST':
        search_type = request.POST.get('search_type', 'order_number')
        
        if search_type == 'email':
            # Search by email - return all orders
            customer_email = request.POST.get('customer_email')
            if customer_email:
                orders = models.Order.objects.filter(
                    customer_email=customer_email
                ).order_by('-created_at')
                
                if not orders.exists():
                    messages.error(request, f'未找到与邮箱 {customer_email} 相关的订单')
                    orders = None
        else:
            # Search by order number - return single order
            order_number = request.POST.get('order_number')
            if order_number:
                try:
                    order = models.Order.objects.get(order_number=order_number)
                    # Check if payment window expired and auto-cancel
                    if order.status == 'payment_pending':
                        order.auto_cancel_if_expired()
                    
                    # Check if any books have downloads available
                    has_downloadable_books = any(
                        item.book.has_download 
                        for item in order.orderitem_set.all()
                    )
                except models.Order.DoesNotExist:
                    messages.error(request, '订单号不存在')
    
    context = {
        'order': order,
        'orders': orders,
        'has_downloadable_books': has_downloadable_books
    }
    return render(request, 'public/track_order.html', context)

def download_book(request, order_id, book_id):
    """Download purchased ebook - supports files and external links"""
    from django.http import FileResponse, HttpResponse
    import os
    
    # Verify order and book
    order = get_object_or_404(models.Order, id=order_id)
    book = get_object_or_404(models.Book, id=book_id)
    
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
                return JsonResponse({'success': True, 'message': '支付确认成功'})
            else:
                return JsonResponse({'success': False, 'message': '订单状态无法确认支付'})
                
        except models.Order.DoesNotExist:
            return JsonResponse({'success': False, 'message': '订单不存在'})
        except Exception as e:
            return JsonResponse({'success': False, 'message': str(e)})
    
    return JsonResponse({'success': False, 'message': '无效请求'})


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
            models.Q(order_number__icontains=search_query) |
            models.Q(customer_name__icontains=search_query) |
            models.Q(customer_email__icontains=search_query) |
            models.Q(customer_phone__icontains=search_query)
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
            models.Q(order_number__icontains=search_filter) |
            models.Q(customer_name__icontains=search_filter) |
            models.Q(customer_email__icontains=search_filter) |
            models.Q(customer_phone__icontains=search_filter)
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
            order.items.count(),
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
            order.items.count(),
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

    context = {
        'name': request.session["name"],
        'current_date': now.strftime('%Y年%m月%d日'),
        
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
    """Contact Us page with email sending"""
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

        # Try sending email (non-blocking — saved to DB regardless)
        email_subject = f'[Contact Form] {subject or "No Subject"} - from {name}'
        email_body = (
            f'New message from the contact form\n'
            f'{"-" * 40}\n\n'
            f'Name:    {name}\n'
            f'Email:   {email}\n'
            f'Subject: {subject or "N/A"}\n\n'
            f'Message:\n{message}\n\n'
            f'{"-" * 40}\n'
            f'Sent from Book Management System contact form\n'
        )

        try:
            send_mail(
                subject=email_subject,
                message=email_body,
                from_email=django_settings.DEFAULT_FROM_EMAIL,
                recipient_list=[django_settings.CONTACT_EMAIL],
                fail_silently=False,
            )
            contact_msg.email_sent = True
            contact_msg.save(update_fields=['email_sent'])
        except Exception as e:
            logger.warning(f'Contact form email failed (msg #{contact_msg.id}): {e}')

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
        msg.save(update_fields=['replied', 'replied_at'])

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

    if account.smtp_use_tls:
        server = smtplib.SMTP(account.smtp_host, account.smtp_port)
        server.starttls()
    else:
        server = smtplib.SMTP_SSL(account.smtp_host, account.smtp_port)

    server.login(account.username, account.password)
    server.send_message(msg, to_addrs=all_recipients)
    server.quit()

    return msg['Message-ID'] or ''


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
    """Fetch emails from IMAP for a single account"""
    if account.imap_use_ssl:
        mail = imaplib.IMAP4_SSL(account.imap_host, account.imap_port)
    else:
        mail = imaplib.IMAP4(account.imap_host, account.imap_port)

    mail.login(account.username, account.password)
    mail.select(folder)

    existing_uids = set(
        models.EmailMessage.objects.filter(account=account)
        .exclude(message_uid='')
        .values_list('message_uid', flat=True)
    )

    status, data = mail.search(None, 'ALL')
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
                    m = imaplib.IMAP4_SSL(account.imap_host, account.imap_port)
                else:
                    m = imaplib.IMAP4(account.imap_host, account.imap_port)
                m.login(account.username, account.password)
                m.logout()
            except Exception as e:
                errors.append(f'IMAP: {str(e)}')
            try:
                if account.smtp_use_tls:
                    s = smtplib.SMTP(account.smtp_host, account.smtp_port)
                    s.starttls()
                else:
                    s = smtplib.SMTP_SSL(account.smtp_host, account.smtp_port)
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
