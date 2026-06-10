"""Twilio Verify — SMS OTP for signup phone authentication."""
import logging
import re

from django.conf import settings
from django.utils.translation import gettext as _

logger = logging.getLogger(__name__)


def is_twilio_verify_enabled():
    return bool(getattr(settings, 'TWILIO_VERIFY_ENABLED', False))


def normalize_phone_e164(phone: str) -> str:
    """Normalize to E.164 (+...). Input should include country code."""
    raw = (phone or '').strip()
    if not raw:
        return ''
    compact = re.sub(r'[\s\-\(\)\.]', '', raw)
    if compact.startswith('+'):
        digits = re.sub(r'\D', '', compact[1:])
        return f'+{digits}' if digits else ''
    digits = re.sub(r'\D', '', compact)
    if not digits:
        return ''
    return f'+{digits}'


def validate_phone_e164(phone_e164: str) -> tuple[bool, str]:
    if not phone_e164 or not phone_e164.startswith('+'):
        return False, _('Invalid number. Use international format, e.g. +242061234567 or +12676567750.')
    digits = phone_e164[1:]
    if not digits.isdigit() or len(digits) < 8 or len(digits) > 15:
        return False, _('Invalid number. Check the country code and number.')
    return True, ''


def mask_phone(phone_e164: str) -> str:
    if not phone_e164 or len(phone_e164) < 8:
        return phone_e164 or ''
    return f'{phone_e164[:4]} *** **{phone_e164[-3:]}'


def _get_client():
    from twilio.rest import Client
    return Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)


def send_verification_sms(phone_e164: str) -> tuple[bool, str]:
    """Send OTP via Twilio Verify. Returns (ok, message)."""
    if not is_twilio_verify_enabled():
        logger.warning('Twilio Verify not configured — SMS skipped')
        return False, _('SMS verification is not configured on the server.')

    ok, err = validate_phone_e164(phone_e164)
    if not ok:
        return False, err

    try:
        client = _get_client()
        client.verify.v2.services(settings.TWILIO_VERIFY_SERVICE_SID).verifications.create(
            to=phone_e164,
            channel='sms',
        )
        return True, _('SMS code sent.')
    except Exception as exc:
        logger.exception('Twilio Verify send failed for %s: %s', phone_e164, exc)
        return False, _('Unable to send SMS. Check your number or try again later.')


def check_verification_sms(phone_e164: str, code: str) -> tuple[bool, str]:
    """Validate OTP with Twilio Verify. Returns (ok, message)."""
    if not is_twilio_verify_enabled():
        return True, ''

    code = (code or '').strip()
    if not code:
        return False, _('Enter the code received by SMS.')

    ok, err = validate_phone_e164(phone_e164)
    if not ok:
        return False, err

    try:
        client = _get_client()
        result = client.verify.v2.services(settings.TWILIO_VERIFY_SERVICE_SID).verification_checks.create(
            to=phone_e164,
            code=code,
        )
        if result.status == 'approved':
            return True, ''
        return False, _('Incorrect or expired SMS code.')
    except Exception as exc:
        logger.exception('Twilio Verify check failed for %s: %s', phone_e164, exc)
        return False, _('SMS verification failed. Try again or request a new code.')
