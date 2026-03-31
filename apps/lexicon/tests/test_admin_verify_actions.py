import pytest
from django.urls import reverse

from apps.lexicon.models import Entry, SuggestedHeadword
from apps.users.models import User


@pytest.mark.django_db
def test_admin_verify_entry_button_endpoint_marks_entry_verified(admin_client, entry_category):
    entry = Entry.objects.create(headword="تایید سریع", category=entry_category, is_verified=False)

    response = admin_client.get(reverse("admin:lexicon_entry_verify", args=[entry.pk]))

    assert response.status_code == 302
    entry.refresh_from_db()
    assert entry.is_verified is True


@pytest.mark.django_db
def test_admin_verify_suggested_headword_endpoint_approves_pending(admin_client, admin_user, entry_category):
    submitter = User.objects.create_user(
        email="suggestion-submit@example.com",
        password="password123",
        role=User.Roles.CONTRIBUTOR,
    )
    entry = Entry.objects.create(headword="مدخل", category=entry_category, is_verified=True)
    suggestion = SuggestedHeadword.objects.create(
        entry=entry,
        headword="عنوان دیگر",
        submitted_by=submitter,
        status=SuggestedHeadword.Status.PENDING,
    )

    response = admin_client.get(reverse("admin:lexicon_suggestedheadword_verify", args=[suggestion.pk]))

    assert response.status_code == 302
    suggestion.refresh_from_db()
    assert suggestion.status == SuggestedHeadword.Status.APPROVED
    assert suggestion.reviewed_by_id == admin_user.id
    assert suggestion.reviewed_at is not None
