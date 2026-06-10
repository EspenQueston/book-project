"""
Currency template filters for DUNO 360.
Prices are stored and displayed in FCFA (XAF).
"""
from django import template

register = template.Library()


def _format_amount(value):
    """Format a FCFA amount with French-style grouping."""
    amount = round(float(value))
    return f"{amount:,}".replace(",", "\u202f")


@register.filter(name='fcfa')
def to_fcfa(value):
    """Format a FCFA price. Returns e.g. '35 000 FCFA'."""
    try:
        return f"{_format_amount(value)} FCFA"
    except (ValueError, TypeError):
        return f"{value} FCFA"


@register.filter(name='fcfa_raw')
def to_fcfa_raw(value):
    """Return FCFA amount as integer (no symbol)."""
    try:
        return round(float(value))
    except (ValueError, TypeError):
        return value


@register.simple_tag
def fcfa_rate():
    """Legacy tag — platform uses FCFA directly (no conversion)."""
    return 1
