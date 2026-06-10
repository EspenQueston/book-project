"""Registry for DUNO 360 public information pages (content from PAGES DUNO 360.docx)."""

from django.urls import reverse
from django.utils.translation import gettext_lazy as _


PLATFORM_GRADIENT = ('#667eea', '#764ba2')

INFO_PAGES = {
    'politique-remboursement': {
        'title': _('退款政策'),
        'subtitle': _('DUNO 360 平台退款条件与争议处理流程。'),
        'icon': 'fa-rotate-left',
        'gradient': PLATFORM_GRADIENT,
        'highlights': [
            {'icon': 'fa-clock', 'text': _('5 个工作日内退款')},
            {'icon': 'fa-mobile-screen', 'text': _('移动支付')},
            {'icon': 'fa-handshake', 'text': _('DUNO 360 调解')},
        ],
        'content_template': 'public/pages/content/refund.html',
        'sections': [
            {'id': 'introduction', 'label': _('简介'), 'icon': 'fa-info-circle'},
            {'id': 'conditions', 'label': _('退款条件'), 'icon': 'fa-list-check'},
            {'id': 'procedure', 'label': _('流程与期限'), 'icon': 'fa-route'},
            {'id': 'litiges', 'label': _('争议与滥用'), 'icon': 'fa-scale-balanced'},
        ],
        'cta': {
            'title': _('需要帮助？'),
            'text': _('我们的客户服务团队随时为您服务。'),
            'button': _('客户服务'),
            'url_name': 'manager:info_page',
            'url_kwargs': {'slug': 'service-client'},
            'icon': 'fa-headset',
        },
    },
    'commande-livraison': {
        'title': _('下单与配送'),
        'subtitle': _('下单、移动支付及取货点自提指南。'),
        'icon': 'fa-truck-fast',
        'gradient': PLATFORM_GRADIENT,
        'highlights': [
            {'icon': 'fa-wallet', 'text': _('移动支付')},
            {'icon': 'fa-location-dot', 'text': _('取货点')},
            {'icon': 'fa-bell', 'text': _('实时跟踪')},
        ],
        'content_template': 'public/pages/content/shipping.html',
        'sections': [
            {'id': 'commander', 'label': _('下单'), 'icon': 'fa-cart-shopping'},
            {'id': 'paiement', 'label': _('支付方式'), 'icon': 'fa-mobile-screen'},
            {'id': 'livraison', 'label': _('配送'), 'icon': 'fa-location-dot'},
            {'id': 'suivi', 'label': _('跟踪'), 'icon': 'fa-bell'},
        ],
        'cta': {
            'title': _('准备下单？'),
            'text': _('探索 DUNO 360 综合市场。'),
            'button': _('综合市场'),
            'url_name': 'marketplace:home',
            'icon': 'fa-store',
        },
    },
    'devenir-partenaire': {
        'title': _('成为合作伙伴'),
        'subtitle': _('以卖家、培训师或取货点身份加入 DUNO 360 生态。'),
        'icon': 'fa-handshake',
        'gradient': PLATFORM_GRADIENT,
        'highlights': [
            {'icon': 'fa-store', 'text': _('在线店铺')},
            {'icon': 'fa-chart-line', 'text': _('本地曝光')},
            {'icon': 'fa-coins', 'text': _('数字收入')},
        ],
        'content_template': 'public/pages/content/partner.html',
        'sections': [
            {'id': 'pourquoi', 'label': _('为什么'), 'icon': 'fa-star'},
            {'id': 'types', 'label': _('合作类型'), 'icon': 'fa-layer-group'},
            {'id': 'inscription', 'label': _('注册'), 'icon': 'fa-user-plus'},
        ],
        'cta': {
            'title': _('开设您的店铺'),
            'text': _('几分钟内完成卖家注册。'),
            'button': _('成为卖家'),
            'url_name': 'manager:vendor_register',
            'icon': 'fa-store',
        },
    },
    'partenaire-premium': {
        'title': _('Premium 合作伙伴'),
        'subtitle': _('优先曝光、增强推广及专业工具。'),
        'icon': 'fa-gem',
        'gradient': PLATFORM_GRADIENT,
        'highlights': [
            {'icon': 'fa-arrow-up', 'text': _('搜索结果置顶')},
            {'icon': 'fa-bullhorn', 'text': _('增强推广')},
            {'icon': 'fa-crown', 'text': _('Premium 徽章')},
        ],
        'content_template': 'public/pages/content/premium.html',
        'sections': [
            {'id': 'avantages', 'label': _('优势'), 'icon': 'fa-gem'},
            {'id': 'tarifs', 'label': _('套餐'), 'icon': 'fa-tags'},
            {'id': 'souscrire', 'label': _('订阅'), 'icon': 'fa-bolt'},
        ],
        'cta': {
            'title': _('升级 Premium'),
            'text': _('在 DUNO 360 上提升您的曝光度。'),
            'button': _('开设店铺'),
            'url_name': 'manager:vendor_register',
            'icon': 'fa-crown',
        },
    },
    'service-client': {
        'title': _('客户服务'),
        'subtitle': _('订单、配送、退款及账户协助。'),
        'icon': 'fa-headset',
        'gradient': PLATFORM_GRADIENT,
        'highlights': [
            {'icon': 'fa-bolt', 'text': _('24 小时内回复')},
            {'icon': 'fa-life-ring', 'text': _('专属支持')},
            {'icon': 'fa-comments', 'text': _('WhatsApp 与邮件')},
        ],
        'content_template': 'public/pages/content/support.html',
        'sections': [
            {'id': 'aide', 'label': _('帮助'), 'icon': 'fa-life-ring'},
            {'id': 'contact', 'label': _('联系'), 'icon': 'fa-phone'},
            {'id': 'conseils', 'label': _('建议'), 'icon': 'fa-lightbulb'},
        ],
        'cta': {
            'title': _('联系我们'),
            'text': _('联系表单全天候可用。'),
            'button': _('联系我们'),
            'url_name': 'manager:public_contact',
            'icon': 'fa-envelope',
        },
    },
}


LEGAL_PAGE = {
    'title': _('隐私政策'),
    'subtitle': _('DUNO 360 数据保护及使用条款说明。'),
    'icon': 'fa-shield-halved',
    'gradient': PLATFORM_GRADIENT,
    'sections': [
        {'id': 'confidentialite', 'label': _('概要'), 'icon': 'fa-shield-halved'},
        {'id': 'donnees-collectees', 'label': _('数据'), 'icon': 'fa-database'},
        {'id': 'utilisation-donnees', 'label': _('使用'), 'icon': 'fa-gears'},
        {'id': 'partage-donnees', 'label': _('共享'), 'icon': 'fa-share-nodes'},
        {'id': 'securite-conservation', 'label': _('安全'), 'icon': 'fa-lock'},
        {'id': 'vos-droits', 'label': _('您的权利'), 'icon': 'fa-user-shield'},
        {'id': 'cookies', 'label': _('Cookie'), 'icon': 'fa-cookie-bite'},
        {'id': 'conditions-utilisation', 'label': _('使用条款'), 'icon': 'fa-file-contract'},
    ],
    'cta': {
        'title': _('对您的数据有疑问？'),
        'text': _('我们的团队将在 24 小时内回复。'),
        'button': _('联系我们'),
        'url_name': 'manager:public_contact',
        'icon': 'fa-envelope',
    },
}


ABOUT_PAGE = {
    'title': _('关于 DUNO 360'),
    'subtitle': _('为非洲打造的数字市场 — 本地贸易、移动支付与取货点。'),
    'icon': 'fa-globe-africa',
    'gradient': PLATFORM_GRADIENT,
    'content_template': 'public/pages/content/about.html',
    'sections': [
        {'id': 'mission', 'label': _('使命'), 'icon': 'fa-rocket'},
        {'id': 'plateforme', 'label': _('平台'), 'icon': 'fa-store'},
        {'id': 'afrique', 'label': _('非洲'), 'icon': 'fa-mobile-screen'},
        {'id': 'vision', 'label': _('愿景'), 'icon': 'fa-eye'},
        {'id': 'faq', 'label': _('常见问题'), 'icon': 'fa-circle-question'},
    ],
}


def get_info_page(slug):
    return INFO_PAGES.get(slug)


def get_all_info_pages():
    return INFO_PAGES


def get_sitemap_sections():
    """Structured links for the site map page."""
    return [
        {
            'slug': 'plateforme',
            'title': _('平台'),
            'icon': 'fa-compass',
            'color': '#667eea',
            'links': [
                {'label': _('首页'), 'url_name': 'manager:public_home'},
                {'label': _('综合市场'), 'url_name': 'marketplace:home'},
                {'label': _('图书'), 'url_name': 'manager:public_books'},
                {'label': _('博客'), 'url_name': 'manager:public_blog'},
                {'label': _('关于我们'), 'url_name': 'manager:public_about'},
                {'label': _('我们的服务'), 'url_name': 'manager:public_services'},
                {'label': _('联系我们'), 'url_name': 'manager:public_contact'},
            ],
        },
        {
            'slug': 'compte-achat',
            'title': _('账户与购买'),
            'icon': 'fa-user-circle',
            'color': '#764ba2',
            'links': [
                {'label': _('创建账户'), 'url_name': 'manager:user_register'},
                {'label': _('登录'), 'url_name': 'manager:user_login'},
                {'label': _('购物车'), 'url_name': 'manager:view_cart'},
                {'label': _('订单跟踪'), 'url_name': 'manager:track_order'},
                {'label': _('下单与配送'), 'url_name': 'manager:info_page', 'url_kwargs': {'slug': 'commande-livraison'}},
                {'label': _('客户服务'), 'url_name': 'manager:info_page', 'url_kwargs': {'slug': 'service-client'}},
            ],
        },
        {
            'slug': 'vendeurs-partenaires',
            'title': _('卖家与合作伙伴'),
            'icon': 'fa-store',
            'color': '#6366f1',
            'links': [
                {'label': _('开设店铺'), 'url_name': 'manager:vendor_register'},
                {'label': _('卖家登录'), 'url_name': 'manager:vendor_login'},
                {'label': _('成为合作伙伴'), 'url_name': 'manager:info_page', 'url_kwargs': {'slug': 'devenir-partenaire'}},
                {'label': _('Premium 合作伙伴'), 'url_name': 'manager:info_page', 'url_kwargs': {'slug': 'partenaire-premium'}},
            ],
        },
        {
            'slug': 'informations-legales',
            'title': _('法律信息'),
            'icon': 'fa-scale-balanced',
            'color': '#8b5cf6',
            'links': [
                {'label': _('隐私政策'), 'url_name': 'manager:legal_privacy'},
                {'label': _('使用条款'), 'url_name': 'manager:legal_terms'},
                {'label': _('退款政策'), 'url_name': 'manager:info_page', 'url_kwargs': {'slug': 'politique-remboursement'}},
            ],
        },
    ]
