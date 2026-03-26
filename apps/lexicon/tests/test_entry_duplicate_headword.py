import pytest
from allauth.account.models import EmailAddress
from django.urls import reverse

from apps.lexicon.models import Entry, Epoch
from apps.users.models import User


@pytest.fixture
def epoch(db):
    return Epoch.objects.create(
        name="Dup Epoch",
        start_date="2010-01-01",
        end_date=None,
        description="dup",
    )


@pytest.fixture
def verified_contributor(db):
    user = User.objects.create_user(
        email="dup-verified@example.com",
        password="password123",
        role=User.Roles.CONTRIBUTOR,
    )
    EmailAddress.objects.create(
        user=user,
        email=user.email,
        verified=True,
        primary=True,
    )
    return user


@pytest.fixture
def verified_editor(db):
    user = User.objects.create_user(
        email="dup-editor@example.com",
        password="password123",
        role=User.Roles.EDITOR,
    )
    EmailAddress.objects.create(
        user=user,
        email=user.email,
        verified=True,
        primary=True,
    )
    return user


@pytest.mark.django_db
def test_create_duplicate_verified_headword_shows_link(client, epoch, verified_contributor):
    existing = Entry.objects.create(headword="یکسان", is_verified=True)
    existing.epochs.add(epoch)

    client.force_login(verified_contributor)
    url = reverse("lexicon:entry-create")
    response = client.post(
        url,
        data={
            "headword": "یکسان",
            "epochs": [epoch.pk],
        },
    )

    assert response.status_code == 200
    content = response.content.decode()
    assert "lexicon:entry-detail" not in content  # reverse name not in HTML
    detail_url = reverse("lexicon:entry-detail", kwargs={"slug": existing.slug})
    assert detail_url in content
    assert Entry.objects.filter(headword="یکسان").count() == 1


@pytest.mark.django_db
def test_create_duplicate_unverified_headword_message(client, epoch, verified_contributor):
    existing = Entry.objects.create(headword="در انتظار", is_verified=False)
    existing.epochs.add(epoch)

    client.force_login(verified_contributor)
    response = client.post(
        reverse("lexicon:entry-create"),
        data={
            "headword": "در انتظار",
            "epochs": [epoch.pk],
        },
    )

    assert response.status_code == 200
    content = response.content.decode()
    assert "انتظار تایید" in content


@pytest.mark.django_db
def test_update_entry_same_headword_ok(client, epoch, verified_editor):
    entry = Entry.objects.create(headword="ثابت", is_verified=False, created_by=verified_editor)
    entry.epochs.add(epoch)

    client.force_login(verified_editor)
    response = client.post(
        reverse("lexicon:entry-update", kwargs={"slug": entry.slug}),
        data={
            "headword": "ثابت",
            "epochs": [epoch.pk],
        },
    )

    assert response.status_code == 302


@pytest.mark.django_db
def test_update_entry_headword_conflict(client, epoch, verified_editor):
    a = Entry.objects.create(headword="الف", is_verified=True)
    a.epochs.add(epoch)
    b = Entry.objects.create(headword="ب", is_verified=False, created_by=verified_editor)
    b.epochs.add(epoch)

    client.force_login(verified_editor)
    response = client.post(
        reverse("lexicon:entry-update", kwargs={"slug": b.slug}),
        data={
            "headword": "الف",
            "epochs": [epoch.pk],
        },
    )

    assert response.status_code == 200
    assert reverse("lexicon:entry-detail", kwargs={"slug": a.slug}) in response.content.decode()
