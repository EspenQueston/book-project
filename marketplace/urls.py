from django.urls import path
from . import views

app_name = 'marketplace'

urlpatterns = [
    # Public pages
    path('', views.marketplace_home, name='home'),
    path('products/', views.product_list, name='product_list'),
    path('products/<slug:slug>/', views.product_detail, name='product_detail'),
    path('courses/', views.course_list, name='course_list'),
    path('courses/<slug:slug>/', views.course_detail, name='course_detail'),
    path('supermarket/', views.supermarket_list, name='supermarket_list'),
    path('supermarket/<slug:slug>/', views.supermarket_detail, name='supermarket_detail'),

    # Cart & Checkout
    path('cart/', views.view_cart, name='view_cart'),
    path('cart/add/', views.add_to_cart, name='add_to_cart'),
    path('cart/update/', views.update_cart, name='update_cart'),
    path('cart/remove/<int:item_id>/', views.remove_from_cart, name='remove_from_cart'),
    path('cart/count/', views.get_cart_count, name='get_cart_count'),
    path('buy-now/', views.buy_now, name='buy_now'),
    path('checkout/', views.checkout, name='checkout'),
    path('order/<str:order_number>/', views.order_confirmation, name='order_confirmation'),

    # Course progress
    path('lesson/<int:lesson_id>/toggle/', views.toggle_lesson_complete, name='toggle_lesson_complete'),
    path('lesson/<int:lesson_id>/pdf/', views.serve_lesson_pdf, name='serve_lesson_pdf'),

    # Admin management
    path('admin/dashboard/', views.admin_dashboard, name='admin_dashboard'),
    path('admin/products/', views.admin_products, name='admin_products'),
    path('admin/products/add/', views.admin_product_add, name='admin_product_add'),
    path('admin/products/<int:pk>/edit/', views.admin_product_edit, name='admin_product_edit'),
    path('admin/products/<int:pk>/delete/', views.admin_product_delete, name='admin_product_delete'),
    path('admin/courses/', views.admin_courses, name='admin_courses'),
    path('admin/courses/add/', views.admin_course_add, name='admin_course_add'),
    path('admin/courses/<int:pk>/edit/', views.admin_course_edit, name='admin_course_edit'),
    path('admin/courses/<int:pk>/delete/', views.admin_course_delete, name='admin_course_delete'),
    path('admin/courses/<int:pk>/content/', views.admin_course_content, name='admin_course_content'),
    path('admin/courses/<int:course_pk>/sections/add/', views.admin_section_add, name='admin_section_add'),
    path('admin/courses/sections/<int:pk>/edit/', views.admin_section_edit, name='admin_section_edit'),
    path('admin/courses/sections/<int:pk>/delete/', views.admin_section_delete, name='admin_section_delete'),
    path('admin/courses/sections/<int:section_pk>/lessons/add/', views.admin_lesson_add, name='admin_lesson_add'),
    path('admin/courses/lessons/<int:pk>/edit/', views.admin_lesson_edit, name='admin_lesson_edit'),
    path('admin/courses/lessons/<int:pk>/delete/', views.admin_lesson_delete, name='admin_lesson_delete'),
    path('admin/supermarket/', views.admin_supermarket, name='admin_supermarket'),
    path('admin/supermarket/add/', views.admin_supermarket_add, name='admin_supermarket_add'),
    path('admin/supermarket/<int:pk>/edit/', views.admin_supermarket_edit, name='admin_supermarket_edit'),
    path('admin/supermarket/<int:pk>/delete/', views.admin_supermarket_delete, name='admin_supermarket_delete'),
    path('admin/categories/', views.admin_categories, name='admin_categories'),
    path('admin/categories/add/', views.admin_category_add, name='admin_category_add'),
    path('admin/categories/<int:pk>/edit/', views.admin_category_edit, name='admin_category_edit'),
    path('admin/categories/<int:pk>/delete/', views.admin_category_delete, name='admin_category_delete'),
    path('admin/orders/', views.admin_orders, name='admin_orders'),
    path('admin/orders/<int:pk>/', views.admin_order_detail, name='admin_order_detail'),
    path('admin/orders/update-status/', views.admin_update_order_status, name='admin_update_order_status'),
    path('admin/orders/update-payment/', views.admin_update_payment_status, name='admin_update_payment_status'),
    path('admin/orders/<int:pk>/delete/', views.admin_delete_order, name='admin_delete_order'),

    # Vendor management
    path('vendor/dashboard/', views.vendor_dashboard, name='vendor_dashboard'),
    path('vendor/products/', views.vendor_products, name='vendor_products'),
    path('vendor/products/add/', views.vendor_product_add, name='vendor_product_add'),
    path('vendor/products/<int:pk>/edit/', views.vendor_product_edit, name='vendor_product_edit'),
    path('vendor/products/<int:pk>/delete/', views.vendor_product_delete, name='vendor_product_delete'),
    path('vendor/products/<int:pk>/toggle/', views.vendor_product_toggle, name='vendor_product_toggle'),
    path('vendor/courses/', views.vendor_courses, name='vendor_courses'),
    path('vendor/courses/add/', views.vendor_course_add, name='vendor_course_add'),
    path('vendor/courses/<int:pk>/edit/', views.vendor_course_edit, name='vendor_course_edit'),
    path('vendor/courses/<int:pk>/delete/', views.vendor_course_delete, name='vendor_course_delete'),
    path('vendor/courses/<int:pk>/toggle/', views.vendor_course_toggle, name='vendor_course_toggle'),
    path('vendor/courses/<int:pk>/content/', views.vendor_course_content, name='vendor_course_content'),
    path('vendor/courses/<int:course_pk>/sections/add/', views.vendor_section_add, name='vendor_section_add'),
    path('vendor/courses/sections/<int:pk>/edit/', views.vendor_section_edit, name='vendor_section_edit'),
    path('vendor/courses/sections/<int:pk>/delete/', views.vendor_section_delete, name='vendor_section_delete'),
    path('vendor/courses/sections/<int:section_pk>/lessons/add/', views.vendor_lesson_add, name='vendor_lesson_add'),
    path('vendor/courses/lessons/<int:pk>/edit/', views.vendor_lesson_edit, name='vendor_lesson_edit'),
    path('vendor/courses/lessons/<int:pk>/delete/', views.vendor_lesson_delete, name='vendor_lesson_delete'),
]
