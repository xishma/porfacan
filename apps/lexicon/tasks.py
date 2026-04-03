from celery import shared_task
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.postgres.search import TrigramSimilarity
from django.core.mail import EmailMultiAlternatives
from django.db.models import Max
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils import translation
from django.utils.translation import gettext as _

from apps.users.email_unsubscribe import sign_email_notifications_unsubscribe

from .contribution_recipients import contributor_user_ids_for_entry
from .models import Entry, EntryQuerySet, SimilarEntryLink

SIMILAR_AUTO_MAX = 8


@shared_task
def recompute_auto_similar_entries(entry_id: int) -> None:
    entry = Entry.objects.filter(pk=entry_id).first()
    if not entry:
        return

    SimilarEntryLink.objects.filter(entry_id=entry_id, is_auto=True).delete()

    headword = (entry.headword or "").strip()
    if not headword:
        return

    manual_ids = set(
        SimilarEntryLink.objects.filter(entry_id=entry_id).values_list("similar_entry_id", flat=True)
    )

    candidates = (
        Entry.objects.filter(is_verified=True)
        .exclude(pk=entry_id)
        .annotate(trigram_similarity=TrigramSimilarity("headword", headword))
        .filter(trigram_similarity__gte=EntryQuerySet.SUGGESTION_TRIGRAM_THRESHOLD)
        .order_by("-trigram_similarity", "-created_at")[: SIMILAR_AUTO_MAX * 3]
    )

    max_order = SimilarEntryLink.objects.filter(entry_id=entry_id).aggregate(m=Max("sort_order"))["m"]
    next_order = (max_order if max_order is not None else -1) + 1

    to_create = []
    for cand in candidates:
        if cand.pk in manual_ids:
            continue
        if len(to_create) >= SIMILAR_AUTO_MAX:
            break
        to_create.append(
            SimilarEntryLink(
                entry_id=entry_id,
                similar_entry_id=cand.pk,
                sort_order=next_order,
                is_auto=True,
            )
        )
        manual_ids.add(cand.pk)
        next_order += 1

    if to_create:
        SimilarEntryLink.objects.bulk_create(to_create)


def _absolute_site_url(path: str) -> str:
    base = (getattr(settings, "SITE_CANONICAL_URL", "") or "").strip().rstrip("/")
    if not base:
        return path
    return f"{base}{path}" if path.startswith("/") else f"{base}/{path}"


@shared_task
def send_entry_published_notification_emails(entry_id: int) -> None:
    entry = Entry.objects.filter(pk=entry_id, is_verified=True).first()
    if not entry:
        return

    User = get_user_model()
    user_ids = contributor_user_ids_for_entry(entry)
    if not user_ids:
        return

    users = list(
        User.objects.filter(pk__in=user_ids, receive_email_notifications=True).exclude(email="")
    )
    if not users:
        return

    entry_path = reverse("lexicon:entry-detail", kwargs={"slug": entry.slug})
    entry_url = _absolute_site_url(entry_path)

    with translation.override(settings.LANGUAGE_CODE):
        subject = str(_("The entry you contributed to is now published on Porfacan"))
        from_email = settings.DEFAULT_FROM_EMAIL
        for user in users:
            unsubscribe_path = reverse(
                "users:email-unsubscribe-notifications",
                kwargs={"token": sign_email_notifications_unsubscribe(user.pk)},
            )
            ctx = {
                "user": user,
                "entry": entry,
                "entry_url": entry_url,
                "unsubscribe_url": _absolute_site_url(unsubscribe_path),
            }
            text_body = render_to_string("emails/entry_published_notification.txt", ctx)
            html_body = render_to_string("emails/entry_published_notification.html", ctx)
            msg = EmailMultiAlternatives(
                subject=subject,
                body=text_body,
                from_email=from_email,
                to=[user.email],
            )
            msg.attach_alternative(html_body, "text/html")
            msg.send()
