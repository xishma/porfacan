from __future__ import annotations

import re

try:
    from hazm import Normalizer
except ImportError:  # pragma: no cover - handled by fallback.
    Normalizer = None  # type: ignore[assignment]

_ARABIC_TO_PERSIAN = str.maketrans(
    {
        "ي": "ی",
        "ك": "ک",
        "ة": "ه",
    }
)
_MULTI_SPACES = re.compile(r"\s+")
_HAZM_NORMALIZER = Normalizer(persian_style=True, remove_diacritics=True) if Normalizer else None


def normalize_persian(text: str) -> str:
    if not text:
        return text

    normalized = text.translate(_ARABIC_TO_PERSIAN).strip()
    normalized = _MULTI_SPACES.sub(" ", normalized)

    if _HAZM_NORMALIZER:
        normalized = _HAZM_NORMALIZER.normalize(normalized)
    return normalized
