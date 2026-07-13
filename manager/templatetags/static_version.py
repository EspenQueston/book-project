"""Cache-busting for static JS/CSS.

`{% static %}` in this project always resolves through whichever storage
backend is configured in STORAGES['staticfiles'] — when real Supabase/R2
credentials are present in .env, that's an S3-compatible backend whose
.url() always builds an R2 CDN URL, completely ignoring DEBUG/STATIC_URL.
That's exactly why templates use the existing `use_local_static` (DEBUG)
conditional to force a hardcoded /static/... path during local
development instead: it's the only way to bypass the storage backend and
serve straight off disk, so edits are visible without an R2 upload.

Neither path has cache-busting on top of that: R2 is uploaded with
file_overwrite=True and no filename hashing, and the local /static/ path
has no versioning either — so a browser that already cached an old script
keeps using it indefinitely, silently running stale code against new
markup. This is exactly what broke the sign-up country selector: the
previously-cached signup_location.js didn't know the new country
<select> existed at all.

Use both tags together, inside the existing use_local_static branches:

    {% if use_local_static %}
    <script src="{% versioned_local_static 'js/signup_location.js' %}"></script>
    {% else %}
    <script src="{% versioned_static 'js/signup_location.js' %}"></script>
    {% endif %}

Both append ?v=<mtime> using the file's on-disk modification time as the
cache key — it changes automatically whenever the file is edited, no
manual version bump required.
"""
import os

from django import template
from django.templatetags.static import static as static_url
from django.contrib.staticfiles.finders import find as find_static

register = template.Library()


def _mtime_for(path):
    try:
        fs_path = find_static(path)
        return int(os.path.getmtime(fs_path)) if fs_path else 0
    except OSError:
        return 0


@register.simple_tag
def versioned_static(path):
    """Storage-backend URL (R2/S3 in production) + ?v=<mtime>."""
    url = static_url(path)
    separator = '&' if '?' in url else '?'
    return f'{url}{separator}v={_mtime_for(path)}'


@register.simple_tag
def versioned_local_static(path):
    """Hardcoded /static/<path> + ?v=<mtime> — bypasses the storage
    backend entirely, matching the existing use_local_static intent."""
    return f'/static/{path}?v={_mtime_for(path)}'
