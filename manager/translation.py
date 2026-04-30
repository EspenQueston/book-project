"""
django-modeltranslation registration for manager app.

Adds columns name_en / name_fr (etc.) to Book, Publisher, Author
directly in PostgreSQL. The original column (e.g. name) always holds
the default-language value (zh-hans).
"""
from modeltranslation.translator import register, TranslationOptions
from .models import Book, Publisher, Author, BlogPost


@register(Book)
class BookTranslationOptions(TranslationOptions):
    fields = ('name', 'description')


@register(Publisher)
class PublisherTranslationOptions(TranslationOptions):
    fields = ('publisher_name', 'publisher_address')


@register(Author)
class AuthorTranslationOptions(TranslationOptions):
    fields = ('name',)


@register(BlogPost)
class BlogPostTranslationOptions(TranslationOptions):
    fields = ('title', 'excerpt', 'content')
