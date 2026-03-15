import pytest
from allauth.account.models import EmailAddress
from django.urls import reverse

from apps.lexicon.models import Definition, Entry, Epoch
from apps.users.models import User


@pytest.fixture
def base_entry(db):
    epoch = Epoch.objects.create(
        name="Verification Epoch",
        start_date="2018-01-01",
        end_date="2018-12-31",
        description="verification tests",
    )
    return Entry.objects.create(
        headword="همبستگی",
        epoch=epoch,
        etymology="verification test",
        is_verified=True,
    )


@pytest.fixture
def definition_author(db):
    user = User.objects.create_user(
        email="definition-author@example.com",
        password="password123",
        role=User.Roles.CONTRIBUTOR,
    )
    EmailAddress.objects.create(user=user, email=user.email, verified=True, primary=True)
    return user


@pytest.mark.django_db
def test_unverified_user_sees_disabled_definition_and_vote_actions(client, base_entry, definition_author):
    Definition.objects.create(
        entry=base_entry,
        author=definition_author,
        content="تعریف آزمایشی",
    )
    unverified_user = User.objects.create_user(
        email="unverified-ui@example.com",
        password="password123",
        role=User.Roles.CONTRIBUTOR,
    )
    client.force_login(unverified_user)

    response = client.get(reverse("lexicon:entry-detail", kwargs={"slug": base_entry.slug}))

    assert response.status_code == 200
    html = response.content.decode()
    assert reverse("users:profile") in html
    assert "disabled" in html


@pytest.mark.django_db
def test_unverified_user_cannot_vote(client, base_entry, definition_author):
    definition = Definition.objects.create(
        entry=base_entry,
        author=definition_author,
        content="تعریف برای رای",
    )
    unverified_user = User.objects.create_user(
        email="unverified-vote@example.com",
        password="password123",
        role=User.Roles.CONTRIBUTOR,
    )
    client.force_login(unverified_user)

    response = client.post(
        reverse("lexicon:definition-vote", kwargs={"pk": definition.pk}),
        data={"value": "1"},
    )

    assert response.status_code == 403
    payload = response.json()
    assert "error" in payload
