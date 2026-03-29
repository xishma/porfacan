"""Contribution guide CMS page URL (see LEXICON_CONTRIBUTION_GUIDE_PAGE_ADDRESS)."""

from django.conf import settings
from django.urls import reverse


def get_contribution_guide_page_url() -> str:
    address = getattr(settings, "LEXICON_CONTRIBUTION_GUIDE_PAGE_ADDRESS", "contribute")
    return reverse("lexicon:page-detail", kwargs={"address": address})
