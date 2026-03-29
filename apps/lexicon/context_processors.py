from django.conf import settings
from django.core.cache import cache
from django.templatetags.static import static

from .cache import build_versioned_cache_key
from .models import Page


def share_meta(request):
    origin = getattr(settings, "SITE_CANONICAL_URL", "") or ""
    static_ref = static("porfacan.png")
    if static_ref.startswith(("http://", "https://")):
        default_image = static_ref
    elif origin:
        default_image = f"{origin}{static_ref}" if static_ref.startswith("/") else f"{origin}/{static_ref}"
    else:
        default_image = request.build_absolute_uri(static_ref)
    path = request.path
    if origin:
        canonical_url = f"{origin}{path}"
    else:
        canonical_url = request.build_absolute_uri(path)
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
