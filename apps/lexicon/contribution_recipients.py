"""Users to notify when an entry becomes verified (published)."""

from .models import Definition, Entry, EntryAlias, SuggestedHeadword


def contributor_user_ids_for_entry(entry: Entry) -> set[int]:
    ids: set[int] = set()
    if entry.created_by_id:
        ids.add(entry.created_by_id)
    ids.update(Definition.objects.filter(entry_id=entry.pk).values_list("author_id", flat=True))
    ids.update(
        EntryAlias.objects.filter(entry_id=entry.pk)
        .exclude(created_by_id=None)
        .values_list("created_by_id", flat=True)
    )
    ids.update(
        SuggestedHeadword.objects.filter(entry_id=entry.pk)
        .exclude(submitted_by_id=None)
        .values_list("submitted_by_id", flat=True)
    )
    return ids
