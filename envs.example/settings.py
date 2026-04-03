"""
Copy this file to envs/settings.py and update values for your environment.
This file is loaded automatically by config/settings/local.py and
config/settings/production.py when present.
"""

SECRET_KEY = "change-me"
ALLOWED_HOSTS = ["localhost", "127.0.0.1"]
SITE_CANONICAL_URL = "https://porfacan.com"
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
GROK_API_KEY = ""
# GROK_API_BASE_URL = "https://api.x.ai/v1"
# GROK_MODEL = "grok-3-mini"
# GROK_TIMEOUT_SECONDS = 180
# GROK_TEMPERATURE = 0.2

GOOGLE_OAUTH_CLIENT_ID = ""
GOOGLE_OAUTH_CLIENT_SECRET = ""
X_OAUTH_CLIENT_ID = ""
X_OAUTH_CLIENT_SECRET = ""

HCAPTCHA_SITEKEY = ""
HCAPTCHA_SECRET = ""

# Outbound mail (django.core.mail defaults: SMTP backend, localhost:25, no TLS).
EMAIL_HOST = ""
EMAIL_PORT = 587
EMAIL_USE_TLS = True
EMAIL_HOST_USER = ""
EMAIL_HOST_PASSWORD = ""
DEFAULT_FROM_EMAIL = ""

# If you replace this dict, include every provider you use (e.g. twitter_oauth2 for X).
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

AWS_ACCESS_KEY_ID = ""
AWS_SECRET_ACCESS_KEY = ""
AWS_STORAGE_BUCKET_NAME = ""
AWS_S3_REGION_NAME = "eu-central-1"
