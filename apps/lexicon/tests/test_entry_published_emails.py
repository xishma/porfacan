import pytest
from django.core import mail
from django.urls import reverse

from apps.lexicon.models import Definition, Entry
from apps.users.email_unsubscribe import sign_email_notifications_unsubscribe
from apps.users.models import User


@pytest.mark.django_db
def test_verify_entry_sends_individual_emails_to_contributors(admin_client, entry_category):
    creator = User.objects.create_user(
        email="creator@example.com",
        password="password123",
        role=User.Roles.CONTRIBUTOR,
    )
    definer = User.objects.create_user(
        email="definer@example.com",
        password="password123",
        role=User.Roles.CONTRIBUTOR,
    )
    entry = Entry.objects.create(
        headword="کلمه تست",
        category=entry_category,
        is_verified=False,
        created_by=creator,
    )
    Definition.objects.create(
        entry=entry,
        content="معنی",
        author=definer,
    )

    mail.outbox.clear()
    response = admin_client.get(reverse("admin:lexicon_entry_verify", args=[entry.pk]))

    assert response.status_code == 302
    entry.refresh_from_db()
    assert entry.is_verified is True
    assert len(mail.outbox) == 2
    recipients = {m.to[0] for m in mail.outbox}
    assert recipients == {"creator@example.com", "definer@example.com"}
    for m in mail.outbox:
        assert m.to == [m.to[0]]
        assert len(m.alternatives) == 1
        assert m.alternatives[0][1] == "text/html"
        assert entry.headword in (m.body or "")
        html = m.alternatives[0][0]
        assert reverse("lexicon:entry-detail", kwargs={"slug": entry.slug}) in html


@pytest.mark.django_db
def test_verify_entry_skips_users_who_opted_out(admin_client, entry_category):
    creator = User.objects.create_user(
        email="quiet@example.com",
        password="password123",
        role=User.Roles.CONTRIBUTOR,
    )
    creator.receive_email_notifications = False
    creator.save(update_fields=["receive_email_notifications"])
    entry = Entry.objects.create(
        headword="بدون ایمیل",
        category=entry_category,
        is_verified=False,
        created_by=creator,
    )

    mail.outbox.clear()
    admin_client.get(reverse("admin:lexicon_entry_verify", args=[entry.pk]))

    assert len(mail.outbox) == 0


@pytest.mark.django_db
def test_unsubscribe_entry_published_without_login(client):
    user = User.objects.create_user(
        email="sub@example.com",
        password="password123",
        role=User.Roles.CONTRIBUTOR,
    )
    assert user.receive_email_notifications is True
    token = sign_email_notifications_unsubscribe(user.pk)
    response = client.get(reverse("users:email-unsubscribe-notifications", kwargs={"token": token}))
    assert response.status_code == 200
    user.refresh_from_db()
    assert user.receive_email_notifications is False


@pytest.mark.django_db
def test_unsubscribe_invalid_token(client):
    response = client.get(
        reverse("users:email-unsubscribe-notifications", kwargs={"token": "not-a-valid-token"})
    )
    assert response.status_code == 400
