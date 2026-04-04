from urllib.parse import urlparse

from django.conf import settings
from django.core.cache import cache
from django.templatetags.static import static

from .cache import build_versioned_cache_key
from .models import Page


def _normalize_request_path(path: str) -> str:
    if not path:
        return "/"
    return path if path.startswith("/") else f"/{path}"


def _upgrade_same_host_http_to_https(url: str, request) -> str:
    if not url.startswith("http://"):
        return url
    if not getattr(settings, "SECURE_SSL_REDIRECT", False):
        return url
    parsed = urlparse(url)
    if parsed.netloc == request.get_host():
        return "https://" + url[7:]
    return url


def share_meta(request):
    origin = (getattr(settings, "SITE_CANONICAL_URL", "") or "").strip().rstrip("/")
    static_ref = static("porfacan.png")
    if not static_ref.startswith(("/", "http://", "https://")):
        static_ref = f"/{static_ref.lstrip('/')}"
    if static_ref.startswith(("http://", "https://")):
        default_image = static_ref
    elif origin:
        default_image = f"{origin}{static_ref}" if static_ref.startswith("/") else f"{origin}/{static_ref}"
    else:
        default_image = request.build_absolute_uri(static_ref)
    default_image = _upgrade_same_host_http_to_https(default_image, request)

    path = _normalize_request_path(request.path)
    if origin:
        canonical_url = f"{origin}{path}"
    else:
        canonical_url = request.build_absolute_uri(path)
    canonical_url = _upgrade_same_host_http_to_https(canonical_url, request)

    return {
        "share_default_og_image": default_image,
        "share_canonical_url": canonical_url,
    }


def published_pages(request):
    cache_key = build_versioned_cache_key("published_pages", {"published": True}, version_scope="pages")
    pages = cache.get(cache_key)
    if pages is None:
        pages = list(Page.objects.filter(is_published=True).only("title", "address"))
        cache.set(cache_key, pages, timeout=settings.LEXICON_CACHE_TIMEOUT_PAGES)
    return {"site_pages": pages}


def lexicon_site_flags(request):
    return {"lexicon_epochs_enabled": settings.LEXICON_EPOCHS_ENABLED}
