"""
Copy this file to envs/settings.py and update values for your environment.
This file is loaded automatically by config/settings/local.py and
config/settings/production.py when present.
"""

SECRET_KEY = "change-me"
ALLOWED_HOSTS = ["localhost", "127.0.0.1"]
TIME_ZONE = "Asia/Tehran"

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": "porfacan",
        "USER": "porfacan",
        "PASSWORD": "porfacan",
        "HOST": "porfacan-db",
        "PORT": "5432",
    }
}

REDIS_URL = "redis://porfacan-redis:6379/1"
CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": REDIS_URL,
        "TIMEOUT": 300,
        "KEY_PREFIX": "porfacan",
        "OPTIONS": {
            "CLIENT_CLASS": "django_redis.client.DefaultClient",
            "IGNORE_EXCEPTIONS": True,
            "SOCKET_CONNECT_TIMEOUT": 0.5,
            "SOCKET_TIMEOUT": 0.5,
            "COMPRESSOR": "django_redis.compressors.zlib.ZlibCompressor",
            "CONNECTION_POOL_KWARGS": {
                "max_connections": 200,
                "retry_on_timeout": True,
            },
        },
    }
}
SESSION_ENGINE = "django.contrib.sessions.backends.cached_db"
SESSION_CACHE_ALIAS = "default"
LEXICON_CACHE_TIMEOUT_SEARCH = 180
LEXICON_CACHE_TIMEOUT_SUGGESTIONS = 120
LEXICON_CACHE_TIMEOUT_PAGES = 600
LEXICON_CACHE_MAX_RESULT_IDS = 1000

# Optional: CMS page slug for the contribution guide (default "contribute").
# LEXICON_CONTRIBUTION_GUIDE_PAGE_ADDRESS = "contribute"

CELERY_BROKER_URL = "amqp://porfacan:porfacan@porfacan-rabbitmq:5672/porfacan"
CELERY_RESULT_BACKEND = "redis://porfacan-redis:6379/2"

GOOGLE_OAUTH_CLIENT_ID = ""
GOOGLE_OAUTH_CLIENT_SECRET = ""
X_OAUTH_CLIENT_ID = ""
X_OAUTH_CLIENT_SECRET = ""

HCAPTCHA_SITEKEY = ""
HCAPTCHA_SECRET = ""

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
    "twitter": {
        "SCOPE": ["users.read", "tweet.read", "offline.access"],
        "APP": {
            "client_id": X_OAUTH_CLIENT_ID,
            "secret": X_OAUTH_CLIENT_SECRET,
            "key": "",
        },
    },
}

AWS_ACCESS_KEY_ID = ""
AWS_SECRET_ACCESS_KEY = ""
AWS_STORAGE_BUCKET_NAME = ""
AWS_S3_REGION_NAME = "eu-central-1"
AWS_S3_SIGNATURE_VERSION = "s3v4"
AWS_QUERYSTRING_AUTH = False
AWS_DEFAULT_ACL = None
AWS_S3_CUSTOM_DOMAIN = ""
if AWS_STORAGE_BUCKET_NAME:
    if AWS_S3_CUSTOM_DOMAIN:
        _S3_PUBLIC_BASE = f"https://{AWS_S3_CUSTOM_DOMAIN}".rstrip("/")
    else:
        _S3_PUBLIC_BASE = (
            f"https://{AWS_STORAGE_BUCKET_NAME}.s3.{AWS_S3_REGION_NAME}.amazonaws.com"
        )
    MEDIA_URL = f"{_S3_PUBLIC_BASE}/"
    STATIC_URL = f"{_S3_PUBLIC_BASE}/static/"
    STORAGES = {
        "default": {
            "BACKEND": "storages.backends.s3boto3.S3Boto3Storage",
        },
        "staticfiles": {
            "BACKEND": "storages.backends.s3boto3.S3StaticStorage",
            "OPTIONS": {"location": "static"},
        },
    }
