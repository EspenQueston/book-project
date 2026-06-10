"""Helpers for platform email account configuration."""
from django.conf import settings

from manager.models import EmailAccount


def platform_email_address():
    return (
        getattr(settings, 'EMAIL_HOST_USER', '') or getattr(settings, 'CONTACT_EMAIL', '') or 'admin@duno360.com'
    ).strip()


def ensure_platform_email_account():
    """
    Create or update the default EmailAccount from Django settings (.env).
    Deactivates legacy Profitex accounts.
    """
    email = platform_email_address()
    if not email:
        return None

    password = getattr(settings, 'EMAIL_HOST_PASSWORD', '') or ''
    smtp_host = getattr(settings, 'EMAIL_HOST', 'smtp.zoho.com') or 'smtp.zoho.com'
    smtp_port = int(getattr(settings, 'EMAIL_PORT', 465) or 465)
    use_ssl = getattr(settings, 'EMAIL_USE_SSL', True)

    account, _ = EmailAccount.objects.update_or_create(
        email_address=email,
        defaults={
            'name': 'DUNO 360',
            'imap_host': 'imap.zoho.com',
            'imap_port': 993,
            'imap_use_ssl': True,
            'smtp_host': smtp_host,
            'smtp_port': smtp_port,
            'smtp_use_tls': not use_ssl and getattr(settings, 'EMAIL_USE_TLS', False),
            'username': email,
            'password': password,
            'is_active': True,
            'is_default': True,
        },
    )
    if password and account.password != password:
        account.password = password
        account.save(update_fields=['password'])

    EmailAccount.objects.exclude(id=account.id).update(is_default=False)
    EmailAccount.objects.filter(email_address__icontains='profitex').update(
        is_active=False,
        is_default=False,
    )
    return account
