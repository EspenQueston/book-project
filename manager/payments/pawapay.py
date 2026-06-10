"""
PawaPay deposit API — Central Africa mobile money.
Docs: https://docs.pawapay.io/
"""
from __future__ import annotations

import logging
import uuid

import requests
from django.conf import settings

logger = logging.getLogger(__name__)


def _cfg():
    return {
        'base_url': getattr(settings, 'PAWAPAY_BASE_URL', 'https://api.sandbox.pawapay.io').rstrip('/'),
        'token': getattr(settings, 'PAWAPAY_API_TOKEN', ''),
        'currency': getattr(settings, 'PAWAPAY_CURRENCY', 'XAF'),
    }


def _headers(token):
    return {
        'Authorization': f'Bearer {token}',
        'Content-Type': 'application/json',
        'Accept': 'application/json',
    }


def create_deposit(*, amount, phone_number, order_number, provider=None, deposit_id=None):
    """
    Initiate a PawaPay deposit (customer pays via mobile money).
    Returns dict with depositId, status, raw response or error.
    """
    cfg = _cfg()
    if not cfg['token']:
        return {'success': False, 'error': 'PAWAPAY_API_TOKEN not configured', 'status': 'FAILED'}

    deposit_id = deposit_id or str(uuid.uuid4())
    payload = {
        'depositId': deposit_id,
        'amount': str(int(amount)),
        'currency': cfg['currency'],
        'payer': {
            'type': 'MSISDN',
            'accountDetails': {
                'phoneNumber': phone_number,
            },
        },
        'metadata': [
            {'fieldName': 'orderNumber', 'fieldValue': order_number},
        ],
    }
    if provider:
        payload['payer']['accountDetails']['provider'] = provider

    url = f"{cfg['base_url']}/deposits"
    try:
        resp = requests.post(url, json=payload, headers=_headers(cfg['token']), timeout=45)
        data = resp.json() if resp.content else {}
        if resp.status_code >= 400:
            logger.warning('PawaPay deposit HTTP %s: %s', resp.status_code, data)
            return {
                'success': False,
                'deposit_id': deposit_id,
                'status': data.get('status', 'FAILED'),
                'error': data.get('failureReason', {}).get('failureMessage', resp.text),
                'raw': data,
            }
        status = data.get('status', 'ACCEPTED')
        return {
            'success': status not in ('FAILED', 'REJECTED'),
            'deposit_id': data.get('depositId', deposit_id),
            'status': status,
            'raw': data,
        }
    except requests.RequestException as exc:
        logger.exception('PawaPay deposit request failed: %s', exc)
        return {'success': False, 'deposit_id': deposit_id, 'status': 'FAILED', 'error': str(exc)}


def get_deposit_status(deposit_id):
    """Poll deposit status from PawaPay."""
    cfg = _cfg()
    if not cfg['token']:
        return {'status': 'UNKNOWN', 'error': 'PAWAPAY_API_TOKEN not configured'}

    url = f"{cfg['base_url']}/deposits/{deposit_id}"
    try:
        resp = requests.get(url, headers=_headers(cfg['token']), timeout=30)
        data = resp.json() if resp.content else {}
        return {
            'status': data.get('status', 'UNKNOWN'),
            'raw': data,
        }
    except requests.RequestException as exc:
        logger.exception('PawaPay status poll failed: %s', exc)
        return {'status': 'UNKNOWN', 'error': str(exc)}


def normalize_pawapay_status(status):
    """Map PawaPay statuses to internal SUCCESSFUL / FAILED / PENDING."""
    if status in ('COMPLETED', 'SUCCESSFUL'):
        return 'SUCCESSFUL'
    if status in ('FAILED', 'REJECTED', 'CANCELLED'):
        return 'FAILED'
    return 'PENDING'
