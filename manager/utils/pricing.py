"""CNY → XAF (FCFA) formatting shared by templates, APIs, and feeds."""

CNY_TO_XAF = 82


def format_fcfa(amount):
    """Format stored CNY amount as FCFA string (e.g. '3\u202f198 FCFA')."""
    try:
        n = round(float(amount) * CNY_TO_XAF)
        formatted = f"{n:,}".replace(",", "\u202f")
        return f"{formatted} FCFA"
    except (TypeError, ValueError):
        return f"{amount} FCFA"
