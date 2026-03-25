from django.conf import settings
from django.core.cache import cache

from .cache import build_versioned_cache_key
from .models import Page


def published_pages(request):
    cache_key = build_versioned_cache_key("published_pages", {"published": True}, version_scope="pages")
    pages = cache.get(cache_key)
    if pages is None:
        pages = list(Page.objects.filter(is_published=True).only("title", "address"))
        cache.set(cache_key, pages, timeout=settings.LEXICON_CACHE_TIMEOUT_PAGES)
    return {"site_pages": pages}
