"""PWA endpoints: web app manifest + service worker.

Both are served by Django views instead of static files because in
production STATIC_URL points to Cloudflare R2 (a different origin), and a
service worker MUST be same-origin and its scope is capped at its own URL
path — so /sw.js has to come from the site root. The manifest lives here
too so start_url/scope stay same-origin (its icon URLs may point at R2,
which is allowed).
"""

from django.conf import settings
from django.http import HttpResponse, JsonResponse
from django.views.decorators.cache import cache_control
from django.views.decorators.http import require_GET

# Bump to invalidate every installed client's caches on the next visit.
PWA_CACHE_VERSION = 'duno360-v1'


@require_GET
@cache_control(max_age=3600)
def manifest(request):
    static = settings.STATIC_URL
    return JsonResponse({
        'name': 'DUNO 360',
        'short_name': 'DUNO 360',
        'description': 'Books, online courses, marketplace & fresh supermarket — all in one platform.',
        'id': '/',
        'start_url': '/manager/public/?source=pwa',
        'scope': '/',
        'display': 'standalone',
        'orientation': 'portrait',
        'background_color': '#14245f',
        'theme_color': '#14245f',
        'lang': 'fr',
        'categories': ['shopping', 'education', 'books'],
        'icons': [
            {
                'src': f'{static}img/pwa-icon-192.png',
                'sizes': '192x192',
                'type': 'image/png',
                'purpose': 'any',
            },
            {
                'src': f'{static}img/pwa-icon-512.png',
                'sizes': '512x512',
                'type': 'image/png',
                'purpose': 'any',
            },
            {
                'src': f'{static}img/pwa-icon-512.png',
                'sizes': '512x512',
                'type': 'image/png',
                'purpose': 'maskable',
            },
        ],
        'shortcuts': [
            {
                'name': 'Marché',
                'url': '/marketplace/?source=pwa',
                'icons': [{'src': f'{static}img/pwa-icon-192.png', 'sizes': '192x192'}],
            },
            {
                'name': 'Livres',
                'url': '/manager/public/books/?source=pwa',
                'icons': [{'src': f'{static}img/pwa-icon-192.png', 'sizes': '192x192'}],
            },
            {
                'name': 'Supermarché',
                'url': '/marketplace/supermarket/?source=pwa',
                'icons': [{'src': f'{static}img/pwa-icon-192.png', 'sizes': '192x192'}],
            },
        ],
    }, content_type='application/manifest+json')


_SW_TEMPLATE = """\
// DUNO 360 service worker — %(version)s
// Network-first for pages, stale-while-revalidate for assets. Never touches
// non-GET requests or vendor/admin/API paths, so nothing dynamic can go stale.
const CACHE_STATIC = '%(version)s-static';
const CACHE_PAGES = '%(version)s-pages';

const NEVER_CACHE = [
    '/manager/vendor/', '/marketplace/vendor/', '/marketplace/admin/',
    '/manager/api/', '/api/', '/manager/cart/', '/marketplace/cart/',
    '/manager/checkout', '/marketplace/checkout', '/sw.js',
];

self.addEventListener('install', (event) => {
    self.skipWaiting();
});

self.addEventListener('activate', (event) => {
    event.waitUntil((async () => {
        const names = await caches.keys();
        await Promise.all(names
            .filter((n) => !n.startsWith('%(version)s'))
            .map((n) => caches.delete(n)));
        await self.clients.claim();
    })());
});

self.addEventListener('fetch', (event) => {
    const request = event.request;
    if (request.method !== 'GET') return;

    const url = new URL(request.url);
    if (url.origin === self.location.origin &&
        NEVER_CACHE.some((p) => url.pathname.startsWith(p))) return;

    const dest = request.destination;

    // Assets: serve from cache immediately, refresh in the background.
    if (['style', 'script', 'image', 'font'].includes(dest)) {
        event.respondWith((async () => {
            const cache = await caches.open(CACHE_STATIC);
            const cached = await cache.match(request);
            const refresh = fetch(request).then((resp) => {
                if (resp && resp.ok) cache.put(request, resp.clone());
                return resp;
            }).catch(() => cached);
            return cached || refresh;
        })());
        return;
    }

    // Page navigations: network first, cached copy when offline.
    if (request.mode === 'navigate') {
        event.respondWith((async () => {
            const cache = await caches.open(CACHE_PAGES);
            try {
                const resp = await fetch(request);
                if (resp && resp.ok) cache.put(request, resp.clone());
                return resp;
            } catch (err) {
                const cached = await cache.match(request);
                if (cached) return cached;
                return new Response(
                    '<!DOCTYPE html><html lang="fr"><head><meta charset="utf-8">' +
                    '<meta name="viewport" content="width=device-width,initial-scale=1">' +
                    '<title>Hors ligne — DUNO 360</title>' +
                    '<style>body{font-family:system-ui,sans-serif;background:#14245f;color:#fff;' +
                    'display:flex;align-items:center;justify-content:center;min-height:100vh;margin:0;text-align:center;padding:24px}' +
                    'h1{font-size:1.4rem}p{opacity:.75}</style></head><body><div>' +
                    '<h1>Vous êtes hors ligne</h1>' +
                    '<p>Vérifiez votre connexion internet puis réessayez.<br>' +
                    'Please check your internet connection and try again.</p>' +
                    '</div></body></html>',
                    { status: 503, headers: { 'Content-Type': 'text/html; charset=utf-8' } }
                );
            }
        })());
    }
});
"""


@require_GET
@cache_control(max_age=0)
def service_worker(request):
    body = _SW_TEMPLATE % {'version': PWA_CACHE_VERSION}
    response = HttpResponse(body, content_type='application/javascript')
    response['Service-Worker-Allowed'] = '/'
    return response
