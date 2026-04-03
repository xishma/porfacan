from pathlib import Path

import os
from django.utils.translation import gettext_lazy as _

BASE_DIR = Path(__file__).resolve().parent.parent.parent

SECRET_KEY = os.getenv("DJANGO_SECRET_KEY", "unsafe-dev-secret-key")
DEBUG = False
ALLOWED_HOSTS = [h for h in os.getenv("DJANGO_ALLOWED_HOSTS", "").split(",") if h]

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.postgres",
    "django.contrib.sessions",
    "django.contrib.sites",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "allauth",
    "allauth.account",
    "allauth.socialaccount",
    "allauth.socialaccount.providers.google",
    "allauth.socialaccount.providers.twitter_oauth2",
    "storages",
    "hcaptcha_field",
    "apps.users",
    "apps.lexicon",
    "apps.ai",
    "apps.api",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.locale.LocaleMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "allauth.account.middleware.AccountMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "apps.lexicon.context_processors.share_meta",
                "apps.lexicon.context_processors.published_pages",
            ],
        },
    }
]

WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.getenv("POSTGRES_DB", "porfacan"),
        "USER": os.getenv("POSTGRES_USER", "porfacan"),
        "PASSWORD": os.getenv("POSTGRES_PASSWORD", "porfacan"),
        "HOST": os.getenv("POSTGRES_HOST", "localhost"),
        "PORT": os.getenv("POSTGRES_PORT", "5432"),
    }
}

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "fa"
LANGUAGES = [
    ("fa", _("Persian")),
]
TIME_ZONE = os.getenv("DJANGO_TIME_ZONE", "Asia/Tehran")
USE_I18N = True
USE_TZ = True
LOCALE_PATHS = [BASE_DIR / "locale"]

STATIC_URL = "/static/"
STATICFILES_DIRS = [BASE_DIR / "static"]
STATIC_ROOT = BASE_DIR / "staticfiles"

MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
AUTH_USER_MODEL = "users.User"
LOGIN_URL = "users:login"
LOGIN_REDIRECT_URL = "lexicon:entry-list"
LOGOUT_REDIRECT_URL = "lexicon:entry-list"
SITE_ID = 1

AUTHENTICATION_BACKENDS = [
    "django.contrib.auth.backends.ModelBackend",
    "allauth.account.auth_backends.AuthenticationBackend",
]

ACCOUNT_LOGIN_METHODS = {"email"}
ACCOUNT_SIGNUP_FIELDS = ["email*", "password1*", "password2*"]
ACCOUNT_UNIQUE_EMAIL = True
ACCOUNT_LOGIN_ON_EMAIL_CONFIRMATION = True
ACCOUNT_USER_MODEL_USERNAME_FIELD = None
ACCOUNT_EMAIL_VERIFICATION = "optional"
ACCOUNT_EMAIL_SUBJECT_PREFIX = ""
ACCOUNT_CONFIRM_EMAIL_ON_GET = True
ACCOUNT_EMAIL_CONFIRMATION_EXPIRE_DAYS = 3
VERIFICATION_EMAIL_COOLDOWN_SECONDS = int(
    os.getenv("VERIFICATION_EMAIL_COOLDOWN_SECONDS", "300")
)

SOCIALACCOUNT_ADAPTER = "apps.users.adapters.UserSocialAccountAdapter"
ACCOUNT_ADAPTER = "apps.users.adapters.UserAccountAdapter"
SOCIALACCOUNT_LOGIN_ON_GET = True
SOCIALACCOUNT_AUTO_SIGNUP = True
SOCIALACCOUNT_STORE_TOKENS = True
SOCIALACCOUNT_EMAIL_AUTHENTICATION = True
SOCIALACCOUNT_EMAIL_AUTHENTICATION_AUTO_CONNECT = True

GOOGLE_OAUTH_CLIENT_ID = os.getenv("GOOGLE_OAUTH_CLIENT_ID", "")
GOOGLE_OAUTH_CLIENT_SECRET = os.getenv("GOOGLE_OAUTH_CLIENT_SECRET", "")
X_OAUTH_CLIENT_ID = os.getenv("X_OAUTH_CLIENT_ID", "")
X_OAUTH_CLIENT_SECRET = os.getenv("X_OAUTH_CLIENT_SECRET", "")

HCAPTCHA_SITEKEY = os.getenv("HCAPTCHA_SITEKEY", "")
HCAPTCHA_SECRET = os.getenv("HCAPTCHA_SECRET", "")

SOCIALACCOUNT_PROVIDERS = {
    "google": {
        "SCOPE": ["email", "profile"],
        "AUTH_PARAMS": {"access_type": "online"},
        "APP": {
            "client_id": GOOGLE_OAUTH_CLIENT_ID,
            "secret": GOOGLE_OAUTH_CLIENT_SECRET,
            "key": "",
        },
    },
    "twitter_oauth2": {
        "SCOPE": ["users.read", "tweet.read", "offline.access"],
        "APP": {
            "client_id": X_OAUTH_CLIENT_ID,
            "secret": X_OAUTH_CLIENT_SECRET,
            "key": "",
        },
    },
}

CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": os.getenv("REDIS_URL", "redis://127.0.0.1:6379/1"),
        "TIMEOUT": int(os.getenv("CACHE_DEFAULT_TIMEOUT", "300")),
        "KEY_PREFIX": os.getenv("CACHE_KEY_PREFIX", "porfacan"),
        "OPTIONS": {
            "CLIENT_CLASS": "django_redis.client.DefaultClient",
            "IGNORE_EXCEPTIONS": os.getenv("CACHE_IGNORE_EXCEPTIONS", "1") == "1",
            "SOCKET_CONNECT_TIMEOUT": float(os.getenv("CACHE_SOCKET_CONNECT_TIMEOUT", "0.5")),
            "SOCKET_TIMEOUT": float(os.getenv("CACHE_SOCKET_TIMEOUT", "0.5")),
            "COMPRESSOR": "django_redis.compressors.zlib.ZlibCompressor",
            "CONNECTION_POOL_KWARGS": {
                "max_connections": int(os.getenv("CACHE_MAX_CONNECTIONS", "200")),
                "retry_on_timeout": True,
            },
        },
    }
}
# Keep session persistence in DB while using Redis as fast-path cache.
SESSION_ENGINE = "django.contrib.sessions.backends.cached_db"
SESSION_CACHE_ALIAS = "default"

LEXICON_CACHE_TIMEOUT_SEARCH = int(os.getenv("LEXICON_CACHE_TIMEOUT_SEARCH", "180"))
LEXICON_CACHE_TIMEOUT_SUGGESTIONS = int(os.getenv("LEXICON_CACHE_TIMEOUT_SUGGESTIONS", "120"))
LEXICON_CACHE_TIMEOUT_PAGES = int(os.getenv("LEXICON_CACHE_TIMEOUT_PAGES", "600"))
LEXICON_CACHE_MAX_RESULT_IDS = int(os.getenv("LEXICON_CACHE_MAX_RESULT_IDS", "1000"))

# Slug for the CMS Page that explains how to contribute (path: /lexicon/pages/<address>/).
LEXICON_CONTRIBUTION_GUIDE_PAGE_ADDRESS = "contribute"

# e.g. https://porfacan.org | used for Open Graph absolute URLs when set (recommended in production).
SITE_CANONICAL_URL = os.getenv("DJANGO_SITE_URL", "").strip().rstrip("/")

CELERY_BROKER_URL = os.getenv("CELERY_BROKER_URL", "amqp://porfacan:porfacan@localhost:5672/porfacan")
CELERY_RESULT_BACKEND = os.getenv("CELERY_RESULT_BACKEND", "redis://127.0.0.1:6379/2")
CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"
CELERY_TIMEZONE = TIME_ZONE

GROK_API_KEY = os.getenv("GROK_API_KEY", "")
GROK_API_BASE_URL = os.getenv("GROK_API_BASE_URL", "https://api.x.ai/v1")
GROK_MODEL = os.getenv("GROK_MODEL", "grok-4.20-reasoning-latest")
GROK_TIMEOUT_SECONDS = int(os.getenv("GROK_TIMEOUT_SECONDS", "180"))
GROK_TEMPERATURE = float(os.getenv("GROK_TEMPERATURE", "0.8"))

AI_ENTRY_ALLOWED_EPOCHS = [
    "عمومی",
    "جنبش سبز",
    "دوران برجام",
    "اعتراضات دی ماه ۹۶",
    "آبان خونین",
    "زمستان ۹۸",
    "دوران کرونا",
    "اعتراضات زن زندگی آزادی",
    "جنگ ۱۲ روزه",
    "انقلاب شیر و خورشید",
]

AI_ENTRY_ALLOWED_CATEGORIES = [
    "اصطلاحات",
    "القاب افراد",
    "شعارها",
    "عمومی",
    "میم‌ها",
]

SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = "DENY"
CSRF_COOKIE_HTTPONLY = True
CSRF_COOKIE_SECURE = True
SESSION_COOKIE_SECURE = True

AWS_STORAGE_BUCKET_NAME = ""
AWS_S3_CUSTOM_DOMAIN = None
AWS_LOCATION = ""
AWS_S3_REGION_NAME = ""
AWS_S3_SIGNATURE_VERSION = "s3v4"
AWS_QUERYSTRING_AUTH = True

try:
    from envs.settings import *  # noqa
except ImportError:
    pass

if AWS_STORAGE_BUCKET_NAME:
    if AWS_S3_CUSTOM_DOMAIN:
        _S3_PUBLIC_BASE = f"https://{AWS_S3_CUSTOM_DOMAIN}".rstrip("/")
    else:
        _S3_PUBLIC_BASE = (
            f"https://{AWS_STORAGE_BUCKET_NAME}.s3.{AWS_S3_REGION_NAME}.amazonaws.com"
        )
    _s3_url_prefix = f"{AWS_LOCATION}/" if AWS_LOCATION else ""
    MEDIA_URL = f"{_S3_PUBLIC_BASE}/{_s3_url_prefix}media/"
    STATIC_URL = f"{_S3_PUBLIC_BASE}/{_s3_url_prefix}static/"
    _default_storage_opts = {"location": AWS_LOCATION} if AWS_LOCATION else {}
    _staticfiles_location = f"{AWS_LOCATION}/static" if AWS_LOCATION else "static"
    STORAGES = {
        "default": {
            "BACKEND": "storages.backends.s3boto3.S3Boto3Storage",
            **({"OPTIONS": _default_storage_opts} if _default_storage_opts else {}),
        },
        "staticfiles": {
            "BACKEND": "storages.backends.s3boto3.S3StaticStorage",
            "OPTIONS": {"location": _staticfiles_location},
        },
    }
