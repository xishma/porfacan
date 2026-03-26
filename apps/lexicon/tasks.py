from celery import shared_task
from django.contrib.postgres.search import TrigramSimilarity
from django.db.models import Max

from .models import Entry, EntryQuerySet, SimilarEntryLink

SIMILAR_AUTO_MAX = 8


@shared_task
def recompute_auto_similar_entries(entry_id: int) -> None:
    entry = Entry.objects.filter(pk=entry_id).first()
    if not entry:
        return

    SimilarEntryLink.objects.filter(entry_id=entry_id, is_auto=True).delete()

    headword = (entry.headword or "").strip()
    if not headword:
        return

    manual_ids = set(
        SimilarEntryLink.objects.filter(entry_id=entry_id).values_list("similar_entry_id", flat=True)
    )

    candidates = (
        Entry.objects.filter(is_verified=True)
        .exclude(pk=entry_id)
        .annotate(trigram_similarity=TrigramSimilarity("headword", headword))
        .filter(trigram_similarity__gte=EntryQuerySet.SUGGESTION_TRIGRAM_THRESHOLD)
        .order_by("-trigram_similarity", "-created_at")[: SIMILAR_AUTO_MAX * 3]
    )

    max_order = SimilarEntryLink.objects.filter(entry_id=entry_id).aggregate(m=Max("sort_order"))["m"]
    next_order = (max_order if max_order is not None else -1) + 1

    to_create = []
    for cand in candidates:
        if cand.pk in manual_ids:
            continue
        if len(to_create) >= SIMILAR_AUTO_MAX:
            break
        to_create.append(
            SimilarEntryLink(
                entry_id=entry_id,
                similar_entry_id=cand.pk,
                sort_order=next_order,
                is_auto=True,
            )
        )
        manual_ids.add(cand.pk)
        next_order += 1

    if to_create:
        SimilarEntryLink.objects.bulk_create(to_create)
