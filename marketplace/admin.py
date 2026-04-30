from django.contrib import admin
from .models import Category, Product, Course, SupermarketItem, MarketplaceOrder, MarketplaceOrderItem


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'section', 'parent', 'display_order', 'is_active']
    list_filter = ['section', 'is_active']
    prepopulated_fields = {'slug': ('name',)}


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ['name', 'price', 'stock', 'category', 'is_featured', 'is_active']
    list_filter = ['is_active', 'is_featured', 'condition', 'category']
    search_fields = ['name', 'sku', 'brand']
    prepopulated_fields = {'slug': ('name',)}


@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = ['title', 'price', 'instructor', 'level', 'is_featured', 'is_active']
    list_filter = ['is_active', 'is_featured', 'level', 'category']
    search_fields = ['title', 'instructor']
    prepopulated_fields = {'slug': ('title',)}


@admin.register(SupermarketItem)
class SupermarketItemAdmin(admin.ModelAdmin):
    list_display = ['name', 'price', 'stock', 'unit', 'category', 'is_featured', 'is_active']
    list_filter = ['is_active', 'is_featured', 'is_organic', 'category']
    search_fields = ['name', 'brand']
    prepopulated_fields = {'slug': ('name',)}


class MarketplaceOrderItemInline(admin.TabularInline):
    model = MarketplaceOrderItem
    extra = 0
    readonly_fields = ['subtotal']


@admin.register(MarketplaceOrder)
class MarketplaceOrderAdmin(admin.ModelAdmin):
    list_display = ['order_number', 'user_email', 'status', 'total_amount', 'created_at']
    list_filter = ['status']
    search_fields = ['order_number', 'user_email', 'user_name']
    inlines = [MarketplaceOrderItemInline]
