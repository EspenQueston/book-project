from django.urls import path, include, re_path
from django.shortcuts import redirect
from django.conf import settings
from django.conf.urls.static import static
from django.contrib.staticfiles.views import serve as staticfiles_serve
from django.http import HttpResponseForbidden
import sys


def home_redirect(request):
    """Redirect root URL to manager app"""
    return redirect('manager/public')


def _rosetta_guard(get_response):
    """Middleware-style guard: only verified admin sessions can reach Rosetta."""
    def middleware(request):
        if not request.session.get('is_admin'):
            return HttpResponseForbidden('Forbidden: admin access required.')
        return get_response(request)
    return middleware


class RosettaAdminMiddleware:
    """Restricts the /rosetta/ path to admin sessions."""
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.path.startswith('/rosetta/') and not request.session.get('is_admin'):
            return redirect(f'/manager/login/?next={request.path}')
        return self.get_response(request)

# Main URL patterns
urlpatterns = [
    # Django's built-in admin (django.contrib.admin) was deliberately never
    # mounted here — the custom "manager" admin panel fully covers every
    # model, and a second, separately-authenticated admin surface sitting
    # at a well-known public path is just extra attack surface for no
    # operational benefit. See marketplace/admin.py — its ModelAdmin
    # registrations are now inert with no URL to reach them.
    path('i18n/', include('django.conf.urls.i18n')),  # Language switching
    path('marketplace/', include('marketplace.urls')),  # Marketplace
    path('manager/', include('manager.urls')),  # Public interface at /manager/
    path('', home_redirect, name='home'),  # Add this line for root URL
]

handler404 = 'django.views.defaults.page_not_found'
handler500 = 'django.views.defaults.server_error'

# Serve media files during development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += [
        re_path(r'^static/(?P<path>.*)$', staticfiles_serve, {'insecure': True}),
    ]
elif 'runserver' in sys.argv:
    # Local runserver can use DEBUG=False for production-like settings. In that
    # mode Django does not expose app static files, which hides admin_i18n.js
    # and chatbot_widget.js. Keep this limited to runserver only.
    urlpatterns += [
        re_path(r'^static/(?P<path>.*)$', staticfiles_serve, {'insecure': True}),
    ]
