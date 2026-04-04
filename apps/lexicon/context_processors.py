from types import SimpleNamespace
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
    cache_key = build_versioned_cache_key("published_pages_nav", {"published": True}, version_scope="pages")
    rows = cache.get(cache_key)
    if rows is None:
        rows = []
        qs = Page.objects.filter(is_published=True).prefetch_related("visible_to_groups").only("title", "address")
        for p in qs:
            gids = frozenset(p.visible_to_groups.values_list("id", flat=True))
            rows.append((p.title, p.address, gids))
        cache.set(cache_key, rows, timeout=settings.LEXICON_CACHE_TIMEOUT_PAGES)

    user = request.user
    staff_like = user.is_authenticated and (user.is_staff or user.is_superuser)
    user_group_ids = set(user.groups.values_list("id", flat=True)) if user.is_authenticated else set()
    nav = []
    for title, address, required_groups in rows:
        if staff_like or not required_groups or (user_group_ids & required_groups):
            nav.append(SimpleNamespace(title=title, address=address))
    return {"site_pages": nav}


def lexicon_site_flags(request):
    return {"lexicon_epochs_enabled": settings.LEXICON_EPOCHS_ENABLED}
