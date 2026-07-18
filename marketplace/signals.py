"""
Marketplace signals — traduction automatique des nouveaux contenus
via TranslationService (OpenRouter / Gemma 4 gratuit).

Les traductions sont effectuées uniquement à la création (created=True),
à partir de la langue réellement utilisée pour saisir le contenu (voir
core.services.translation_service.auto_translate_new_instance).
Le signal utilise .update() pour éviter la récursion.
"""
import logging
from django.db.models.signals import post_save
from django.dispatch import receiver

logger = logging.getLogger(__name__)


def _auto_translate(sender_label, instance, created, model_cls, field_specs):
    if not created:
        return
    try:
        from core.services.translation_service import auto_translate_new_instance
        auto_translate_new_instance(instance, model_cls, field_specs)
        logger.info("Auto-translated %s #%s", sender_label, instance.pk)
    except Exception as exc:
        logger.error("auto_translate %s error for #%s: %s", sender_label, instance.pk, exc)


# ──────────────────────────────────────────────
# Product
# ──────────────────────────────────────────────
@receiver(post_save, sender='marketplace.Product')
def auto_translate_product(sender, instance, created, **kwargs):
    from marketplace.models import Product
    _auto_translate('Product', instance, created, Product, [
        ('name', 'product_name'),
        ('description', 'product_description'),
    ])


# ──────────────────────────────────────────────
# SupermarketItem
# ──────────────────────────────────────────────
@receiver(post_save, sender='marketplace.SupermarketItem')
def auto_translate_supermarket_item(sender, instance, created, **kwargs):
    from marketplace.models import SupermarketItem
    _auto_translate('SupermarketItem', instance, created, SupermarketItem, [
        ('name', 'product_name'),
        ('description', 'product_description'),
    ])


# ──────────────────────────────────────────────
# Course
# ──────────────────────────────────────────────
@receiver(post_save, sender='marketplace.Course')
def auto_translate_course(sender, instance, created, **kwargs):
    from marketplace.models import Course
    _auto_translate('Course', instance, created, Course, [
        ('title', 'course_title'),
        ('description', 'course_description'),
    ])


# ──────────────────────────────────────────────
# Category
# ──────────────────────────────────────────────
@receiver(post_save, sender='marketplace.Category')
def auto_translate_category(sender, instance, created, **kwargs):
    from marketplace.models import Category
    _auto_translate('Category', instance, created, Category, [
        ('name', 'general'),
    ])
