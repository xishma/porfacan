import pytest
from urllib.parse import quote_plus
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
def other_epoch(db):
    return Epoch.objects.create(
        name="Other Visibility Epoch",
        start_date="2017-01-01",
        end_date="2018-12-31",
        description="Secondary visibility tests",
    )


@pytest.fixture
def verified_entry(epoch):
    entry = Entry.objects.create(
        headword="پیروزی",
        is_verified=True,
    )
    entry.epochs.add(epoch)
    return entry


@pytest.fixture
def verified_entry_other_epoch(other_epoch):
    entry = Entry.objects.create(
        headword="پایداری",
        is_verified=True,
    )
    entry.epochs.add(other_epoch)
    return entry


@pytest.fixture
def unverified_entry(epoch):
    entry = Entry.objects.create(
        headword="ناپیدا",
        is_verified=False,
    )
    entry.epochs.add(epoch)
    return entry


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
def test_entry_search_rejects_low_quality_persian_fuzzy_matches(client, epoch):
    entry_one = Entry.objects.create(headword="آهو به کون", is_verified=True)
    entry_one.epochs.add(epoch)
    entry_two = Entry.objects.create(headword="زیرساخت به کون", is_verified=True)
    entry_two.epochs.add(epoch)

    response = client.get(reverse("lexicon:entry-list"), data={"q": "کونشسیششسیشسی"})

    assert response.status_code == 200
    content = response.content.decode()
    assert entry_one.headword not in content
    assert entry_two.headword not in content


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
    verified_content = verified_response.content.decode()
    assert f'?epoch={quote_plus("Visibility Epoch")}' in verified_content
    assert unverified_response.status_code == 404


@pytest.mark.django_db
def test_entry_epoch_filter_hides_other_epochs(
    client,
    epoch,
    verified_entry,
    verified_entry_other_epoch,
):
    response = client.get(reverse("lexicon:entry-list"), data={"epoch": epoch.name})

    assert response.status_code == 200
    content = response.content.decode()
    assert verified_entry.headword in content
    assert verified_entry_other_epoch.headword not in content


@pytest.mark.django_db
def test_entry_epoch_filter_with_search(
    client,
    epoch,
    verified_entry,
    verified_entry_other_epoch,
):
    response = client.get(
        reverse("lexicon:entry-list"),
        data={"q": "پی", "epoch": epoch.name},
    )

    assert response.status_code == 200
    content = response.content.decode()
    assert verified_entry.headword in content
    assert verified_entry_other_epoch.headword not in content
