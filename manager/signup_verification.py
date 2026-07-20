"""Async signup verification dispatch (SMS + email) with cache status."""
import logging
import threading

from django.core.cache import cache
from django.db import close_old_connections
from django.utils import translation

logger = logging.getLogger(__name__)

CACHE_TTL = 900


def _cache_key(email: str, verification_type: str) -> str:
    return f'signup_verify:{verification_type}:{email.strip().lower()}'


def set_signup_verification_pending(email: str, verification_type: str = 'user') -> None:
    cache.set(
        _cache_key(email, verification_type),
        {'pending': True},
        CACHE_TTL,
    )


def get_signup_verification_status(email: str, verification_type: str = 'user') -> dict | None:
    return cache.get(_cache_key(email, verification_type))


def _complete_signup_verification(verification_id: int, lang_code: str) -> None:
    close_old_connections()
    try:
        from django.utils.translation import gettext as _

        with translation.override(lang_code or 'en'):
            from manager.models import EmailVerification
            from manager.twilio_verify import is_twilio_verify_enabled
            from manager.views import _send_registration_phone_otp, _send_verification_email

            verification = EmailVerification.objects.get(pk=verification_id)
            email = verification.email
            vtype = verification.verification_type

            sms_failed = False
            sms_error = ''
            require_sms = False

            if is_twilio_verify_enabled():
                sms_ok, sms_err = _send_registration_phone_otp(verification.phone)
                if sms_ok:
                    require_sms = True
                else:
                    sms_failed = True
                    sms_error = sms_err or _(
                        'Unable to send SMS. Check your number or try again later.'
                    )

            verification.require_sms_verification = require_sms
            verification.save(update_fields=['require_sms_verification'])

            sent = _send_verification_email(
                verification.email, verification.pin_code, verification.name,
            )
            if not sent:
                # Deliberately NOT deleting the pending verification record
                # here — the initial send already retries transient
                # failures (see _send_verification_email), so a failure
                # reaching this point is more likely a real outage than a
                # one-off blip. Deleting it used to force the user to
                # re-enter their whole registration from scratch just to
                # get a second attempt; keeping it lets the existing
                # "resend code" button (resend_verification_pin) actually
                # work, since that view looks the record up by email.
                cache.set(
                    _cache_key(email, vtype),
                    {
                        'pending': False,
                        'email_sent': False,
                        'require_sms': require_sms,
                        'sms_failed': sms_failed,
                        'sms_error': sms_error,
                        'error': True,
                    },
                    CACHE_TTL,
                )
                return

            cache.set(
                _cache_key(email, vtype),
                {
                    'pending': False,
                    'email_sent': True,
                    'require_sms': require_sms,
                    'sms_failed': sms_failed,
                    'sms_error': sms_error,
                    'fallback_message': _(
                        'Email verification has been started automatically. '
                        'Enter the 6-digit code from your inbox.'
                    ) if sms_failed else '',
                },
                CACHE_TTL,
            )
    except Exception as exc:
        from manager.models import EmailVerification
        if isinstance(exc, EmailVerification.DoesNotExist):
            logger.warning('Signup verification record %s missing during async dispatch', verification_id)
        else:
            logger.exception('Async signup verification failed for id=%s', verification_id)
    finally:
        close_old_connections()


def start_signup_verification_async(verification, redirect_url: str, lang_code: str | None = None) -> dict:
    from django.utils.translation import gettext as _

    lang = lang_code or translation.get_language() or 'en'
    set_signup_verification_pending(verification.email, verification.verification_type)

    threading.Thread(
        target=_complete_signup_verification,
        args=(verification.pk, lang),
        daemon=True,
    ).start()

    return {
        'success': True,
        'async': True,
        'redirect': redirect_url,
        'message': _('Redirecting to verification…'),
    }
