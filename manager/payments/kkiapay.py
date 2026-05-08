"""
KKiaPay Payment Aggregator — Python Admin SDK Wrapper
=====================================================
Docs: https://docs.kkiapay.me/v1/plugin-et-sdk/admin-sdks-server-side/python-admin-sdk

Handles server-side transaction verification for all KKiaPay payments
(Mobile Money: MTN, Moov, Orange, Wave, T-Money, Airtel…).
"""

import logging
from django.conf import settings

logger = logging.getLogger(__name__)


def _get_instance():
    """Return a configured Kkiapay SDK instance."""
    try:
        from kkiapay import Kkiapay
    except ImportError:
        raise ImportError(
            "KKiaPay SDK not installed. Run: pip install kkiapay"
        )

    public_key = getattr(settings, 'KKIAPAY_PUBLIC_KEY', '')
    private_key = getattr(settings, 'KKIAPAY_PRIVATE_KEY', '')
    secret = getattr(settings, 'KKIAPAY_SECRET', '')
    sandbox = getattr(settings, 'KKIAPAY_SANDBOX', True)

    if not all([public_key, private_key, secret]):
        raise ValueError(
            "Missing KKiaPay credentials. "
            "Set KKIAPAY_PUBLIC_KEY, KKIAPAY_PRIVATE_KEY, KKIAPAY_SECRET."
        )

    return Kkiapay(public_key, private_key, secret, sandbox=sandbox)


def verify_transaction(transaction_id):
    """
    Verify a KKiaPay transaction by its ID.

    Args:
        transaction_id (str): The transactionId received from the JS widget
                              addSuccessListener callback.

    Returns:
        KkiapayTransaction object with attributes:
            - status:        'SUCCESS' | 'FAILED' | 'PENDING'
            - amount:        int  (amount in XOF/currency)
            - fees:          int
            - transactionId: str
            - source:        'MOBILE_MONEY' | 'CARD' | 'WALLET'
            - country:       'BJ' | 'CI' | 'TG' | 'SN' | 'NE' | …
            - performedAt:   str (date string)
            - reason:        str (failure reason if failed)

    Raises:
        Exception on network or SDK error.
    """
    k = _get_instance()
    logger.info('KKiaPay: verifying transaction %s', transaction_id)
    transaction = k.verify_transaction(transaction_id)
    logger.info(
        'KKiaPay: transaction %s → status=%s amount=%s',
        transaction_id,
        getattr(transaction, 'status', 'UNKNOWN'),
        getattr(transaction, 'amount', '?'),
    )
    return transaction


def is_transaction_successful(transaction_id):
    """
    Convenience helper — returns True if the transaction is successful.

    Args:
        transaction_id (str): KKiaPay transaction ID.

    Returns:
        (bool, transaction_object) — (True, tx) on success, (False, tx or None) on failure.
    """
    try:
        tx = verify_transaction(transaction_id)
        status = getattr(tx, 'status', '').upper()
        success = status == 'SUCCESS'
        if not success:
            logger.warning(
                'KKiaPay: transaction %s NOT successful — status=%s reason=%s',
                transaction_id, status, getattr(tx, 'reason', '')
            )
        return success, tx
    except Exception as exc:
        logger.exception('KKiaPay: verification error for %s: %s', transaction_id, exc)
        return False, None
