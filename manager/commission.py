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

# Chinese-first labels (primary); EN/FR via template i18n where needed
COMMISSION_LABELS = {
    'product': '商品',
    'course': '课程',
    'supermarket': '超市',
    'book': '图书',
}

COMMISSION_LABELS_EN = {
    'product': 'Products',
    'course': 'Courses',
    'supermarket': 'Supermarket',
    'book': 'Books',
}

COMMISSION_LABELS_FR = {
    'product': 'Produits',
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
    Example: gross=500 FCFA, book rate 9% → commission=45, vendor_net=455.
    Returns (commission_rate, commission_amount, vendor_net).
    """
    gross = Decimal(str(gross_amount)).quantize(MONEY, rounding=ROUND_HALF_UP)
    rate = get_commission_rate(item_type)
    commission = (gross * rate / Decimal('100')).quantize(MONEY, rounding=ROUND_HALF_UP)
    vendor_net = (gross - commission).quantize(MONEY, rounding=ROUND_HALF_UP)
    return rate, commission, vendor_net


def commission_rates_for_display():
    """Ordered list for admin/vendor UI."""
    return [
        {
            'type': key,
            'label': COMMISSION_LABELS[key],
            'label_en': COMMISSION_LABELS_EN[key],
            'label_fr': COMMISSION_LABELS_FR[key],
            'rate': COMMISSION_RATES[key],
        }
        for key in ('book', 'product', 'course', 'supermarket')
    ]
