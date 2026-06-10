"""Platform commission rates by publish / item type."""
from decimal import Decimal, ROUND_HALF_UP

MONEY = Decimal('0.01')

# product = boutique / ordinary shop listing
COMMISSION_RATES = {
    'product': Decimal('10.00'),
    'course': Decimal('10.00'),
    'supermarket': Decimal('12.00'),
    'book': Decimal('9.00'),
}

COMMISSION_LABELS = {
    'product': 'Boutique / produits',
    'course': 'Cours',
    'supermarket': 'Supermarché',
    'book': 'Livres',
}


def get_commission_rate(item_type):
    """Return platform commission % for an item type."""
    return COMMISSION_RATES.get(item_type, Decimal('10.00'))


def split_gross_amount(gross_amount, item_type):
    """
    Split a gross line amount into platform commission and vendor net.
    Returns (commission_rate, commission_amount, vendor_net).
    """
    gross = Decimal(str(gross_amount)).quantize(MONEY, rounding=ROUND_HALF_UP)
    rate = get_commission_rate(item_type)
    commission = (gross * rate / Decimal('100')).quantize(MONEY, rounding=ROUND_HALF_UP)
    vendor_net = (gross - commission).quantize(MONEY, rounding=ROUND_HALF_UP)
    return rate, commission, vendor_net
