import pytest
from django.urls import reverse

from apps.lexicon.models import Entry, Epoch


@pytest.fixture
def epoch(db):
    return Epoch.objects.create(
        name="Visibility Epoch",
        start_date="2015-01-01",
        end_date="2016-12-31",
        description="Visibility tests",
    )


@pytest.fixture
def verified_entry(epoch):
    return Entry.objects.create(
        headword="پیروزی",
        epoch=epoch,
        etymology="verified",
        is_verified=True,
    )


@pytest.fixture
def unverified_entry(epoch):
    return Entry.objects.create(
        headword="ناپیدا",
        epoch=epoch,
        etymology="unverified",
        is_verified=False,
    )


@pytest.mark.django_db
def test_entry_list_hides_unverified_entries(client, verified_entry, unverified_entry):
    response = client.get(reverse("lexicon:entry-list"))

    assert response.status_code == 200
    content = response.content.decode()
    assert verified_entry.headword in content
    assert unverified_entry.headword not in content


@pytest.mark.django_db
def test_entry_search_hides_unverified_entries(client, verified_entry, unverified_entry):
    response = client.get(reverse("lexicon:entry-list"), data={"q": "پیروزی"})

    assert response.status_code == 200
    content = response.content.decode()
    assert verified_entry.headword in content
    assert unverified_entry.headword not in content


@pytest.mark.django_db
def test_entry_suggestion_hides_unverified_entries(client, verified_entry, unverified_entry):
    response = client.get(reverse("lexicon:entry-suggest"), data={"q": "پی"})

    assert response.status_code == 200
    payload = response.json()
    suggested_headwords = [item["headword"] for item in payload["results"]]
    assert unverified_entry.headword not in suggested_headwords
    assert verified_entry.headword in suggested_headwords


@pytest.mark.django_db
def test_unverified_entry_detail_is_not_visible(client, verified_entry, unverified_entry):
    verified_response = client.get(reverse("lexicon:entry-detail", kwargs={"slug": verified_entry.slug}))
    unverified_response = client.get(reverse("lexicon:entry-detail", kwargs={"slug": unverified_entry.slug}))

    assert verified_response.status_code == 200
    assert unverified_response.status_code == 404
