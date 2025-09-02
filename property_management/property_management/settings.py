"""
Django settings for property_management
Safe drop-in for local dev + DigitalOcean App Platform.
"""
from pathlib import Path
import os
from dotenv import load_dotenv
import dj_database_url

# -----------------------------------------------------------------------------
# Base + environment
# -----------------------------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent.parent

ENV = os.getenv("ENV", "").lower() or "development"
IS_PRODUCTION = ENV == "production"

# Load .env only outside production
if not IS_PRODUCTION:
    load_dotenv(BASE_DIR / ".env")

def csv_env(name: str, default: str = "") -> list[str]:
    return [x.strip() for x in os.getenv(name, default).split(",") if x.strip()]

# -----------------------------------------------------------------------------
# Core
# -----------------------------------------------------------------------------
# In production, SECRET_KEY must be provided. In dev we fall back (ok for local only).
SECRET_KEY = os.getenv("SECRET_KEY") or ("dev-insecure-key" if not IS_PRODUCTION else None)
if IS_PRODUCTION and not SECRET_KEY:
    raise RuntimeError("SECRET_KEY is required in production")

DEBUG = os.getenv("DEBUG", "False") == "True"

ALLOWED_HOSTS = csv_env("ALLOWED_HOSTS", "127.0.0.1,localhost")
CSRF_TRUSTED_ORIGINS = csv_env("CSRF_TRUSTED_ORIGINS", "")

# -----------------------------------------------------------------------------
# Apps / Middleware / Templates / WSGI
# -----------------------------------------------------------------------------
INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "properties",
    "tenants",
    "storages",  # harmless if S3 is off; required if S3 is on
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "property_management.urls"

TEMPLATES = [{
    "BACKEND": "django.template.backends.django.DjangoTemplates",
    "DIRS": [BASE_DIR / "templates"],
    "APP_DIRS": True,
    "OPTIONS": {
        "context_processors": [
            "django.template.context_processors.request",
            "django.contrib.auth.context_processors.auth",
            "django.contrib.messages.context_processors.messages",
        ],
    },
}]

WSGI_APPLICATION = "property_management.wsgi.application"

# -----------------------------------------------------------------------------
# Database (DigitalOcean: set DATABASE_URL; local dev: sqlite fallback)
# -----------------------------------------------------------------------------
db_url = os.getenv("DATABASE_URL")
if not db_url and not IS_PRODUCTION and os.getenv("USE_SQLITE", "1") == "1":
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",
        }
    }
else:
    if IS_PRODUCTION and not db_url:
        raise RuntimeError("DATABASE_URL is required in production")
    DATABASES = {
        "default": dj_database_url.parse(db_url, conn_max_age=600, ssl_require=True)
    }

# -----------------------------------------------------------------------------
# Password validation
# -----------------------------------------------------------------------------
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# -----------------------------------------------------------------------------
# Internationalization
# -----------------------------------------------------------------------------
LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

# -----------------------------------------------------------------------------
# Static & Media (WhiteNoise + optional DigitalOcean Spaces)
# -----------------------------------------------------------------------------
STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
# Don’t crash if a referenced file is missing from the manifest
WHITENOISE_MANIFEST_STRICT = False
USE_S3 = os.getenv("USE_S3", "0") == "1"  # flip to 1 in DO after Spaces is configured

if USE_S3:
    AWS_ACCESS_KEY_ID       = os.getenv("DO_SPACES_KEY")
    AWS_SECRET_ACCESS_KEY   = os.getenv("DO_SPACES_SECRET")
    AWS_STORAGE_BUCKET_NAME = os.getenv("AWS_STORAGE_BUCKET_NAME")
    AWS_S3_REGION_NAME      = os.getenv("DO_SPACES_REGION")     # e.g. "nyc3"
    AWS_S3_ENDPOINT_URL     = os.getenv("DO_SPACES_ENDPOINT")   # e.g. "https://nyc3.digitaloceanspaces.com"

    if not all([AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, AWS_STORAGE_BUCKET_NAME, AWS_S3_REGION_NAME, AWS_S3_ENDPOINT_URL]):
        raise RuntimeError("USE_S3=1 but one or more DO/AWS Spaces vars are missing")

    AWS_DEFAULT_ACL = "public-read"
    AWS_QUERYSTRING_AUTH = False
    AWS_S3_OBJECT_PARAMETERS = {"CacheControl": "max-age=86400"}
    AWS_S3_CUSTOM_DOMAIN = f"{AWS_STORAGE_BUCKET_NAME}.{AWS_S3_REGION_NAME}.digitaloceanspaces.com"

    STORAGES = {
        "default": {  # media files to Spaces
            "BACKEND": "storages.backends.s3boto3.S3Boto3Storage",
            "OPTIONS": {"location": "media"},
        },
        "staticfiles": {  # static via WhiteNoise
            "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
        },
    }
    MEDIA_URL = f"https://{AWS_S3_CUSTOM_DOMAIN}/media/"
else:
    STORAGES = {
        "default": {  # local media storage (works fine on DO if you don't need Spaces yet)
            "BACKEND": "django.core.files.storage.FileSystemStorage",
        },
        "staticfiles": {
            "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
        },
    }
    MEDIA_URL = "/media/"
    MEDIA_ROOT = BASE_DIR / "media"

# -----------------------------------------------------------------------------
# Email (Gmail SMTP or provider via env)
# -----------------------------------------------------------------------------
EMAIL_BACKEND = os.getenv("EMAIL_BACKEND", "django.core.mail.backends.smtp.EmailBackend")
EMAIL_HOST = os.getenv("EMAIL_HOST", "smtp.gmail.com")
EMAIL_PORT = int(os.getenv("EMAIL_PORT", 587))
EMAIL_USE_TLS = os.getenv("EMAIL_USE_TLS", "True") == "True"
EMAIL_HOST_USER = os.getenv("EMAIL_HOST_USER")                  # set in DO env
EMAIL_HOST_PASSWORD = os.getenv("EMAIL_HOST_PASSWORD")          # set in DO env (Gmail app password)
DEFAULT_FROM_EMAIL = os.getenv("DEFAULT_FROM_EMAIL", EMAIL_HOST_USER or "webmaster@localhost")
SERVER_EMAIL = os.getenv("SERVER_EMAIL", DEFAULT_FROM_EMAIL)
EMAIL_SUBJECT_PREFIX = os.getenv("EMAIL_SUBJECT_PREFIX", "[Smart Home Management] ")
EMAIL_TIMEOUT = int(os.getenv("EMAIL_TIMEOUT", 20))

ADMINS = [
    ("You", os.getenv("ADMIN_EMAIL", "muhammadadnan.py@gmail.com")),
]

# -----------------------------------------------------------------------------
# Project-specific toggles
# -----------------------------------------------------------------------------
BOOKING_SETS_UNAVAILABLE_ON_APPROVAL = True
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# -----------------------------------------------------------------------------
# Security (safe defaults behind DO reverse proxy; enable via env if needed)
# -----------------------------------------------------------------------------
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SECURE_SSL_REDIRECT = os.getenv("SECURE_SSL_REDIRECT", "False") == "True"
SESSION_COOKIE_SECURE = os.getenv("SESSION_COOKIE_SECURE", "False") == "True"
CSRF_COOKIE_SECURE = os.getenv("CSRF_COOKIE_SECURE", "False") == "True"

# -----------------------------------------------------------------------------
# Logging to console (so 500s show up clearly in DO logs)
# -----------------------------------------------------------------------------
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {"console": {"class": "logging.StreamHandler"}},
    "root": {"handlers": ["console"], "level": "INFO"},
    "loggers": {
        "django": {"handlers": ["console"], "level": "INFO", "propagate": True},
        # Uncomment for noisy SQL during debugging:
        # "django.db.backends": {"handlers": ["console"], "level": "DEBUG"},
    },
}
