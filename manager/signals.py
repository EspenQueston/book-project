"""
Order Management System - Django Signals
Handles database notifications when payments are made
Also auto-translates Book / Publisher / Author on creation via Gemma 4.
"""

from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from django.core.mail import send_mail
from django.conf import settings
from django.utils import timezone
from .models import Order, OrderNotification
import logging

logger = logging.getLogger(__name__)

# Debug logging only — avoid non-ASCII in print() (Windows cp1252 consoles raise UnicodeEncodeError).
logger.debug("Order management signals module loaded")

@receiver(pre_save, sender=Order)
def track_payment_status_change(sender, instance, **kwargs):
    """Track payment status changes before saving"""
    logger.debug(
        "Order pre_save: %s",
        instance.order_number if hasattr(instance, "order_number") else "NEW",
    )
    if instance.pk:  # Only for existing orders
        try:
            old_order = Order.objects.get(pk=instance.pk)
            instance._old_payment_status = old_order.payment_status
            logger.debug(
                "Order payment status change: %s -> %s",
                old_order.payment_status,
                instance.payment_status,
            )
        except Order.DoesNotExist:
            instance._old_payment_status = None
    else:
        instance._old_payment_status = None


@receiver(post_save, sender=Order)
def handle_payment_status_change(sender, instance, created, **kwargs):
    """Handle payment status changes and send notifications"""
    logger.debug(
        "Order post_save: %s, created=%s",
        instance.order_number,
        created,
    )
    
    # Skip if this is a new order creation
    if created:
        logger.info(f"New order created: {instance.order_number}")
        return
    
    # Check if payment status changed
    old_status = getattr(instance, '_old_payment_status', None)
    current_status = instance.payment_status

    logger.debug("Order payment check: %s -> %s", old_status, current_status)

    if old_status and old_status != current_status:
        logger.info(f"Payment status changed for order {instance.order_number}: {old_status} -> {current_status}")
        
        # Create notification record
        create_payment_notification(instance, old_status, current_status)
        
        # Send email notification if payment is successful
        if current_status == 'paid':
            send_payment_confirmation(instance)
        
        # Handle refund notifications
        elif current_status == 'refunded':
            send_refund_notification(instance)
    else:
        logger.debug(
            "No payment status change for order %s (old=%s)",
            instance.order_number,
            old_status,
        )


def create_payment_notification(order, old_status, new_status):
    """Create a notification record in the database"""
    try:
        # Create notification message
        status_messages = {
            ('pending', 'paid'): f"订单 {order.order_number} 支付成功",
            ('pending', 'failed'): f"订单 {order.order_number} 支付失败",
            ('paid', 'refunded'): f"订单 {order.order_number} 已退款",
            ('failed', 'paid'): f"订单 {order.order_number} 重新支付成功",
        }
        
        message = status_messages.get((old_status, new_status), 
                                    f"订单 {order.order_number} 支付状态从 {old_status} 变更为 {new_status}")
        
        # Create notification record
        OrderNotification.objects.create(
            order=order,
            notification_type='payment_status_change',
            message=message,
            details={
                'old_status': old_status,
                'new_status': new_status,
                'order_number': order.order_number,
                'customer_name': order.customer_name,
                'total_amount': str(order.total_amount),
                'timestamp': timezone.now().isoformat()
            }
        )
        
        logger.info(f"Payment notification created for order {order.order_number}")
        
    except Exception as e:
        logger.error(f"Failed to create payment notification for order {order.order_number}: {str(e)}")


def send_payment_confirmation(order):
    """Send payment confirmation email to customer"""
    try:
        if not order.customer_email:
            logger.warning(f"No email address for order {order.order_number}")
            return
        
        subject = f'Payment confirmed - Order {order.order_number} / Paiement confirmé - Commande {order.order_number}'
        message = f"""
Hello {order.customer_name},

Your order has been paid successfully!

Order details:
Order number: {order.order_number}
Amount paid: {order.total_amount}
Payment time: {timezone.now().strftime('%Y-%m-%d %H:%M:%S')}

We will process your order as soon as possible. Thank you for your purchase!

This is an automated message — please do not reply.

---

Bonjour {order.customer_name},

Votre commande a été payée avec succès !

Détails de la commande :
Numéro de commande : {order.order_number}
Montant payé : {order.total_amount}
Date de paiement : {timezone.now().strftime('%Y-%m-%d %H:%M:%S')}

Nous traiterons votre commande dans les plus brefs délais. Merci pour votre achat !

Message automatique — merci de ne pas répondre.
        """
        
        send_mail(
            subject=subject,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[order.customer_email],
            fail_silently=False
        )
        
        logger.info(f"Payment confirmation email sent for order {order.order_number}")
        
    except Exception as e:
        logger.error(f"Failed to send payment confirmation email for order {order.order_number}: {str(e)}")


def send_refund_notification(order):
    """Send refund notification email to customer"""
    try:
        if not order.customer_email:
            logger.warning(f"No email address for order {order.order_number}")
            return
        
        subject = f'Refund processed - Order {order.order_number} / Remboursement - Commande {order.order_number}'
        message = f"""
Hello {order.customer_name},

Your order refund has been processed.

Order details:
Order number: {order.order_number}
Refund amount: {order.total_amount}
Refund time: {timezone.now().strftime('%Y-%m-%d %H:%M:%S')}

The refund should appear within 3–5 business days.

If you have any questions, please contact us at admin@duno360.com.

This is an automated message — please do not reply.

---

Bonjour {order.customer_name},

Le remboursement de votre commande a été traité.

Détails de la commande :
Numéro de commande : {order.order_number}
Montant remboursé : {order.total_amount}
Date du remboursement : {timezone.now().strftime('%Y-%m-%d %H:%M:%S')}

Le remboursement devrait apparaître sous 3 à 5 jours ouvrables.

Pour toute question, contactez-nous à admin@duno360.com.

Message automatique — merci de ne pas répondre.
        """
        
        send_mail(
            subject=subject,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[order.customer_email],
            fail_silently=False
        )
        
        logger.info(f"Refund notification email sent for order {order.order_number}")
        
    except Exception as e:
        logger.error(f"Failed to send refund notification email for order {order.order_number}: {str(e)}")


@receiver(post_save, sender=Order)
def update_order_status_on_payment(sender, instance, created, **kwargs):
    """Automatically update order status when payment is confirmed"""

    if not created and instance.payment_status == 'paid' and instance.status == 'pending':
        # Automatically move to processing when payment is confirmed
        Order.objects.filter(pk=instance.pk).update(status='processing')
        logger.info(f"Order {instance.order_number} status automatically updated to processing after payment")


# ──────────────────────────────────────────────────────────────────────────────
# Traduction automatique — Book / Author
# ──────────────────────────────────────────────────────────────────────────────

def _get_translation_service():
    """Import lazy pour éviter les problèmes de démarrage."""
    from core.services.translation_service import TranslationService
    return TranslationService()


@receiver(post_save, sender='manager.Book')
def auto_translate_book(sender, instance, created, **kwargs):
    """Translate Book name & description to EN and FR on creation."""
    if not created:
        return
    name_src = instance.name_zh_hans or instance.name
    desc_src = instance.description_zh_hans or instance.description or ''
    if not name_src:
        return
    try:
        svc = _get_translation_service()
        from manager.models import Book
        Book.objects.filter(pk=instance.pk).update(
            name_en=svc.translate(name_src, 'zh-hans', 'en', 'book_name'),
            name_fr=svc.translate(name_src, 'zh-hans', 'fr', 'book_name'),
            description_en=svc.translate(desc_src, 'zh-hans', 'en', 'book_description') if desc_src else '',
            description_fr=svc.translate(desc_src, 'zh-hans', 'fr', 'book_description') if desc_src else '',
        )
        logger.info("Auto-translated Book #%s", instance.pk)
    except Exception as exc:
        logger.error("auto_translate_book error for #%s: %s", instance.pk, exc)


@receiver(post_save, sender='manager.Author')
def auto_translate_author(sender, instance, created, **kwargs):
    """Translate Author name to EN and FR on creation."""
    if not created:
        return
    name_src = instance.name_zh_hans or instance.name
    if not name_src:
        return
    try:
        svc = _get_translation_service()
        from manager.models import Author
        Author.objects.filter(pk=instance.pk).update(
            name_en=svc.translate(name_src, 'zh-hans', 'en', 'general'),
            name_fr=svc.translate(name_src, 'zh-hans', 'fr', 'general'),
        )
        logger.info("Auto-translated Author #%s", instance.pk)
    except Exception as exc:
        logger.error("auto_translate_author error for #%s: %s", instance.pk, exc)


# ──────────────────────────────────────────────────────────────────────────────
# Auto-create wallet for new SiteUser
# ──────────────────────────────────────────────────────────────────────────────

@receiver(post_save, sender='manager.SiteUser')
def auto_create_wallet(sender, instance, created, **kwargs):
    """Create a UserWallet with zero balance for every new SiteUser."""
    if not created:
        return
    from decimal import Decimal
    from manager.models import UserWallet
    UserWallet.objects.get_or_create(user=instance, defaults={
        'balance': Decimal('0.00'),
        'total_deposited': Decimal('0.00'),
        'total_spent': Decimal('0.00'),
    })
