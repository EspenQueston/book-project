import os
from pathlib import Path
from urllib.parse import urlparse, unquote, parse_qs
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
    'ALLOWED_HOSTS', 'scholarquest.tech,www.scholarquest.tech,localhost,127.0.0.1'
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
LANGUAGE_CODE = 'zh-hans'

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
# Provider must be 'litellm'; model uses 'openrouter/<model>' prefix for litellm routing
# Primary: meta-llama/llama-4-scout:free (more reliable than gemma on free tier)
# Fallback: openrouter/google/gemma-4-31b-it:free
OPENROUTER_API_KEY = os.environ.get('OPENROUTER_API_KEY', '')
TRANSLATEBOT_PROVIDER = 'litellm'
TRANSLATEBOT_MODEL = 'openrouter/openai/gpt-oss-20b:free'
TRANSLATEBOT_API_KEY = os.environ.get('OPENROUTER_API_KEY', '')
TRANSLATEBOT_SOURCE_LANGUAGE = 'zh-hans'

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

# WhiteNoise compressed static files storage
if _whitenoise_available:
    STORAGES = {
        'default': {'BACKEND': 'django.core.files.storage.FileSystemStorage'},
        'staticfiles': {'BACKEND': 'whitenoise.storage.CompressedManifestStaticFilesStorage'},
    }

# Media files configuration for file uploads (图片上传配置)
MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')

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

# Email configuration (ProfitexB2B SMTP with SSL)
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = 'mail.profitexb2b.com'
EMAIL_PORT = 465
EMAIL_USE_TLS = False
EMAIL_USE_SSL = True
EMAIL_HOST_USER = os.environ.get('EMAIL_HOST_USER', '')
EMAIL_HOST_PASSWORD = os.environ.get('EMAIL_HOST_PASSWORD', '')
DEFAULT_FROM_EMAIL = 'DUNO 360 <espen@profitexb2b.com>'
CONTACT_EMAIL = 'espen@profitexb2b.com'

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
    'https://scholarquest.tech,https://www.scholarquest.tech'
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
# ngrok Configuration (auto-tunnel for development callbacks)
# ============================================================
NGROK_AUTH_TOKEN = os.environ.get('NGROK_AUTH_TOKEN', '')
NGROK_ENABLED = os.environ.get('NGROK_ENABLED', 'False') == 'True'

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