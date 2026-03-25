import hashlib
import json
from typing import Any

from django.core.cache import cache


CACHE_VERSION_KEY_PREFIX = "lexicon:cache_version"


def _serialize_key_data(data: Any) -> str:
    return json.dumps(data, sort_keys=True, ensure_ascii=False, separators=(",", ":"))


def build_versioned_cache_key(namespace: str, payload: dict[str, Any], version_scope: str) -> str:
    payload_hash = hashlib.sha256(_serialize_key_data(payload).encode("utf-8")).hexdigest()
    return f"lexicon:{namespace}:v{get_cache_version(version_scope)}:{payload_hash}"


def get_cache_version(scope: str) -> int:
    version = cache.get(_version_key(scope))
    if version is None:
        cache.set(_version_key(scope), 1, timeout=None)
        return 1
    return int(version)


def bump_cache_version(scope: str) -> int:
    key = _version_key(scope)
    if cache.add(key, 1, timeout=None):
        return 1
    try:
        return int(cache.incr(key))
    except ValueError:
        cache.set(key, 1, timeout=None)
        return 1


def _version_key(scope: str) -> str:
    return f"{CACHE_VERSION_KEY_PREFIX}:{scope}"
