from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from django.db.models import Q

from .models import Definition
from .pagination import LIST_PAGE_SIZE, decode_cursor, encode_cursor


@dataclass
class DefinitionPageResult:
    definitions: list[Definition]
    next_cursor: str | None
    has_more: bool
    reset: bool


def _q_after_definition(is_featured: bool, hot_score_value: float, created_at: datetime, pk: int) -> Q:
    if is_featured:
        return (
            Q(is_featured=False)
            | Q(is_featured=True, hot_score_value__lt=hot_score_value)
            | Q(is_featured=True, hot_score_value=hot_score_value, created_at__lt=created_at)
            | Q(is_featured=True, hot_score_value=hot_score_value, created_at=created_at, id__lt=pk)
        )
    return (
        Q(is_featured=False, hot_score_value__lt=hot_score_value)
        | Q(is_featured=False, hot_score_value=hot_score_value, created_at__lt=created_at)
        | Q(is_featured=False, hot_score_value=hot_score_value, created_at=created_at, id__lt=pk)
    )


def _cursor_from_definition_row(d: Definition) -> str:
    return encode_cursor(
        {
            "k": "def",
            "feat": bool(d.is_featured),
            "hsv": float(d.hot_score_value),
            "ca": d.created_at.isoformat(),
            "id": d.id,
        }
    )


def _definition_ordered():
    return (
        Definition.objects.select_related("author")
        .prefetch_related("attachments", "votes")
        .order_by("-is_featured", "-hot_score_value", "-created_at", "-id")
    )


def definition_first_page_prefetch_queryset():
    return _definition_ordered()[:LIST_PAGE_SIZE]


def definition_list_base_queryset(entry_id: int):
    return _definition_ordered().filter(entry_id=entry_id)


def initial_definition_infinite_scroll_state(visible: list[Definition], total_count: int) -> tuple[bool, str]:
    if total_count <= LIST_PAGE_SIZE or not visible or len(visible) < LIST_PAGE_SIZE:
        return False, ""
    return True, _cursor_from_definition_row(visible[-1])


def fetch_definition_page(
    *,
    entry_id: int,
    after_token: str | None,
    limit: int = LIST_PAGE_SIZE,
) -> DefinitionPageResult:
    after = (after_token or "").strip()
    cur = decode_cursor(after) if after else None
    if after and cur is None:
        return DefinitionPageResult(definitions=[], next_cursor=None, has_more=False, reset=True)

    qs = definition_list_base_queryset(entry_id)
    if cur:
        if cur.get("k") != "def":
            return DefinitionPageResult(definitions=[], next_cursor=None, has_more=False, reset=True)
        try:
            ca = datetime.fromisoformat(cur["ca"])
            qs = qs.filter(
                _q_after_definition(
                    bool(cur["feat"]),
                    float(cur["hsv"]),
                    ca,
                    int(cur["id"]),
                )
            )
        except (KeyError, TypeError, ValueError):
            return DefinitionPageResult(definitions=[], next_cursor=None, has_more=False, reset=True)

    rows = list(qs[: limit + 1])
    has_more = len(rows) > limit
    page = rows[:limit]
    next_c = _cursor_from_definition_row(page[-1]) if has_more else None
    return DefinitionPageResult(definitions=page, next_cursor=next_c, has_more=has_more, reset=False)
