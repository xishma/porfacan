import pytest
from allauth.account.models import EmailAddress
from django.urls import reverse

from apps.lexicon.headwords import merge_entries
from apps.lexicon.models import Definition, Entry, EntryAlias, EntrySlugRedirect, Epoch, SuggestedHeadword
from apps.users.models import User


@pytest.fixture
def verified_contributor(db):
    user = User.objects.create_user(
        email="alias-contributor@example.com",
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
        email="alias-editor@example.com",
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


@pytest.fixture
def epoch(db):
    return Epoch.objects.create(
        name="Alias Epoch",
        start_date="2010-01-01",
        end_date=None,
        description="alias",
    )


@pytest.mark.django_db
def test_merge_moves_definitions_alias_and_slug_redirect(epoch, verified_editor, entry_category):
    primary = Entry.objects.create(
        headword="merge-primary",
        is_verified=True,
        category=entry_category,
        created_by=verified_editor,
    )
    primary.epochs.add(epoch)
    secondary = Entry.objects.create(
        headword="merge-secondary",
        is_verified=True,
        category=entry_category,
        created_by=verified_editor,
    )
    secondary.epochs.add(epoch)
    old_secondary_slug = secondary.slug
    Definition.objects.create(entry=secondary, author=verified_editor, content="merged-def")

    merge_entries(primary_id=primary.pk, secondary_id=secondary.pk)

    primary.refresh_from_db()
    assert not Entry.objects.filter(pk=secondary.pk).exists()
    assert Definition.objects.filter(entry=primary).count() == 1
    assert EntryAlias.objects.filter(entry=primary, headword="merge-secondary").exists()
    assert EntrySlugRedirect.objects.filter(slug=old_secondary_slug, entry=primary).exists()


@pytest.mark.django_db
def test_entry_detail_slug_redirect_permanent(client, epoch, verified_editor, entry_category):
    primary = Entry.objects.create(
        headword="canon",
        is_verified=True,
        category=entry_category,
        created_by=verified_editor,
    )
    primary.epochs.add(epoch)
    secondary = Entry.objects.create(
        headword="old-title",
        is_verified=True,
        category=entry_category,
        created_by=verified_editor,
    )
    secondary.epochs.add(epoch)
    old_slug = secondary.slug
    merge_entries(primary_id=primary.pk, secondary_id=secondary.pk)

    url = reverse("lexicon:entry-detail", kwargs={"slug": old_slug})
    response = client.get(url, follow=False)
    assert response.status_code == 301
    assert response.url == reverse("lexicon:entry-detail", kwargs={"slug": primary.slug})


@pytest.mark.django_db
def test_search_includes_alias_headword(epoch, verified_editor, entry_category):
    entry = Entry.objects.create(
        headword="main-title",
        is_verified=True,
        category=entry_category,
        created_by=verified_editor,
    )
    entry.epochs.add(epoch)
    EntryAlias.objects.create(entry=entry, headword="other-title")

    hits = list(Entry.objects.filter(is_verified=True).search("other-title"))
    assert any(e.pk == entry.pk for e in hits)


@pytest.mark.django_db
def test_suggest_headword_creates_pending(epoch, verified_contributor, entry_category, client):
    entry = Entry.objects.create(
        headword="suggest-target",
        is_verified=True,
        category=entry_category,
        created_by=verified_contributor,
    )
    entry.epochs.add(epoch)
    client.force_login(verified_contributor)
    url = reverse("lexicon:suggest-headword", kwargs={"slug": entry.slug})
    response = client.post(url, {"headword": "alternate-name"})
    assert response.status_code == 302
    assert SuggestedHeadword.objects.filter(
        entry=entry,
        headword="alternate-name",
        status=SuggestedHeadword.Status.PENDING,
        submitted_by=verified_contributor,
    ).exists()


@pytest.mark.django_db
def test_create_entry_rejects_headword_used_as_alias_elsewhere(
    client, epoch, verified_contributor, entry_category
):
    existing = Entry.objects.create(
        headword="primary-x",
        is_verified=True,
        category=entry_category,
    )
    existing.epochs.add(epoch)
    EntryAlias.objects.create(entry=existing, headword="alias-x")

    client.force_login(verified_contributor)
    response = client.post(
        reverse("lexicon:entry-create"),
        data={
            "headword": "alias-x",
            "category": entry_category.pk,
            "epochs": [epoch.pk],
        },
    )
    assert response.status_code == 200
    assert Entry.objects.filter(headword="alias-x").exclude(pk=existing.pk).count() == 0
