# -*- coding: utf-8 -*-
"""Official DUNO 360 social media links (footer, contact, blog)."""

from django.conf import settings


def get_platform_social_links():
    return [
        {
            'key': 'facebook',
            'url': settings.SOCIAL_FACEBOOK_URL,
            'icon': 'fab fa-facebook-f',
            'label': 'Facebook',
            'handle': 'DUNO 360',
            'color': '#1877f2',
        },
        {
            'key': 'instagram',
            'url': settings.SOCIAL_INSTAGRAM_URL,
            'icon': 'fab fa-instagram',
            'label': 'Instagram',
            'handle': '@duno_360',
            'color': 'linear-gradient(135deg,#f58529,#dd2a7b,#8134af)',
        },
        {
            'key': 'tiktok',
            'url': settings.SOCIAL_TIKTOK_URL,
            'icon': 'fab fa-tiktok',
            'label': 'TikTok',
            'handle': '@duno.360',
            'color': '#010101',
        },
        {
            'key': 'youtube',
            'url': settings.SOCIAL_YOUTUBE_URL,
            'icon': 'fab fa-youtube',
            'label': 'YouTube',
            'handle': '@DUNO360',
            'color': '#ff0000',
        },
    ]
