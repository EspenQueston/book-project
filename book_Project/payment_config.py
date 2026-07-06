import os

# ---------------------------------------------------------------------------
# Geographic regions — KKiaPay (West Africa) · PawaPay (Central Africa)
# ---------------------------------------------------------------------------
WEST_AFRICAN_COUNTRIES = {
    'Benin', 'Burkina Faso', 'Cape Verde', "Côte d'Ivoire", 'Gambia', 'Ghana',
    'Guinea', 'Guinea-Bissau', 'Liberia', 'Mali', 'Mauritania', 'Niger',
    'Nigeria', 'Senegal', 'Sierra Leone', 'Togo',
    'Bénin', 'Sénégal', 'Guinée',
}

CENTRAL_AFRICAN_COUNTRIES = {
    'Angola', 'Cameroon', 'Central African Republic', 'Chad', 'Congo',
    'Democratic Republic of the Congo', 'Equatorial Guinea', 'Gabon',
    'São Tomé and Príncipe',
    'Cameroun', 'République centrafricaine', 'République du Congo',
    'République démocratique du Congo', 'Guinée équatoriale', 'Gabon',
}

GREATER_CHINA_COUNTRIES = {'China', 'Hong Kong', 'Taiwan'}

# ISO codes — KKiaPay West Africa (CM removed → PawaPay)
KKIAPAY_COUNTRY_CODES = ['BJ', 'CI', 'TG', 'SN', 'NE', 'GN', 'BF', 'ML']

# ISO codes — PawaPay Central Africa (CEMAC + common coverage)
PAWAPAY_COUNTRY_CODES = ['CM', 'CG', 'CF', 'TD', 'GQ', 'GA', 'AO', 'CD', 'ST']

# ---------------------------------------------------------------------------
# "Coming soon" countries — listed at checkout so shoppers see their country,
# but mobile money isn't wired up for them yet (no active KKiaPay/PawaPay
# corridor on this merchant account). Verified live against PawaPay's
# GET /active-conf on 2026-07-07: Congo, DRC, Cameroon and Gabon are active;
# Angola, Chad, CAR, Equatorial Guinea and São Tomé are absent from that
# response and would reject every deposit with DEPOSITS_NOT_ALLOWED.
CENTRAL_AFRICA_COMING_SOON = {
    'Angola', 'Chad', 'Central African Republic', 'Equatorial Guinea',
    'São Tomé and Príncipe',
    'République centrafricaine', 'Guinée équatoriale',
}

# West African countries with no active KKiaPay corridor configured yet.
WEST_AFRICA_COMING_SOON = {
    'Cape Verde', 'Gambia', 'Ghana', 'Guinea-Bissau', 'Liberia',
    'Mauritania', 'Nigeria', 'Sierra Leone',
}

COMING_SOON_COUNTRIES = CENTRAL_AFRICA_COMING_SOON | WEST_AFRICA_COMING_SOON


def is_coming_soon(country):
    return country in COMING_SOON_COUNTRIES

PAYMENT_METHODS = {
    'kkiapay': {
        'label': 'Mobile Money (KKiaPay)',
        'label_zh': '移动支付 (KKiaPay)',
        'icon': 'fas fa-mobile-alt',
        'accent': '#e85d04',
        'provider': 'kkiapay',
        'mode': 'widget',
        'enabled': os.environ.get('KKIAPAY_ENABLED', 'True') == 'True',
        'requires_manual_review': False,
        'description': 'MTN, Moov, Orange, Wave, T-Money…',
        'region_label': '西非',
    },
    'pawapay': {
        'label': 'Mobile Money (PawaPay)',
        'label_zh': '移动支付 (PawaPay)',
        'icon': 'fas fa-wallet',
        'accent': '#059669',
        'provider': 'pawapay',
        'mode': 'api',
        'enabled': os.environ.get('PAWAPAY_ENABLED', 'True') == 'True',
        'requires_manual_review': False,
        'description': 'MTN, Orange, Airtel — Afrique centrale',
        'region_label': '中非',
    },
    'wechat_pay': {
        'label': '微信支付',
        'icon': 'fab fa-weixin',
        'accent': '#07c160',
        'provider': os.environ.get('PAYMENT_WECHAT_PROVIDER', 'manual_qr'),
        'mode': os.environ.get('PAYMENT_WECHAT_MODE', 'manual_qr'),
        'enabled': os.environ.get('PAYMENT_WECHAT_ENABLED', 'True') == 'True',
        'requires_manual_review': os.environ.get('PAYMENT_WECHAT_MANUAL_REVIEW', 'True') == 'True',
    },
    'alipay': {
        'label': '支付宝',
        'icon': 'fab fa-alipay',
        'accent': '#1677ff',
        'provider': os.environ.get('PAYMENT_ALIPAY_PROVIDER', 'manual_qr'),
        'mode': os.environ.get('PAYMENT_ALIPAY_MODE', 'manual_qr'),
        'enabled': os.environ.get('PAYMENT_ALIPAY_ENABLED', 'True') == 'True',
        'requires_manual_review': os.environ.get('PAYMENT_ALIPAY_MANUAL_REVIEW', 'True') == 'True',
    },
    'paypal': {
        'label': 'PayPal',
        'icon': 'fab fa-paypal',
        'accent': '#0070ba',
        'provider': os.environ.get('PAYMENT_PAYPAL_PROVIDER', 'paypal'),
        'mode': os.environ.get('PAYMENT_PAYPAL_MODE', 'redirect_api'),
        'enabled': os.environ.get('PAYMENT_PAYPAL_ENABLED', 'True') == 'True',
        'requires_manual_review': os.environ.get('PAYMENT_PAYPAL_MANUAL_REVIEW', 'False') == 'True',
    },
    'credit_card': {
        'label': 'Visa / Mastercard',
        'icon': 'fas fa-credit-card',
        'accent': '#475569',
        'provider': os.environ.get('PAYMENT_CARD_PROVIDER', 'stripe'),
        'mode': os.environ.get('PAYMENT_CARD_MODE', 'redirect_api'),
        'enabled': os.environ.get('PAYMENT_CARD_ENABLED', 'True') == 'True',
        'requires_manual_review': os.environ.get('PAYMENT_CARD_MANUAL_REVIEW', 'False') == 'True',
    },
    'bank_transfer': {
        'label': 'Bank Transfer',
        'icon': 'fas fa-building-columns',
        'accent': '#10b981',
        'provider': os.environ.get('PAYMENT_BANK_PROVIDER', 'manual'),
        'mode': os.environ.get('PAYMENT_BANK_MODE', 'manual'),
        'enabled': os.environ.get('PAYMENT_BANK_ENABLED', 'True') == 'True',
        'requires_manual_review': True,
        'instructions': 'Ajoutez vos coordonnées bancaires avant activation.',
    },
}

PAYMENT_METHODS_BY_REGION = {
    'west_africa': ['kkiapay'],
    'central_africa': ['pawapay'],
    'china': ['wechat_pay', 'alipay'],
    'others': ['paypal', 'credit_card', 'bank_transfer'],
}


def resolve_payment_region(country):
    if country in WEST_AFRICAN_COUNTRIES:
        return 'west_africa'
    if country in CENTRAL_AFRICAN_COUNTRIES:
        return 'central_africa'
    if country in GREATER_CHINA_COUNTRIES:
        return 'china'
    return 'others'


def get_kkiapay_country_codes():
    try:
        from manager.models import KkiapayCountry
        codes = KkiapayCountry.get_active_iso_codes()
        filtered = [c for c in codes if c in KKIAPAY_COUNTRY_CODES]
        return filtered if filtered else KKIAPAY_COUNTRY_CODES
    except Exception:
        return KKIAPAY_COUNTRY_CODES


def get_pawapay_country_codes():
    return PAWAPAY_COUNTRY_CODES


def build_payment_options(country=None):
    region = resolve_payment_region(country) if country else None
    # A specific country that falls in a "coming soon" bucket gets zero
    # methods for its region — this is the server-side enforcement that
    # backs the checkout UI's "coming soon" state (see is_coming_soon()).
    # Called without a country (region is None), the full catalog is
    # returned unfiltered — the checkout page needs every region's methods
    # available client-side to render per-country as the shopper picks one.
    if region is not None and is_coming_soon(country):
        region_map = {region: []}
    else:
        region_map = (
            PAYMENT_METHODS_BY_REGION
            if region is None
            else {region: PAYMENT_METHODS_BY_REGION.get(region, [])}
        )
    result = {}

    for region_key, method_keys in region_map.items():
        options = []
        for method_key in method_keys:
            method = PAYMENT_METHODS.get(method_key)
            if not method or not method.get('enabled', False):
                continue
            options.append({
                'method': method_key,
                'name': method['label'],
                'icon': method['icon'],
                'color': method['accent'],
                'provider': method['provider'],
                'mode': method['mode'],
                'requires_manual_review': method['requires_manual_review'],
                'instructions': method.get('description') or method.get('instructions', ''),
                'region': region_key,
            })
        result[region_key] = options

    return result
