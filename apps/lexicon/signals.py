from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from .models import DefinitionVote


@receiver(post_save, sender=DefinitionVote)
def update_vote_metrics_on_save(sender, instance: DefinitionVote, **kwargs):
    instance.definition.refresh_vote_metrics()


@receiver(post_delete, sender=DefinitionVote)
def update_vote_metrics_on_delete(sender, instance: DefinitionVote, **kwargs):
    instance.definition.refresh_vote_metrics()
