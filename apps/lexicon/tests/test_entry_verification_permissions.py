import pytest
from allauth.account.models import EmailAddress
from django.urls import reverse

from apps.lexicon.forms import EntryForm
from apps.lexicon.models import Entry, Epoch
from apps.users.models import User


@pytest.fixture
def epoch(db):
    return Epoch.objects.create(
        name="Green Movement",
        start_date="2009-01-01",
        end_date="2010-12-31",
        description="Test epoch",
    )


@pytest.mark.django_db
def test_entry_form_hides_is_verified_for_non_admin():
    contributor = User.objects.create_user(
        email="contributor@example.com",
        password="password123",
        role=User.Roles.CONTRIBUTOR,
    )

    form = EntryForm(user=contributor)

    assert "is_verified" not in form.fields


@pytest.mark.django_db
def test_entry_form_shows_is_verified_for_admin():
    admin = User.objects.create_user(
        email="admin@example.com",
        password="password123",
        role=User.Roles.ADMIN,
    )

    form = EntryForm(user=admin)

    assert "is_verified" in form.fields


@pytest.mark.django_db
def test_contributor_cannot_set_is_verified_on_create(client, epoch):
    contributor = User.objects.create_user(
        email="contributor-create@example.com",
        password="password123",
        role=User.Roles.CONTRIBUTOR,
    )
    EmailAddress.objects.create(
        user=contributor,
        email=contributor.email,
        verified=True,
        primary=True,
    )
    client.force_login(contributor)

    response = client.post(
        reverse("lexicon:entry-create"),
        data={
            "headword": "آزادی",
            "epoch": epoch.pk,
            "etymology": "ریشه تست",
            "is_verified": "on",
        },
    )

    assert response.status_code == 302
    created = Entry.objects.get(headword="آزادی")
    assert created.is_verified is False


@pytest.mark.django_db
def test_admin_can_set_is_verified_on_create(client, epoch):
    admin = User.objects.create_user(
        email="admin-create@example.com",
        password="password123",
        role=User.Roles.ADMIN,
    )
    EmailAddress.objects.create(
        user=admin,
        email=admin.email,
        verified=True,
        primary=True,
    )
    client.force_login(admin)

    response = client.post(
        reverse("lexicon:entry-create"),
        data={
            "headword": "امید",
            "epoch": epoch.pk,
            "etymology": "ریشه تست",
            "is_verified": "on",
        },
    )

    assert response.status_code == 302
    created = Entry.objects.get(headword="امید")
    assert created.is_verified is True
