"""
Marketplace signals — traduction automatique des nouveaux contenus
via TranslationService (OpenRouter / Gemma 4 gratuit).

Les traductions sont effectuées uniquement à la création (created=True)
et seulement si le texte source en zh-hans est renseigné.
Le signal utilise .update() pour éviter la récursion.
"""
import logging
from django.db.models.signals import post_save
from django.dispatch import receiver

logger = logging.getLogger(__name__)


def _get_service():
    """Import lazy pour éviter les imports circulaires au démarrage."""
    from core.services.translation_service import TranslationService
    return TranslationService()


# ──────────────────────────────────────────────
# Product
# ──────────────────────────────────────────────
@receiver(post_save, sender='marketplace.Product')
def auto_translate_product(sender, instance, created, **kwargs):
    if not created:
        return
    name_src = instance.name_zh_hans or instance.name
    desc_src = instance.description_zh_hans or instance.description or ''
    if not name_src:
        return
    try:
        svc = _get_service()
        from marketplace.models import Product
        Product.objects.filter(pk=instance.pk).update(
            name_en=svc.translate(name_src, 'zh-hans', 'en', 'product_name'),
            name_fr=svc.translate(name_src, 'zh-hans', 'fr', 'product_name'),
            description_en=svc.translate(desc_src, 'zh-hans', 'en', 'product_description') if desc_src else '',
            description_fr=svc.translate(desc_src, 'zh-hans', 'fr', 'product_description') if desc_src else '',
        )
        logger.info("Auto-translated Product #%s", instance.pk)
    except Exception as exc:
        logger.error("auto_translate_product error for #%s: %s", instance.pk, exc)


# ──────────────────────────────────────────────
# SupermarketItem
# ──────────────────────────────────────────────
@receiver(post_save, sender='marketplace.SupermarketItem')
def auto_translate_supermarket_item(sender, instance, created, **kwargs):
    if not created:
        return
    name_src = instance.name_zh_hans or instance.name
    desc_src = instance.description_zh_hans or instance.description or ''
    if not name_src:
        return
    try:
        svc = _get_service()
        from marketplace.models import SupermarketItem
        SupermarketItem.objects.filter(pk=instance.pk).update(
            name_en=svc.translate(name_src, 'zh-hans', 'en', 'product_name'),
            name_fr=svc.translate(name_src, 'zh-hans', 'fr', 'product_name'),
            description_en=svc.translate(desc_src, 'zh-hans', 'en', 'product_description') if desc_src else '',
            description_fr=svc.translate(desc_src, 'zh-hans', 'fr', 'product_description') if desc_src else '',
        )
        logger.info("Auto-translated SupermarketItem #%s", instance.pk)
    except Exception as exc:
        logger.error("auto_translate_supermarket_item error for #%s: %s", instance.pk, exc)


# ──────────────────────────────────────────────
# Course
# ──────────────────────────────────────────────
@receiver(post_save, sender='marketplace.Course')
def auto_translate_course(sender, instance, created, **kwargs):
    if not created:
        return
    title_src = instance.title_zh_hans or instance.title
    desc_src = instance.description_zh_hans or instance.description or ''
    if not title_src:
        return
    try:
        svc = _get_service()
        from marketplace.models import Course
        Course.objects.filter(pk=instance.pk).update(
            title_en=svc.translate(title_src, 'zh-hans', 'en', 'course_title'),
            title_fr=svc.translate(title_src, 'zh-hans', 'fr', 'course_title'),
            description_en=svc.translate(desc_src, 'zh-hans', 'en', 'course_description') if desc_src else '',
            description_fr=svc.translate(desc_src, 'zh-hans', 'fr', 'course_description') if desc_src else '',
        )
        logger.info("Auto-translated Course #%s", instance.pk)
    except Exception as exc:
        logger.error("auto_translate_course error for #%s: %s", instance.pk, exc)


# ──────────────────────────────────────────────
# Category
# ──────────────────────────────────────────────
@receiver(post_save, sender='marketplace.Category')
def auto_translate_category(sender, instance, created, **kwargs):
    if not created:
        return
    name_src = instance.name_zh_hans or instance.name
    if not name_src:
        return
    try:
        svc = _get_service()
        from marketplace.models import Category
        Category.objects.filter(pk=instance.pk).update(
            name_en=svc.translate(name_src, 'zh-hans', 'en', 'general'),
            name_fr=svc.translate(name_src, 'zh-hans', 'fr', 'general'),
        )
        logger.info("Auto-translated Category #%s", instance.pk)
    except Exception as exc:
        logger.error("auto_translate_category error for #%s: %s", instance.pk, exc)
