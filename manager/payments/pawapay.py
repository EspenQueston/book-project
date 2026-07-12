"""
PawaPay deposit API — Central Africa mobile money.
Docs: https://docs.pawapay.io/

Uses the PawaPay v1 API (POST {base}/deposits):
  - correspondent is required at top-level (not inside payer.accountDetails)
  - payer uses {type: MSISDN, address: {value}} — NOT the v2
    payer.accountDetails format
  - customerTimestamp (ISO8601) is required
  - statementDescription must be alphanumeric + spaces only, 4-22 chars
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
#
# IMPORTANT: this list is scoped to what is actually ACTIVE on the DUNO_360
# PawaPay merchant account (re-verified against GET /v2/active-conf on the
# LIVE production account on 2026-07-11 — re-run that check whenever PawaPay
# enables a new corridor, since correspondents that exist in PawaPay's docs
# are not automatically active on every merchant account).
COUNTRY_CORRESPONDENTS = {
    'Congo': {
        'MTN Mobile Money': 'MTN_MOMO_COG',
        'Airtel Money': 'AIRTEL_COG',
        'default': 'MTN_MOMO_COG',
    },
    'Democratic Republic of the Congo': {
        # 'Vodacom' (bare, code VODACOM_COD) is a distinct correspondent from
        # 'Vodacom M-Pesa' (VODACOM_COD) in PawaPay's catalogue, but only the
        # M-Pesa one is active on this account — offering the bare option
        # would always fail with DEPOSITS_NOT_ALLOWED, so it is omitted.
        'Vodacom M-Pesa': 'VODACOM_MPESA_COD',
        'Airtel Money': 'AIRTEL_COD',
        'Orange Money': 'ORANGE_COD',
        'default': 'VODACOM_MPESA_COD',
    },
    'Cameroon': {
        # 'Orange Money' (ORANGE_CMR) is documented by PawaPay but NOT active
        # on the LIVE merchant account (confirmed via GET /v2/active-conf on
        # production — only MTN_MOMO_CMR is listed for CMR). Offering it would
        # fail every real deposit with DEPOSITS_NOT_ALLOWED. Re-add once
        # PawaPay confirms it active for this account.
        'MTN Mobile Money': 'MTN_MOMO_CMR',
        'default': 'MTN_MOMO_CMR',
    },
    'Gabon': {
        'Airtel Money': 'AIRTEL_GAB',
        'default': 'AIRTEL_GAB',
    },
    'Angola': {
        # UNITEL_AGO is documented by PawaPay but NOT active on this merchant
        # account yet (confirmed via /active-conf — Angola is absent from the
        # active country list, and a test deposit is rejected with
        # DEPOSITS_NOT_ALLOWED). Leave disabled until PawaPay enables it;
        # re-add 'Unitel': 'UNITEL_AGO' once confirmed active.
        'default': '',
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

# Country → settlement currency actually accepted by PawaPay for that
# corridor (confirmed via /active-conf). This is NOT the platform's display
# currency (orders are quoted in FCFA/XAF) — it's what must be sent to
# PawaPay's API for the deposit to be accepted at all. Sending the wrong
# currency code gets the deposit REJECTED with INVALID_CURRENCY even though
# the HTTP call itself succeeds (200 OK).
#
# NOTE: PawaPay does not convert currency — amounts are charged at face
# value in whatever currency is submitted. Central African corridors (Congo,
# Cameroon, Gabon) share XAF with the platform's own pricing, so no
# conversion is needed there. DRC settles in CDF or USD, NOT XAF — until the
# platform has a real XAF→CDF exchange rate and applies it to the amount,
# treat DRC checkout as a distinct price list / manual-conversion concern,
# not just a currency-code swap.
COUNTRY_CURRENCY = {
    'Congo': 'XAF',
    'Cameroon': 'XAF',
    'Gabon': 'XAF',
    'Chad': 'XAF',
    'Central African Republic': 'XAF',
    'Equatorial Guinea': 'XAF',
    'Democratic Republic of the Congo': 'CDF',
    'Angola': 'AOA',
    'São Tomé and Príncipe': 'STN',
}


# ISO 3166-1 alpha-3 codes for the Payment Page's optional `country` field
# (v2 /v2/paymentpage). Only needed for corridors we actually offer.
COUNTRY_ALPHA3 = {
    'Congo': 'COG',
    'Democratic Republic of the Congo': 'COD',
    'Cameroon': 'CMR',
    'Gabon': 'GAB',
    'Angola': 'AGO',
    'Chad': 'TCD',
    'Central African Republic': 'CAF',
    'Equatorial Guinea': 'GNQ',
    'São Tomé and Príncipe': 'STP',
}


def get_country_currency(country):
    """Return the PawaPay settlement currency for a country, falling back to the configured default."""
    return COUNTRY_CURRENCY.get(country or '') or getattr(settings, 'PAWAPAY_CURRENCY', 'XAF')


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
        if country == 'Congo':
            # Republic of the Congo keeps the trunk 0 in international format:
            # 06 612 34 56 -> 242066123456 (PawaPay sandbox numbers confirm:
            # 242053456039). Stripping the 0 yields an 11-digit MSISDN that
            # PawaPay rejects as INVALID_PHONE_NUMBER.
            local = digits if digits.startswith('0') else '0' + digits
            return f'{dial}{local}'
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
    currency = get_country_currency(country)

    payload = {
        'depositId': deposit_id,
        'amount': str(int(amount)),
        'currency': currency,
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
        result = {
            'success': status not in ('FAILED', 'REJECTED'),
            'deposit_id': data.get('depositId', deposit_id),
            'status': status,
            'raw': raw,
        }
        if status in ('FAILED', 'REJECTED'):
            # PawaPay reports rejections with HTTP 200 (the call itself
            # succeeded; the payment did not) — extract the reason the same
            # way the HTTP-error branch above does, so the customer/admin
            # sees why (e.g. INVALID_CURRENCY, DEPOSITS_NOT_ALLOWED) instead
            # of a bare "payment failed".
            logger.warning('PawaPay deposit %s: %s', status, raw)
            failure = data.get('failureReason') or data.get('rejectionReason') or {}
            if isinstance(failure, dict):
                result['error'] = failure.get('failureMessage') or failure.get('rejectionMessage') or f'Payment {status.lower()}'
            else:
                result['error'] = f'Payment {status.lower()}'
        return result
    except requests.RequestException as exc:
        logger.exception('PawaPay deposit request failed: %s', exc)
        return {'success': False, 'deposit_id': deposit_id, 'status': 'FAILED', 'error': str(exc)}


def create_payment_page_session(*, amount, order_number, return_url, phone_number=None,
                                 country=None, reason=None, language='FR', deposit_id=None):
    """
    Create a PawaPay Payment Page (hosted checkout widget) session — PawaPay's
    own polished payment UI (operator selection, phone entry, PIN-prompt
    waiting screen), rendered entirely on pawapay.io's domain.

    Uses the v2 API (POST {base}/v2/paymentpage), which is a distinct surface
    from the v1 `/deposits` endpoint used by create_deposit(): only `depositId`
    and `returnUrl` are required; everything else (amount, phone, country) is
    an optional hint that pre-fills / narrows the widget, and the customer can
    still adjust it there. The widget redirects the browser back to
    `return_url` with `?depositId=...` once the customer finishes.

    Returns {'success': True, 'deposit_id', 'redirect_url'} or
    {'success': False, 'error', 'deposit_id'}.
    """
    cfg = _cfg()
    if not cfg['token']:
        return {'success': False, 'error': 'PAWAPAY_API_TOKEN not configured'}

    deposit_id = deposit_id or str(uuid.uuid4())
    currency = get_country_currency(country)

    # PawaPay's returnUrl validator rejects the literal hostname "localhost"
    # but accepts 127.0.0.1 (verified empirically against the sandbox API).
    # Rewrite so the hosted page also works during local development;
    # production URLs are untouched.
    if return_url:
        return_url = return_url.replace('://localhost', '://127.0.0.1')

    payload = {
        'depositId': deposit_id,
        'returnUrl': return_url,
        'amountDetails': {'amount': str(int(amount)), 'currency': currency},
        'reason': (reason or _clean_statement(order_number))[:50],
        'language': 'EN' if str(language or '').upper().startswith('EN') else 'FR',
        'metadata': [
            {'fieldName': 'orderNumber', 'fieldValue': str(order_number)},
        ],
    }
    if phone_number:
        msisdn = normalize_msisdn(phone_number, country)
        if msisdn:
            payload['phoneNumber'] = msisdn
    alpha3 = COUNTRY_ALPHA3.get(country or '')
    if alpha3:
        payload['country'] = alpha3

    url = f"{cfg['base_url']}/v2/paymentpage"
    try:
        resp = requests.post(url, json=payload, headers=_headers(cfg['token']), timeout=30)
        raw = resp.json() if resp.content else {}
        if resp.status_code >= 400:
            logger.warning('PawaPay paymentpage HTTP %s: %s', resp.status_code, raw)
            failure = raw.get('failureReason') or {}
            err_msg = failure.get('failureMessage') if isinstance(failure, dict) else None
            return {'success': False, 'deposit_id': deposit_id, 'error': err_msg or str(raw), 'raw': raw}
        redirect_url = raw.get('redirectUrl')
        if not redirect_url:
            # PawaPay sometimes reports failures (e.g. INVALID_PHONE_NUMBER)
            # in a 2xx body with a failureReason instead of an HTTP error.
            logger.warning('PawaPay paymentpage returned no redirectUrl: %s', raw)
            failure = raw.get('failureReason') or {}
            err_msg = failure.get('failureMessage') if isinstance(failure, dict) else None
            return {'success': False, 'deposit_id': deposit_id,
                    'error': err_msg or 'No redirectUrl in PawaPay response', 'raw': raw}
        return {'success': True, 'deposit_id': raw.get('depositId', deposit_id), 'redirect_url': redirect_url, 'raw': raw}
    except requests.RequestException as exc:
        logger.exception('PawaPay paymentpage request failed: %s', exc)
        return {'success': False, 'deposit_id': deposit_id, 'error': str(exc)}


def get_deposit_status_v2(deposit_id):
    """Check deposit status via the v2 endpoint (GET {base}/v2/deposits/{id}).

    Needed specifically for deposits created through create_payment_page_session():
    the v1 status endpoint used by get_deposit_status() does not reliably see
    deposits created via the v2 Payment Page (confirmed empty result in
    testing), because v2 wraps the payload differently
    ({"status": "FOUND"/"NOT_FOUND", "data": {...}}) and uses its own status
    vocabulary (ACCEPTED/PROCESSING/IN_RECONCILIATION/COMPLETED/FAILED).
    Returns the same shape as get_deposit_status() so callers (and
    normalize_pawapay_status) don't need to care which version created it.
    """
    cfg = _cfg()
    if not cfg['token']:
        return {'status': 'UNKNOWN', 'error': 'PAWAPAY_API_TOKEN not configured'}

    url = f"{cfg['base_url']}/v2/deposits/{deposit_id}"
    try:
        resp = requests.get(url, headers=_headers(cfg['token']), timeout=30)
        raw = resp.json() if resp.content else {}
        if resp.status_code >= 400:
            logger.warning('PawaPay v2 status HTTP %s for %s: %s', resp.status_code, deposit_id, raw)
            return {'status': 'UNKNOWN', 'error': resp.text or f'HTTP {resp.status_code}', 'raw': raw}

        if raw.get('status') == 'NOT_FOUND' or not raw.get('data'):
            return {'status': 'NOT_FOUND', 'raw': raw}

        data = raw.get('data') or {}
        status = data.get('status', 'UNKNOWN')
        result = {'status': status, 'raw': raw}
        if status == 'FAILED':
            failure = data.get('failureReason') or {}
            if isinstance(failure, dict):
                result['error'] = failure.get('failureMessage') or f'Payment {status.lower()}'
            else:
                result['error'] = f'Payment {status.lower()}'
        return result
    except (requests.RequestException, ValueError) as exc:
        logger.exception('PawaPay v2 status poll failed: %s', exc)
        return {'status': 'UNKNOWN', 'error': str(exc)}


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
        status = data.get('status', 'UNKNOWN')
        result = {'status': status, 'raw': raw}
        if status in ('FAILED', 'REJECTED'):
            failure = data.get('failureReason') or data.get('rejectionReason') or {}
            if isinstance(failure, dict):
                result['error'] = failure.get('failureMessage') or failure.get('rejectionMessage') or f'Payment {status.lower()}'
            else:
                result['error'] = f'Payment {status.lower()}'
        return result
    except (requests.RequestException, ValueError) as exc:
        logger.exception('PawaPay status poll failed: %s', exc)
        return {'status': 'UNKNOWN', 'error': str(exc)}


def create_refund(*, deposit_id, amount, currency, refund_id=None):
    """
    Initiate a real refund against a completed deposit (POST {base}/v2/refunds).

    Unlike the old behaviour (an admin flipping payment_status='refunded' in
    Django admin with no money actually moving), this calls PawaPay's own
    refund endpoint — the customer's mobile money account is actually
    credited back. The call is idempotent: resubmitting the same refund_id
    returns DUPLICATE_IGNORED instead of double-refunding.

    Returns {'success': True, 'refund_id', 'status'} or
    {'success': False, 'refund_id', 'error'}. A 'success' True here means
    PawaPay *accepted* the refund request (status ACCEPTED) — the refund
    still needs to be verified via get_refund_status()/its callback before
    treating it as actually completed, same pattern as deposits.
    """
    cfg = _cfg()
    if not cfg['token']:
        return {'success': False, 'error': 'PAWAPAY_API_TOKEN not configured'}

    refund_id = refund_id or str(uuid.uuid4())
    payload = {
        'refundId': refund_id,
        'depositId': deposit_id,
        'amount': str(int(amount)) if float(amount) == int(amount) else str(amount),
        'currency': currency,
    }

    url = f"{cfg['base_url']}/v2/refunds"
    try:
        resp = requests.post(url, json=payload, headers=_headers(cfg['token']), timeout=30)
        raw = resp.json() if resp.content else {}
        if resp.status_code >= 400:
            logger.warning('PawaPay refund HTTP %s: %s', resp.status_code, raw)
            failure = raw.get('failureReason') or {}
            err_msg = failure.get('failureMessage') if isinstance(failure, dict) else None
            return {'success': False, 'refund_id': refund_id, 'error': err_msg or str(raw), 'raw': raw}

        status = raw.get('status', 'UNKNOWN')
        if status == 'REJECTED':
            failure = raw.get('failureReason') or {}
            err_msg = failure.get('failureMessage') if isinstance(failure, dict) else None
            return {'success': False, 'refund_id': refund_id, 'status': status, 'error': err_msg or 'Refund rejected', 'raw': raw}

        return {'success': True, 'refund_id': raw.get('refundId', refund_id), 'status': status, 'raw': raw}
    except requests.RequestException as exc:
        logger.exception('PawaPay refund request failed: %s', exc)
        return {'success': False, 'refund_id': refund_id, 'error': str(exc)}


def get_refund_status(refund_id):
    """Check refund status via GET {base}/v2/refunds/{refundId}.

    Refund statuses: ACCEPTED, ENQUEUED, PROCESSING, IN_RECONCILIATION,
    COMPLETED, FAILED — COMPLETED/FAILED are final."""
    cfg = _cfg()
    if not cfg['token']:
        return {'status': 'UNKNOWN', 'error': 'PAWAPAY_API_TOKEN not configured'}

    url = f"{cfg['base_url']}/v2/refunds/{refund_id}"
    try:
        resp = requests.get(url, headers=_headers(cfg['token']), timeout=30)
        raw = resp.json() if resp.content else {}
        if resp.status_code >= 400:
            logger.warning('PawaPay refund status HTTP %s for %s: %s', resp.status_code, refund_id, raw)
            return {'status': 'UNKNOWN', 'error': resp.text or f'HTTP {resp.status_code}', 'raw': raw}

        if raw.get('status') == 'NOT_FOUND' or not raw.get('data'):
            return {'status': 'NOT_FOUND', 'raw': raw}

        data = raw.get('data') or {}
        status = data.get('status', 'UNKNOWN')
        result = {'status': status, 'raw': raw}
        if status == 'FAILED':
            failure = data.get('failureReason') or {}
            if isinstance(failure, dict):
                result['error'] = failure.get('failureMessage') or 'Refund failed'
            else:
                result['error'] = 'Refund failed'
        return result
    except (requests.RequestException, ValueError) as exc:
        logger.exception('PawaPay refund status poll failed: %s', exc)
        return {'status': 'UNKNOWN', 'error': str(exc)}


def normalize_pawapay_status(status):
    """Map PawaPay statuses to internal SUCCESSFUL / FAILED / PENDING."""
    if status in ('COMPLETED', 'SUCCESSFUL'):
        return 'SUCCESSFUL'
    if status in ('FAILED', 'REJECTED', 'CANCELLED'):
        return 'FAILED'
    return 'PENDING'
