import re

import pytest
from django.urls import reverse

from apps.lexicon.models import Definition, Entry, Epoch
from apps.users.models import User


def _article_count(html: str) -> int:
    return len(re.findall(r"<article\b", html))


@pytest.mark.django_db
def test_entry_list_feed_pages_by_ten(client):
    for i in range(12):
        Entry.objects.create(headword=f"scrollword{i}", is_verified=True)

    first = client.get(reverse("lexicon:entry-list-more"))
    assert first.status_code == 200
    p1 = first.json()
    assert p1["reset"] is False
    assert p1["has_more"] is True
    assert p1["next_cursor"]
    assert _article_count(p1["html"]) == 10

    second = client.get(reverse("lexicon:entry-list-more"), data={"after": p1["next_cursor"]})
    assert second.status_code == 200
    p2 = second.json()
    assert p2["reset"] is False
    assert p2["has_more"] is False
    assert _article_count(p2["html"]) == 2


@pytest.mark.django_db
def test_definition_feed_pages_by_ten(client):
    author = User.objects.create_user(
        email="def-scroll@example.com",
        password="password123",
        role=User.Roles.CONTRIBUTOR,
    )
    entry = Entry.objects.create(headword="scroll-entry", is_verified=True)
    for i in range(12):
        Definition.objects.create(entry=entry, author=author, content=f"def body {i}")

    url = reverse("lexicon:entry-definitions-more", kwargs={"slug": entry.slug})
    first = client.get(url)
    assert first.status_code == 200
    p1 = first.json()
    assert p1["reset"] is False
    assert p1["has_more"] is True
    assert p1["next_cursor"]
    assert _article_count(p1["html"]) == 10

    second = client.get(url, data={"after": p1["next_cursor"]})
    assert second.status_code == 200
    p2 = second.json()
    assert p2["reset"] is False
    assert p2["has_more"] is False
    assert _article_count(p2["html"]) == 2


@pytest.mark.django_db
def test_entry_list_feed_invalid_cursor_requests_reset(client):
    epoch = Epoch.objects.create(
        name="Epoch scroll",
        start_date="2020-01-01",
        end_date="2020-12-31",
        description="x",
    )
    e1 = Entry.objects.create(headword="onlyone", is_verified=True)
    e1.epochs.add(epoch)

    bogus = "not-valid-cursor"
    r = client.get(reverse("lexicon:entry-list-more"), data={"epoch": epoch.name, "after": bogus})
    assert r.status_code == 200
    assert r.json()["reset"] is True
