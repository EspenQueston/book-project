from django.contrib import admin
from django.urls import path, include
from django.shortcuts import redirect
from django.conf import settings
from django.conf.urls.static import static

def home_redirect(request):
    """Redirect root URL to manager app"""
    return redirect('manager/public')

# Main URL patterns
urlpatterns = [
    path('admin/', admin.site.urls),  # Django admin
    path('i18n/', include('django.conf.urls.i18n')),  # Language switching
    path('rosetta/', include('rosetta.urls')),  # Translation interface
    path('manager/', include('manager.urls')),  # Public interface at /manager/
    path('', home_redirect, name='home'),  # Add this line for root URL
]

# Serve media files during development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
