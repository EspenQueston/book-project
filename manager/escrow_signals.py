"""Signals linking orders to escrow hold / release."""
import logging

from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver

logger = logging.getLogger(__name__)


@receiver(pre_save, sender='manager.Order')
def order_track_escrow_state(sender, instance, **kwargs):
    if instance.pk:
        from manager.models import Order
        try:
            old = Order.objects.get(pk=instance.pk)
            instance._escrow_old_status = old.status
            instance._escrow_old_payment = old.payment_status
        except Order.DoesNotExist:
            instance._escrow_old_status = None
            instance._escrow_old_payment = None
    else:
        instance._escrow_old_status = None
        instance._escrow_old_payment = None


@receiver(post_save, sender='manager.Order')
def order_escrow_sync(sender, instance, created, **kwargs):
    from manager.escrow_service import sync_escrow_on_order_update, sync_escrow_on_payment

    if created:
        if instance.payment_status == 'completed':
            try:
                sync_escrow_on_payment(instance, 'book')
            except Exception as exc:
                logger.exception('Escrow create failed for new book order %s: %s', instance.order_number, exc)
        return
    old_status = getattr(instance, '_escrow_old_status', None)
    old_payment = getattr(instance, '_escrow_old_payment', None)
    try:
        sync_escrow_on_order_update(instance, 'book', old_status, old_payment)
    except Exception as exc:
        logger.exception('Escrow sync failed for book order %s: %s', instance.order_number, exc)


@receiver(pre_save, sender='marketplace.MarketplaceOrder')
def mkt_order_track_escrow_state(sender, instance, **kwargs):
    if instance.pk:
        from marketplace.models import MarketplaceOrder
        try:
            old = MarketplaceOrder.objects.get(pk=instance.pk)
            instance._escrow_old_status = old.status
            instance._escrow_old_payment = old.payment_status
        except MarketplaceOrder.DoesNotExist:
            instance._escrow_old_status = None
            instance._escrow_old_payment = None
    else:
        instance._escrow_old_status = None
        instance._escrow_old_payment = None


@receiver(post_save, sender='marketplace.MarketplaceOrder')
def mkt_order_escrow_sync(sender, instance, created, **kwargs):
    from manager.escrow_service import sync_escrow_on_order_update, sync_escrow_on_payment

    if created:
        if instance.payment_status == 'completed':
            try:
                sync_escrow_on_payment(instance, 'marketplace')
            except Exception as exc:
                logger.exception('Escrow create failed for new mkt order %s: %s', instance.order_number, exc)
        return
    old_status = getattr(instance, '_escrow_old_status', None)
    old_payment = getattr(instance, '_escrow_old_payment', None)
    try:
        sync_escrow_on_order_update(instance, 'marketplace', old_status, old_payment)
    except Exception as exc:
        logger.exception('Escrow sync failed for marketplace order %s: %s', instance.order_number, exc)
