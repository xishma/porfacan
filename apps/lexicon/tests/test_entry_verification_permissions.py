import pytest
from allauth.account.models import EmailAddress
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse

from apps.lexicon.forms import EntryForm
from apps.lexicon.models import Definition, DefinitionAttachment, Entry, Epoch
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
def test_entry_form_hides_is_verified_for_admin_on_create():
    admin = User.objects.create_user(
        email="admin@example.com",
        password="password123",
        role=User.Roles.ADMIN,
    )

    form = EntryForm(user=admin)

    assert "is_verified" not in form.fields


@pytest.mark.django_db
def test_entry_form_shows_is_verified_for_admin_on_update(epoch):
    admin = User.objects.create_user(
        email="admin-update@example.com",
        password="password123",
        role=User.Roles.ADMIN,
    )
    entry = Entry.objects.create(headword="امید")
    entry.epochs.add(epoch)

    form = EntryForm(user=admin, instance=entry)

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
            "epochs": [epoch.pk],
            "is_verified": "on",
        },
    )

    assert response.status_code == 302
    created = Entry.objects.get(headword="آزادی")
    assert created.is_verified is False


@pytest.mark.django_db
def test_admin_cannot_set_is_verified_on_create(client, epoch):
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
            "epochs": [epoch.pk],
            "is_verified": "on",
        },
    )

    assert response.status_code == 302
    created = Entry.objects.get(headword="امید")
    assert created.is_verified is False


@pytest.mark.django_db
def test_entry_form_hides_description_for_non_admin():
    contributor = User.objects.create_user(
        email="contributor-description@example.com",
        password="password123",
        role=User.Roles.CONTRIBUTOR,
    )
    form = EntryForm(user=contributor)
    assert "description" not in form.fields


@pytest.mark.django_db
def test_entry_form_shows_description_for_admin():
    admin = User.objects.create_user(
        email="admin-description@example.com",
        password="password123",
        role=User.Roles.ADMIN,
    )
    form = EntryForm(user=admin)
    assert "description" in form.fields


@pytest.mark.django_db
def test_entry_create_with_first_definition_content_creates_definition(client, epoch):
    contributor = User.objects.create_user(
        email="contributor-first-definition@example.com",
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
            "headword": "همبستگی",
            "epochs": [epoch.pk],
            "definition-content": "تعریف اولیه برای مدخل",
            "attachments-TOTAL_FORMS": "1",
            "attachments-INITIAL_FORMS": "0",
            "attachments-MIN_NUM_FORMS": "0",
            "attachments-MAX_NUM_FORMS": "5",
            "attachments-0-link": "",
        },
    )

    assert response.status_code == 302
    created = Entry.objects.get(headword="همبستگی")
    assert created.created_by == contributor
    definition = Definition.objects.get(entry=created)
    assert definition.author == contributor
    assert definition.content == "تعریف اولیه برای مدخل"


@pytest.mark.django_db
def test_entry_create_without_first_definition_content_skips_definition(client, epoch):
    contributor = User.objects.create_user(
        email="contributor-no-first-definition@example.com",
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
            "headword": "پیوستگی",
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
    created = Entry.objects.get(headword="پیوستگی")
    assert not Definition.objects.filter(entry=created).exists()


def _tiny_gif(name="example.gif"):
    return SimpleUploadedFile(
        name=name,
        content=(
            b"GIF89a\x01\x00\x01\x00\x80\x00\x00\x00\x00\x00"
            b"\xff\xff\xff!\xf9\x04\x01\x00\x00\x00\x00,\x00\x00"
            b"\x00\x00\x01\x00\x01\x00\x00\x02\x02D\x01\x00;"
        ),
        content_type="image/gif",
    )


@pytest.mark.django_db
def test_entry_create_with_initial_definition_examples_saves_attachments(client, epoch, settings, tmp_path):
    settings.MEDIA_ROOT = tmp_path
    contributor = User.objects.create_user(
        email="contributor-first-definition-examples@example.com",
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
            "headword": "همراهی",
            "epochs": [epoch.pk],
            "definition-content": "تعریف اولیه با مثال",
            "attachments-TOTAL_FORMS": "5",
            "attachments-INITIAL_FORMS": "0",
            "attachments-MIN_NUM_FORMS": "0",
            "attachments-MAX_NUM_FORMS": "5",
            "attachments-0-link": "https://example.com/source",
            "attachments-1-image": _tiny_gif(),
            "attachments-2-link": "",
            "attachments-3-link": "",
            "attachments-4-link": "",
        },
    )

    assert response.status_code == 302
    created = Entry.objects.get(headword="همراهی")
    definition = Definition.objects.get(entry=created)
    attachments = list(definition.attachments.order_by("id"))
    assert len(attachments) == 2
    assert attachments[0].link == "https://example.com/source"
    assert bool(attachments[1].image)
    assert DefinitionAttachment.objects.filter(definition=definition).count() == 2
