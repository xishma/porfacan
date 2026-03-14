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


def normalize_persian(text: str) -> str:
    if not text:
        return text

    normalized = text.translate(_ARABIC_TO_PERSIAN).strip()
    normalized = _MULTI_SPACES.sub(" ", normalized)

    if Normalizer:
        normalizer = Normalizer(persian_style=True, remove_diacritics=True)
        normalized = normalizer.normalize(normalized)
    return normalized
