import pytest

from apps.lexicon.models import Entry, Epoch


@pytest.mark.django_db
def test_entry_full_clean_accepts_persian_slug():
    epoch = Epoch.objects.create(
        name="Unicode Slug Epoch",
        start_date="2017-01-01",
        end_date="2018-12-31",
        description="Unicode slug validation test",
    )
    entry = Entry(
        headword="آزادی",
        slug="آزادی",
        epoch=epoch,
        etymology="",
        is_verified=True,
    )

    entry.full_clean()
