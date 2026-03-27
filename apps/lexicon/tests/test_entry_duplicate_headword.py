import pytest
from allauth.account.models import EmailAddress
from django.urls import reverse

from apps.lexicon.models import Definition, Entry, Epoch
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
def test_create_duplicate_verified_headword_shows_link(client, epoch, verified_contributor, entry_category):
    existing = Entry.objects.create(headword="یکسان", is_verified=True, category=entry_category)
    existing.epochs.add(epoch)

    client.force_login(verified_contributor)
    url = reverse("lexicon:entry-create")
    response = client.post(
        url,
        data={
            "headword": "یکسان",
            "category": entry_category.pk,
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
def test_create_duplicate_unverified_headword_merges_without_new_entry(
    client, epoch, verified_contributor, entry_category
):
    existing = Entry.objects.create(headword="در انتظار", is_verified=False, category=entry_category)
    existing.epochs.add(epoch)

    client.force_login(verified_contributor)
    response = client.post(
        reverse("lexicon:entry-create"),
        data={
            "headword": "در انتظار",
            "category": entry_category.pk,
            "epochs": [epoch.pk],
            "definition-content": "",
            "attachments-TOTAL_FORMS": "1",
            "attachments-INITIAL_FORMS": "0",
            "attachments-MIN_NUM_FORMS": "0",
            "attachments-MAX_NUM_FORMS": "5",
            "attachments-0-link": "",
        },
    )

    assert response.status_code == 302
    assert response.url == reverse("lexicon:entry-create")
    assert Entry.objects.filter(headword="در انتظار").count() == 1


@pytest.mark.django_db
def test_create_duplicate_unverified_headword_adds_second_definition(
    client, epoch, verified_contributor, verified_editor, entry_category
):
    existing = Entry.objects.create(
        headword="اشتراکی",
        is_verified=False,
        category=entry_category,
        created_by=verified_editor,
    )
    existing.epochs.add(epoch)
    Definition.objects.create(
        entry=existing,
        author=verified_editor,
        content="تعریف نخست",
    )

    client.force_login(verified_contributor)
    response = client.post(
        reverse("lexicon:entry-create"),
        data={
            "headword": "اشتراکی",
            "category": entry_category.pk,
            "epochs": [epoch.pk],
            "definition-content": "تعریف دوم از کاربر دیگر",
            "attachments-TOTAL_FORMS": "1",
            "attachments-INITIAL_FORMS": "0",
            "attachments-MIN_NUM_FORMS": "0",
            "attachments-MAX_NUM_FORMS": "5",
            "attachments-0-link": "",
        },
    )

    assert response.status_code == 302
    assert response.url == reverse("lexicon:entry-create")
    assert Entry.objects.filter(headword="اشتراکی").count() == 1
    assert Definition.objects.filter(entry=existing).count() == 2
    second = Definition.objects.get(entry=existing, author=verified_contributor)
    assert second.content == "تعریف دوم از کاربر دیگر"


@pytest.mark.django_db
def test_create_duplicate_unverified_same_user_can_add_second_definition(
    client, epoch, verified_contributor, entry_category
):
    existing = Entry.objects.create(
        headword="تک تکرار",
        is_verified=False,
        category=entry_category,
        created_by=verified_contributor,
    )
    existing.epochs.add(epoch)
    Definition.objects.create(
        entry=existing,
        author=verified_contributor,
        content="تعریف اول",
    )

    client.force_login(verified_contributor)
    response = client.post(
        reverse("lexicon:entry-create"),
        data={
            "headword": "تک تکرار",
            "category": entry_category.pk,
            "epochs": [epoch.pk],
            "definition-content": "تعریف دوم همان کاربر",
            "attachments-TOTAL_FORMS": "1",
            "attachments-INITIAL_FORMS": "0",
            "attachments-MIN_NUM_FORMS": "0",
            "attachments-MAX_NUM_FORMS": "5",
            "attachments-0-link": "",
        },
    )

    assert response.status_code == 302
    assert response.url == reverse("lexicon:entry-create")
    assert Definition.objects.filter(entry=existing, author=verified_contributor).count() == 2


@pytest.mark.django_db
def test_pending_headword_check_json(client, epoch, verified_contributor, entry_category):
    pending = Entry.objects.create(
        headword="در صف",
        is_verified=False,
        category=entry_category,
        description="ctx",
    )
    pending.epochs.add(epoch)
    Entry.objects.create(headword="تایید شده", is_verified=True, category=entry_category)

    client.force_login(verified_contributor)
    r1 = client.get(reverse("lexicon:entry-pending-headword"), {"q": "در صف"})
    assert r1.status_code == 200
    assert r1.json() == {
        "matches_pending": True,
        "category_id": entry_category.pk,
        "epoch_ids": [epoch.pk],
        "description": "ctx",
    }

    r2 = client.get(reverse("lexicon:entry-pending-headword"), {"q": "تایید شده"})
    assert r2.json() == {"matches_pending": False}

    r3 = client.get(reverse("lexicon:entry-pending-headword"), {"q": ""})
    assert r3.json() == {"matches_pending": False}


@pytest.mark.django_db
def test_update_entry_same_headword_ok(client, epoch, verified_editor, entry_category):
    entry = Entry.objects.create(headword="ثابت", is_verified=False, created_by=verified_editor, category=entry_category)
    entry.epochs.add(epoch)

    client.force_login(verified_editor)
    response = client.post(
        reverse("lexicon:entry-update", kwargs={"slug": entry.slug}),
        data={
            "headword": "ثابت",
            "category": entry_category.pk,
            "epochs": [epoch.pk],
        },
    )

    assert response.status_code == 302


@pytest.mark.django_db
def test_update_entry_headword_conflict(client, epoch, verified_editor, entry_category):
    a = Entry.objects.create(headword="الف", is_verified=True, category=entry_category)
    a.epochs.add(epoch)
    b = Entry.objects.create(headword="ب", is_verified=False, created_by=verified_editor, category=entry_category)
    b.epochs.add(epoch)

    client.force_login(verified_editor)
    response = client.post(
        reverse("lexicon:entry-update", kwargs={"slug": b.slug}),
        data={
            "headword": "الف",
            "category": entry_category.pk,
            "epochs": [epoch.pk],
        },
    )

    assert response.status_code == 200
    assert reverse("lexicon:entry-detail", kwargs={"slug": a.slug}) in response.content.decode()
