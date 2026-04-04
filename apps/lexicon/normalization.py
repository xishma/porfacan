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
# Collapse horizontal whitespace only; newlines are preserved (split/process/join).
_HORIZONTAL_SPACE_RUN = re.compile(r"[^\S\n]+")
# Hazm joins "می" + space + stem with ZWNJ when the pair is in its lexicon. A stray
# space or NBSP inside words like «میمون» (e.g. paste/PDF) becomes «می‌مون». Glue the
# verbal prefix to the following Persian letters before Hazm; real verbs still normalize
# (e.g. «می روم» → «میروم» → «می‌روم»). Do not match «می»/«نمی» when preceded by a Persian
# letter (e.g. «قدیمی فارسی» or «برنمی گردد» | suffix / infix, not the prefix alone).
_PERSIAN_LETTERS = "آابپتثجچحخدذرزژسشصضطظعغفقکگلمنوهی"
_MI_PREFIX_GLUE = re.compile(
    rf"(?<![{_PERSIAN_LETTERS}])(نمی|می)\s+(?=[{_PERSIAN_LETTERS}])",
)
_HAZM_NORMALIZER = Normalizer(persian_style=True, remove_diacritics=True) if Normalizer else None


def normalize_persian(text: str) -> str:
    if not text:
        return text

    normalized = text.translate(_ARABIC_TO_PERSIAN).replace("\r\n", "\n").replace("\r", "\n").strip()
    if not normalized:
        return ""

    lines_out: list[str] = []
    for line in normalized.split("\n"):
        line = _MI_PREFIX_GLUE.sub(r"\1", line)
        line = _HORIZONTAL_SPACE_RUN.sub(" ", line)
        if _HAZM_NORMALIZER and line:
            line = _HAZM_NORMALIZER.normalize(line)
        lines_out.append(line)
    return "\n".join(lines_out)
