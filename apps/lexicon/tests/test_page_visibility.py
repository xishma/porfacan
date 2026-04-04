import pytest
from django.contrib.auth.models import Group
from django.core.cache import cache
from django.test import Client
from django.urls import reverse

from apps.lexicon.cache import bump_cache_version
from apps.lexicon.context_processors import published_pages
from apps.lexicon.models import Page


@pytest.fixture
def clear_pages_cache():
    bump_cache_version("pages")
    cache.clear()
    yield
    bump_cache_version("pages")
    cache.clear()


@pytest.fixture
def inner_group(db):
    return Group.objects.create(name="inner_circle")


@pytest.fixture
def restricted_page(db, inner_group):
    page = Page.objects.create(
        address="secret-page",
        title="Secret",
        content="<p>Hidden</p>",
        is_published=True,
    )
    page.visible_to_groups.add(inner_group)
    return page


@pytest.fixture
def public_page(db):
    return Page.objects.create(
        address="public-page",
        title="Public",
        content="<p>Hi</p>",
        is_published=True,
    )


@pytest.mark.django_db
def test_restricted_page_404_anonymous(client: Client, restricted_page, clear_pages_cache):
    url = reverse("lexicon:page-detail", kwargs={"address": restricted_page.address})
    assert client.get(url).status_code == 404


@pytest.mark.django_db
def test_restricted_page_404_wrong_group(client: Client, django_user_model, restricted_page, clear_pages_cache):
    user = django_user_model.objects.create_user(email="nobody@example.com", password="pw")
    client.force_login(user)
    url = reverse("lexicon:page-detail", kwargs={"address": restricted_page.address})
    assert client.get(url).status_code == 404


@pytest.mark.django_db
def test_restricted_page_200_group_member(client: Client, django_user_model, restricted_page, inner_group, clear_pages_cache):
    user = django_user_model.objects.create_user(email="member@example.com", password="pw")
    user.groups.add(inner_group)
    client.force_login(user)
    url = reverse("lexicon:page-detail", kwargs={"address": restricted_page.address})
    response = client.get(url)
    assert response.status_code == 200
    assert b"Hidden" in response.content


@pytest.mark.django_db
def test_staff_sees_restricted_page_without_group(client: Client, django_user_model, restricted_page, clear_pages_cache):
    staff = django_user_model.objects.create_user(
        email="staff@example.com",
        password="pw",
        is_staff=True,
    )
    client.force_login(staff)
    url = reverse("lexicon:page-detail", kwargs={"address": restricted_page.address})
    assert client.get(url).status_code == 200


@pytest.mark.django_db
def test_published_pages_nav_filters_by_group(rf, django_user_model, restricted_page, public_page, inner_group, clear_pages_cache):
    from django.contrib.auth.models import AnonymousUser

    req = rf.get("/")
    req.user = AnonymousUser()
    nav = published_pages(req)["site_pages"]
    addresses = {p.address for p in nav}
    assert public_page.address in addresses
    assert restricted_page.address not in addresses

    user = django_user_model.objects.create_user(email="nav@example.com", password="pw")
    user.groups.add(inner_group)
    req.user = user
    nav = published_pages(req)["site_pages"]
    addresses = {p.address for p in nav}
    assert restricted_page.address in addresses
