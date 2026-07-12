"""
Payment callback views for MTN MoMo & Airtel Money webhooks.
These endpoints receive asynchronous payment notifications.
"""

import json
import logging
import hmac
import hashlib

from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST, require_GET
from django.conf import settings
from django.utils import timezone

from manager import models
from marketplace.models import MarketplaceOrder

logger = logging.getLogger(__name__)


def _find_order(reference_id):
    """
    Find the order associated with a payment reference.
    Checks both book orders and marketplace orders.
    Returns (order, order_type) tuple.
    """
    # Check book orders
    try:
        order = models.Order.objects.get(payment_transaction_id=reference_id)
        return order, 'book'
    except models.Order.DoesNotExist:
        pass

    # Check marketplace orders
    try:
        order = MarketplaceOrder.objects.get(payment_transaction_id=reference_id)
        return order, 'marketplace'
    except MarketplaceOrder.DoesNotExist:
        pass

    return None, None


def _update_order_status(order, status, transaction_id=None):
    """Update order payment status based on provider callback."""
    was_already_completed = order.payment_status == 'completed'

    if status == 'SUCCESSFUL':
        order.payment_status = 'completed'
        order.payment_completed_at = timezone.now()
        if hasattr(order, 'status'):
            if order.status in ('payment_pending', 'pending'):
                order.status = 'processing'
    elif status == 'FAILED':
        order.payment_status = 'failed'
        if hasattr(order, 'status'):
            if order.status == 'payment_pending':
                order.status = 'cancelled'
    # Keep 'pending'/'processing' as-is for PENDING status

    if transaction_id:
        order.payment_transaction_id = transaction_id
    order.save()
    logger.info('Order %s updated: payment_status=%s',
                getattr(order, 'order_number', order.pk),
                order.payment_status)
    order_source = 'marketplace' if isinstance(order, MarketplaceOrder) else 'book'
    if order.payment_status == 'completed':
        try:
            from manager.fulfillment_service import create_shipments_for_order
            create_shipments_for_order(order, order_source)
        except Exception as exc:
            logger.exception('Shipment/escrow creation failed: %s', exc)
        if not was_already_completed:
            try:
                from manager import notifications_service
                notifications_service.send_payment_confirmed(order, order_source)
            except Exception:
                logger.exception('Payment confirmation email failed for %s', order.order_number)

            if getattr(order, 'donation_amount', None):
                try:
                    from manager.views import create_notification
                    from manager.templatetags.currency_filters import to_fcfa
                    create_notification(
                        'donation_received',
                        f'\U0001F49B Don reçu — {order.order_number}',
                        f'Ce paiement inclut un don solidaire de {to_fcfa(order.donation_amount)} '
                        f'(commande {order.order_number}, {to_fcfa(order.total_amount)} au total). '
                        f'À ne pas compter comme chiffre d\'affaires produit.',
                        icon='fas fa-heart', color='#ef4444',
                        link=f'/manager/order_detail/{order.id}/' if order_source == 'book' else '',
                        related_id=order.id,
                    )
                except Exception:
                    logger.exception('Donation admin notification failed for %s', order.order_number)


# =========================================================================
# MTN MoMo Callback
# =========================================================================
@csrf_exempt
@require_POST
def mtn_momo_callback(request):
    """
    Receive MTN MoMo payment notification.

    MTN sends a POST with JSON body containing:
    {
        "financialTransactionId": "...",
        "externalId": "...",
        "amount": "100",
        "currency": "EUR",
        "payer": {"partyIdType": "MSISDN", "partyId": "0612345678"},
        "payerMessage": "...",
        "payeeNote": "...",
        "status": "SUCCESSFUL" | "FAILED"
    }
    """
    try:
        body = json.loads(request.body)
        logger.info('MTN MoMo callback received: %s', json.dumps(body, indent=2))

        status = body.get('status', '')
        external_id = body.get('externalId', '')
        financial_tx_id = body.get('financialTransactionId', '')
        reference_id = body.get('referenceId', '')  # X-Reference-Id echoed

        # Try to find order by external_id (order_number) first
        order = None
        order_type = None

        # external_id is the order_number we set during initiation
        if external_id:
            try:
                order = models.Order.objects.get(order_number=external_id)
                order_type = 'book'
            except models.Order.DoesNotExist:
                try:
                    order = MarketplaceOrder.objects.get(order_number=external_id)
                    order_type = 'marketplace'
                except MarketplaceOrder.DoesNotExist:
                    pass

        # Fallback: find by payment_transaction_id (reference_id)
        if not order and reference_id:
            order, order_type = _find_order(reference_id)

        if not order:
            logger.warning('MTN callback: No order found for externalId=%s, '
                           'referenceId=%s', external_id, reference_id)
            return HttpResponse(status=200)  # Return 200 to stop retries

        _update_order_status(order, status,
                             transaction_id=financial_tx_id or reference_id)

        return HttpResponse(status=200)

    except json.JSONDecodeError:
        logger.error('MTN callback: Invalid JSON body')
        return HttpResponse(status=400)
    except Exception as e:
        logger.exception('MTN callback error: %s', e)
        return HttpResponse(status=200)  # Return 200 to prevent retries


# =========================================================================
# Airtel Money Callback
# =========================================================================
@csrf_exempt
@require_POST
def airtel_money_callback(request):
    """
    Receive Airtel Money payment notification.

    Airtel sends a POST with JSON body containing transaction details.
    The exact format depends on the API version. Typically:
    {
        "transaction": {
            "id": "...",
            "status_code": "TS",  (TS=success, TF=failed, TIP=in-progress)
            "message": "...",
            "airtel_money_id": "..."
        }
    }
    """
    try:
        body = json.loads(request.body)
        logger.info('Airtel callback received: %s', json.dumps(body, indent=2))

        tx = body.get('transaction', {})
        tx_id = tx.get('id', '')
        status_code = tx.get('status_code', '')
        airtel_money_id = tx.get('airtel_money_id', '')

        # Map Airtel status codes
        status_map = {
            'TS': 'SUCCESSFUL',
            'TF': 'FAILED',
            'TIP': 'PENDING',
            'TA': 'PENDING',
        }
        status = status_map.get(status_code, 'PENDING')

        # Find order by transaction reference
        order, order_type = _find_order(tx_id)
        if not order:
            logger.warning('Airtel callback: No order found for tx_id=%s',
                           tx_id)
            return HttpResponse(status=200)

        _update_order_status(order, status,
                             transaction_id=airtel_money_id or tx_id)

        return HttpResponse(status=200)

    except json.JSONDecodeError:
        logger.error('Airtel callback: Invalid JSON body')
        return HttpResponse(status=400)
    except Exception as e:
        logger.exception('Airtel callback error: %s', e)
        return HttpResponse(status=200)


# =========================================================================
# Payment initiation endpoint (AJAX from checkout)
# =========================================================================
@csrf_exempt
@require_POST
def initiate_momo_payment(request):
    """
    AJAX endpoint: Initiate an MTN MoMo or Airtel Money payment.

    POST JSON:
    {
        "order_number": "ORD-...",
        "phone_number": "0612345678",
        "payment_method": "mtn_money" | "airtel_money",
        "amount": 100.00
    }

    Returns JSON:
    {
        "success": true,
        "reference_id": "...",
        "status": "PENDING"
    }
    """
    try:
        body = json.loads(request.body)
        order_number = body.get('order_number', '')
        phone_number = body.get('phone_number', '')
        payment_method = body.get('payment_method', '')
        amount = body.get('amount', 0)

        if not all([order_number, phone_number, payment_method]):
            return JsonResponse({
                'success': False,
                'error': 'Missing required fields'
            }, status=400)

        # Find the order
        order = None
        try:
            order = models.Order.objects.get(order_number=order_number)
        except models.Order.DoesNotExist:
            try:
                order = MarketplaceOrder.objects.get(order_number=order_number)
            except MarketplaceOrder.DoesNotExist:
                return JsonResponse({
                    'success': False,
                    'error': 'Order not found'
                }, status=404)

        # Use order amount if not provided
        if not amount:
            amount = float(order.total_amount)

        # Initiate payment based on method
        if payment_method == 'mtn_money':
            from manager.payments.mtn_momo import MTNMoMoService
            result = MTNMoMoService.request_to_pay(
                amount=amount,
                phone_number=phone_number,
                external_id=order_number,
                payer_message=f'DUNO 360 - Order {order_number}',
            )
        elif payment_method == 'airtel_money':
            from manager.payments.airtel_money import AirtelMoneyService
            result = AirtelMoneyService.request_to_pay(
                amount=amount,
                phone_number=phone_number,
                external_id=order_number,
            )
        else:
            return JsonResponse({
                'success': False,
                'error': f'Unsupported payment method: {payment_method}'
            }, status=400)

        # Store the reference on the order
        if result.get('reference_id'):
            order.payment_transaction_id = result['reference_id']
            order.payment_status = 'processing'
            order.save()

        success = result.get('status') != 'FAILED'
        return JsonResponse({
            'success': success,
            'reference_id': result.get('reference_id', ''),
            'status': result.get('status', 'UNKNOWN'),
            'error': result.get('error', '') if not success else '',
        })

    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': 'Invalid JSON'}, status=400)
    except Exception as e:
        logger.exception('Payment initiation error: %s', e)
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


# =========================================================================
# Payment status polling endpoint (AJAX from confirmation page)
# =========================================================================
@require_GET
def check_payment_status(request):
    """
    AJAX polling endpoint to check payment status.

    GET /api/payment/status/?order_number=ORD-...

    Returns JSON:
    {
        "payment_status": "pending" | "completed" | "failed",
        "order_status": "processing" | "cancelled" | ...
    }
    """
    order_number = request.GET.get('order_number', '')
    if not order_number:
        return JsonResponse({'error': 'Missing order_number'}, status=400)

    # Find order
    order = None
    try:
        order = models.Order.objects.get(order_number=order_number)
    except models.Order.DoesNotExist:
        try:
            order = MarketplaceOrder.objects.get(order_number=order_number)
        except MarketplaceOrder.DoesNotExist:
            return JsonResponse({'error': 'Order not found'}, status=404)

    # If payment is still processing, try polling the provider
    if order.payment_status == 'processing' and order.payment_transaction_id:
        try:
            ref_id = order.payment_transaction_id
            payment_method = order.payment_method

            if payment_method == 'mtn_money':
                from manager.payments.mtn_momo import MTNMoMoService
                result = MTNMoMoService.get_payment_status(ref_id)
                provider_status = result.get('status', 'PENDING')
                if provider_status in ('SUCCESSFUL', 'FAILED'):
                    _update_order_status(order, provider_status, ref_id)

            elif payment_method == 'airtel_money':
                from manager.payments.airtel_money import AirtelMoneyService
                result = AirtelMoneyService.get_payment_status(ref_id)
                provider_status = AirtelMoneyService.normalize_status(result)
                if provider_status in ('SUCCESSFUL', 'FAILED'):
                    _update_order_status(order, provider_status, ref_id)

            elif payment_method == 'pawapay':
                # Deposits created via the hosted Payment Page (create_payment_page_session,
                # used by pawapay_pay()) are v2 deposits — the v1 status endpoint does not
                # reliably see them (confirmed empty result in testing). Check v2 first and
                # only fall back to v1 for any older/direct-API deposit that predates the
                # hosted-page integration.
                from manager.payments.pawapay import get_deposit_status, get_deposit_status_v2, normalize_pawapay_status
                result = get_deposit_status_v2(ref_id)
                if result.get('status') == 'NOT_FOUND':
                    result = get_deposit_status(ref_id)
                provider_status = normalize_pawapay_status(result.get('status', 'PENDING'))
                if provider_status in ('SUCCESSFUL', 'FAILED'):
                    _update_order_status(order, provider_status, ref_id)
                elif result.get('status') == 'NOT_FOUND':
                    # PawaPay: an abandoned Payment Page session is NOT_FOUND
                    # and "should be considered FAILED after 15 minutes" —
                    # without this the order stays stuck on 'processing'
                    # forever if the customer never pressed Pay.
                    age = (timezone.now() - order.created_at).total_seconds()
                    if age >= 15 * 60:
                        _update_order_status(order, 'FAILED', ref_id)

        except Exception as e:
            logger.warning('Error polling payment status: %s', e)

    return JsonResponse({
        'payment_status': order.payment_status,
        'order_status': order.status,
    })


# =========================================================================
# KKiaPay — Server-side transaction verification (called from JS widget)
# =========================================================================
@csrf_exempt
@require_POST
def kkiapay_verify(request):
    """
    Verify a KKiaPay transaction server-side after the JS widget fires
    addSuccessListener.

    POST JSON:
    {
        "transaction_id": "3iH6wjHJ3",
        "order_number":   "ORD-..."
    }

    Returns JSON:
    {
        "success": true | false,
        "payment_status": "completed" | "failed",
        "message": "..."
    }

    Security: always verify server-side — never trust the JS callback alone.
    """
    try:
        body = json.loads(request.body)
        transaction_id = body.get('transaction_id', '').strip()
        order_number = body.get('order_number', '').strip()

        if not transaction_id or not order_number:
            return JsonResponse(
                {'success': False, 'message': 'transaction_id and order_number are required'},
                status=400
            )

        # --- Find the order ---
        order = None
        try:
            order = models.Order.objects.get(order_number=order_number)
        except models.Order.DoesNotExist:
            try:
                order = MarketplaceOrder.objects.get(order_number=order_number)
            except MarketplaceOrder.DoesNotExist:
                return JsonResponse(
                    {'success': False, 'message': 'Order not found'},
                    status=404
                )

        # --- Idempotence: already processed ---
        if order.payment_status == 'completed':
            return JsonResponse({
                'success': True,
                'payment_status': 'completed',
                'message': 'Payment already confirmed',
            })

        # --- Verify with KKiaPay SDK ---
        from manager.payments.kkiapay import is_transaction_successful
        success, tx = is_transaction_successful(transaction_id)

        if success:
            _update_order_status(order, 'SUCCESSFUL', transaction_id=transaction_id)
            logger.info('KKiaPay verify OK: order=%s tx=%s amount=%s',
                        order_number, transaction_id,
                        getattr(tx, 'amount', '?'))
            return JsonResponse({
                'success': True,
                'payment_status': 'completed',
                'message': 'Payment verified and confirmed',
            })
        else:
            _update_order_status(order, 'FAILED', transaction_id=transaction_id)
            reason = getattr(tx, 'reason', 'unknown') if tx else 'verification_error'
            logger.warning('KKiaPay verify FAILED: order=%s tx=%s reason=%s',
                           order_number, transaction_id, reason)
            return JsonResponse({
                'success': False,
                'payment_status': 'failed',
                'message': f'Payment verification failed: {reason}',
            })

    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'message': 'Invalid JSON body'}, status=400)
    except Exception as exc:
        logger.exception('KKiaPay verify error: %s', exc)
        return JsonResponse({'success': False, 'message': 'Server error'}, status=500)


# =========================================================================
# KKiaPay — Webhook (async notification from KKiaPay servers)
# =========================================================================
@csrf_exempt
@require_POST
def kkiapay_webhook(request):
    """
    Receive asynchronous payment notifications from KKiaPay.

    KKiaPay sends POST with header:
        x-kkiapay-secret: <KKIAPAY_WEBHOOK_SECRET>

    Payload (success):
    {
        "transactionId": "3iH6wjHJ3",
        "isPaymentSucces": true,
        "event": "transaction.success",
        "amount": 1000,
        "fees": 19,
        "partnerId": "...",          <- order_number stored here
        "method": "MOBILE_MONEY",
        "account": "22996000000"
    }

    Payload (failure):
    {
        "transactionId": "erjEU5P9o",
        "isPaymentSucces": false,
        "event": "transaction.failed",
        "failureCode": "processing_error",
        "failureMessage": "processing_error",
        ...
    }

    Must return HTTP 2xx — otherwise KKiaPay retries 5 times.
    """
    # --- Verify webhook signature ---
    webhook_secret = getattr(settings, 'KKIAPAY_WEBHOOK_SECRET', '')
    if webhook_secret:
        incoming_secret = request.headers.get('x-kkiapay-secret', '')
        if incoming_secret != webhook_secret:
            logger.warning('KKiaPay webhook: invalid secret header — rejected')
            return HttpResponse(status=403)

    try:
        body = json.loads(request.body)
        logger.info('KKiaPay webhook received: %s', json.dumps(body))

        transaction_id = body.get('transactionId', '')
        is_success = body.get('isPaymentSucces', False)
        event = body.get('event', '')
        # partnerId is the order_number we store via widget `data` attribute
        order_number = body.get('partnerId', '')

        if not transaction_id:
            logger.warning('KKiaPay webhook: missing transactionId')
            return HttpResponse(status=200)

        # --- Find the order ---
        order = None
        if order_number:
            try:
                order = models.Order.objects.get(order_number=order_number)
            except models.Order.DoesNotExist:
                try:
                    order = MarketplaceOrder.objects.get(order_number=order_number)
                except MarketplaceOrder.DoesNotExist:
                    order = None

        # Fallback: find by payment_transaction_id
        if not order:
            order, _ = _find_order(transaction_id)

        if not order:
            logger.warning('KKiaPay webhook: no order found for tx=%s partnerId=%s',
                           transaction_id, order_number)
            return HttpResponse(status=200)  # 200 to stop retries

        # --- Idempotence ---
        if order.payment_status == 'completed':
            logger.info('KKiaPay webhook: order %s already completed, skipping',
                        order_number)
            return HttpResponse(status=200)

        # --- Update order ---
        if event == 'transaction.success' or is_success:
            _update_order_status(order, 'SUCCESSFUL', transaction_id=transaction_id)
            logger.info('KKiaPay webhook SUCCESS: order=%s tx=%s amount=%s',
                        order_number, transaction_id, body.get('amount'))
        elif event == 'transaction.failed' or not is_success:
            _update_order_status(order, 'FAILED', transaction_id=transaction_id)
            logger.warning('KKiaPay webhook FAILED: order=%s tx=%s code=%s msg=%s',
                           order_number, transaction_id,
                           body.get('failureCode', ''),
                           body.get('failureMessage', ''))

        return HttpResponse(status=200)

    except json.JSONDecodeError:
        logger.error('KKiaPay webhook: invalid JSON body')
        return HttpResponse(status=200)  # Still 200 to stop retries
    except Exception as exc:
        logger.exception('KKiaPay webhook error: %s', exc)
        return HttpResponse(status=200)  # Always 200 to avoid infinite retries


def _find_order_by_number(order_number):
    if not order_number:
        return None
    try:
        return models.Order.objects.get(order_number=order_number)
    except models.Order.DoesNotExist:
        try:
            return MarketplaceOrder.objects.get(order_number=order_number)
        except MarketplaceOrder.DoesNotExist:
            return None


def _process_seller_activation_callback(order_number, payment_id, internal_status, raw_status):
    """Handle a PawaPay webhook for a seller-activation fee payment (order
    numbers prefixed 'SVP-', created by manager.views.publish_entry()) —
    same re-verification safeguard as _pawapay_process_callback() below."""
    from manager.payments.pawapay import get_deposit_status, normalize_pawapay_status

    try:
        payment = models.SellerActivationPayment.objects.get(order_number=order_number)
    except models.SellerActivationPayment.DoesNotExist:
        logger.warning('PawaPay callback: no SellerActivationPayment for order_number=%s', order_number)
        return False

    if payment.status == 'paid':
        return True

    if internal_status == 'SUCCESSFUL' and payment_id:
        verified = get_deposit_status(payment_id)
        verified_status = normalize_pawapay_status(verified.get('status', 'PENDING'))
        if verified_status != 'SUCCESSFUL':
            logger.warning(
                'PawaPay callback: payload said %s but API verification returned %s '
                'for seller-activation deposit %s — not activating %s',
                raw_status, verified.get('status'), payment_id, order_number)
            internal_status = verified_status

    if internal_status == 'SUCCESSFUL':
        from manager.views import _activate_seller_from_payment
        _activate_seller_from_payment(payment)
    elif internal_status == 'FAILED':
        payment.status = 'failed'
        payment.external_status = 'failed'
        payment.save(update_fields=['status', 'external_status', 'updated_at'])
    return True


def _pawapay_process_callback(data):
    """Shared logic for PawaPay deposit/payout/refund webhooks.

    Security: the callback endpoint is unauthenticated, so the payload status
    is never trusted directly — a SUCCESSFUL status is confirmed against the
    PawaPay API before the order is marked paid.
    """
    from manager.payments.pawapay import get_deposit_status, normalize_pawapay_status

    payment_id = (
        data.get('depositId')
        or data.get('payoutId')
        or data.get('refundId')
        or data.get('id')
    )
    status = data.get('status', '')
    internal_status = normalize_pawapay_status(status)

    order_number = None
    for meta in data.get('metadata', []) or []:
        if meta.get('fieldName') == 'orderNumber':
            order_number = meta.get('fieldValue')
            break

    if order_number and order_number.startswith('SVP-'):
        return _process_seller_activation_callback(order_number, payment_id, internal_status, status)

    order = None
    if order_number:
        order = _find_order_by_number(order_number)
    if not order and payment_id:
        order, _ = _find_order(payment_id)

    if not order:
        logger.warning('PawaPay callback: no order for payment_id=%s order_number=%s',
                       payment_id, order_number)
        return False

    if order.payment_status == 'completed' and internal_status == 'SUCCESSFUL':
        return True

    # Never complete an order on the callback's word alone — re-check with
    # PawaPay. If the API is unreachable, leave the order pending; the
    # confirmation-page poller or a later callback retry will settle it.
    if internal_status == 'SUCCESSFUL' and data.get('depositId'):
        verified = get_deposit_status(data['depositId'])
        verified_status = normalize_pawapay_status(verified.get('status', 'PENDING'))
        if verified_status != 'SUCCESSFUL':
            logger.warning(
                'PawaPay callback: payload said %s but API verification returned %s '
                'for deposit %s — not completing order %s',
                status, verified.get('status'), payment_id,
                getattr(order, 'order_number', order.pk))
            internal_status = verified_status

    _update_order_status(order, internal_status, transaction_id=payment_id)
    return True


# =========================================================================
# PawaPay — Webhooks (deposits / payouts / refunds)
# =========================================================================
@csrf_exempt
@require_POST
def pawapay_callback(request):
    """Receive PawaPay async notifications (deposits, payouts, refunds).

    Verifies the RFC-9421 signature PawaPay sends once "Signed Callbacks" is
    enabled in the Dashboard. This is on top of — not instead of — the
    existing safeguard in _pawapay_process_callback() that re-checks a
    "SUCCESSFUL" status against the live API before ever completing an order,
    so a missing/invalid signature can never itself mark an order paid.
    """
    from manager.payments.pawapay_signatures import verify_callback_signature

    verified, detail = verify_callback_signature(request)
    if verified:
        logger.info('PawaPay callback: signature verified OK')
    else:
        logger.warning('PawaPay callback: signature not verified (%s)', detail)
        if getattr(settings, 'PAWAPAY_REQUIRE_SIGNED_CALLBACKS', False):
            return JsonResponse({'error': 'invalid or missing signature'}, status=403)

    try:
        body = json.loads(request.body)
        logger.info('PawaPay callback received: %s', json.dumps(body))
        payloads = body if isinstance(body, list) else [body]
        for payload in payloads:
            if isinstance(payload, dict):
                _pawapay_process_callback(payload)
        return JsonResponse({'status': 'ok'}, status=200)
    except json.JSONDecodeError:
        logger.error('PawaPay callback: invalid JSON')
        return JsonResponse({'error': 'invalid json'}, status=400)
    except Exception as exc:
        logger.exception('PawaPay callback error: %s', exc)
        return JsonResponse({'error': str(exc)}, status=400)
