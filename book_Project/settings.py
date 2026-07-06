import os
import warnings
from pathlib import Path
from urllib.parse import urlparse, unquote, parse_qs

from django.core.exceptions import ImproperlyConfigured
from django.utils.translation import gettext_lazy as _

# Build paths inside the project
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# ---------------------------------------------------------------------------
# Environment loading — try python-dotenv first, then fall back to reading
# the .env file manually so the app works even if python-dotenv is absent.
# ---------------------------------------------------------------------------
_dotenv_path = os.path.join(BASE_DIR, '.env')

try:
    from dotenv import load_dotenv
    load_dotenv(_dotenv_path)
except ImportError:
    # python-dotenv not installed — parse the .env file ourselves (simple
    # KEY=VALUE lines, no special expansion needed for our use-case).
    if os.path.isfile(_dotenv_path):
        with open(_dotenv_path, encoding='utf-8') as _f:
            for _line in _f:
                _line = _line.strip()
                if _line and not _line.startswith('#') and '=' in _line:
                    _eq = _line.index('=')
                    os.environ.setdefault(_line[:_eq].strip(), _line[_eq + 1:].strip())


def _required_env(name: str) -> str:
    """Return env var or raise a clear error pointing at the .env file."""
    value = os.environ.get(name)
    if not value:
        raise EnvironmentError(
            f"\n\n  ❌  Required environment variable '{name}' is not set.\n"
            f"  → Make sure it exists in your .env file at:\n"
            f"     {_dotenv_path}\n"
            f"  → Copy .env.example to .env if you haven't already.\n"
        )
    return value


# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = _required_env('SECRET_KEY')

# SECURITY WARNING: don't run with debug turned on in production!
# Set to False for production deployment
DEBUG = os.environ.get('DEBUG', 'False') == 'True'

# Allowed hosts for production
ALLOWED_HOSTS = os.environ.get(
    'ALLOWED_HOSTS', 'duno360.com,www.duno360.com,localhost,127.0.0.1'
).split(',')


# 应用程序定义
INSTALLED_APPS = [
    'modeltranslation',   # DOIT être avant django.contrib.admin
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'rosetta',
    'translatebot_django',
    'manager.apps.ManagerConfig',
    'marketplace.apps.MarketplaceConfig',
    # 新加入的程序模块放这里
]

# --- WhiteNoise (serve static files via gunicorn in production) ---
# Injected here so it runs even if whitenoise is absent in dev
try:
    import whitenoise  # noqa: F401
    _whitenoise_available = True
except ImportError:
    _whitenoise_available = False

# 中间件
_whitenoise_middleware = ['whitenoise.middleware.WhiteNoiseMiddleware'] if _whitenoise_available else []
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
] + _whitenoise_middleware + [
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.locale.LocaleMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'book_Project.middleware.AdminDebugMiddleware',
    'book_Project.urls.RosettaAdminMiddleware',  # Restrict /rosetta/ to admin sessions
]

# 根URL配置
ROOT_URLCONF = 'book_Project.urls'
# ROOT_URLCONF = 'manager.urls'

# 模板（前端页面）
TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [os.path.join(BASE_DIR, 'templates')],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'django.template.context_processors.i18n',
                'django.template.context_processors.media',
                'manager.context_processors.platform_branding',
                'manager.context_processors.use_local_static',
                'manager.context_processors.congo_locations_context',
                'manager.context_processors.tawkto',
            ],
        },
    },
]

# WSGI_应用程序
WSGI_APPLICATION = 'book_Project.wsgi.application'


# Database configuration for PostgreSQL
# Supports DATABASE_URL (Supabase/Render) or individual DB_* vars
_database_url = os.environ.get('DATABASE_URL', '').strip()
if _database_url:
    _parsed = urlparse(_database_url)
    if _parsed.scheme not in ('postgresql', 'postgres'):
        raise EnvironmentError(f'Unsupported DATABASE_URL scheme: {_parsed.scheme}')
    if not _parsed.hostname or not _parsed.path:
        raise EnvironmentError('Invalid DATABASE_URL: missing host or database name')

    _db_name = _parsed.path.lstrip('/')
    _query = parse_qs(_parsed.query)
    _sslmode = (
        os.environ.get('DATABASE_SSLMODE')
        or (_query.get('sslmode', [None])[0])
        or ('require' if 'supabase.co' in (_parsed.hostname or '') else None)
    )
    _db_options = {'client_encoding': 'UTF8'}
    if _sslmode:
        _db_options['sslmode'] = _sslmode

    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql',
            'NAME': unquote(_db_name),
            'USER': unquote(_parsed.username or ''),
            'PASSWORD': unquote(_parsed.password or ''),
            'HOST': _parsed.hostname,
            'PORT': str(_parsed.port or '5432'),
            'OPTIONS': _db_options,
            'CONN_MAX_AGE': int(os.environ.get('DB_CONN_MAX_AGE', '120')),
            'CONN_HEALTH_CHECKS': True,
        }
    }
else:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql',
            'NAME': os.environ.get('DB_NAME', 'db_book'),
            'USER': os.environ.get('DB_USER', 'bookuser'),
            'PASSWORD': _required_env('DB_PASSWORD'),
            'HOST': os.environ.get('DB_HOST', '127.0.0.1'),
            'PORT': os.environ.get('DB_PORT', '5432'),
            'OPTIONS': {'client_encoding': 'UTF8'},
            'CONN_MAX_AGE': int(os.environ.get('DB_CONN_MAX_AGE', '120')),
            'CONN_HEALTH_CHECKS': True,
        },
    }

# No database router needed - single unified database


# 密码验证
AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]


# 国际化配置 / Internationalization
# Default language for visitors/crawlers with no explicit preference. The public
# platform serves the francophone market (Congo), so French is the default and
# what search engines index — content is still authored in Chinese and
# translated to FR/EN. Users can switch language via the navbar; their choice is
# stored per-session and overrides this default.
LANGUAGE_CODE = 'fr'

LANGUAGES = [
    ('zh-hans', _('中文')),
    ('en', _('English')),
    ('fr', _('Français')),
]

LOCALE_PATHS = [
    os.path.join(BASE_DIR, 'locale'),
]

# django-modeltranslation — langue par défaut pour les champs traduits
MODELTRANSLATION_DEFAULT_LANGUAGE = 'zh-hans'
MODELTRANSLATION_LANGUAGES = ('zh-hans', 'en', 'fr')
MODELTRANSLATION_FALLBACK_LANGUAGES = {'default': ('zh-hans', 'en', 'fr')}

# translatebot — traduction automatique des .po via OpenRouter / LLM
OPENROUTER_API_KEY = os.environ.get('OPENROUTER_API_KEY', '')
TRANSLATEBOT_PROVIDER = 'litellm'
TRANSLATEBOT_MODEL = 'openrouter/openai/gpt-oss-20b:free'
TRANSLATEBOT_API_KEY = os.environ.get('OPENROUTER_API_KEY', '')
TRANSLATEBOT_SOURCE_LANGUAGE = 'zh-hans'

# Tawk.to Live Chat Widget
# Get these from your Tawk.to dashboard → Administration → Property Settings
TAWKTO_PROPERTY_ID = os.environ.get('TAWKTO_PROPERTY_ID', '')
TAWKTO_WIDGET_ID = os.environ.get('TAWKTO_WIDGET_ID', 'default')

TIME_ZONE = 'UTC'
USE_I18N = True
USE_L10N = True
USE_TZ = True


# Static files (CSS, JavaScript, Images)
STATIC_URL = '/static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')  # For collectstatic
STATICFILES_DIRS = [
    os.path.join(BASE_DIR, 'static'),
] if os.path.exists(os.path.join(BASE_DIR, 'static')) else []

# Media files configuration for file uploads (图片上传配置)
MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')

# Supabase Storage (S3 compatible) for static/media
_supabase_storage_enabled = os.environ.get('SUPABASE_STORAGE_ENABLED', 'False') == 'True'
_supabase_bucket = os.environ.get('SUPABASE_STORAGE_BUCKET', 'duno360_bucket')
_supabase_s3_key = os.environ.get('SUPABASE_S3_ACCESS_KEY_ID', '')
_supabase_s3_secret = os.environ.get('SUPABASE_S3_SECRET_ACCESS_KEY', '')
_supabase_s3_region = os.environ.get('SUPABASE_S3_REGION', 'us-east-1')

_supabase_project_url = os.environ.get('SUPABASE_PROJECT_URL', '').rstrip('/')
_supabase_storage_endpoint = os.environ.get('SUPABASE_S3_ENDPOINT', '').strip()
if not _supabase_storage_endpoint and _supabase_project_url:
    _project_host = urlparse(_supabase_project_url).netloc
    if _project_host:
        _project_ref = _project_host.split('.')[0]
        _supabase_storage_endpoint = f'https://{_project_ref}.storage.supabase.co/storage/v1/s3'

_supabase_public_base = os.environ.get('SUPABASE_STORAGE_PUBLIC_BASE_URL', '').strip()
if not _supabase_public_base and _supabase_project_url:
    _supabase_public_base = f'{_supabase_project_url}/storage/v1/object/public/{_supabase_bucket}'
_supabase_public_base = _supabase_public_base.rstrip('/')
_r2_public_domain = urlparse(_supabase_public_base).netloc if _supabase_public_base else ''

_supabase_ready = all([
    _supabase_storage_enabled,
    _supabase_storage_endpoint,
    _supabase_s3_key,
    _supabase_s3_secret,
])

if _supabase_ready:
    STORAGES = {
        'default': {
            'BACKEND': 'storages.backends.s3boto3.S3Boto3Storage',
            'OPTIONS': {
                'bucket_name': _supabase_bucket,
                'location': 'media',
                'access_key': _supabase_s3_key,
                'secret_key': _supabase_s3_secret,
                'region_name': _supabase_s3_region,
                'endpoint_url': _supabase_storage_endpoint,
                'custom_domain': _r2_public_domain or None,
                'default_acl': None,
                'querystring_auth': False,
                'file_overwrite': False,
                'addressing_style': 'path',
                'signature_version': 's3v4',
            },
        },
        'staticfiles': {
            'BACKEND': 'storages.backends.s3boto3.S3Boto3Storage',
            'OPTIONS': {
                'bucket_name': _supabase_bucket,
                'location': 'static',
                'access_key': _supabase_s3_key,
                'secret_key': _supabase_s3_secret,
                'region_name': _supabase_s3_region,
                'endpoint_url': _supabase_storage_endpoint,
                'custom_domain': _r2_public_domain or None,
                'default_acl': None,
                'querystring_auth': False,
                'file_overwrite': True,
                'addressing_style': 'path',
                'signature_version': 's3v4',
            },
        },
    }
    if _supabase_public_base:
        MEDIA_URL = f'{_supabase_public_base}/media/'
        STATIC_URL = f'{_supabase_public_base}/static/'
elif _whitenoise_available:
    # WhiteNoise compressed static files storage
    _use_manifest_storage = os.environ.get('STATICFILES_USE_MANIFEST', 'True') == 'True'
    STORAGES = {
        'default': {'BACKEND': 'django.core.files.storage.FileSystemStorage'},
        'staticfiles': {
            'BACKEND': (
                'whitenoise.storage.CompressedManifestStaticFilesStorage'
                if _use_manifest_storage
                else 'whitenoise.storage.CompressedStaticFilesStorage'
            )
        },
    }

# In development, serve static files locally so new JS/CSS is available
# without uploading to Supabase/R2 on every change.
if DEBUG:
    STATIC_URL = '/static/'

# File upload settings
FILE_UPLOAD_MAX_MEMORY_SIZE = 5242880   # 5 MB
# 500 MB in-memory buffer is a DoS risk; cap at 50 MB.
# Video uploads are chunked server-side and should not hit this limit.
DATA_UPLOAD_MAX_MEMORY_SIZE = 52428800  # 50 MB

# Image upload validation
ALLOWED_IMAGE_EXTENSIONS = ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp']
MAX_IMAGE_SIZE = 5 * 1024 * 1024  # 5MB

# Video upload validation
ALLOWED_VIDEO_EXTENSIONS = ['.mp4', '.webm', '.ogg', '.mov', '.avi', '.mkv']
MAX_VIDEO_SIZE = 500 * 1024 * 1024  # 500MB

# Email configuration (Zoho Mail SMTP)
EMAIL_HOST_USER = os.environ.get('EMAIL_HOST_USER', '')
EMAIL_HOST_PASSWORD = os.environ.get('EMAIL_HOST_PASSWORD', '')
EMAIL_HOST = os.environ.get('EMAIL_HOST', 'smtp.zoho.com')
EMAIL_PORT = int(os.environ.get('EMAIL_PORT', '465'))
EMAIL_USE_SSL = os.environ.get('EMAIL_USE_SSL', 'True') == 'True'
EMAIL_USE_TLS = os.environ.get('EMAIL_USE_TLS', 'False') == 'True'

# Fall back to console backend when SMTP credentials are missing (local dev)
if EMAIL_HOST_USER and EMAIL_HOST_PASSWORD:
    EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
else:
    EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

_PLATFORM_EMAIL = os.environ.get('CONTACT_EMAIL', 'admin@duno360.com')
DEFAULT_FROM_EMAIL = os.environ.get(
    'DEFAULT_FROM_EMAIL',
    f'DUNO 360 <{_PLATFORM_EMAIL}>',
)
CONTACT_EMAIL = _PLATFORM_EMAIL

# Platform phone (calls + WhatsApp)
PLATFORM_PHONE = os.environ.get('PLATFORM_PHONE', '+242066790386')

# Official social media (override via .env if needed)
SOCIAL_FACEBOOK_URL = os.environ.get(
    'SOCIAL_FACEBOOK_URL',
    'https://www.facebook.com/share/1BSHYjDZtN/?mibextid=wwXIfr',
)
SOCIAL_INSTAGRAM_URL = os.environ.get(
    'SOCIAL_INSTAGRAM_URL',
    'https://www.instagram.com/duno_360?igsh=ZTFiNTMyYXFndmM0&utm_source=qr',
)
SOCIAL_TIKTOK_URL = os.environ.get(
    'SOCIAL_TIKTOK_URL',
    'https://www.tiktok.com/@duno.360?_r=1&_t=ZS-974QAexSzBZ',
)
SOCIAL_YOUTUBE_URL = os.environ.get(
    'SOCIAL_YOUTUBE_URL',
    'https://www.youtube.com/@DUNO360',
)

# Security settings for production
if not DEBUG:
    _force_https = os.environ.get('FORCE_HTTPS', 'True') == 'True'

    # SSL/HTTPS Settings
    SECURE_SSL_REDIRECT = _force_https
    SESSION_COOKIE_SECURE = _force_https
    CSRF_COOKIE_SECURE = _force_https
    
    # Security Headers
    SECURE_BROWSER_XSS_FILTER = True
    SECURE_CONTENT_TYPE_NOSNIFF = True
    X_FRAME_OPTIONS = 'DENY'
    if _force_https:
        SECURE_HSTS_SECONDS = 31536000  # 1 year
        SECURE_HSTS_INCLUDE_SUBDOMAINS = True
        SECURE_HSTS_PRELOAD = True
    
    # Additional security
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
    SECURE_REFERRER_POLICY = 'strict-origin-when-cross-origin'
    SECURE_CROSS_ORIGIN_OPENER_POLICY = 'same-origin'
    USE_X_FORWARDED_HOST = True

# Session security — expire sessions after 1 hour of inactivity and on browser close
SESSION_COOKIE_AGE = 3600          # 1 hour (seconds)
SESSION_EXPIRE_AT_BROWSER_CLOSE = True
SESSION_COOKIE_HTTPONLY = True     # JS cannot read the session cookie
SESSION_SAVE_EVERY_REQUEST = True  # Slide the expiry window on each request
SESSION_COOKIE_SAMESITE = os.environ.get('SESSION_COOKIE_SAMESITE', 'Lax')
CSRF_COOKIE_SAMESITE = os.environ.get('CSRF_COOKIE_SAMESITE', 'Lax')

# Rosetta translation UI — restrict access to admin sessions only
ROSETTA_REQUIRES_AUTH = True
ROSETTA_LOGIN_URL = '/manager/login/'

# CSRF trusted origins (required for Django 4.x with HTTPS)
CSRF_TRUSTED_ORIGINS = os.environ.get(
    'CSRF_TRUSTED_ORIGINS',
    'https://duno360.com,https://www.duno360.com'
).split(',')

# ============================================================
# MTN MoMo Sandbox Configuration
# ============================================================
MTN_MOMO_BASE_URL = os.environ.get(
    'MTN_MOMO_BASE_URL', 'https://sandbox.momodeveloper.mtn.com')
MTN_MOMO_SUBSCRIPTION_KEY = os.environ.get('MTN_MOMO_SUBSCRIPTION_KEY', '')
MTN_MOMO_API_USER = os.environ.get('MTN_MOMO_API_USER', '')
MTN_MOMO_API_KEY = os.environ.get('MTN_MOMO_API_KEY', '')
MTN_MOMO_ENVIRONMENT = os.environ.get('MTN_MOMO_ENVIRONMENT', 'sandbox')
MTN_MOMO_CURRENCY = os.environ.get('MTN_MOMO_CURRENCY', 'EUR')
MTN_MOMO_CALLBACK_URL = os.environ.get('MTN_MOMO_CALLBACK_URL', '')

# ============================================================
# Airtel Money Sandbox Configuration
# ============================================================
AIRTEL_MONEY_BASE_URL = os.environ.get(
    'AIRTEL_MONEY_BASE_URL', 'https://openapiuat.airtel.africa')
AIRTEL_MONEY_CLIENT_ID = os.environ.get('AIRTEL_MONEY_CLIENT_ID', '')
AIRTEL_MONEY_CLIENT_SECRET = os.environ.get('AIRTEL_MONEY_CLIENT_SECRET', '')
AIRTEL_MONEY_COUNTRY = os.environ.get('AIRTEL_MONEY_COUNTRY', 'CG')
AIRTEL_MONEY_CURRENCY = os.environ.get('AIRTEL_MONEY_CURRENCY', 'XAF')
AIRTEL_MONEY_CALLBACK_URL = os.environ.get('AIRTEL_MONEY_CALLBACK_URL', '')

# ============================================================
# KKiaPay Payment Aggregator — West Africa
# ============================================================
KKIAPAY_PUBLIC_KEY     = os.environ.get('KKIAPAY_PUBLIC_KEY',     '')
KKIAPAY_PRIVATE_KEY    = os.environ.get('KKIAPAY_PRIVATE_KEY',    '')
KKIAPAY_SECRET         = os.environ.get('KKIAPAY_SECRET',         '')
KKIAPAY_SANDBOX        = os.environ.get('KKIAPAY_SANDBOX',        'True') == 'True'
KKIAPAY_WEBHOOK_SECRET = os.environ.get('KKIAPAY_WEBHOOK_SECRET', '')

# ============================================================
# PawaPay — Central Africa mobile money
# ============================================================
PAWAPAY_API_TOKEN = os.environ.get('PAWAPAY_API_TOKEN', '')
PAWAPAY_BASE_URL = os.environ.get(
    'PAWAPAY_BASE_URL', 'https://api.sandbox.pawapay.io')
PAWAPAY_SANDBOX = os.environ.get('PAWAPAY_SANDBOX', 'True') == 'True'
PAWAPAY_ENABLED = os.environ.get('PAWAPAY_ENABLED', 'True') == 'True'
PAWAPAY_CURRENCY = os.environ.get('PAWAPAY_CURRENCY', 'XAF')
PAWAPAY_CALLBACK_DEPOSITS = os.environ.get('PAWAPAY_CALLBACK_DEPOSITS', '')
PAWAPAY_CALLBACK_PAYOUTS = os.environ.get('PAWAPAY_CALLBACK_PAYOUTS', '')
PAWAPAY_CALLBACK_REFUNDS = os.environ.get('PAWAPAY_CALLBACK_REFUNDS', '')

# Twilio Verify — SMS OTP for signup (optional; set all three vars to enable)
TWILIO_ACCOUNT_SID = os.environ.get('TWILIO_ACCOUNT_SID', '')
TWILIO_AUTH_TOKEN = os.environ.get('TWILIO_AUTH_TOKEN', '')
TWILIO_VERIFY_SERVICE_SID = os.environ.get('TWILIO_VERIFY_SERVICE_SID', '').strip()
TWILIO_VERIFY_ENABLED = bool(
    TWILIO_ACCOUNT_SID
    and TWILIO_AUTH_TOKEN
    and TWILIO_VERIFY_SERVICE_SID.startswith('VA')
)

# ============================================================
# Cache (live product presence; use Redis in production)
# ============================================================
def _build_cache_settings():
    """Pick Redis when reachable; fall back to LocMem in DEBUG for local dev."""
    redis_url = os.environ.get('REDIS_URL', '').strip()
    locmem = {
        'default': {
            'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
            'LOCATION': 'duno360-default',
        }
    }
    if not redis_url:
        return locmem

    try:
        import redis
    except ImportError:
        warnings.warn(
            'REDIS_URL is set but the redis package is not installed; using LocMemCache. '
            'Run: pip install "redis>=5.0.0"',
            stacklevel=1,
        )
        return locmem

    try:
        client = redis.from_url(redis_url, socket_connect_timeout=1.5)
        client.ping()
    except Exception as exc:
        if DEBUG:
            warnings.warn(
                f'Redis unavailable at {redis_url} ({exc}). '
                'Using LocMemCache. Start Redis with .\\scripts\\start-redis.ps1 '
                'or remove REDIS_URL from .env for offline dev.',
                stacklevel=1,
            )
            return locmem
        raise ImproperlyConfigured(
            f'REDIS_URL is set but Redis is not reachable at {redis_url}: {exc}'
        ) from exc

    return {
        'default': {
            'BACKEND': 'django.core.cache.backends.redis.RedisCache',
            'LOCATION': redis_url,
        }
    }


CACHES = _build_cache_settings()

# ============================================================
# ngrok Configuration (auto-tunnel for development callbacks)
# ============================================================
NGROK_AUTH_TOKEN = os.environ.get('NGROK_AUTH_TOKEN', '')
NGROK_ENABLED = os.environ.get('NGROK_ENABLED', 'False') == 'True'
NGROK_PUBLIC_URL = os.environ.get('NGROK_PUBLIC_URL', '').rstrip('/')

if NGROK_PUBLIC_URL:
    _ngrok_parsed = urlparse(NGROK_PUBLIC_URL)
    _ngrok_host = _ngrok_parsed.netloc
    if _ngrok_host and _ngrok_host not in ALLOWED_HOSTS:
        ALLOWED_HOSTS.append(_ngrok_host)
    if NGROK_PUBLIC_URL not in CSRF_TRUSTED_ORIGINS:
        CSRF_TRUSTED_ORIGINS.append(NGROK_PUBLIC_URL)
    _ngrok_base = NGROK_PUBLIC_URL + '/manager'
    if not PAWAPAY_CALLBACK_DEPOSITS:
        PAWAPAY_CALLBACK_DEPOSITS = f'{_ngrok_base}/api/payment/pawapay/callback/deposits/'
    if not PAWAPAY_CALLBACK_PAYOUTS:
        PAWAPAY_CALLBACK_PAYOUTS = f'{_ngrok_base}/api/payment/pawapay/callback/payouts/'
    if not PAWAPAY_CALLBACK_REFUNDS:
        PAWAPAY_CALLBACK_REFUNDS = f'{_ngrok_base}/api/payment/pawapay/callback/refunds/'

# Logging configuration for payment callbacks
os.makedirs(os.path.join(BASE_DIR, 'logs'), exist_ok=True)
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '[{asctime}] {levelname} {name}: {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
        'payment_file': {
            'class': 'logging.FileHandler',
            'filename': os.path.join(BASE_DIR, 'logs', 'payments.log'),
            'formatter': 'verbose',
        },
    },
    'loggers': {
        'manager.payments': {
            'handlers': ['console', 'payment_file'],
            'level': 'INFO',
            'propagate': False,
        },
    },
}