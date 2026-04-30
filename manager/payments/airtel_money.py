"""
Airtel Money Collection API – Sandbox Integration
============================================================
Docs: https://developers.airtel.africa/documentation
"""

import uuid
import logging
import requests
from django.conf import settings

logger = logging.getLogger(__name__)


def _cfg():
    """Return a dict of Airtel Money config values."""
    return {
        'base_url': getattr(settings, 'AIRTEL_MONEY_BASE_URL',
                            'https://openapiuat.airtel.africa'),
        'client_id': getattr(settings, 'AIRTEL_MONEY_CLIENT_ID', ''),
        'client_secret': getattr(settings, 'AIRTEL_MONEY_CLIENT_SECRET', ''),
        'country': getattr(settings, 'AIRTEL_MONEY_COUNTRY', 'CG'),
        'currency': getattr(settings, 'AIRTEL_MONEY_CURRENCY', 'XAF'),
        'callback_url': getattr(settings, 'AIRTEL_MONEY_CALLBACK_URL', ''),
    }


class AirtelMoneyService:
    """Thin wrapper around the Airtel Money Collection API."""

    # ---- helpers -----------------------------------------------------------
    @staticmethod
    def _get_access_token():
        """Get an OAuth2 token using client credentials."""
        cfg = _cfg()
        url = f"{cfg['base_url']}/auth/oauth2/token"
        body = {
            'client_id': cfg['client_id'],
            'client_secret': cfg['client_secret'],
            'grant_type': 'client_credentials',
        }
        resp = requests.post(
            url,
            json=body,
            headers={'Content-Type': 'application/json'},
            timeout=30,
        )
        resp.raise_for_status()
        data = resp.json()
        return data['access_token']

    # ---- Request to Pay ---------------------------------------------------
    @staticmethod
    def request_to_pay(amount, phone_number, external_id, payer_message=''):
        """
        Initiate an Airtel Money collection (USSD push).

        Returns:
            dict with 'reference_id' and 'status'
        """
        cfg = _cfg()
        token = AirtelMoneyService._get_access_token()
        reference_id = str(uuid.uuid4())

        url = f"{cfg['base_url']}/merchant/v2/payments/"
        body = {
            'reference': external_id,
            'subscriber': {
                'country': cfg['country'],
                'currency': cfg['currency'],
                'msisdn': phone_number,
            },
            'transaction': {
                'amount': str(amount),
                'country': cfg['country'],
                'currency': cfg['currency'],
                'id': reference_id,
            },
        }
        headers = {
            'Authorization': f'Bearer {token}',
            'Content-Type': 'application/json',
            'X-Country': cfg['country'],
            'X-Currency': cfg['currency'],
        }
        if cfg['callback_url']:
            headers['X-Callback-Url'] = cfg['callback_url']

        resp = requests.post(url, json=body, headers=headers, timeout=30)

        if resp.status_code in (200, 202):
            data = resp.json()
            status_data = data.get('status', {})
            logger.info('Airtel payment accepted: ref=%s, response_code=%s',
                        reference_id, status_data.get('response_code'))
            return {
                'reference_id': reference_id,
                'status': 'PENDING',
                'response': data,
            }
        else:
            logger.error('Airtel payment failed: %s %s',
                         resp.status_code, resp.text)
            return {
                'reference_id': reference_id,
                'status': 'FAILED',
                'error': resp.text,
                'http_status': resp.status_code,
            }

    # ---- Check status -----------------------------------------------------
    @staticmethod
    def get_payment_status(reference_id):
        """
        Check the status of an Airtel Money transaction.

        Returns:
            dict with 'status' key ('TIP' = in progress, 'TS' = success, 
            'TF' = failed)
        """
        cfg = _cfg()
        token = AirtelMoneyService._get_access_token()
        url = (f"{cfg['base_url']}/standard/v1/payments/"
               f"{reference_id}")
        resp = requests.get(
            url,
            headers={
                'Authorization': f'Bearer {token}',
                'Content-Type': 'application/json',
                'X-Country': cfg['country'],
                'X-Currency': cfg['currency'],
            },
            timeout=30,
        )
        resp.raise_for_status()
        data = resp.json()
        logger.info('Airtel payment status for %s: %s',
                     reference_id, data.get('data', {}).get('transaction', {}).get('status'))
        return data

    # ---- Map Airtel status to our status ----------------------------------
    @staticmethod
    def normalize_status(airtel_data):
        """
        Convert Airtel response to a simple status string.

        Returns: 'SUCCESSFUL', 'FAILED', or 'PENDING'
        """
        try:
            tx_status = (airtel_data.get('data', {})
                         .get('transaction', {})
                         .get('status', ''))
            mapping = {
                'TS': 'SUCCESSFUL',
                'TF': 'FAILED',
                'TIP': 'PENDING',
                'TA': 'PENDING',
            }
            return mapping.get(tx_status, 'PENDING')
        except Exception:
            return 'PENDING'
