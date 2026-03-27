import pytest

from apps.lexicon.models import Entry, Epoch


@pytest.mark.django_db
def test_entry_full_clean_accepts_persian_slug(entry_category):
    epoch = Epoch.objects.create(
        name="Unicode Slug Epoch",
        start_date="2017-01-01",
        end_date="2018-12-31",
        description="Unicode slug validation test",
    )
    entry = Entry.objects.create(
        headword="آزادی",
        slug="آزادی",
        is_verified=True,
        category=entry_category,
    )
    entry.epochs.add(epoch)

    entry.full_clean()
