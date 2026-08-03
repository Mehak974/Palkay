"""
Palkay Production Settings
---------------------------
Extends base settings.py with:
  - Full security hardening
  - Performance optimisations (caching, query tuning, compression)
  - Cloudflare integration
  - PostgreSQL + Redis configuration

Usage:
  DJANGO_SETTINGS_MODULE=palkay.settings_production gunicorn palkay.wsgi
  or set in .env: DJANGO_SETTINGS_MODULE=palkay.settings_production
"""

from .settings import *  # noqa: F401, F403
from decouple import config, Csv

# ── CORE ────────────────────────────────────────────────────────────────────
DEBUG = False
SECRET_KEY = config('SECRET_KEY')
ALLOWED_HOSTS = config('ALLOWED_HOSTS', cast=Csv())

from django.core.exceptions import ImproperlyConfigured
if not ALLOWED_HOSTS or any(host in ALLOWED_HOSTS for host in ['localhost', '127.0.0.1', '*']):
    raise ImproperlyConfigured("ALLOWED_HOSTS must be explicitly set to real domains in production.")

# ── DATABASE (PostgreSQL) ────────────────────────────────────────────────────
import dj_database_url  # noqa: E402

DATABASES = {
    'default': dj_database_url.parse(
        config('DATABASE_URL', default=f'sqlite:///{BASE_DIR / "db.sqlite3"}'),
        conn_max_age=600,           # persistent connections, 10 min
        conn_health_checks=True,
    )
}

# PgBouncer-safe: disable server-side cursors when using a pooler
DISABLE_SERVER_SIDE_CURSORS = config('DISABLE_SERVER_SIDE_CURSORS', default=False, cast=bool)

# ── CACHE & SESSIONS ─────────────────────────────────────────────────────────
REDIS_URL = config('REDIS_URL', default='')

if REDIS_URL:
    CACHES = {
        'default': {
            'BACKEND': 'django_redis.cache.RedisCache',
            'LOCATION': REDIS_URL,
            'KEY_PREFIX': 'palkay',
            'TIMEOUT': 300,
            'OPTIONS': {
                'CLIENT_CLASS': 'django_redis.client.DefaultClient',
                'SOCKET_CONNECT_TIMEOUT': 5,
                'SOCKET_TIMEOUT': 5,
                'RETRY_ON_TIMEOUT': True,
                'MAX_CONNECTIONS': 20,
                'CONNECTION_POOL_KWARGS': {'max_connections': 20},
            },
        }
    }
    SESSION_ENGINE = 'django.contrib.sessions.backends.cache'
    SESSION_CACHE_ALIAS = 'default'
else:
    CACHES = {
        'default': {
            'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
            'LOCATION': 'palkay-local-cache',
        }
    }
    SESSION_ENGINE = 'django.contrib.sessions.backends.db'

# ── SECURITY MIDDLEWARE ──────────────────────────────────────────────────────
MIDDLEWARE = [
    'palkay.security.CloudflareMiddleware',       # Must be first
    'palkay.security.RequestValidationMiddleware', # Block bad requests early
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'palkay.security.RateLimitMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'palkay.security.SecurityHeadersMiddleware',  # Last — adds headers to every response
    'cart.middleware.CartMiddleware',
]

# ── CLOUDFLARE ───────────────────────────────────────────────────────────────
TRUST_CLOUDFLARE = True
CLOUDFLARE_ONLY = config('CLOUDFLARE_ONLY', default=False, cast=bool)

# Tell Django the real scheme comes from CF
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
USE_X_FORWARDED_HOST = True
USE_X_FORWARDED_PORT = True

# ── HTTPS / HSTS ─────────────────────────────────────────────────────────────
SECURE_SSL_REDIRECT = True
SECURE_HSTS_SECONDS = 31536000          # 1 year
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = 'DENY'
SECURE_REFERRER_POLICY = 'strict-origin-when-cross-origin'

# ── COOKIES ───────────────────────────────────────────────────────────────────
SESSION_COOKIE_SECURE = True
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = 'Lax'
SESSION_COOKIE_NAME = 'plk_session'      # non-default name (obscures framework)
SESSION_COOKIE_AGE = 60 * 60 * 24 * 30  # 30 days
SESSION_EXPIRE_AT_BROWSER_CLOSE = True

CSRF_COOKIE_SECURE = True
CSRF_COOKIE_HTTPONLY = True
CSRF_COOKIE_SAMESITE = 'Lax'
CSRF_COOKIE_NAME = 'plk_csrf'           # non-default name

# ── STATIC FILES ─────────────────────────────────────────────────────────────
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'
STATIC_ROOT = BASE_DIR / 'staticfiles'   # noqa: F405

# WhiteNoise config
WHITENOISE_MAX_AGE = 31536000            # 1 year (files are content-hashed)
WHITENOISE_SKIP_COMPRESS_EXTENSIONS = [
    'jpg', 'jpeg', 'png', 'gif', 'webp', 'zip', 'gz', 'tgz', 'bz2',
    'tbz', 'xz', 'br', 'swf', 'flv', 'woff', 'woff2',
]

# ── MEDIA FILES (S3) ──────────────────────────────────────────────────────────
USE_S3 = config('USE_S3', default=False, cast=bool)
if USE_S3:
    AWS_ACCESS_KEY_ID = config('AWS_ACCESS_KEY_ID')
    AWS_SECRET_ACCESS_KEY = config('AWS_SECRET_ACCESS_KEY')
    AWS_STORAGE_BUCKET_NAME = config('AWS_STORAGE_BUCKET_NAME')
    AWS_S3_REGION_NAME = config('AWS_S3_REGION_NAME', default='us-east-1')
    AWS_S3_CUSTOM_DOMAIN = config(
        'AWS_S3_CUSTOM_DOMAIN',
        default=f'{AWS_STORAGE_BUCKET_NAME}.s3.amazonaws.com'
    )
    AWS_DEFAULT_ACL = 'public-read'
    AWS_S3_OBJECT_PARAMETERS = {
        'CacheControl': 'max-age=86400, public',  # 1 day CDN cache for media
    }
    AWS_S3_FILE_OVERWRITE = False
    AWS_QUERYSTRING_AUTH = False
    DEFAULT_FILE_STORAGE = 'storages.backends.s3boto3.S3Boto3Storage'
    MEDIA_URL = f'https://{AWS_S3_CUSTOM_DOMAIN}/media/'

# ── RATE LIMITING CONFIG ──────────────────────────────────────────────────────
RATE_LIMITS = {
    # name: (url_pattern, max_requests, window_seconds, block_seconds)
    'auth':     (r'^/account/(login|register)/', 10,  300, 900),
    'checkout': (r'^/checkout/',                 20,   60, 300),
    'cart':     (r'^/cart/add/',                 60,   60, 120),
    'api':      (r'^/api/',                      100,  60, 120),
    'global':   (r'.*',                          200,  60,  60),
}

# ── EMAIL ─────────────────────────────────────────────────────────────────────
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = config('EMAIL_HOST', default='smtp.gmail.com')
EMAIL_PORT = config('EMAIL_PORT', default=587, cast=int)
EMAIL_USE_TLS = True
EMAIL_HOST_USER = config('EMAIL_HOST_USER', default='')
EMAIL_HOST_PASSWORD = config('EMAIL_HOST_PASSWORD', default='')

if not EMAIL_HOST_USER or not EMAIL_HOST_PASSWORD:
    import warnings
    warnings.warn("EMAIL_HOST_USER/PASSWORD not set — falling back to console email backend.")
    EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
DEFAULT_FROM_EMAIL = config('DEFAULT_FROM_EMAIL', default='Palkay <noreply@palkay.com>')
SERVER_EMAIL = config('SERVER_EMAIL', default='errors@palkay.com')

# ── LOGGING ───────────────────────────────────────────────────────────────────
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '[{asctime}] {levelname} {name} {process:d} {thread:d} {message}',
            'style': '{',
        },
        'simple': {
            'format': '[{asctime}] {levelname} {message}',
            'style': '{',
        },
    },
    'filters': {
        'require_debug_false': {
            '()': 'django.utils.log.RequireDebugFalse',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'simple',
        },
        'security_file': {
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': BASE_DIR / 'logs' / 'security.log',  # noqa: F405
            'maxBytes': 10 * 1024 * 1024,  # 10MB
            'backupCount': 5,
            'formatter': 'verbose',
        },
        'mail_admins': {
            'level': 'ERROR',
            'class': 'django.utils.log.AdminEmailHandler',
            'filters': ['require_debug_false'],
        },
    },
    'loggers': {
        'django': {
            'handlers': ['console'],
            'level': 'WARNING',
            'propagate': True,
        },
        'django.request': {
            'handlers': ['console', 'mail_admins'],
            'level': 'ERROR',
            'propagate': False,
        },
        'palkay.security': {
            'handlers': ['console', 'security_file'],
            'level': 'INFO',
            'propagate': False,
        },
    },
}

# ── PERFORMANCE: TEMPLATE CACHING ────────────────────────────────────────────
TEMPLATES[0]['OPTIONS']['loaders'] = [  # noqa: F405
    ('django.template.loaders.cached.Loader', [
        'django.template.loaders.filesystem.Loader',
        'django.template.loaders.app_directories.Loader',
    ]),
]
# Remove APP_DIRS when using cached loader
TEMPLATES[0].pop('APP_DIRS', None)  # noqa: F405

# ── ADMIN HARDENING ──────────────────────────────────────────────────────────
ADMIN_URL = config('ADMIN_URL', default='admin/')  # Change to random slug in prod
