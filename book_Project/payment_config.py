import os

AFRICAN_COUNTRIES = {
    'Benin', 'Burkina Faso', 'Cape Verde', "Côte d'Ivoire", 'Gambia', 'Ghana', 'Guinea',
    'Guinea-Bissau', 'Liberia', 'Mali', 'Mauritania', 'Niger', 'Nigeria', 'Senegal',
    'Sierra Leone', 'Togo', 'Angola', 'Cameroon', 'Central African Republic', 'Chad',
    'Congo', 'Democratic Republic of the Congo', 'Equatorial Guinea', 'Gabon',
    'São Tomé and Príncipe', 'Rwanda', 'Uganda', 'Kenya', 'Tanzania', 'Zambia', 'Malawi'
}
GREATER_CHINA_COUNTRIES = {'China', 'Hong Kong', 'Taiwan'}

PAYMENT_METHODS = {
    'mtn_money': {
        'label': 'MTN Money',
        'icon': 'fas fa-signal',
        'accent': '#ffcb05',
        'provider': os.environ.get('PAYMENT_MTN_PROVIDER', 'mtn_momo_api'),
        'mode': os.environ.get('PAYMENT_MTN_MODE', 'direct_api'),
        'enabled': os.environ.get('PAYMENT_MTN_ENABLED', 'True') == 'True',
        'requires_manual_review': os.environ.get('PAYMENT_MTN_MANUAL_REVIEW', 'False') == 'True',
    },
    'orange_money': {
        'label': 'Orange Money',
        'icon': 'fas fa-mobile-screen-button',
        'accent': '#ff7900',
        'provider': os.environ.get('PAYMENT_ORANGE_PROVIDER', 'cinetpay'),
        'mode': os.environ.get('PAYMENT_ORANGE_MODE', 'redirect_api'),
        'enabled': os.environ.get('PAYMENT_ORANGE_ENABLED', 'True') == 'True',
        'requires_manual_review': os.environ.get('PAYMENT_ORANGE_MANUAL_REVIEW', 'False') == 'True',
        # 'instructions': 'Renseignez vos identifiants Orange Money ou agrégateur.',
    },
    'airtel_money': {
        'label': 'Airtel Money',
        'icon': 'fas fa-tower-cell',
        'accent': '#ed1c24',
        'provider': os.environ.get('PAYMENT_AIRTEL_PROVIDER', 'airtel_money_api'),
        'mode': os.environ.get('PAYMENT_AIRTEL_MODE', 'direct_api'),
        'enabled': os.environ.get('PAYMENT_AIRTEL_ENABLED', 'True') == 'True',
        'requires_manual_review': os.environ.get('PAYMENT_AIRTEL_MANUAL_REVIEW', 'False') == 'True',
    },
    'wechat_pay': {
        'label': '微信支付',
        'icon': 'fab fa-weixin',
        'accent': '#07c160',
        'provider': os.environ.get('PAYMENT_WECHAT_PROVIDER', 'manual_qr'),
        'mode': os.environ.get('PAYMENT_WECHAT_MODE', 'manual_qr'),
        'enabled': os.environ.get('PAYMENT_WECHAT_ENABLED', 'True') == 'True',
        'requires_manual_review': os.environ.get('PAYMENT_WECHAT_MANUAL_REVIEW', 'True') == 'True',
        # 'instructions': 'Par défaut en QR manuel. Remplacez par votre provider PSP si vous avez un contrat marchand.',
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
        # 'instructions': 'Ajoutez PAYPAL_CLIENT_ID et PAYPAL_CLIENT_SECRET pour le live.',
    },
    'credit_card': {
        'label': 'Visa / Mastercard',
        'icon': 'fas fa-credit-card',
        'accent': '#475569',
        'provider': os.environ.get('PAYMENT_CARD_PROVIDER', 'stripe'),
        'mode': os.environ.get('PAYMENT_CARD_MODE', 'redirect_api'),
        'enabled': os.environ.get('PAYMENT_CARD_ENABLED', 'True') == 'True',
        'requires_manual_review': os.environ.get('PAYMENT_CARD_MANUAL_REVIEW', 'False') == 'True',
        # 'instructions': 'Ajoutez STRIPE_SECRET_KEY et STRIPE_PUBLISHABLE_KEY, ou remplacez par votre PSP.',
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
    'africa': ['mtn_money', 'orange_money', 'airtel_money'],
    'china': ['wechat_pay', 'alipay'],
    'others': ['paypal', 'credit_card', 'bank_transfer'],
}


def resolve_payment_region(country):
    if country in AFRICAN_COUNTRIES:
        return 'africa'
    if country in GREATER_CHINA_COUNTRIES:
        return 'china'
    return 'others'



def build_payment_options(country=None):
    region = resolve_payment_region(country) if country else None
    region_map = PAYMENT_METHODS_BY_REGION if region is None else {region: PAYMENT_METHODS_BY_REGION[region]}
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
                'instructions': method.get('instructions', ''),
            })
        result[region_key] = options

    return result
