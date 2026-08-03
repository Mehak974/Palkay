"""
Palkay Django Settings
Production-ready configuration with environment variable support.
"""

import os
from pathlib import Path
from decouple import config, Csv

BASE_DIR = Path(__file__).resolve().parent.parent

# ─── SECURITY ──────────────────────────────────────────────────
SECRET_KEY = config('SECRET_KEY', default='django-insecure-change-me-in-production-do-not-use-this-key')
DEBUG = config('DEBUG', default=False, cast=bool)
ALLOWED_HOSTS = config('ALLOWED_HOSTS', default='localhost,127.0.0.1', cast=Csv())
SECURE_HSTS_PRELOAD = config('SECURE_HSTS_PRELOAD', default=True, cast=bool)

# ─── APPLICATIONS ──────────────────────────────────────────────
INSTALLED_APPS = [
    'unfold.contrib.forms',
    'unfold',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.humanize',
    'django.contrib.sitemaps',
    # Third-party
    'crispy_forms',
    'crispy_bootstrap5',
    # Local apps
    'users',
    'catalog',
    'cart',
    'orders',
    'pages',
    'blog',
    'support',
    'analytics',
    'experiments',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'cart.middleware.CartMiddleware',
]

ROOT_URLCONF = 'palkay.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'cart.context_processors.cart_context',
                'pages.context_processors.site_context',
            ],
        },
    },
]

WSGI_APPLICATION = 'palkay.wsgi.application'

# ─── DATABASE ──────────────────────────────────────────────────
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

# For production PostgreSQL, set DATABASE_URL in .env:
# DATABASE_URL=postgres://user:pass@host:5432/palkay
if config('DATABASE_URL', default=None):
    import dj_database_url
    DATABASES['default'] = dj_database_url.parse(config('DATABASE_URL'))

# ─── AUTHENTICATION ─────────────────────────────────────────────
AUTH_USER_MODEL = 'users.User'
LOGIN_URL = '/account/login/'
LOGIN_REDIRECT_URL = '/account/'
LOGOUT_REDIRECT_URL = '/'

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator', 'OPTIONS': {'min_length': 8}},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

# Argon2 password hashing
PASSWORD_HASHERS = [
    'django.contrib.auth.hashers.Argon2PasswordHasher',
    'django.contrib.auth.hashers.PBKDF2PasswordHasher',
]

# ─── INTERNATIONALISATION ───────────────────────────────────────
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'America/Chicago'
USE_I18N = True
USE_TZ = True

# ─── STATIC & MEDIA ─────────────────────────────────────────────
STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_DIRS = [BASE_DIR / 'static']
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# ─── CRISPY FORMS ───────────────────────────────────────────────
CRISPY_ALLOWED_TEMPLATE_PACKS = 'bootstrap5'
CRISPY_TEMPLATE_PACK = 'bootstrap5'

# ─── SESSIONS ────────────────────────────────────────────────────
SESSION_ENGINE = 'django.contrib.sessions.backends.db'
SESSION_COOKIE_AGE = 60 * 60 * 24 * 30  # 30 days
SESSION_SAVE_EVERY_REQUEST = False

# ─── EMAIL ───────────────────────────────────────────────────────
EMAIL_BACKEND = config('EMAIL_BACKEND', default='django.core.mail.backends.console.EmailBackend')
EMAIL_HOST = config('EMAIL_HOST', default='smtp.gmail.com')
EMAIL_PORT = config('EMAIL_PORT', default=587, cast=int)
EMAIL_USE_TLS = True
EMAIL_HOST_USER = config('EMAIL_HOST_USER', default='')
EMAIL_HOST_PASSWORD = config('EMAIL_HOST_PASSWORD', default='')
DEFAULT_FROM_EMAIL = config('DEFAULT_FROM_EMAIL', default='Palkay <noreply@palkay.com>')

# ─── BUSINESS RULES ──────────────────────────────────────────────
FREE_SHIPPING_THRESHOLD = 200   # USD — orders over $200 get free shipping
ORDER_CANCEL_WINDOW_HOURS = 2   # hours after order creation user can self-cancel
CART_ITEM_MAX_QTY = 100
CART_EXPIRY_DAYS = 30

# ─── S3 / MEDIA STORAGE (optional) ──────────────────────────────
USE_S3 = config('USE_S3', default=False, cast=bool)
if USE_S3:
    AWS_ACCESS_KEY_ID = config('AWS_ACCESS_KEY_ID')
    AWS_SECRET_ACCESS_KEY = config('AWS_SECRET_ACCESS_KEY')
    AWS_STORAGE_BUCKET_NAME = config('AWS_STORAGE_BUCKET_NAME')
    AWS_S3_REGION_NAME = config('AWS_S3_REGION_NAME', default='us-east-1')
    AWS_S3_CUSTOM_DOMAIN = f'{AWS_STORAGE_BUCKET_NAME}.s3.amazonaws.com'
    AWS_DEFAULT_ACL = 'public-read'
    DEFAULT_FILE_STORAGE = 'storages.backends.s3boto3.S3Boto3Storage'
    MEDIA_URL = f'https://{AWS_S3_CUSTOM_DOMAIN}/media/'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# ─── SECURITY HEADERS (production) ───────────────────────────────
if not DEBUG:
    SECURE_SSL_REDIRECT = True
    SECURE_HSTS_SECONDS = 31536000
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_BROWSER_XSS_FILTER = True
    X_FRAME_OPTIONS = 'DENY'
    SECURE_CONTENT_TYPE_NOSNIFF = True
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True

# CPython 3.14 compatibility monkey-patch for Django BaseContext.__copy__
try:
    import copy
    from django.template.context import BaseContext
    
    def _patched_copy(self):
        duplicate = BaseContext()
        duplicate.__class__ = self.__class__
        duplicate.__dict__ = copy.copy(self.__dict__)
        duplicate.dicts = self.dicts[:]
        return duplicate
        
    BaseContext.__copy__ = _patched_copy
except (ImportError, AttributeError):
    pass

# ─── UNFOLD ADMIN SETTINGS ──────────────────────────────────────
UNFOLD = {
    "SITE_TITLE": "Palkay Admin",
    "SITE_HEADER": "Palkay",
    "SITE_URL": "/",
    "SIDEBAR": {
        "show_search": True,
        "show_all_applications": True,
        "navigation": [
            {
                "title": "Store Management",
                "separator": True,
                "items": [
                    {
                        "title": "Orders",
                        "icon": "shopping_cart",
                        "link": "/admin/orders/order/",
                    },
                    {
                        "title": "Products",
                        "icon": "inventory_2",
                        "link": "/admin/catalog/product/",
                    },
                    {
                        "title": "Categories",
                        "icon": "category",
                        "link": "/admin/catalog/category/",
                    },
                    {
                        "title": "Brands",
                        "icon": "branding_watermark",
                        "link": "/admin/catalog/brand/",
                    },
                    {
                        "title": "Reviews",
                        "icon": "star",
                        "link": "/admin/catalog/review/",
                    },
                    {
                        "title": "Coupons",
                        "icon": "local_offer",
                        "link": "/admin/orders/coupon/",
                    },
                ],
            },
            {
                "title": "Content & Blog",
                "separator": True,
                "items": [
                    {
                        "title": "Blog Posts",
                        "icon": "article",
                        "link": "/admin/blog/post/",
                    },
                    {
                        "title": "Pages",
                        "icon": "description",
                        "link": "/admin/pages/page/",
                    },
                ],
            },
            {
                "title": "Customers",
                "separator": True,
                "items": [
                    {
                        "title": "Users",
                        "icon": "people",
                        "link": "/admin/users/user/",
                    },
                    {
                        "title": "Support Tickets",
                        "icon": "support_agent",
                        "link": "/admin/support/ticket/",
                    },
                ],
            },
        ],
    },
}
