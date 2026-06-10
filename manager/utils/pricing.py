"""FCFA formatting shared by templates, APIs, and feeds."""


def format_fcfa(amount):
    """Format stored FCFA amount (e.g. '35\u202f000 FCFA')."""
    try:
        n = round(float(amount))
        formatted = f"{n:,}".replace(",", "\u202f")
        return f"{formatted} FCFA"
    except (TypeError, ValueError):
        return f"{amount} FCFA"
