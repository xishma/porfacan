import pytest

from apps.lexicon.models import EntryCategory


@pytest.fixture
def entry_category(db):
    return EntryCategory.objects.get(slug="general")
