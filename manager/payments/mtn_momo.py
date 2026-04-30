"""
MTN MoMo Collection API v2 – Sandbox Integration
============================================================
Docs: https://momodeveloper.mtn.com/api-documentation/collection/
"""

import uuid
import logging
import requests
from django.conf import settings

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Configuration – override via Django settings or environment variables
# ---------------------------------------------------------------------------
def _cfg():
    """Return a dict of MTN MoMo config values."""
    return {
        'base_url': getattr(settings, 'MTN_MOMO_BASE_URL',
                            'https://sandbox.momodeveloper.mtn.com'),
        'subscription_key': getattr(settings, 'MTN_MOMO_SUBSCRIPTION_KEY', ''),
        'api_user': getattr(settings, 'MTN_MOMO_API_USER', ''),
        'api_key': getattr(settings, 'MTN_MOMO_API_KEY', ''),
        'environment': getattr(settings, 'MTN_MOMO_ENVIRONMENT', 'sandbox'),
        'currency': getattr(settings, 'MTN_MOMO_CURRENCY', 'EUR'),
        'callback_url': getattr(settings, 'MTN_MOMO_CALLBACK_URL', ''),
    }


class MTNMoMoService:
    """Thin wrapper around the MTN MoMo Collection API."""

    # ---- helpers -----------------------------------------------------------
    @staticmethod
    def _get_access_token():
        """Get an OAuth2 token using API User / API Key (Basic auth)."""
        cfg = _cfg()
        url = f"{cfg['base_url']}/collection/token/"
        resp = requests.post(
            url,
            headers={
                'Ocp-Apim-Subscription-Key': cfg['subscription_key'],
            },
            auth=(cfg['api_user'], cfg['api_key']),
            timeout=30,
        )
        resp.raise_for_status()
        data = resp.json()
        return data['access_token']

    # ---- sandbox provisioning ---------------------------------------------
    @staticmethod
    def create_sandbox_api_user(callback_host=''):
        """
        Provision a Sandbox API User.
        Returns the X-Reference-Id (= api_user UUID).
        """
        cfg = _cfg()
        ref_id = str(uuid.uuid4())
        url = f"{cfg['base_url']}/v1_0/apiuser"
        body = {'providerCallbackHost': callback_host or cfg['callback_url']}
        resp = requests.post(
            url,
            json=body,
            headers={
                'X-Reference-Id': ref_id,
                'Ocp-Apim-Subscription-Key': cfg['subscription_key'],
                'Content-Type': 'application/json',
            },
            timeout=30,
        )
        resp.raise_for_status()
        logger.info('MTN sandbox API user created: %s', ref_id)
        return ref_id

    @staticmethod
    def create_sandbox_api_key(api_user):
        """Generate an API Key for the given Sandbox API User."""
        cfg = _cfg()
        url = f"{cfg['base_url']}/v1_0/apiuser/{api_user}/apikey"
        resp = requests.post(
            url,
            headers={
                'Ocp-Apim-Subscription-Key': cfg['subscription_key'],
            },
            timeout=30,
        )
        resp.raise_for_status()
        api_key = resp.json()['apiKey']
        logger.info('MTN sandbox API key generated for user %s', api_user)
        return api_key

    # ---- Request to Pay ---------------------------------------------------
    @staticmethod
    def request_to_pay(amount, phone_number, external_id, payer_message='',
                       payee_note=''):
        """
        Initiate an MTN MoMo "Request to Pay".

        Returns:
            dict with 'reference_id' and 'status' ('PENDING' or error info)
        """
        cfg = _cfg()
        token = MTNMoMoService._get_access_token()
        reference_id = str(uuid.uuid4())

        url = f"{cfg['base_url']}/collection/v1_0/requesttopay"
        body = {
            'amount': str(amount),
            'currency': cfg['currency'],
            'externalId': external_id,
            'payer': {
                'partyIdType': 'MSISDN',
                'partyId': phone_number,
            },
            'payerMessage': payer_message or f'DUNO 360 payment #{external_id}',
            'payeeNote': payee_note or f'Order {external_id}',
        }
        headers = {
            'Authorization': f'Bearer {token}',
            'X-Reference-Id': reference_id,
            'X-Target-Environment': cfg['environment'],
            'Ocp-Apim-Subscription-Key': cfg['subscription_key'],
            'Content-Type': 'application/json',
        }
        # Add callback URL if configured
        if cfg['callback_url']:
            headers['X-Callback-Url'] = cfg['callback_url']

        resp = requests.post(url, json=body, headers=headers, timeout=30)

        if resp.status_code == 202:
            logger.info('MTN RequestToPay accepted: ref=%s', reference_id)
            return {'reference_id': reference_id, 'status': 'PENDING'}
        else:
            logger.error('MTN RequestToPay failed: %s %s',
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
        Poll the status of a Request-to-Pay.

        Returns:
            dict from MTN API with 'status' key
            ('SUCCESSFUL', 'FAILED', 'PENDING')
        """
        cfg = _cfg()
        token = MTNMoMoService._get_access_token()
        url = (f"{cfg['base_url']}/collection/v1_0/"
               f"requesttopay/{reference_id}")
        resp = requests.get(
            url,
            headers={
                'Authorization': f'Bearer {token}',
                'X-Target-Environment': cfg['environment'],
                'Ocp-Apim-Subscription-Key': cfg['subscription_key'],
            },
            timeout=30,
        )
        resp.raise_for_status()
        data = resp.json()
        logger.info('MTN payment status for %s: %s',
                     reference_id, data.get('status'))
        return data

    # ---- Account balance --------------------------------------------------
    @staticmethod
    def get_balance():
        """Check the collection account balance (mainly for debugging)."""
        cfg = _cfg()
        token = MTNMoMoService._get_access_token()
        url = f"{cfg['base_url']}/collection/v1_0/account/balance"
        resp = requests.get(
            url,
            headers={
                'Authorization': f'Bearer {token}',
                'X-Target-Environment': cfg['environment'],
                'Ocp-Apim-Subscription-Key': cfg['subscription_key'],
            },
            timeout=30,
        )
        resp.raise_for_status()
        return resp.json()
