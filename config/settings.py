"""
Django settings for the WH booking project.

Every environment-dependent value is read from environment variables (12-factor),
so the same code runs in Docker, without Docker (SQLite) and in production.
See `.env.example` for the full list.
"""

from pathlib import Path

import environ
from django.core.exceptions import ImproperlyConfigured
from django.utils.translation import gettext_lazy as _

BASE_DIR = Path(__file__).resolve().parent.parent

env = environ.Env()
# A local `.env` only fills variables that are not already defined in the environment.
if (BASE_DIR / ".env").is_file():
    environ.Env.read_env(BASE_DIR / ".env")

DEBUG = env.bool("DEBUG", default=False)

SECRET_KEY = env("SECRET_KEY", default=None)
if not SECRET_KEY:
    if not DEBUG:
        raise ImproperlyConfigured("SECRET_KEY must be set when DEBUG is false.")
    SECRET_KEY = "dev-only-insecure-secret-key"

ALLOWED_HOSTS = env.list("ALLOWED_HOSTS", default=["localhost", "127.0.0.1"])
CSRF_TRUSTED_ORIGINS = env.list("CSRF_TRUSTED_ORIGINS", default=[])


# Applications

INSTALLED_APPS = [
    # modeltranslation must load before the admin to patch its forms.
    "modeltranslation",
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "whitenoise.runserver_nostatic",
    "django.contrib.staticfiles",
    # Third-party apps
    "django_countries",
    # Local apps
    "apps.core",
    "apps.accounts",
    "apps.properties",
    "apps.bookings",
    "apps.payments",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.locale.LocaleMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"
WSGI_APPLICATION = "config.wsgi.application"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.template.context_processors.i18n",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "apps.core.context_processors.site",
            ],
        },
    },
]


# Database: PostgreSQL by default, SQLite supported through DATABASE_URL.

DATABASES = {"default": env.db("DATABASE_URL", default="postgres://wh:wh@localhost:5432/wh")}
DATABASES["default"]["CONN_MAX_AGE"] = env.int("CONN_MAX_AGE", default=60)
DATABASES["default"]["CONN_HEALTH_CHECKS"] = True

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"


# Authentication

AUTH_USER_MODEL = "accounts.User"

# PersonalInfoValidator replaces Django's UserAttributeSimilarityValidator: it is stricter for the
# e-mail and the name, and the guest gets one clear message instead of two (see D05).
AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
        "OPTIONS": {"min_length": 8},
    },
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
    {"NAME": "apps.accounts.validators.NumberOrSymbolValidator"},
    {"NAME": "apps.accounts.validators.PersonalInfoValidator"},
    {"NAME": "apps.accounts.validators.CommonWordValidator"},
]

LOGIN_URL = "accounts:login"
LOGIN_REDIRECT_URL = "core:home"
LOGOUT_REDIRECT_URL = "core:home"


# Internationalization

LANGUAGE_CODE = "es"
# Order matches the header switcher in the design: "EN / ES".
LANGUAGES = [
    ("en", _("English")),
    ("es", _("Spanish")),
]
LOCALE_PATHS = [BASE_DIR / "locale"]
USE_I18N = True

# Content translations (django-modeltranslation): `title` -> `title_es` / `title_en`.
# Spanish is the source language; an empty English value falls back to Spanish.
MODELTRANSLATION_DEFAULT_LANGUAGE = "es"
# Field order in admin forms: the required Spanish value first.
MODELTRANSLATION_LANGUAGES = ("es", "en")
MODELTRANSLATION_FALLBACK_LANGUAGES = {"default": ("es",)}

TIME_ZONE = env("TIME_ZONE", default="America/Lima")
USE_TZ = True


# Static and media files

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_DIRS = [BASE_DIR / "static"]

MEDIA_URL = "media/"
MEDIA_ROOT = BASE_DIR / "media"

# WhiteNoise serves static files in development and production; its built-in table has no
# .otf type, so fonts would go out as application/octet-stream and browsers might not match
# them with their <link rel="preload" type="font/otf">.
WHITENOISE_MIMETYPES = {".otf": "font/otf", ".woff2": "font/woff2"}

STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {
        "BACKEND": (
            "django.contrib.staticfiles.storage.StaticFilesStorage"
            if DEBUG
            else "whitenoise.storage.CompressedManifestStaticFilesStorage"
        )
    },
}


# Email (D37). Local: EMAIL_URL (smtp://mailpit:1025 in Docker, consolemail:// otherwise) expands
# into EMAIL_BACKEND, EMAIL_HOST, EMAIL_PORT, etc. Production: with BREVO_API_KEY the e-mails go
# through Brevo's HTTP API (free hosting plans usually block the SMTP ports).

vars().update(env.email_url("EMAIL_URL", default="consolemail://"))
BREVO_API_KEY = env("BREVO_API_KEY", default="")
if BREVO_API_KEY:
    EMAIL_BACKEND = "anymail.backends.brevo.EmailBackend"
    ANYMAIL = {"BREVO_API_KEY": BREVO_API_KEY}
DEFAULT_FROM_EMAIL = env("DEFAULT_FROM_EMAIL", default="Wynwood House <reservas@example.com>")

# Public address of the site, for links and images inside e-mails (there is no request there).
SITE_URL = env("SITE_URL", default="http://localhost:8000").rstrip("/")


# Security. Production hardening is on whenever DEBUG is false.

SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SECURE_SSL_REDIRECT = env.bool("SECURE_SSL_REDIRECT", default=not DEBUG)
# The provider's internal health probe talks plain HTTP to the container.
SECURE_REDIRECT_EXEMPT = [r"^health/$"]
SESSION_COOKIE_SECURE = not DEBUG
CSRF_COOKIE_SECURE = not DEBUG
SECURE_HSTS_SECONDS = env.int("SECURE_HSTS_SECONDS", default=0 if DEBUG else 31536000)
SECURE_HSTS_INCLUDE_SUBDOMAINS = not DEBUG
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = "strict-origin-when-cross-origin"
X_FRAME_OPTIONS = "DENY"
# The site is not submitted to the browsers' HSTS preload list.
SILENCED_SYSTEM_CHECKS = ["security.W021"]

ADMIN_URL = env("ADMIN_URL", default="admin/")


# Business settings

# Prices are stored in this currency (the design shows US$ everywhere).
CURRENCY = env("CURRENCY", default="USD")
# Uploaded images are converted to WebP and fit inside this box (requirement 8).
IMAGE_MAX_DIMENSION = 1200
IMAGE_WEBP_QUALITY = 80

# Bookings (see D08): "Book now" holds the dates for this many minutes while the guest pays.
BOOKING_HOLD_MINUTES = env.int("BOOKING_HOLD_MINUTES", default=15)
# Online bookings up to this many nights; longer stays go through the long-stay contact (D32).
BOOKING_MAX_NIGHTS = env.int("BOOKING_MAX_NIGHTS", default=30)
# How far ahead the calendar accepts check-ins.
BOOKING_MAX_DAYS_AHEAD = env.int("BOOKING_MAX_DAYS_AHEAD", default=365)
# The person who books and pays must be an adult (D36).
BOOKING_MIN_GUEST_AGE = 18

# Countries where Wynwood House operates are listed first in the nationality and phone selects.
COUNTRIES_FIRST = ["PE", "CO", "MX", "PA", "ES"]
COUNTRIES_FIRST_BREAK = "──────────"

# Payments (D11): the simulated gateway accepts only test cards. A real provider (dLocal, Stripe)
# is another class with the same interface.
PAYMENT_GATEWAY = env("PAYMENT_GATEWAY", default="apps.payments.gateways.SimulatedGateway")


# Logging: everything to stdout, collected by Docker or the hosting provider.

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {"console": {"class": "logging.StreamHandler"}},
    "root": {"handlers": ["console"], "level": env("LOG_LEVEL", default="INFO")},
}
