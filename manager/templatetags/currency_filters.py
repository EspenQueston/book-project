"""
Currency template filters for DUNO 360.
Converts CNY (Yuan) prices to FCFA (Central African Franc / XAF).
Rate: 1 CNY ≈ 82 XAF  (May 2026 approximate)
"""
from django import template

register = template.Library()

CNY_TO_XAF = 82  # 1 CNY = 82 FCFA (XAF)


@register.filter(name='fcfa')
def to_fcfa(value):
    """Convert a CNY price to FCFA and format it. Returns e.g. '4 100 FCFA'."""
    try:
        amount = round(float(value) * CNY_TO_XAF)
        # French-style thousands separator (space)
        formatted = f"{amount:,}".replace(",", "\u202f")  # narrow no-break space
        return f"{formatted} FCFA"
    except (ValueError, TypeError):
        return f"{value} FCFA"


@register.filter(name='fcfa_raw')
def to_fcfa_raw(value):
    """Convert CNY → FCFA, return integer only (no formatting/symbol)."""
    try:
        return round(float(value) * CNY_TO_XAF)
    except (ValueError, TypeError):
        return value


@register.simple_tag
def fcfa_rate():
    """Return the CNY→XAF conversion rate (for JS use)."""
    return CNY_TO_XAF
