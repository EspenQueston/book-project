from django.urls import path, re_path
from manager import views
from manager import views_review
from manager.payments.views import (
    mtn_momo_callback, airtel_money_callback,
    initiate_momo_payment, check_payment_status,
    kkiapay_verify, kkiapay_webhook,
    pawapay_callback,
)

# manager中转路由
app_name = 'manager'

urlpatterns = [
    # 指定跳转 - Default redirect to login
    re_path(r'^$', views.index),

    # =========================管理员登录========================
    path("login/", views.manager_login, name='manager_login'),
    path("logout/", views.manager_logout, name='manager_logout'),

    # =========================Dashboard and analytics========================
    path("dashboard/", views.manager_dashboard, name='manager_dashboard'),
    path('dashboard/analytics/', views.dashboard_analytics_api, name='dashboard_analytics_api'),

    # =========================出版社========================
    path("add_publisher/", views.add_publisher, name='add_publisher'),
    path("publisher_list/", views.publisher_list, name='publisher_list'),
    path("edit_publisher/", views.edit_publisher, name='edit_publisher'),
    path("delete_publisher/", views.delete_publisher, name='delete_publisher'),

    # =========================图书 ========================
    path("add_book/", views.add_book, name='add_book'),
    path("book_list/", views.book_list, name='book_list'),
    path("edit_book/", views.edit_book, name='edit_book'),
    path("delete_book/", views.delete_book, name='delete_book'),
    path("book_categories/", views.manage_book_categories, name='book_categories'),

    # =========================作家 ========================
    path("add_author/", views.add_author, name='add_author'),
    path("author_list/", views.author_list, name='author_list'),
    path("edit_author/", views.edit_author, name='edit_author'),
    path("delete_author/", views.delete_author, name='delete_author'),

    # =========================Public Interface URLs========================
    path('public/', views.public_home, name='public_home'),
    path('public/books/', views.public_books, name='public_books'),
    path('public/books/<int:book_id>/', views.public_book_detail, name='public_book_detail'),
    path('public/authors/', views.public_authors, name='public_authors'),
    path('public/authors/<int:author_id>/', views.public_author_detail, name='public_author_detail'),
    path('public/publishers/', views.public_publishers, name='public_publishers'),
    path('public/publishers/<int:publisher_id>/', views.public_publisher_detail, name='public_publisher_detail'),
    path('public/messages/', views.public_messages, name='public_messages'),
    path('public/messages/start/', views.start_conversation, name='start_conversation'),
    path('public/messages/send/', views.public_send_message, name='public_send_message'),
    path('api/conversations/unread_count/', views.api_buyer_unread_count, name='api_buyer_unread_count'),
    path('api/conversations/', views.api_conversations, name='api_conversations'),
    path('api/conversations/<int:conversation_id>/messages/', views.api_conversation_messages, name='api_conversation_messages'),
    path('api/conversations/<int:conversation_id>/mark_read/', views.api_mark_conversation_read, name='api_mark_conversation_read'),
    path('api/conversations/<int:conversation_id>/delete/', views.api_conversation_delete, name='api_conversation_delete'),
    path('api/conversations/<int:conversation_id>/block/', views.api_conversation_block_vendor, name='api_conversation_block_vendor'),
    path('api/conversations/<int:conversation_id>/unblock/', views.api_conversation_unblock_vendor, name='api_conversation_unblock_vendor'),
    path('api/messages/<int:message_id>/recall/', views.api_message_recall, name='api_message_recall'),
    path('api/messages/<int:message_id>/delete_for_me/', views.api_message_delete_for_me, name='api_message_delete_for_me'),
    path('public/my-profile/', views.public_my_profile, name='public_my_profile'),
    path('public/reviews/write/', views_review.review_write, name='review_write'),
    path('public/reviews/submit/', views_review.review_submit, name='review_submit'),
    path('public/wishlist/', views.public_wishlist, name='public_wishlist'),
    path('public/wallet/', views.public_wallet, name='public_wallet'),
    path('public/wallet/top-up/', views.public_wallet_topup, name='public_wallet_topup'),
    path('wallet/webhook/', views.public_wallet_topup_webhook, name='public_wallet_topup_webhook'),
    path('publisher/<int:publisher_id>/follow/', views.follow_publisher, name='follow_publisher'),
    path('vendor/<int:vendor_id>/follow/', views.follow_vendor, name='follow_vendor'),
    
    # =========================Public Vendor Storefront========================
    path('public/shop/<int:vendor_id>/', views.public_vendor_shop, name='public_vendor_shop'),

    # =========================Public Static Pages========================
    path('public/about/', views.public_about, name='public_about'),
    path('public/services/', views.public_services, name='public_services'),
    path('public/contact/', views.public_contact, name='public_contact'),
    path('public/legal/', views.public_legal_privacy, name='legal_privacy'),
    path('public/legal/terms/', views.public_legal_terms, name='legal_terms'),
    path('public/pages/<slug:slug>/', views.public_info_page, name='info_page'),
    path('public/site-map/', views.public_site_map, name='site_map'),

    # =========================Public Blog========================
    path('public/blog/', views.public_blog, name='public_blog'),
    path('public/blog/<slug:slug>/', views.public_blog_detail, name='public_blog_detail'),

    # =========================Admin Blog Management========================
    path('blog_list/', views.blog_list, name='blog_list'),
    path('add_blog/', views.add_blog_post, name='add_blog'),
    path('edit_blog/', views.edit_blog_post, name='edit_blog'),
    path('delete_blog/', views.delete_blog_post, name='delete_blog'),
    path('blog_categories/', views.manage_blog_categories, name='blog_categories'),

    # =========================E-commerce URLs========================
    path('cart/add/<int:book_id>/', views.add_to_cart, name='add_to_cart'),
    path('cart/add-item/', views.add_marketplace_item_to_cart, name='add_marketplace_item_to_cart'),
    path('cart/', views.view_cart, name='view_cart'),
    path('cart/update/', views.update_cart, name='update_cart'),
    path('cart/remove/<int:item_id>/', views.remove_from_cart, name='remove_from_cart'),
    path('cart/clear/', views.clear_cart, name='clear_cart'),
    path('cart/count/', views.get_cart_count, name='get_cart_count'),
    path('buy-now/<int:book_id>/', views.buy_now, name='buy_now'),
    path('checkout/', views.checkout, name='checkout'),
    path('payment/kkiapay/<str:order_number>/', views.kkiapay_pay, name='kkiapay_pay'),
    path('payment/pawapay/<str:order_number>/', views.pawapay_pay, name='pawapay_pay'),
    path('payment/pawapay/return/<str:order_number>/', views.pawapay_return, name='pawapay_return'),
    path('payment/pawapay/seller-activation/return/<str:order_number>/', views.seller_activation_return, name='seller_activation_return'),
    path('api/payment/seller-activation/status/', views.seller_activation_status, name='seller_activation_status'),
    path('public/kkiapay/success/<str:order_number>/', views.kkiapay_success_redirect, name='kkiapay_success_redirect'),
    path('order-confirmation/<str:order_number>/', views.order_confirmation, name='order_confirmation'),
    path('api/shipment/confirm-receipt/', views.confirm_delivery_receipt, name='confirm_delivery_receipt'),
    path('api/shipment/return-request/', views.submit_return_request, name='submit_return_request'),
    path('track-order/', views.track_order, name='track_order'),
    path('download/<int:order_id>/<int:book_id>/', views.download_book, name='download_book'),

    # =========================API Endpoints for Order Actions========================
    path('api/cancel-order/', views.api_cancel_order, name='api_cancel_order'),
    path('api/confirm-payment/', views.api_confirm_payment, name='api_confirm_payment'),
    path('api/feed/', views.api_home_feed, name='api_home_feed'),
    path('api/recommendations/', views.api_recommendations, name='api_recommendations'),
    path('api/search/', views.api_unified_search, name='api_unified_search'),
    path('api/spin-wheel/', views.api_spin_wheel, name='api_spin_wheel'),
    path('public/search/', views.public_search, name='public_search'),

    # =========================Contact Messages Admin========================
    path("admin_messages/", views.admin_messages, name='admin_messages'),
    path("admin_messages/<int:msg_id>/", views.admin_message_detail, name='admin_message_detail'),
    path("admin_messages/<int:msg_id>/reply/", views.reply_to_contact, name='reply_to_contact'),
    path("admin_messages/toggle_read/", views.admin_message_toggle_read, name='admin_message_toggle_read'),
    path("admin_messages/delete/", views.admin_message_delete, name='admin_message_delete'),
    path("admin_messages/bulk/", views.admin_message_bulk_action, name='admin_message_bulk_action'),
    path("admin_messages/label_action/", views.contact_label_action, name='contact_label_action'),

    # =========================Email Management URLs========================
    path("email/", views.email_dashboard, name='email_dashboard'),
    path("email/detail/<int:email_id>/", views.email_detail, name='email_detail'),
    path("email/compose/", views.email_compose, name='email_compose'),
    path("email/sync/", views.email_sync, name='email_sync'),
    path("email/action/", views.email_action, name='email_action'),
    path("email/accounts/", views.email_accounts, name='email_accounts'),
    path("email/labels/", views.email_labels, name='email_labels'),
    path("email/rules/", views.email_rules, name='email_rules'),

    # =========================Order Management URLs========================
    path("order_list/", views.order_list, name='order_list'),
    path("order_detail/<int:order_id>/", views.order_detail, name='order_detail'),
    path("update_order_status/", views.update_order_status, name='update_order_status'),
    path("update_payment_status/", views.update_payment_status, name='update_payment_status'),
    path("delete_order/<int:order_id>/", views.delete_order, name='delete_order'),
    path("export_orders/", views.export_orders, name='export_orders'),

    # =========================Site User Authentication========================
    path('public/user/register/', views.user_register, name='user_register'),
    path('public/user/verify-email/', views.verify_email_pin, name='verify_email_pin'),
    path('public/user/resend-pin/', views.resend_verification_pin, name='resend_verification_pin'),
    path('public/user/resend-phone/', views.resend_phone_verification, name='resend_phone_verification'),
    path('public/user/verification-status/', views.signup_verification_status, name='signup_verification_status'),
    path('public/user/login/', views.user_login, name='user_login'),
    path('public/user/logout/', views.user_logout, name='user_logout'),
    path('public/user/profile/', views.user_profile, name='user_profile'),
    path('public/user/wishlist/toggle/', views.user_toggle_wishlist, name='user_toggle_wishlist'),
    path('public/user/wishlist/check/', views.user_check_wishlist, name='user_check_wishlist'),
    path('public/publish/', views.publish_entry, name='publish_entry'),
    path('inventory/', views.admin_inventory, name='admin_inventory'),
    path('admin/escrow/', views.admin_escrow_transactions, name='admin_escrow'),
    path('public/forgot-password/', views.forgot_password, name='forgot_password'),
    path('public/reset-password/', views.reset_password_verify, name='reset_password_verify'),

    # =========================Admin User Management========================
    path('admin/users/', views.admin_site_users, name='admin_site_users'),
    path('admin/users/toggle/', views.admin_toggle_user, name='admin_toggle_user'),
    path('admin/users/delete/', views.admin_delete_user, name='admin_delete_user'),
    path('admin/users/edit/', views.admin_edit_user, name='admin_edit_user'),
    path('admin/users/add/', views.admin_add_user, name='admin_add_user'),

    # =========================Admin: Official Store Messages========================
    path('admin/store-messages/', views.admin_store_messages_page, name='admin_store_messages'),
    path('api/admin/store-messages/conversations/', views.api_admin_store_conversations, name='api_admin_store_conversations'),
    path('api/admin/store-messages/conversations/<int:conversation_id>/messages/', views.api_admin_store_conversation_messages, name='api_admin_store_conversation_messages'),
    path('api/admin/store-messages/conversations/<int:conversation_id>/delete/', views.api_admin_store_conversation_delete, name='api_admin_store_conversation_delete'),
    path('api/admin/store-messages/conversations/<int:conversation_id>/mark_read/', views.api_admin_store_mark_read, name='api_admin_store_mark_read'),
    path('api/admin/store-messages/messages/<int:message_id>/recall/', views.api_admin_store_message_recall, name='api_admin_store_message_recall'),
    path('api/admin/store-messages/messages/<int:message_id>/delete_for_me/', views.api_admin_store_message_delete_for_me, name='api_admin_store_message_delete_for_me'),
    path('api/admin/store-messages/listings/', views.api_admin_store_listings, name='api_admin_store_listings'),
    path('api/admin/store-messages/send/', views.admin_store_send_message, name='admin_store_send_message'),
    path('api/admin/store-messages/auto-reply/settings/', views.api_admin_store_auto_reply_settings, name='api_admin_store_auto_reply_settings'),
    path('api/admin/store-messages/auto-reply/keywords/', views.api_admin_store_auto_reply_keywords, name='api_admin_store_auto_reply_keywords'),
    path('api/admin/store-messages/auto-reply/keywords/<int:keyword_id>/update/', views.api_admin_store_auto_reply_keyword_update, name='api_admin_store_auto_reply_keyword_update'),
    path('api/admin/store-messages/auto-reply/keywords/<int:keyword_id>/delete/', views.api_admin_store_auto_reply_keyword_delete, name='api_admin_store_auto_reply_keyword_delete'),

    # =========================Vendor / Seller========================
    path('vendor/register/', views.vendor_register, name='vendor_register'),
    path('vendor/verify-email/', views.verify_vendor_pin, name='verify_vendor_pin'),
    path('vendor/login/', views.vendor_login, name='vendor_login'),
    path('vendor/logout/', views.vendor_logout, name='vendor_logout'),
    path('vendor/dashboard/', views.vendor_dashboard, name='vendor_dashboard'),
    path('vendor/settings/', views.vendor_settings, name='vendor_settings'),
    path('vendor/settings/save/', views.vendor_settings_save, name='vendor_settings_save'),
    path('vendor/orders/hub/update/', views.vendor_hub_order_update, name='vendor_hub_order_update'),
    path('vendor/orders/', views.vendor_orders_hub, name='vendor_orders_hub'),
    path('vendor/books/', views.vendor_books, name='vendor_books'),
    path('vendor/inventory/', views.vendor_inventory, name='vendor_inventory'),
    path('vendor/orders/books/', views.vendor_book_orders, name='vendor_book_orders'),
    path('vendor/orders/books/<int:order_id>/', views.vendor_book_order_detail, name='vendor_book_order_detail'),
    path('vendor/orders/books/update-status/', views.vendor_book_order_update_status, name='vendor_book_order_update_status'),
    path('vendor/shipments/action/', views.vendor_shipment_action, name='vendor_shipment_action'),
    path('vendor/orders/books/customer/', views.vendor_book_order_update_customer, name='vendor_book_order_update_customer'),
    path('vendor/messages/', views.vendor_messages_page, name='vendor_messages'),
    path('vendor/notifications/', views.vendor_notifications_page, name='vendor_notifications'),
    path('vendor/payments/', views.vendor_payments_page, name='vendor_payments'),
    path('api/vendor/notifications/', views.vendor_notifications_api, name='vendor_notifications_api'),
    path('api/vendor/conversations/', views.api_vendor_conversations, name='api_vendor_conversations'),
    path('api/vendor/conversations/<int:conversation_id>/messages/', views.api_vendor_conversation_messages, name='api_vendor_conversation_messages'),
    path('api/vendor/conversations/<int:conversation_id>/delete/', views.api_vendor_conversation_delete, name='api_vendor_conversation_delete'),
    path('api/vendor/conversations/<int:conversation_id>/mark_read/', views.api_vendor_mark_conversation_read, name='api_vendor_mark_conversation_read'),
    path('api/vendor/conversations/create/', views.vendor_create_conversation, name='vendor_create_conversation'),
    path('api/vendor/messages/send/', views.vendor_send_message, name='vendor_send_message'),
    path('api/vendor/messages/<int:message_id>/recall/', views.api_vendor_message_recall, name='api_vendor_message_recall'),
    path('api/vendor/messages/<int:message_id>/delete_for_me/', views.api_vendor_message_delete_for_me, name='api_vendor_message_delete_for_me'),
    path('api/vendor/listings/', views.api_vendor_my_listings, name='api_vendor_my_listings'),
    path('api/vendor/auto-reply/settings/', views.api_vendor_auto_reply_settings, name='api_vendor_auto_reply_settings'),
    path('api/vendor/auto-reply/keywords/', views.api_vendor_auto_reply_keywords, name='api_vendor_auto_reply_keywords'),
    path('api/vendor/auto-reply/keywords/<int:keyword_id>/update/', views.api_vendor_auto_reply_keyword_update, name='api_vendor_auto_reply_keyword_update'),
    path('api/vendor/auto-reply/keywords/<int:keyword_id>/delete/', views.api_vendor_auto_reply_keyword_delete, name='api_vendor_auto_reply_keyword_delete'),
    path('vendor/add-book/', views.vendor_add_book, name='vendor_add_book'),
    path('vendor/edit-book/', views.vendor_edit_book, name='vendor_edit_book'),
    path('vendor/delete-book/', views.vendor_delete_book, name='vendor_delete_book'),
    path('vendor/toggle-book/', views.vendor_toggle_book, name='vendor_toggle_book'),

    # =========================Admin Vendor Management========================
    path('admin/returns/', views.admin_returns_queue, name='admin_returns_queue'),
    path('admin/returns/resolve/', views.admin_resolve_return, name='admin_resolve_return'),
    path('admin/returns/confirm-received/', views.admin_confirm_return_received, name='admin_confirm_return_received'),
    path('admin/vendors/', views.admin_vendor_list, name='admin_vendor_list'),
    path('admin/vendors/status/', views.admin_vendor_status, name='admin_vendor_status'),
    path('admin/vendors/certify/', views.admin_vendor_certify, name='admin_vendor_certify'),
    path('admin/vendors/edit/', views.admin_edit_vendor, name='admin_edit_vendor'),
    path('admin/vendors/add/', views.admin_add_vendor, name='admin_add_vendor'),
    path('admin/vendors/delete/', views.admin_delete_vendor, name='admin_delete_vendor'),
    path('admin/vendors/delete-item/', views.admin_delete_vendor_item, name='admin_delete_vendor_item'),

    # =========================Notification System========================
    path('admin/notifications/', views.admin_notifications_api, name='admin_notifications'),
    path('admin/notifications/page/', views.admin_notifications_page, name='admin_notifications_page'),

    # =========================Payment Callbacks (MoMo/Airtel)========================
    path('api/payment/mtn/callback/', mtn_momo_callback, name='mtn_momo_callback'),
    path('api/payment/airtel/callback/', airtel_money_callback, name='airtel_money_callback'),
    path('api/payment/initiate/', initiate_momo_payment, name='initiate_momo_payment'),
    path('api/payment/status/', check_payment_status, name='check_payment_status'),

    # =========================KKiaPay========================
    path('api/payment/kkiapay/verify/',  kkiapay_verify,  name='kkiapay_verify'),
    path('api/payment/kkiapay/webhook/', kkiapay_webhook, name='kkiapay_webhook'),
    path('api/payment/pawapay/callback/deposits/', pawapay_callback, name='pawapay_callback_deposits'),
    path('api/payment/pawapay/callback/payouts/', pawapay_callback, name='pawapay_callback_payouts'),
    path('api/payment/pawapay/callback/refunds/', pawapay_callback, name='pawapay_callback_refunds'),

    path('admin/contact-reply/', views.admin_contact_quick_reply, name='admin_contact_quick_reply'),
]
