"""
Order lifecycle email notifications.

Every previous version of this project sent exactly two order-related
emails (payment confirmed, refund processed) — shipped/delivered/cancelled/
review-request never sent anything, and the payment-confirmed one was
actually dead code (it fired on payment_status == 'paid', a value that
doesn't exist in PAYMENT_STATUS_CHOICES; the real value is 'completed').

This module is the single place every order-lifecycle email is built and
sent from, called explicitly at each fulfillment_service.py transition
(not via signals — the previous signal-based approach is what let the
'paid' vs 'completed' bug go unnoticed for so long).
"""
import logging

from django.conf import settings
from django.core.mail import EmailMultiAlternatives

logger = logging.getLogger(__name__)

# Matches the site's actual --hero-gradient (manager/templates/public/home.html)
# — the purple #667eea/#764ba2 pair used here previously was a leftover from an
# older theme and didn't match the current blue brand identity anywhere else
# on the platform.
BRAND_GRADIENT = 'linear-gradient(135deg,#14245f 0%,#1d4ed8 100%)'


def _wrap_email(heading, body_html, cta_url=None, cta_label=None, footer_note=''):
    cta_block = ''
    if cta_url and cta_label:
        cta_block = f'''
        <div style="text-align:center;margin:28px 0 4px;">
            <a href="{cta_url}" style="display:inline-block;background:{BRAND_GRADIENT};color:#fff;
               text-decoration:none;font-weight:700;font-size:0.95rem;padding:14px 32px;border-radius:12px;">
                {cta_label}
            </a>
        </div>'''
    return f'''
    <div style="font-family:'Segoe UI',Arial,sans-serif;max-width:560px;margin:0 auto;background:#fff;border-radius:16px;overflow:hidden;box-shadow:0 4px 24px rgba(0,0,0,0.08);">
        <div style="background:{BRAND_GRADIENT};padding:32px 28px;text-align:center;">
            <h1 style="color:#fff;margin:0;font-size:1.4rem;">DUNO 360</h1>
            <p style="color:rgba(255,255,255,0.9);margin:8px 0 0;font-size:1rem;">{heading}</p>
        </div>
        <div style="padding:32px 28px;color:#333;font-size:0.95rem;line-height:1.7;">
            {body_html}
            {cta_block}
        </div>
        <div style="background:#f8f9ff;padding:16px 28px;text-align:center;border-top:1px solid #eee;">
            <p style="color:#aaa;font-size:0.8rem;margin:0;">{footer_note or 'This is an automated message — please do not reply. / Message automatique — merci de ne pas répondre.'}</p>
        </div>
    </div>
    '''


def _send(to_email, subject, heading, body_html, plain_body, cta_url=None, cta_label=None):
    if not to_email:
        return False
    try:
        html = _wrap_email(heading, body_html, cta_url, cta_label)
        msg = EmailMultiAlternatives(subject, plain_body, settings.DEFAULT_FROM_EMAIL, [to_email])
        msg.attach_alternative(html, 'text/html')
        msg.send(fail_silently=False)
        return True
    except Exception:
        logger.exception('Failed to send email "%s" to %s', subject, to_email)
        return False


def _order_email_and_name(order, order_source):
    if order_source == 'book':
        return order.customer_email, order.customer_name
    return order.user_email, (order.user_name or '')


def _fcfa(amount):
    try:
        return f'{int(amount):,} FCFA'.replace(',', ' ')
    except (TypeError, ValueError):
        return f'{amount} FCFA'


def _track_url(order_number):
    base = getattr(settings, 'SITE_BASE_URL', 'https://duno360.com')
    return f'{base}/manager/track-order/?order_number={order_number}'


# ---------------------------------------------------------------------------
# Payment confirmed — fixes the previously-dead 'paid' vs 'completed' bug
# ---------------------------------------------------------------------------

def send_payment_confirmed(order, order_source):
    email, name = _order_email_and_name(order, order_source)
    subject = f'Paiement confirmé — Commande {order.order_number} / Payment confirmed'
    donation_line = ''
    if getattr(order, 'donation_amount', None):
        donation_line = f'''
        <p style="background:rgba(239,68,68,0.08);border-radius:10px;padding:10px 14px;">
            <i class="fas fa-heart" style="color:#ef4444;"></i>
            Thank you — this includes a {_fcfa(order.donation_amount)} donation supporting children in need. /
            Merci — ce paiement inclut un don de {_fcfa(order.donation_amount)} pour soutenir les enfants dans le besoin.
        </p>'''
    body_html = f'''
        <p>Hello <strong>{name}</strong> / Bonjour <strong>{name}</strong>,</p>
        <p>Your payment for order <strong>{order.order_number}</strong> ({_fcfa(order.total_amount)}) has been confirmed.
        We'll notify you again as soon as the seller accepts your order.</p>
        <p>Votre paiement pour la commande <strong>{order.order_number}</strong> ({_fcfa(order.total_amount)}) a été confirmé.
        Nous vous notifierons dès que le vendeur aura accepté votre commande.</p>
        {donation_line}
    '''
    plain = f'Payment confirmed for order {order.order_number} ({_fcfa(order.total_amount)}).'
    if getattr(order, 'donation_amount', None):
        plain += f' Includes a {_fcfa(order.donation_amount)} donation — thank you!'
    return _send(email, subject, 'Paiement confirmé ✅', body_html, plain, _track_url(order.order_number), 'Suivre ma commande')


# ---------------------------------------------------------------------------
# Seller accepted the order
# ---------------------------------------------------------------------------

def send_order_accepted(order, order_source, shipment):
    email, name = _order_email_and_name(order, order_source)
    vendor_name = shipment.vendor.company_name if shipment.vendor else 'DUNO 360'
    subject = f'Commande acceptée — {order.order_number} / Order accepted'
    body_html = f'''
        <p>Hello <strong>{name}</strong> / Bonjour <strong>{name}</strong>,</p>
        <p><strong>{vendor_name}</strong> has accepted your order <strong>{order.order_number}</strong> and is preparing it for shipment.</p>
        <p><strong>{vendor_name}</strong> a accepté votre commande <strong>{order.order_number}</strong> et la prépare pour l'expédition.</p>
    '''
    plain = f'{vendor_name} accepted order {order.order_number}.'
    return _send(email, subject, 'Commande acceptée 📦', body_html, plain, _track_url(order.order_number), 'Suivre ma commande')


# ---------------------------------------------------------------------------
# Shipped — with tracking
# ---------------------------------------------------------------------------

def send_shipment_shipped(order, order_source, shipment):
    email, name = _order_email_and_name(order, order_source)
    subject = f'Expédiée — Commande {order.order_number} / Order shipped'
    eta = f' (livraison estimée : {shipment.estimated_delivery_date.strftime("%d/%m/%Y")})' if shipment.estimated_delivery_date else ''
    body_html = f'''
        <p>Hello <strong>{name}</strong> / Bonjour <strong>{name}</strong>,</p>
        <p>Great news — your order <strong>{order.order_number}</strong> has shipped{eta}.</p>
        <p><strong>Carrier / Transporteur:</strong> {shipment.carrier}<br>
        <strong>Tracking number / N° de suivi:</strong> {shipment.tracking_number}</p>
        <p>Bonne nouvelle — votre commande <strong>{order.order_number}</strong> a été expédiée{eta}.</p>
    '''
    plain = f'Order {order.order_number} shipped via {shipment.carrier}, tracking {shipment.tracking_number}.'
    return _send(email, subject, 'Commande expédiée 🚚', body_html, plain, _track_url(order.order_number), 'Suivre le colis')


# ---------------------------------------------------------------------------
# Out for delivery
# ---------------------------------------------------------------------------

def send_out_for_delivery(order, order_source, shipment):
    email, name = _order_email_and_name(order, order_source)
    subject = f'En cours de livraison — {order.order_number} / Out for delivery'
    body_html = f'''
        <p>Hello <strong>{name}</strong> / Bonjour <strong>{name}</strong>,</p>
        <p>Your order <strong>{order.order_number}</strong> is out for delivery today.</p>
        <p>Votre commande <strong>{order.order_number}</strong> est en cours de livraison aujourd'hui.</p>
    '''
    plain = f'Order {order.order_number} is out for delivery today.'
    return _send(email, subject, 'En cours de livraison 🛵', body_html, plain, _track_url(order.order_number), 'Suivre ma commande')


# ---------------------------------------------------------------------------
# Delivered — confirm receipt CTA
# ---------------------------------------------------------------------------

def send_delivered_confirm_receipt(order, order_source, shipment):
    from manager.fulfillment_service import AUTO_CONFIRM_RECEIPT_DAYS

    email, name = _order_email_and_name(order, order_source)
    subject = f'Livrée — confirmez la réception / Delivered — confirm receipt ({order.order_number})'
    body_html = f'''
        <p>Hello <strong>{name}</strong> / Bonjour <strong>{name}</strong>,</p>
        <p>Your order <strong>{order.order_number}</strong> has been marked as delivered. Please confirm you received it —
        this releases payment to the seller and lets you leave a review.</p>
        <p>If you don't confirm, we'll automatically confirm it in {AUTO_CONFIRM_RECEIPT_DAYS} days
        unless you open a dispute first.</p>
        <p>Votre commande <strong>{order.order_number}</strong> a été marquée comme livrée. Merci de confirmer la réception —
        cela libère le paiement au vendeur et vous permet de laisser un avis.</p>
        <p>Si vous ne confirmez pas, la réception sera confirmée automatiquement dans {AUTO_CONFIRM_RECEIPT_DAYS} jours,
        sauf si vous ouvrez un litige avant.</p>
    '''
    plain = f'Order {order.order_number} delivered — please confirm receipt.'
    return _send(email, subject, 'Colis livré 📬', body_html, plain, _track_url(order.order_number), 'Confirmer la réception')


# ---------------------------------------------------------------------------
# Review request
# ---------------------------------------------------------------------------

def send_review_request(order, order_source, item_name):
    email, name = _order_email_and_name(order, order_source)
    subject = f'Comment était votre achat ? / How was your purchase? ({order.order_number})'
    body_html = f'''
        <p>Hello <strong>{name}</strong> / Bonjour <strong>{name}</strong>,</p>
        <p>Hope you're enjoying <strong>{item_name}</strong>! Would you take a minute to rate your purchase?
        It helps other buyers and the seller.</p>
        <p>Nous espérons que <strong>{item_name}</strong> vous plaît ! Prendriez-vous une minute pour noter votre achat ?
        Cela aide les autres acheteurs et le vendeur.</p>
    '''
    plain = f'Please review your purchase: {item_name} (order {order.order_number}).'
    return _send(email, subject, 'Votre avis compte ⭐', body_html, plain, _track_url(order.order_number), 'Laisser un avis')


# ---------------------------------------------------------------------------
# Return / dispute
# ---------------------------------------------------------------------------

def send_return_opened(order, order_source, return_request):
    email, name = _order_email_and_name(order, order_source)
    subject = f'Demande de retour reçue — {order.order_number} / Return request received'
    body_html = f'''
        <p>Hello <strong>{name}</strong> / Bonjour <strong>{name}</strong>,</p>
        <p>We've received your return request for order <strong>{order.order_number}</strong>
        ({return_request.get_reason_display()}). We'll review it and get back to you shortly.</p>
        <p>Nous avons bien reçu votre demande de retour pour la commande <strong>{order.order_number}</strong>
        ({return_request.get_reason_display()}). Nous l'examinerons et reviendrons vers vous rapidement.</p>
    '''
    plain = f'Return request received for order {order.order_number}.'
    return _send(email, subject, 'Demande de retour reçue 📝', body_html, plain, _track_url(order.order_number), 'Suivre ma demande')


def send_return_resolved(order, order_source, return_request):
    email, name = _order_email_and_name(order, order_source)
    approved = return_request.status == 'approved'
    subject = f'Retour {"approuvé" if approved else "refusé"} — {order.order_number}'
    if approved:
        body_html = f'''
            <p>Hello <strong>{name}</strong> / Bonjour <strong>{name}</strong>,</p>
            <p>Your return request for order <strong>{order.order_number}</strong> has been approved.
            You'll be refunded once the returned item is received.</p>
            <p>Votre demande de retour pour la commande <strong>{order.order_number}</strong> a été approuvée.
            Vous serez remboursé(e) une fois l'article retourné reçu.</p>
        '''
    else:
        note = return_request.resolution_note or ''
        body_html = f'''
            <p>Hello <strong>{name}</strong> / Bonjour <strong>{name}</strong>,</p>
            <p>Your return request for order <strong>{order.order_number}</strong> was not approved.{(' Note: ' + note) if note else ''}</p>
            <p>Votre demande de retour pour la commande <strong>{order.order_number}</strong> n'a pas été approuvée.{(' Note : ' + note) if note else ''}</p>
        '''
    plain = f'Return request for order {order.order_number}: {return_request.get_status_display()}.'
    return _send(email, subject, 'Retour ' + ('approuvé ✅' if approved else 'refusé'), body_html, plain, _track_url(order.order_number), 'Voir ma commande')


# ---------------------------------------------------------------------------
# Cancelled / refunded
# ---------------------------------------------------------------------------

def send_order_cancelled(order, order_source, reason=''):
    email, name = _order_email_and_name(order, order_source)
    subject = f'Commande annulée — {order.order_number} / Order cancelled'
    reason_line = f'<p><strong>Reason / Motif:</strong> {reason}</p>' if reason else ''
    body_html = f'''
        <p>Hello <strong>{name}</strong> / Bonjour <strong>{name}</strong>,</p>
        <p>Your order <strong>{order.order_number}</strong> has been cancelled.
        If you were charged, a refund is being processed.</p>
        {reason_line}
        <p>Votre commande <strong>{order.order_number}</strong> a été annulée.
        Si vous avez été débité(e), un remboursement est en cours.</p>
    '''
    plain = f'Order {order.order_number} cancelled.'
    return _send(email, subject, 'Commande annulée', body_html, plain, _track_url(order.order_number), 'Voir ma commande')


def send_refund_processed(order, order_source, amount):
    email, name = _order_email_and_name(order, order_source)
    subject = f'Remboursement effectué — {order.order_number} / Refund processed'
    body_html = f'''
        <p>Hello <strong>{name}</strong> / Bonjour <strong>{name}</strong>,</p>
        <p>Your refund of <strong>{_fcfa(amount)}</strong> for order <strong>{order.order_number}</strong>
        has been sent to your mobile money account.</p>
        <p>Votre remboursement de <strong>{_fcfa(amount)}</strong> pour la commande <strong>{order.order_number}</strong>
        a été envoyé sur votre compte mobile money.</p>
    '''
    plain = f'Refund of {_fcfa(amount)} processed for order {order.order_number}.'
    return _send(email, subject, 'Remboursement effectué 💸', body_html, plain)


# ---------------------------------------------------------------------------
# Seller-facing: SLA breach nudge (internal, not the buyer)
# ---------------------------------------------------------------------------

def send_seller_sla_nudge(shipment):
    """Sent the moment a new paid shipment lands in a vendor's queue —
    prompts them to accept/reject before the auto-accept SLA kicks in."""
    if not shipment.vendor or not shipment.vendor.email:
        return False
    from manager.fulfillment_service import SELLER_ACCEPT_SLA_HOURS

    subject = f'Nouvelle commande à confirmer — {shipment.order_number}'
    body_html = f'''
        <p>Bonjour {shipment.vendor.company_name},</p>
        <p>Vous avez une nouvelle commande payée : <strong>{shipment.order_number}</strong>.
        Merci de l'accepter ou de la refuser sous {SELLER_ACCEPT_SLA_HOURS}h — passé ce délai,
        elle sera acceptée automatiquement.</p>
    '''
    plain = f'New order {shipment.order_number} — please accept or reject within {SELLER_ACCEPT_SLA_HOURS}h.'
    return _send(shipment.vendor.email, subject, 'Nouvelle commande 🛎️', body_html, plain, '/manager/vendor/orders/', 'Voir la commande')
