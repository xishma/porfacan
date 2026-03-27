from django.core.exceptions import ImproperlyConfigured

from .base import *  # noqa

try:
    from envs.settings import *  # noqa
except ImportError:
    pass

# Cannot be overridden by envs.settings — keeps TLS/HSTS/cookies aligned with deployment.
DEBUG = False
SECURE_SSL_REDIRECT = True
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_REFERRER_POLICY = "same-origin"


def _production_secret_key_valid(key: str) -> bool:
    if not key or len(key) < 50 or key.startswith("django-insecure-"):
        return False
    if len(set(key)) < 5:
        return False
    if key in ("unsafe-dev-secret-key", "change-me"):
        return False
    return True


if not _production_secret_key_valid(SECRET_KEY):
    raise ImproperlyConfigured(
        "SECRET_KEY must be a long random value (50+ characters, at least 5 unique "
        "characters, not django-insecure-*). Set DJANGO_SECRET_KEY in the environment "
        "or replace the placeholder in envs/settings.py before production deploy."
    )

if not ALLOWED_HOSTS:
    raise ImproperlyConfigured(
        "ALLOWED_HOSTS is empty. Set DJANGO_ALLOWED_HOSTS or ALLOWED_HOSTS for production."
    )

if "*" in ALLOWED_HOSTS:
    raise ImproperlyConfigured("ALLOWED_HOSTS must not contain '*' in production.")
