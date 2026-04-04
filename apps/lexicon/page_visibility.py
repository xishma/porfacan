"""Who may see lexicon CMS pages (optional auth.Group restriction)."""

from __future__ import annotations

from django.db.models import Count, Q

from .models import Page


def filter_pages_visible_to_user(queryset, user):
    """
    Restrict queryset to pages the user may access on the public site.

    Pages with no `visible_to_groups` are public (among published). If any group
    is set, the user must be in at least one of them. Staff bypass is handled
    by the caller (views); this helper assumes non-staff callers only.
    """
    qs = queryset.annotate(_lexicon_page_group_count=Count("visible_to_groups", distinct=True))
    if user.is_authenticated:
        gids = list(user.groups.values_list("id", flat=True))
        return qs.filter(Q(_lexicon_page_group_count=0) | Q(visible_to_groups__id__in=gids)).distinct()
    return qs.filter(_lexicon_page_group_count=0)
