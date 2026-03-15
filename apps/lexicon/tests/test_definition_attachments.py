import pytest
from allauth.account.models import EmailAddress
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse

from apps.lexicon.models import Definition, DefinitionAttachment, Entry, Epoch
from apps.users.models import User


@pytest.fixture
def contributor(db):
    user = User.objects.create_user(
        email="contributor-attachments@example.com",
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
def entry(db):
    epoch = Epoch.objects.create(
        name="Attachment Epoch",
        start_date="2012-01-01",
        end_date="2012-12-31",
        description="Attachment tests",
    )
    return Entry.objects.create(
        headword="نمونه",
        epoch=epoch,
        etymology="attachment test",
        is_verified=True,
    )


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
def test_definition_create_saves_link_and_image_attachments(client, contributor, entry, settings, tmp_path):
    settings.MEDIA_ROOT = tmp_path
    client.force_login(contributor)

    response = client.post(
        reverse("lexicon:definition-create", kwargs={"slug": entry.slug}),
        data={
            "content": "این یک تعریف است",
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
    definition = Definition.objects.get(entry=entry)
    attachments = list(definition.attachments.order_by("id"))
    assert len(attachments) == 2
    assert attachments[0].link == "https://example.com/source"
    assert bool(attachments[1].image)


@pytest.mark.django_db
def test_definition_create_rejects_more_than_five_attachments(client, contributor, entry):
    client.force_login(contributor)

    response = client.post(
        reverse("lexicon:definition-create", kwargs={"slug": entry.slug}),
        data={
            "content": "تعریف با مثال زیاد",
            "attachments-TOTAL_FORMS": "6",
            "attachments-INITIAL_FORMS": "0",
            "attachments-MIN_NUM_FORMS": "0",
            "attachments-MAX_NUM_FORMS": "5",
            "attachments-0-link": "https://example.com/0",
            "attachments-1-link": "https://example.com/1",
            "attachments-2-link": "https://example.com/2",
            "attachments-3-link": "https://example.com/3",
            "attachments-4-link": "https://example.com/4",
            "attachments-5-link": "https://example.com/5",
        },
    )

    assert response.status_code == 200
    assert Definition.objects.filter(entry=entry).count() == 0
    assert DefinitionAttachment.objects.count() == 0


@pytest.mark.django_db
def test_user_cannot_add_second_definition_for_same_entry(client, contributor, entry):
    client.force_login(contributor)
    create_url = reverse("lexicon:definition-create", kwargs={"slug": entry.slug})

    first_response = client.post(
        create_url,
        data={
            "content": "تعریف اول",
            "attachments-TOTAL_FORMS": "1",
            "attachments-INITIAL_FORMS": "0",
            "attachments-MIN_NUM_FORMS": "0",
            "attachments-MAX_NUM_FORMS": "5",
            "attachments-0-link": "",
        },
    )
    assert first_response.status_code == 302

    second_response = client.get(create_url, follow=True)
    assert second_response.status_code == 200
    assert Definition.objects.filter(entry=entry, author=contributor).count() == 1
    response_html = second_response.content.decode()
    assert "Add definition" not in response_html
