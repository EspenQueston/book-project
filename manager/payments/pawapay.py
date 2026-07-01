"""
PawaPay deposit API — Central Africa mobile money.
Docs: https://docs.pawapay.io/

Fixed for PawaPay API v2:
  - correspondent is required at top-level (not inside payer.accountDetails)
  - payer uses {type, address: {value}} not {type, accountDetails: {phoneNumber}}
  - customerTimestamp (ISO8601) is required
  - statementDescription must be alphanumeric + spaces only
"""
from __future__ import annotations

import logging
import re
import uuid
from datetime import datetime, timezone

import requests
from django.conf import settings

logger = logging.getLogger(__name__)

COUNTRY_DIAL_CODES = {
    'Angola': '244',
    'Cameroon': '237',
    'Central African Republic': '236',
    'Chad': '235',
    'Congo': '242',
    'Democratic Republic of the Congo': '243',
    'Equatorial Guinea': '240',
    'Gabon': '241',
    'São Tomé and Príncipe': '239',
    'Benin': '229',
    'Burkina Faso': '226',
    "Côte d'Ivoire": '225',
    'Guinea': '224',
    'Mali': '223',
    'Niger': '227',
    'Senegal': '221',
    'Togo': '228',
    'China': '86',
    'Hong Kong': '852',
    'Taiwan': '886',
    'Japan': '81',
}

# Country → available PawaPay correspondent codes
# operator label → PawaPay correspondent code, 'default' = first choice
COUNTRY_CORRESPONDENTS = {
    'Congo': {
        'MTN Mobile Money': 'MTN_MOMO_COG',
        'Airtel Money': 'AIRTEL_COG',
        'default': 'MTN_MOMO_COG',
    },
    'Democratic Republic of the Congo': {
        'Vodacom M-Pesa': 'VODACOM_MPESA_COD',
        'Airtel Money': 'AIRTEL_COD',
        'Vodacom': 'VODACOM_COD',
        'Orange Money': 'ORANGE_COD',
        'default': 'VODACOM_MPESA_COD',
    },
    'Cameroon': {
        'MTN Mobile Money': 'MTN_MOMO_CMR',
        'Orange Money': 'ORANGE_CMR',
        'default': 'MTN_MOMO_CMR',
    },
    'Gabon': {
        'Airtel Money': 'AIRTEL_GAB',
        'default': 'AIRTEL_GAB',
    },
    'Angola': {
        'Unitel': 'UNITEL_AGO',
        'default': 'UNITEL_AGO',
    },
    'Chad': {
        # Chad uses XAF but no dedicated correspondent in this sandbox account
        'default': '',
    },
    'Central African Republic': {
        'default': '',
    },
    'Equatorial Guinea': {
        'default': '',
    },
    'São Tomé and Príncipe': {
        'default': '',
    },
}


def get_country_correspondents(country):
    """Return list of (operator_label, correspondent_code) for a country."""
    country_map = COUNTRY_CORRESPONDENTS.get(country, {})
    return [(label, code) for label, code in country_map.items() if label != 'default' and code]


def get_default_correspondent(country, operator_label=None):
    """Get the PawaPay correspondent code for a country + optional operator selection."""
    country_map = COUNTRY_CORRESPONDENTS.get(country or '', {})
    if operator_label and operator_label in country_map:
        return country_map[operator_label]
    return country_map.get('default', '')


def normalize_msisdn(phone_number, country=None):
    """Return digits-only MSISDN with country code when possible."""
    digits = re.sub(r'\D', '', phone_number or '')
    if not digits:
        return ''
    if digits.startswith('00'):
        digits = digits[2:]

    dial = COUNTRY_DIAL_CODES.get(country or '')
    if dial:
        if digits.startswith(dial) and len(digits) >= len(dial) + 6:
            return digits
        local = digits.lstrip('0')
        return f'{dial}{local}'

    if digits.startswith('0'):
        digits = digits.lstrip('0')
    return digits


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


def _parse_deposit_payload(data, deposit_id=None):
    """Normalize PawaPay deposit API JSON (object or list) to a single dict."""
    if isinstance(data, dict):
        for key in ('deposit', 'data', 'result'):
            nested = data.get(key)
            if isinstance(nested, dict):
                return nested
        return data
    if isinstance(data, list):
        for item in data:
            if not isinstance(item, dict):
                continue
            if deposit_id and item.get('depositId') == deposit_id:
                return item
        for item in data:
            if isinstance(item, dict):
                return item
    return {}


def _clean_statement(order_number):
    """Return a PawaPay-safe statementDescription (alphanumeric + spaces, max 22 chars)."""
    cleaned = re.sub(r'[^A-Za-z0-9 ]', '', f'DUNO360 {order_number}')
    return cleaned[:22].strip()


def create_deposit(*, amount, phone_number, order_number, provider=None, deposit_id=None, country=None):
    """
    Initiate a PawaPay deposit (customer pays via mobile money).

    PawaPay API v2 format:
      - correspondent: required at top level (MNO code e.g. MTN_MOMO_COG)
      - payer.address.value: E.164 phone number digits
      - customerTimestamp: ISO 8601 UTC timestamp
      - statementDescription: alphanumeric + spaces, max 22 chars

    `provider` may be either:
      - a full correspondent code (e.g. 'MTN_MOMO_COG')
      - an operator label (e.g. 'MTN Mobile Money') — mapped via COUNTRY_CORRESPONDENTS
      - None → auto-resolved from country
    """
    cfg = _cfg()
    if not cfg['token']:
        return {'success': False, 'error': 'PAWAPAY_API_TOKEN not configured', 'status': 'FAILED'}

    msisdn = normalize_msisdn(phone_number, country)
    if not msisdn or len(msisdn) < 9:
        return {
            'success': False,
            'error': 'Invalid phone number — include country code or select your country at checkout.',
            'status': 'FAILED',
        }

    # Resolve correspondent
    correspondent = provider or ''
    if not correspondent:
        correspondent = get_default_correspondent(country)
    elif correspondent not in _get_all_correspondent_codes():
        # Treat as an operator label and resolve
        correspondent = get_default_correspondent(country, operator_label=correspondent)

    if not correspondent:
        return {
            'success': False,
            'error': f'No PawaPay correspondent configured for country: {country or "unknown"}. '
                     'Please select your mobile operator.',
            'status': 'FAILED',
        }

    deposit_id = deposit_id or str(uuid.uuid4())
    ts = datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')

    payload = {
        'depositId': deposit_id,
        'amount': str(int(amount)),
        'currency': cfg['currency'],
        'correspondent': correspondent,
        'payer': {
            'type': 'MSISDN',
            'address': {
                'value': msisdn,
            },
        },
        'customerTimestamp': ts,
        'statementDescription': _clean_statement(order_number),
        'metadata': [
            {'fieldName': 'orderNumber', 'fieldValue': str(order_number)},
        ],
    }

    url = f"{cfg['base_url']}/deposits"
    try:
        resp = requests.post(url, json=payload, headers=_headers(cfg['token']), timeout=45)
        raw = resp.json() if resp.content else {}
        data = _parse_deposit_payload(raw, deposit_id)
        if resp.status_code >= 400:
            logger.warning('PawaPay deposit HTTP %s: %s', resp.status_code, raw)
            failure = data.get('failureReason') or data.get('rejectionReason') or {}
            if isinstance(failure, dict):
                err_msg = failure.get('failureMessage') or failure.get('rejectionMessage') or str(raw)
            else:
                err_msg = str(raw)
            return {
                'success': False,
                'deposit_id': deposit_id,
                'status': data.get('status', 'FAILED'),
                'error': err_msg,
                'raw': raw,
            }
        status = data.get('status', 'ACCEPTED')
        return {
            'success': status not in ('FAILED', 'REJECTED'),
            'deposit_id': data.get('depositId', deposit_id),
            'status': status,
            'raw': raw,
        }
    except requests.RequestException as exc:
        logger.exception('PawaPay deposit request failed: %s', exc)
        return {'success': False, 'deposit_id': deposit_id, 'status': 'FAILED', 'error': str(exc)}


def _get_all_correspondent_codes():
    """Return a flat set of all known PawaPay correspondent codes."""
    codes = set()
    for country_map in COUNTRY_CORRESPONDENTS.values():
        for label, code in country_map.items():
            if label != 'default' and code:
                codes.add(code)
    return codes


def get_deposit_status(deposit_id):
    """Poll deposit status from PawaPay."""
    cfg = _cfg()
    if not cfg['token']:
        return {'status': 'UNKNOWN', 'error': 'PAWAPAY_API_TOKEN not configured'}

    url = f"{cfg['base_url']}/deposits/{deposit_id}"
    try:
        resp = requests.get(url, headers=_headers(cfg['token']), timeout=30)
        raw = resp.json() if resp.content else {}
        data = _parse_deposit_payload(raw, deposit_id)
        if resp.status_code >= 400:
            logger.warning('PawaPay status HTTP %s for %s: %s', resp.status_code, deposit_id, raw)
            return {
                'status': data.get('status', 'UNKNOWN'),
                'error': resp.text or f'HTTP {resp.status_code}',
                'raw': raw,
            }
        return {
            'status': data.get('status', 'UNKNOWN'),
            'raw': raw,
        }
    except (requests.RequestException, ValueError) as exc:
        logger.exception('PawaPay status poll failed: %s', exc)
        return {'status': 'UNKNOWN', 'error': str(exc)}


def normalize_pawapay_status(status):
    """Map PawaPay statuses to internal SUCCESSFUL / FAILED / PENDING."""
    if status in ('COMPLETED', 'SUCCESSFUL'):
        return 'SUCCESSFUL'
    if status in ('FAILED', 'REJECTED', 'CANCELLED'):
        return 'FAILED'
    return 'PENDING'
