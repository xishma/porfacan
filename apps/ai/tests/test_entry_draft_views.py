import json
from unittest.mock import patch

import pytest
from allauth.account.models import EmailAddress
from django.contrib.auth.models import Group
from django.urls import reverse

from apps.ai.models import EntryAIDraftJob
from apps.users.models import User


@pytest.fixture
def verified_contributor(db):
    user = User.objects.create_user(
        email="ai-contributor@example.com",
        password="password123",
        role=User.Roles.CONTRIBUTOR,
    )
    EmailAddress.objects.create(user=user, email=user.email, verified=True, primary=True)
    return user


@pytest.fixture
def ai_enabled_user(verified_contributor):
    group, _ = Group.objects.get_or_create(name="ai")
    verified_contributor.groups.add(group)
    return verified_contributor


@pytest.fixture
def other_verified_contributor(db):
    user = User.objects.create_user(
        email="ai-other@example.com",
        password="password123",
        role=User.Roles.CONTRIBUTOR,
    )
    EmailAddress.objects.create(user=user, email=user.email, verified=True, primary=True)
    return user


@pytest.mark.django_db
def test_create_job_requires_ai_group(client, verified_contributor):
    client.force_login(verified_contributor)
    response = client.post(
        reverse("ai:entry-draft-create"),
        data=json.dumps({"headword": "آزمایش"}),
        content_type="application/json",
    )
    assert response.status_code == 403


@pytest.mark.django_db
def test_create_job_enqueues_task(client, ai_enabled_user):
    client.force_login(ai_enabled_user)
    with patch("apps.ai.views.generate_entry_ai_draft.delay") as mocked_delay:
        response = client.post(
            reverse("ai:entry-draft-create"),
            data=json.dumps({"headword": "آزمایش"}),
            content_type="application/json",
        )
    assert response.status_code == 202
    payload = response.json()
    job = EntryAIDraftJob.objects.get(pk=payload["job_id"])
    assert job.headword == "آزمایش"
    mocked_delay.assert_called_once_with(job.id)


@pytest.mark.django_db
def test_status_view_returns_only_owner_job(client, ai_enabled_user, other_verified_contributor):
    group, _ = Group.objects.get_or_create(name="ai")
    other_verified_contributor.groups.add(group)
    own_job = EntryAIDraftJob.objects.create(
        user=ai_enabled_user,
        headword="واژه",
        prompt="p",
        status=EntryAIDraftJob.Status.SUCCEEDED,
        result_payload={"definition": "تعریف"},
    )
    other_job = EntryAIDraftJob.objects.create(
        user=other_verified_contributor,
        headword="دیگری",
        prompt="p",
        status=EntryAIDraftJob.Status.PENDING,
    )
    client.force_login(ai_enabled_user)

    ok_response = client.get(reverse("ai:entry-draft-status", kwargs={"job_id": own_job.id}))
    assert ok_response.status_code == 200
    assert ok_response.json()["status"] == EntryAIDraftJob.Status.SUCCEEDED
    assert "result" in ok_response.json()

    not_found_response = client.get(reverse("ai:entry-draft-status", kwargs={"job_id": other_job.id}))
    assert not_found_response.status_code == 404
