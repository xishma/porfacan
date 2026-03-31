"""Headword aliases, search vectors, and global headword reservation."""

from __future__ import annotations

from django.contrib.postgres.search import SearchVector, Value
from django.conf import settings
from django.db import transaction
from django.db.models import Max, Q

from .cache import bump_cache_version
from .normalization import normalize_persian


def refresh_entry_search_vector(entry_id: int) -> None:
    from .models import Entry, EntryAlias

    entry = Entry.objects.filter(pk=entry_id).first()
    if not entry:
        return
    aliases = list(EntryAlias.objects.filter(entry_id=entry_id).values_list("headword", flat=True))
    vectors = [SearchVector(Value(entry.headword or ""), weight="A", config="simple")]
    if aliases:
        vectors.append(SearchVector(Value(" ".join(aliases)), weight="B", config="simple"))
    combined = vectors[0]
    for part in vectors[1:]:
        combined = combined + part
    Entry.objects.filter(pk=entry_id).update(search_vector=combined)


def headword_reserved_for_other_entry(headword: str, *, exclude_entry_id: int | None) -> bool:
    from .models import Entry, EntryAlias

    hw = normalize_persian(headword or "").strip()
    if not hw:
        return False
    q_entry = Entry.objects.filter(headword=hw)
    q_alias = EntryAlias.objects.filter(headword=hw)
    if exclude_entry_id is not None:
        q_entry = q_entry.exclude(pk=exclude_entry_id)
        q_alias = q_alias.exclude(entry_id=exclude_entry_id)
    return q_entry.exists() or q_alias.exists()


def entry_matching_headword(headword: str):
    from .models import Entry, EntryAlias

    hw = normalize_persian(headword or "").strip()
    if not hw:
        return None
    entry = Entry.objects.filter(headword=hw).first()
    if entry:
        return entry
    alias = EntryAlias.objects.filter(headword=hw).select_related("entry").first()
    return alias.entry if alias else None


def pending_entry_matching_headword(headword: str):
    from .models import Entry, EntryAlias

    hw = normalize_persian(headword or "").strip()
    if not hw:
        return None
    entry = Entry.objects.filter(headword=hw, is_verified=False).order_by("created_at").first()
    if entry:
        return entry
    alias = (
        EntryAlias.objects.filter(headword=hw, entry__is_verified=False)
        .select_related("entry")
        .order_by("entry__created_at")
        .first()
    )
    return alias.entry if alias else None


@transaction.atomic
def merge_entries(*, primary_id: int, secondary_id: int) -> None:
    from .models import (
        Definition,
        Entry,
        EntryAlias,
        EntrySlugRedirect,
        SimilarEntryLink,
        SuggestedHeadword,
    )

    if primary_id == secondary_id:
        raise ValueError("Cannot merge an entry into itself.")
    primary = Entry.objects.select_for_update().filter(pk=primary_id).first()
    secondary = Entry.objects.select_for_update().filter(pk=secondary_id).first()
    if not primary or not secondary:
        raise ValueError("Both entries must exist.")

    primary_hw = normalize_persian(primary.headword or "")
    secondary_hw = normalize_persian(secondary.headword or "")

    incoming_similar = list(
        SimilarEntryLink.objects.filter(similar_entry_id=secondary_id).exclude(entry_id=primary_id)
    )

    SimilarEntryLink.objects.filter(Q(entry_id=secondary_id) | Q(similar_entry_id=secondary_id)).delete()

    Definition.objects.filter(entry_id=secondary_id).update(entry_id=primary_id)

    if secondary_hw and secondary_hw != primary_hw:
        EntryAlias.objects.get_or_create(entry_id=primary_id, headword=secondary_hw, defaults={})

    primary_alias_headwords = set(
        EntryAlias.objects.filter(entry_id=primary_id).values_list("headword", flat=True)
    )
    EntryAlias.objects.filter(entry_id=secondary_id, headword__in=primary_alias_headwords).delete()
    EntryAlias.objects.filter(entry_id=secondary_id, headword=primary_hw).delete()
    EntryAlias.objects.filter(entry_id=secondary_id).update(entry_id=primary_id)
    EntryAlias.objects.filter(entry_id=primary_id, headword=primary_hw).delete()

    EntrySlugRedirect.objects.update_or_create(slug=secondary.slug, defaults={"entry": primary})
    EntrySlugRedirect.objects.filter(entry_id=secondary_id).update(entry_id=primary_id)

    max_order = SimilarEntryLink.objects.filter(entry_id=primary_id).aggregate(m=Max("sort_order"))["m"]
    next_order = (max_order if max_order is not None else -1) + 1
    for link in incoming_similar:
        source_id = link.entry_id
        if source_id == secondary_id:
            continue
        _, created = SimilarEntryLink.objects.get_or_create(
            entry_id=source_id,
            similar_entry_id=primary_id,
            defaults={"sort_order": next_order, "is_auto": link.is_auto},
        )
        if created:
            next_order += 1

    pending_on_primary = set(
        SuggestedHeadword.objects.filter(
            entry_id=primary_id,
            status=SuggestedHeadword.Status.PENDING,
        ).values_list("headword", flat=True)
    )
    SuggestedHeadword.objects.filter(
        entry_id=secondary_id,
        status=SuggestedHeadword.Status.PENDING,
        headword__in=pending_on_primary,
    ).delete()
    SuggestedHeadword.objects.filter(entry_id=secondary_id).update(entry_id=primary_id)

    secondary_epoch_ids = list(secondary.epochs.values_list("pk", flat=True))
    if secondary_epoch_ids:
        primary.epochs.add(*secondary_epoch_ids)

    secondary.delete()
    refresh_entry_search_vector(primary_id)

    from .tasks import recompute_auto_similar_entries

    pid = primary_id

    def _enqueue_similar():
        recompute_auto_similar_entries.delay(pid)

    if getattr(settings, "CELERY_TASK_ALWAYS_EAGER", False):
        _enqueue_similar()
    else:
        transaction.on_commit(_enqueue_similar)

    bump_cache_version("entry_search_results")
    bump_cache_version("entry_suggestions")


def alternate_headwords_for_display(entry) -> list[str]:
    """Primary headword excluded. Merges EntryAlias rows and approved SuggestedHeadword rows (deduped)."""
    from .models import EntryAlias, SuggestedHeadword

    seen: set[str] = set()
    ordered: list[tuple[str, str]] = []

    def add(raw: str) -> None:
        text = (raw or "").strip()
        if not text:
            return
        key = normalize_persian(text)
        if not key or key in seen:
            return
        seen.add(key)
        ordered.append((key, text))

    aliases = list(entry.aliases.all())
    aliases.sort(key=lambda o: normalize_persian(o.headword or ""))
    for a in aliases:
        add(a.headword)

    pref = getattr(entry, "approved_suggestion_headwords", None)
    if pref is not None:
        approved = list(pref)
        approved.sort(key=lambda s: normalize_persian(s.headword or ""))
        for s in approved:
            add(s.headword)
    else:
        for s in SuggestedHeadword.objects.filter(
            entry_id=entry.pk,
            status=SuggestedHeadword.Status.APPROVED,
        ).order_by("headword"):
            add(s.headword)

    ordered.sort(key=lambda t: t[0])
    return [t[1] for t in ordered]
