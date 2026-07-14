"""Read-only diagnostic: is the app actually using Redis right now, or has
it silently fallen back to per-process LocMemCache?

Why this matters: gunicorn runs 3 worker processes in production
(deploy/setup_ionos.sh). LocMemCache is NOT shared between processes — each
worker has its own private cache, so anything cached (live product
presence, rate limiting, etc.) becomes inconsistent depending on which
worker happens to handle a given request, silently, with no error. This
command tells you definitively which backend is active and why, instead
of inferring it from Django's own startup warnings (which only fire in
DEBUG mode).

Run this ON THE SERVER (same environment the app actually runs in):
    .venv/bin/python manage.py check_cache_backend
"""
import os

from django.conf import settings
from django.core.cache import cache
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = 'Report which cache backend is actually active and why.'

    def handle(self, *args, **options):
        redis_url = os.environ.get('REDIS_URL', '').strip()
        backend = settings.CACHES.get('default', {}).get('BACKEND', '<unknown>')
        is_redis = 'redis' in backend.lower()

        self.stdout.write('')
        self.stdout.write(self.style.MIGRATE_HEADING('Cache backend diagnostic'))
        self.stdout.write(f'  REDIS_URL set:      {"yes" if redis_url else "no"}')
        if redis_url:
            # Never print the full URL — it may carry a password.
            safe = redis_url.split('@')[-1] if '@' in redis_url else redis_url
            self.stdout.write(f'  REDIS_URL host:     {safe}')
        self.stdout.write(f'  Active CACHES backend: {backend}')

        if not redis_url:
            self.stdout.write(self.style.WARNING(
                '\nRunning on LocMemCache because REDIS_URL is not set at all. '
                'This is a deliberate no-Redis deployment if that is intended — '
                'but with 3 gunicorn workers, each has its own separate cache, '
                'so anything you expect to be cached/shared across requests '
                'will be inconsistent depending on which worker serves the request.'
            ))
            return

        if not is_redis:
            self.stdout.write(self.style.ERROR(
                '\nREDIS_URL is set but the active backend is NOT Redis — '
                'this means Django could not reach Redis at process startup '
                'and (in DEBUG mode only) silently fell back to LocMemCache. '
                'In production this should have refused to start instead — '
                'if the app is running at all with this state, something is '
                'unexpected. Check Redis is installed/running and REDIS_URL '
                'is correct.'
            ))
            return

        # Backend claims to be Redis — verify it actually responds right now.
        try:
            cache.set('check_cache_backend_probe', 'ok', timeout=10)
            value = cache.get('check_cache_backend_probe')
            if value == 'ok':
                self.stdout.write(self.style.SUCCESS(
                    '\nRedis is configured AND reachable right now — cache is '
                    'correctly shared across all gunicorn workers.'
                ))
            else:
                self.stdout.write(self.style.ERROR(
                    '\nRedis backend is active but a live set/get probe did not '
                    'round-trip correctly — investigate before trusting cached data.'
                ))
        except Exception as exc:
            self.stdout.write(self.style.ERROR(
                f'\nRedis backend is configured but the live probe failed: {exc}'
            ))
