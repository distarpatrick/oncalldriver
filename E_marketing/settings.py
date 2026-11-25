"""
Django settings for the On Call Driver marketplace.

All secrets and environment-specific values come from environment variables
(see .env.example).  Safe development defaults are used when DEBUG is on.
"""
import os
from pathlib import Path

import dj_database_url

BASE_DIR = Path(__file__).resolve().parent.parent


def env(name, default=""):
    return os.environ.get(name, default)


def env_bool(name, default=False):
    value = os.environ.get(name)
    if value is None:
        return default
    return value.strip().lower() in ("1", "true", "yes", "on")


def env_list(name, default=""):
    return [item.strip() for item in env(name, default).split(",") if item.strip()]


# ─── Core ────────────────────────────────────────────────────────────────────
DEBUG = env_bool("DJANGO_DEBUG", default=not bool(env("RENDER")))

SECRET_KEY = env("DJANGO_SECRET_KEY")
if not SECRET_KEY:
    if not DEBUG:
        raise RuntimeError("DJANGO_SECRET_KEY must be set in production.")
    SECRET_KEY = "dev-only-insecure-key-change-me"

ALLOWED_HOSTS = env_list("DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1,[::1]")
RENDER_EXTERNAL_HOSTNAME = env("RENDER_EXTERNAL_HOSTNAME")
if RENDER_EXTERNAL_HOSTNAME:
    ALLOWED_HOSTS.append(RENDER_EXTERNAL_HOSTNAME)

CSRF_TRUSTED_ORIGINS = env_list("DJANGO_CSRF_TRUSTED_ORIGINS")
if RENDER_EXTERNAL_HOSTNAME:
    CSRF_TRUSTED_ORIGINS.append(f"https://{RENDER_EXTERNAL_HOSTNAME}")

# Obscure admin path (set DJANGO_ADMIN_URL, e.g. "control-7f3a/")
ADMIN_URL = env("DJANGO_ADMIN_URL", "admin/").strip("/") + "/"


# ─── Applications ────────────────────────────────────────────────────────────
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'whitenoise.runserver_nostatic',
    'django.contrib.staticfiles',
    "homepage",
    "user",
    "booking",
    "payment",
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
    'E_marketing.security.SecurityHeadersMiddleware',
    'E_marketing.security.LoginRateLimitMiddleware',
]

ROOT_URLCONF = 'E_marketing.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'homepage.context_processors.site_branding',
            ],
        },
    },
]

WSGI_APPLICATION = 'E_marketing.wsgi.application'


# ─── Database ────────────────────────────────────────────────────────────────
# Uses DATABASE_URL (PostgreSQL on Render) and falls back to local SQLite.
DATABASES = {
    'default': dj_database_url.config(
        default=f"sqlite:///{BASE_DIR / 'db.sqlite3'}",
        conn_max_age=600,
        conn_health_checks=True,
    )
}

CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        "LOCATION": "oncall-default",
    }
}


# ─── Authentication & passwords ──────────────────────────────────────────────
AUTH_USER_MODEL = 'homepage.CustomUser'

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator', 'OPTIONS': {'min_length': 8}},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

LOGIN_URL = 'homepage:auth'
LOGIN_REDIRECT_URL = 'homepage:dashboard'
LOGOUT_REDIRECT_URL = 'homepage:auth'

# Brute-force protection on the sign-in form (see E_marketing/security.py)
LOGIN_RATE_LIMIT_ATTEMPTS = int(env("LOGIN_RATE_LIMIT_ATTEMPTS", "6"))
LOGIN_RATE_LIMIT_WINDOW = int(env("LOGIN_RATE_LIMIT_WINDOW", "900"))  # seconds


# ─── Security hardening ──────────────────────────────────────────────────────
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = 'Lax'
SESSION_COOKIE_AGE = 60 * 60 * 12          # 12 hours
CSRF_COOKIE_SAMESITE = 'Lax'
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = 'strict-origin-when-cross-origin'
SECURE_CROSS_ORIGIN_OPENER_POLICY = 'same-origin'
X_FRAME_OPTIONS = 'DENY'

if not DEBUG:
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
    SECURE_SSL_REDIRECT = env_bool("DJANGO_SECURE_SSL_REDIRECT", True)
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_HSTS_SECONDS = int(env("DJANGO_HSTS_SECONDS", "31536000"))
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True

# Upload limits (receipts, car photos, videos)
DATA_UPLOAD_MAX_MEMORY_SIZE = 10 * 1024 * 1024
FILE_UPLOAD_MAX_MEMORY_SIZE = 5 * 1024 * 1024
DATA_UPLOAD_MAX_NUMBER_FIELDS = 2000
FILE_UPLOAD_PERMISSIONS = 0o644


# ─── Internationalisation ────────────────────────────────────────────────────
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'Africa/Kigali'
USE_I18N = True
USE_TZ = True


# ─── Static & media ──────────────────────────────────────────────────────────
STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_DIRS = [BASE_DIR / 'static']
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage"
        if not DEBUG else "django.contrib.staticfiles.storage.StaticFilesStorage"
    },
}

MEDIA_URL = '/media/'
MEDIA_ROOT = Path(env("DJANGO_MEDIA_ROOT", str(BASE_DIR / 'media')))
SERVE_MEDIA = env_bool("DJANGO_SERVE_MEDIA", True)

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'


# ─── Email ───────────────────────────────────────────────────────────────────
EMAIL_BACKEND = env("DJANGO_EMAIL_BACKEND", "django.core.mail.backends.console.EmailBackend")
EMAIL_HOST = env("EMAIL_HOST")
EMAIL_PORT = int(env("EMAIL_PORT", "587"))
EMAIL_HOST_USER = env("EMAIL_HOST_USER")
EMAIL_HOST_PASSWORD = env("EMAIL_HOST_PASSWORD")
EMAIL_USE_TLS = env_bool("EMAIL_USE_TLS", True)
DEFAULT_FROM_EMAIL = env("DEFAULT_FROM_EMAIL", "On Call Driver <no-reply@oncalldriver.rw>")


# ─── Payments (MTN MoMo, Airtel Money, bank transfer) ────────────────────────
# Leave the keys empty to run in "manual" mode: customers pay with the
# MoMoPay code / USSD or bank transfer and upload proof for staff to verify.
SITE_BASE_URL = env("SITE_BASE_URL", f"https://{RENDER_EXTERNAL_HOSTNAME}" if RENDER_EXTERNAL_HOSTNAME else "").rstrip("/")
PAYMENT_CALLBACK_TOKEN = env("PAYMENT_CALLBACK_TOKEN")

PAYMENTS = {
    "MTN": {
        "BASE_URL": env("MTN_MOMO_BASE_URL", "https://sandbox.momodeveloper.mtn.com"),
        "SUBSCRIPTION_KEY": env("MTN_MOMO_SUBSCRIPTION_KEY"),
        "API_USER": env("MTN_MOMO_API_USER"),
        "API_KEY": env("MTN_MOMO_API_KEY"),
        "ENVIRONMENT": env("MTN_MOMO_ENVIRONMENT", "sandbox"),   # "mtnrwanda" in production
        "CURRENCY": env("MTN_MOMO_CURRENCY", "RWF"),             # sandbox only accepts "EUR"
        "CALLBACK_URL": (f"{SITE_BASE_URL}/pay/callback/mtn/{PAYMENT_CALLBACK_TOKEN}/"
                         if SITE_BASE_URL and PAYMENT_CALLBACK_TOKEN else ""),
    },
    "AIRTEL": {
        "BASE_URL": env("AIRTEL_BASE_URL", "https://openapiuat.airtel.africa"),
        "CLIENT_ID": env("AIRTEL_CLIENT_ID"),
        "CLIENT_SECRET": env("AIRTEL_CLIENT_SECRET"),
        "COUNTRY": env("AIRTEL_COUNTRY", "RW"),
        "CURRENCY": env("AIRTEL_CURRENCY", "RWF"),
    },
}


# ─── WhatsApp / Twilio ───────────────────────────────────────────────────────
WHATSAPP_API_VERSION = env("WHATSAPP_API_VERSION", "v22.0")
WHATSAPP_PHONE_NUMBER_ID = env("WHATSAPP_PHONE_NUMBER_ID")
WHATSAPP_ACCESS_TOKEN = env("WHATSAPP_ACCESS_TOKEN")
WHATSAPP_VERIFY_TOKEN = env("WHATSAPP_VERIFY_TOKEN")
COMPANY_PHONE_NUMBER = env("COMPANY_PHONE_NUMBER", "0791273368")

TWILIO_ACCOUNT_SID = env("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN = env("TWILIO_AUTH_TOKEN")
TWILIO_WHATSAPP_NUMBER = env("TWILIO_WHATSAPP_NUMBER", "whatsapp:+14155238886")


# ─── Logging ─────────────────────────────────────────────────────────────────
LOG_DIR = BASE_DIR / 'logs'
LOG_DIR.mkdir(exist_ok=True)
_handlers = {'console': {'class': 'logging.StreamHandler'}}
_default_handlers = ['console']
if DEBUG:
    _handlers['file'] = {'class': 'logging.FileHandler', 'filename': str(LOG_DIR / 'whatsapp.log')}
    _default_handlers.append('file')

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': _handlers,
    'loggers': {
        'homepage.whatsapp_service': {'handlers': _default_handlers, 'level': 'INFO'},
        'homepage.whatsapp_webhook': {'handlers': _default_handlers, 'level': 'INFO'},
        'payment': {'handlers': ['console'], 'level': 'INFO'},
        'django.security': {'handlers': ['console'], 'level': 'WARNING'},
    },
}
