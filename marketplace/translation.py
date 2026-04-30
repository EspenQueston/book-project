"""
django-modeltranslation registration for marketplace app.

Adds _en / _fr columns to Product, SupermarketItem, Course, Category
directly in PostgreSQL. Original columns keep the zh-hans value.
"""
from modeltranslation.translator import register, TranslationOptions
from .models import Product, SupermarketItem, Course, Category


@register(Category)
class CategoryTranslationOptions(TranslationOptions):
    fields = ('name', 'description')


@register(Product)
class ProductTranslationOptions(TranslationOptions):
    fields = ('name', 'description')


@register(Course)
class CourseTranslationOptions(TranslationOptions):
    fields = ('title', 'description')


@register(SupermarketItem)
class SupermarketItemTranslationOptions(TranslationOptions):
    fields = ('name', 'description')
