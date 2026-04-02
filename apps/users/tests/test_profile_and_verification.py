import pytest
from allauth.account.models import EmailAddress
from allauth.socialaccount.models import SocialAccount
from django.urls import reverse
from unittest.mock import patch

from apps.lexicon.models import Epoch
from apps.users.models import User


@pytest.mark.django_db
def test_register_sends_verification_email(client):
    with patch("apps.users.views.send_verification_email_task.delay") as mocked_delay:
        response = client.post(
            reverse("users:register"),
            data={
                "email": "new-user@example.com",
                "first_name": "New",
                "password1": "S3curePass!123",
                "password2": "S3curePass!123",
            },
        )

    assert response.status_code == 302
    user = User.objects.get(email="new-user@example.com")
    email_address = EmailAddress.objects.get(user=user, email=user.email, verified=False, primary=True)
    mocked_delay.assert_called_once_with(email_address.pk, signup=True)
    assert response.url == reverse("lexicon:entry-list")
    assert response.wsgi_request.user.is_authenticated
    assert response.wsgi_request.user.pk == user.pk


@pytest.mark.django_db
def test_unverified_user_cannot_access_contributor_view(client):
    Epoch.objects.create(
        name="Permission Epoch",
        start_date="2012-01-01",
        end_date="2012-12-31",
        description="permission test epoch",
    )
    user = User.objects.create_user(
        email="unverified@example.com",
        password="password123",
        role=User.Roles.CONTRIBUTOR,
    )
    client.force_login(user)

    response = client.get(reverse("lexicon:entry-create"))

    assert response.status_code == 403


@pytest.mark.django_db
def test_verified_user_can_access_contributor_view(client):
    Epoch.objects.create(
        name="Verified Epoch",
        start_date="2013-01-01",
        end_date="2013-12-31",
        description="verified permission test epoch",
    )
    user = User.objects.create_user(
        email="verified@example.com",
        password="password123",
        role=User.Roles.CONTRIBUTOR,
    )
    EmailAddress.objects.create(user=user, email=user.email, verified=True, primary=True)
    client.force_login(user)

    response = client.get(reverse("lexicon:entry-create"))

    assert response.status_code == 200


@pytest.mark.django_db
def test_profile_email_change_requires_reverification(client):
    user = User.objects.create_user(
        email="local-user@example.com",
        password="password123",
        role=User.Roles.CONTRIBUTOR,
        first_name="Local",
    )
    EmailAddress.objects.create(user=user, email=user.email, verified=True, primary=True)
    client.force_login(user)

    with patch("apps.users.views.send_verification_email_task.delay") as mocked_delay:
        response = client.post(
            reverse("users:profile"),
            data={
                "first_name": "Updated",
                "email": "local-user-updated@example.com",
            },
            follow=True,
        )

    user.refresh_from_db()
    assert response.status_code == 200
    assert user.email == "local-user-updated@example.com"
    email_address = EmailAddress.objects.get(
        user=user,
        email="local-user-updated@example.com",
        verified=False,
        primary=True,
    )
    mocked_delay.assert_called_once_with(email_address.pk, signup=False)


@pytest.mark.django_db
def test_social_user_cannot_change_email_from_profile(client):
    user = User.objects.create_user(
        email="social-user@example.com",
        password="password123",
        role=User.Roles.CONTRIBUTOR,
        first_name="Social",
    )
    EmailAddress.objects.create(user=user, email=user.email, verified=True, primary=True)
    SocialAccount.objects.create(user=user, provider="google", uid="social-user-uid")
    client.force_login(user)

    response = client.post(
        reverse("users:profile"),
        data={
            "first_name": "Changed",
            "email": "cannot-change@example.com",
        },
        follow=True,
    )

    user.refresh_from_db()
    assert response.status_code == 200
    assert user.first_name == "Changed"
    assert user.email == "social-user@example.com"
    assert not EmailAddress.objects.filter(user=user, email="cannot-change@example.com").exists()


@pytest.mark.django_db
def test_profile_can_resend_verification_email(client):
    user = User.objects.create_user(
        email="resend@example.com",
        password="password123",
        role=User.Roles.CONTRIBUTOR,
    )
    EmailAddress.objects.create(user=user, email=user.email, verified=False, primary=True)
    client.force_login(user)

    with patch("apps.users.views.send_verification_email_task.delay") as mocked_delay:
        response = client.post(reverse("users:resend-verification"), follow=True)

    assert response.status_code == 200
    email_address = EmailAddress.objects.get(user=user, email=user.email, verified=False, primary=True)
    mocked_delay.assert_called_once_with(email_address.pk, signup=False)
