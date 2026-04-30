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

        except Exception as e:
            logger.warning('Error polling payment status: %s', e)

    return JsonResponse({
        'payment_status': order.payment_status,
        'order_status': order.status,
    })
