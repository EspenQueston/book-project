from django.contrib import admin
from django.urls import path, include
from django.shortcuts import redirect
from django.conf import settings
from django.conf.urls.static import static
from django.http import HttpResponseForbidden


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
    path('admin/', admin.site.urls),  # Django admin
    path('i18n/', include('django.conf.urls.i18n')),  # Language switching
    path('rosetta/', include('rosetta.urls')),  # Translation interface
    path('marketplace/', include('marketplace.urls')),  # Marketplace
    path('manager/', include('manager.urls')),  # Public interface at /manager/
    path('', home_redirect, name='home'),  # Add this line for root URL
]

handler404 = 'django.views.defaults.page_not_found'
handler500 = 'django.views.defaults.server_error'

# Serve media files during development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
