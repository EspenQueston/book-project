from django.conf import settings


def platform_branding(request):
    """Expose platform contact email and social links in all public templates."""
    from manager.platform_contact import get_platform_contact_channels
    from manager.social_media import get_platform_social_links

    contact_email = getattr(settings, 'CONTACT_EMAIL', 'admin@duno360.com')
    from_email = getattr(settings, 'DEFAULT_FROM_EMAIL', f'DUNO 360 <{contact_email}>')
    channels = get_platform_contact_channels()
    return {
        'PLATFORM_CONTACT_EMAIL': contact_email,
        'PLATFORM_FROM_EMAIL': from_email,
        'PLATFORM_SOCIAL_LINKS': get_platform_social_links(),
        'PLATFORM_PHONE': channels['phone_raw'],
        'PLATFORM_PHONE_DISPLAY': channels['phone_display'],
        'PLATFORM_PHONE_TEL': channels['phone_tel'],
        'PLATFORM_WHATSAPP_URL': channels['whatsapp_url'],
    }


def use_local_static(request):
    """When DEBUG, prefer /static/ URLs (CDN may lack newly added assets)."""
    return {'use_local_static': settings.DEBUG}


def congo_locations_context(request):
    import json
    from manager.congo_locations import CONGO_DEPARTMENTS, get_departments_for_js
    return {
        'congo_departments': CONGO_DEPARTMENTS,
        'congo_departments_json': json.dumps(get_departments_for_js()),
    }
