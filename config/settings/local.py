from .base import *  # noqa

DEBUG = True
ALLOWED_HOSTS = ["*"]

CSRF_COOKIE_SECURE = False
SESSION_COOKIE_SECURE = False

try:
    from envs.settings import *  # noqa
except ImportError:
    pass
