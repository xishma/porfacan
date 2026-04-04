import pytest
from django.urls import reverse

from apps.lexicon.models import Definition, Entry, Epoch
from apps.users.models import User


@pytest.mark.django_db
def test_featured_definitions_are_ordered_first_and_badged(client, entry_category):
    epoch = Epoch.objects.create(
        name="Featured epoch",
        start_date="2020-01-01",
        end_date="2020-12-31",
        description="Featured ordering test",
    )
    author = User.objects.create_user(
        email="featured-author@example.com",
        password="password123",
        role=User.Roles.CONTRIBUTOR,
    )
    entry = Entry.objects.create(headword="نمونه", is_verified=True, category=entry_category)
    entry.epochs.add(epoch)

    regular_definition = Definition.objects.create(
        entry=entry,
        author=author,
        content="Regular definition",
        upvotes=100,
        downvotes=0,
    )
    featured_definition = Definition.objects.create(
        entry=entry,
        author=author,
        content="Featured definition",
        is_featured=True,
        upvotes=0,
        downvotes=0,
    )

    assert featured_definition.pk != regular_definition.pk

    response = client.get(reverse("lexicon:entry-detail", kwargs={"slug": entry.slug}))
    assert response.status_code == 200
    content = response.content.decode()

    assert content.index("Featured definition") < content.index("Regular definition")
    assert "Featured" in content


@pytest.mark.django_db
def test_ai_generated_definitions_show_badge(client, entry_category):
    epoch = Epoch.objects.create(
        name="AI epoch",
        start_date="2020-01-01",
        end_date="2020-12-31",
        description="AI badge test",
    )
    author_human = User.objects.create_user(
        email="ai-human@example.com",
        password="password123",
        role=User.Roles.CONTRIBUTOR,
    )
    author_ai = User.objects.create_user(
        email="ai-assisted@example.com",
        password="password123",
        role=User.Roles.CONTRIBUTOR,
    )
    entry = Entry.objects.create(headword="هوش", is_verified=True, category=entry_category)
    entry.epochs.add(epoch)

    Definition.objects.create(
        entry=entry,
        author=author_human,
        content="Human definition",
        is_ai_generated=False,
    )
    Definition.objects.create(
        entry=entry,
        author=author_ai,
        content="AI-assisted definition",
        is_ai_generated=True,
        is_featured=True,
    )

    response = client.get(reverse("lexicon:entry-detail", kwargs={"slug": entry.slug}))
    assert response.status_code == 200
    content = response.content.decode()
    assert "AI-generated" in content
    assert content.index("AI-assisted definition") < content.index("Human definition")
