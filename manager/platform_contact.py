# -*- coding: utf-8 -*-
"""Platform contact phone / WhatsApp (footer, contact page, support)."""

import re

from django.conf import settings


def _digits_only(value):
    return re.sub(r'\D', '', value or '')


def platform_phone_raw():
    return getattr(settings, 'PLATFORM_PHONE', '+242066790386').strip()


def platform_phone_display(raw=None):
    """+242066790386 → +242 06 679 03 86"""
    raw = raw or platform_phone_raw()
    digits = _digits_only(raw)
    if digits.startswith('242') and len(digits) >= 12:
        return f'+242 {digits[3:5]} {digits[5:8]} {digits[8:10]} {digits[10:12]}'
    if len(digits) >= 10:
        return f'+{digits[:3]} {digits[3:5]} {digits[5:8]} {digits[8:10]} {digits[10:]}'
    return raw or '+242 06 679 03 86'


def platform_phone_tel_href(raw=None):
    digits = _digits_only(raw or platform_phone_raw())
    return f'tel:+{digits}' if digits else 'tel:+242066790386'


def platform_whatsapp_url(raw=None):
    digits = _digits_only(raw or platform_phone_raw())
    return f'https://wa.me/{digits}' if digits else 'https://wa.me/242066790386'


def get_platform_contact_channels():
    raw = platform_phone_raw()
    display = platform_phone_display(raw)
    return {
        'phone_raw': raw,
        'phone_display': display,
        'phone_tel': platform_phone_tel_href(raw),
        'whatsapp_url': platform_whatsapp_url(raw),
    }
