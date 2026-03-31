from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from django.conf import settings
from django.core.cache import cache
from django.db.models import Case, IntegerField, OuterRef, Prefetch, Q, Subquery, Value, When

from .cache import build_versioned_cache_key, get_cache_version
from .models import Definition, Entry, EntryAlias, EntryCategory, Epoch, SuggestedHeadword
from .normalization import normalize_persian
from .pagination import LIST_PAGE_SIZE, decode_cursor, encode_cursor

ENTRY_CARD_PREFETCHES = (
    Prefetch(
        "aliases",
        queryset=EntryAlias.objects.order_by("headword").only("id", "headword", "entry_id"),
    ),
    Prefetch(
        "headword_suggestions",
        queryset=SuggestedHeadword.objects.filter(status=SuggestedHeadword.Status.APPROVED)
        .order_by("headword")
        .only("id", "headword", "entry_id"),
        to_attr="approved_suggestion_headwords",
    ),
    "epochs",
)


@dataclass
class EntryListPageResult:
    entries: list[Entry]
    next_cursor: str | None
    has_more: bool
    reset: bool
    invalid_epoch: bool = False
    invalid_category: bool = False


def _cacheable_entry_query(normalized_query: str, selected_epoch: str, selected_category: str) -> bool:
    return bool(normalized_query or selected_epoch or selected_category)


def _entry_search_cache_key(normalized_query: str, selected_epoch: str, selected_category: str) -> str:
    payload = {
        "query": normalized_query,
        "epoch": selected_epoch,
        "category": selected_category,
    }
    return build_versioned_cache_key("entry_search_ids", payload, version_scope="entry_search_results")


def _top_definition_content_subquery():
    return Subquery(
        Definition.objects.filter(entry_id=OuterRef("pk"))
        .order_by("-is_featured", "-hot_score_value", "-created_at", "-id")
        .values("content")[:1]
    )


def _annotate_top_definition_for_list(queryset):
    return queryset.annotate(top_definition_content=_top_definition_content_subquery())


def _ordered_entry_queryset_from_ids(entry_ids: list[int]):
    if not entry_ids:
        return _annotate_top_definition_for_list(
            Entry.objects.filter(is_verified=True)
            .select_related("category")
            .only(
                "id",
                "headword",
                "slug",
                "created_at",
                "is_verified",
                "category_id",
                "category__id",
                "category__name",
                "category__slug",
            )
            .prefetch_related(*ENTRY_CARD_PREFETCHES)
            .none()
        )

    order_by_id = Case(
        *[When(pk=entry_id, then=Value(position)) for position, entry_id in enumerate(entry_ids)],
        output_field=IntegerField(),
    )
    return _annotate_top_definition_for_list(
        Entry.objects.filter(is_verified=True, pk__in=entry_ids)
        .select_related("category")
        .only(
            "id",
            "headword",
            "slug",
            "created_at",
            "is_verified",
            "category_id",
            "category__id",
            "category__name",
            "category__slug",
        )
        .prefetch_related(*ENTRY_CARD_PREFETCHES)
        .annotate(_cached_order=order_by_id)
        .order_by("_cached_order")
    )


def _base_verified_entries():
    return _annotate_top_definition_for_list(
        Entry.objects.filter(is_verified=True)
        .select_related("category")
        .only(
            "id",
            "headword",
            "slug",
            "created_at",
            "is_verified",
            "category_id",
            "category__id",
            "category__name",
            "category__slug",
        )
        .prefetch_related(*ENTRY_CARD_PREFETCHES)
    )


def _filtered_queryset_for_search_epoch_category(query: str, selected_epoch: str, selected_category: str):
    queryset = _base_verified_entries()
    normalized_query = normalize_persian(query or "").strip()
    has_query = bool(normalized_query)
    invalid_epoch = False
    invalid_category = False
    if query:
        queryset = queryset.search(query)
    if selected_epoch:
        epochs = Epoch.objects.filter(name__iexact=selected_epoch)
        if not epochs.exists():
            invalid_epoch = True
            return queryset.none(), normalized_query, has_query, invalid_epoch, invalid_category
        queryset = queryset.filter(epochs__in=epochs)
    if selected_category:
        categories = EntryCategory.objects.filter(slug__iexact=selected_category)
        if not categories.exists():
            invalid_category = True
            return queryset.none(), normalized_query, has_query, invalid_epoch, invalid_category
        queryset = queryset.filter(category__in=categories)
    return queryset, normalized_query, has_query, invalid_epoch, invalid_category


def _resolve_id_sequence(
    queryset,
    *,
    normalized_query: str,
    selected_epoch: str,
    selected_category: str,
) -> list[int] | None:
    if not _cacheable_entry_query(normalized_query, selected_epoch, selected_category):
        return None
    cache_key = _entry_search_cache_key(normalized_query, selected_epoch, selected_category)
    cached_entry_ids = cache.get(cache_key)
    if cached_entry_ids is not None:
        return list(cached_entry_ids)

    max_cached_results = settings.LEXICON_CACHE_MAX_RESULT_IDS
    result_ids = list(queryset.values_list("id", flat=True)[: max_cached_results + 1])
    if len(result_ids) <= max_cached_results:
        cache.set(cache_key, result_ids, timeout=settings.LEXICON_CACHE_TIMEOUT_SEARCH)
        return list(result_ids)
    return None


def _hot_queryset():
    return _base_verified_entries().with_hot_rank().order_by("-hot_rank", "-created_at", "-id")


def _q_after_hot(hot_rank: float, created_at: datetime, pk: int) -> Q:
    return (
        Q(hot_rank__lt=hot_rank)
        | Q(hot_rank=hot_rank, created_at__lt=created_at)
        | Q(hot_rank=hot_rank, created_at=created_at, id__lt=pk)
    )


def _cursor_from_entry_hot(entry: Entry) -> str:
    return encode_cursor(
        {
            "k": "hot",
            "hr": float(entry.hot_rank),
            "ca": entry.created_at.isoformat(),
            "id": entry.id,
        }
    )


def _cursor_from_id_list(after_id: int) -> str:
    return encode_cursor({"k": "ids", "aid": after_id})


def _search_result_order():
    return ("-starts_with", "-has_definition_match", "-search_rank", "-trigram_similarity", "-created_at", "-id")


def _cursor_search_offset(offset: int) -> str:
    return encode_cursor(
        {
            "k": "soff",
            "o": offset,
            "ver": get_cache_version("entry_search_results"),
        }
    )


def fetch_entry_list_page(
    *,
    query: str,
    selected_epoch: str,
    selected_category: str,
    after_token: str | None,
    limit: int = LIST_PAGE_SIZE,
) -> EntryListPageResult:
    queryset, normalized_query, has_query, invalid_epoch, invalid_category = _filtered_queryset_for_search_epoch_category(
        query, selected_epoch, (selected_category or "").strip()
    )
    if invalid_epoch:
        return EntryListPageResult(entries=[], next_cursor=None, has_more=False, reset=False, invalid_epoch=True)
    if invalid_category:
        return EntryListPageResult(entries=[], next_cursor=None, has_more=False, reset=False, invalid_category=True)

    after = (after_token or "").strip()
    parsed_after = decode_cursor(after) if after else None
    if after and parsed_after is None:
        return EntryListPageResult(entries=[], next_cursor=None, has_more=False, reset=True)

    cacheable = _cacheable_entry_query(normalized_query, selected_epoch, (selected_category or "").strip())

    if not cacheable:
        qs = _hot_queryset()
        cur = parsed_after
        if cur and cur.get("k") == "hot":
            try:
                ca = datetime.fromisoformat(cur["ca"])
                qs = qs.filter(
                    _q_after_hot(
                        float(cur["hr"]),
                        ca,
                        int(cur["id"]),
                    )
                )
            except (KeyError, TypeError, ValueError):
                return EntryListPageResult(entries=[], next_cursor=None, has_more=False, reset=True)
        elif cur:
            return EntryListPageResult(entries=[], next_cursor=None, has_more=False, reset=True)

        rows = list(qs[: limit + 1])
        has_more = len(rows) > limit
        page = rows[:limit]
        next_c = _cursor_from_entry_hot(page[-1]) if has_more else None
        return EntryListPageResult(entries=page, next_cursor=next_c, has_more=has_more, reset=False)

    id_sequence = _resolve_id_sequence(
        queryset,
        normalized_query=normalized_query,
        selected_epoch=selected_epoch,
        selected_category=(selected_category or "").strip(),
    )
    if id_sequence is not None:
        cur = parsed_after
        start = 0
        if cur:
            if cur.get("k") != "ids":
                return EntryListPageResult(entries=[], next_cursor=None, has_more=False, reset=True)
            try:
                aid = int(cur["aid"])
            except (KeyError, TypeError, ValueError):
                return EntryListPageResult(entries=[], next_cursor=None, has_more=False, reset=True)
            try:
                start = id_sequence.index(aid) + 1
            except ValueError:
                return EntryListPageResult(entries=[], next_cursor=None, has_more=False, reset=True)

        window = id_sequence[start : start + limit + 1]
        has_more = len(window) > limit
        slice_ids = window[:limit]
        if not slice_ids:
            return EntryListPageResult(entries=[], next_cursor=None, has_more=False, reset=False)
        page = list(_ordered_entry_queryset_from_ids(slice_ids))
        next_c = _cursor_from_id_list(page[-1].id) if has_more else None
        return EntryListPageResult(entries=page, next_cursor=next_c, has_more=has_more, reset=False)

    if has_query:
        qs = queryset.order_by(*_search_result_order())
        cur = parsed_after
        offset = 0
        if cur:
            if cur.get("k") != "soff":
                return EntryListPageResult(entries=[], next_cursor=None, has_more=False, reset=True)
            try:
                offset = int(cur["o"])
                cver = int(cur["ver"])
            except (KeyError, TypeError, ValueError):
                return EntryListPageResult(entries=[], next_cursor=None, has_more=False, reset=True)
            if cver != get_cache_version("entry_search_results"):
                return EntryListPageResult(entries=[], next_cursor=None, has_more=False, reset=True)

        rows = list(qs[offset : offset + limit + 1])
        has_more = len(rows) > limit
        page = rows[:limit]
        next_c = _cursor_search_offset(offset + limit) if has_more else None
        return EntryListPageResult(entries=page, next_cursor=next_c, has_more=has_more, reset=False)

    qs = queryset.with_hot_rank().order_by("-hot_rank", "-created_at", "-id")
    cur = parsed_after
    if cur and cur.get("k") == "hot":
        try:
            ca = datetime.fromisoformat(cur["ca"])
            qs = qs.filter(
                _q_after_hot(
                    float(cur["hr"]),
                    ca,
                    int(cur["id"]),
                )
            )
        except (KeyError, TypeError, ValueError):
            return EntryListPageResult(entries=[], next_cursor=None, has_more=False, reset=True)
    elif cur:
        return EntryListPageResult(entries=[], next_cursor=None, has_more=False, reset=True)

    rows = list(qs[: limit + 1])
    has_more = len(rows) > limit
    page = rows[:limit]
    next_c = _cursor_from_entry_hot(page[-1]) if has_more else None
    return EntryListPageResult(entries=page, next_cursor=next_c, has_more=has_more, reset=False)
