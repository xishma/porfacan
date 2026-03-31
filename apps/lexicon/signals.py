from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from .cache import bump_cache_version
from .headwords import refresh_entry_search_vector
from .models import Definition, DefinitionVote, Entry, EntryAlias, EntryCategory, Epoch, Page, SuggestedHeadword
from .normalization import normalize_persian
from .tasks import recompute_auto_similar_entries


@receiver(post_save, sender=SuggestedHeadword)
def ensure_entry_alias_when_suggestion_approved(sender, instance: SuggestedHeadword, **kwargs):
    if instance.status != SuggestedHeadword.Status.APPROVED:
        return
    norm = normalize_persian(instance.headword or "").strip()
    if not norm:
        return
    existing = EntryAlias.objects.filter(headword=norm).first()
    if existing is not None:
        if existing.entry_id == instance.entry_id:
            return
        return
    alias = EntryAlias(entry_id=instance.entry_id, headword=norm, created_by=None)
    try:
        alias.full_clean()
        alias.save()
    except ValidationError:
        pass


@receiver(post_save, sender=EntryAlias)
def refresh_search_vector_on_alias_save(sender, instance: EntryAlias, **kwargs):
    refresh_entry_search_vector(instance.entry_id)
    bump_cache_version("entry_search_results")
    bump_cache_version("entry_suggestions")


@receiver(post_delete, sender=EntryAlias)
def refresh_search_vector_on_alias_delete(sender, instance: EntryAlias, **kwargs):
    refresh_entry_search_vector(instance.entry_id)
    bump_cache_version("entry_search_results")
    bump_cache_version("entry_suggestions")


@receiver(post_save, sender=Entry)
def invalidate_entry_search_cache_on_entry_save(sender, instance: Entry, **kwargs):
    bump_cache_version("entry_search_results")
    bump_cache_version("entry_suggestions")


@receiver(post_save, sender=Entry)
def schedule_similar_entry_recompute(sender, instance: Entry, **kwargs):
    entry_id = instance.pk

    def enqueue():
        recompute_auto_similar_entries.delay(entry_id)

    if getattr(settings, "CELERY_TASK_ALWAYS_EAGER", False):
        enqueue()
    else:
        transaction.on_commit(enqueue)


@receiver(post_delete, sender=Entry)
def invalidate_entry_search_cache_on_entry_delete(sender, instance: Entry, **kwargs):
    bump_cache_version("entry_search_results")
    bump_cache_version("entry_suggestions")


@receiver(post_save, sender=Definition)
def invalidate_entry_search_cache_on_definition_save(sender, instance: Definition, **kwargs):
    bump_cache_version("entry_search_results")


@receiver(post_delete, sender=Definition)
def invalidate_entry_search_cache_on_definition_delete(sender, instance: Definition, **kwargs):
    bump_cache_version("entry_search_results")


@receiver(post_save, sender=Epoch)
def invalidate_entry_search_cache_on_epoch_save(sender, instance: Epoch, **kwargs):
    bump_cache_version("entry_search_results")


@receiver(post_delete, sender=Epoch)
def invalidate_entry_search_cache_on_epoch_delete(sender, instance: Epoch, **kwargs):
    bump_cache_version("entry_search_results")


@receiver(post_save, sender=EntryCategory)
def invalidate_entry_search_cache_on_entry_category_save(sender, instance: EntryCategory, **kwargs):
    bump_cache_version("entry_search_results")


@receiver(post_delete, sender=EntryCategory)
def invalidate_entry_search_cache_on_entry_category_delete(sender, instance: EntryCategory, **kwargs):
    bump_cache_version("entry_search_results")


@receiver(post_save, sender=Page)
def invalidate_pages_cache_on_page_save(sender, instance: Page, **kwargs):
    bump_cache_version("pages")


@receiver(post_delete, sender=Page)
def invalidate_pages_cache_on_page_delete(sender, instance: Page, **kwargs):
    bump_cache_version("pages")


@receiver(post_save, sender=DefinitionVote)
def update_vote_metrics_on_save(sender, instance: DefinitionVote, **kwargs):
    instance.definition.refresh_vote_metrics()
    bump_cache_version("entry_search_results")


@receiver(post_delete, sender=DefinitionVote)
def update_vote_metrics_on_delete(sender, instance: DefinitionVote, **kwargs):
    instance.definition.refresh_vote_metrics()
    bump_cache_version("entry_search_results")
