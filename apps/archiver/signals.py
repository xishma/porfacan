from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import ArchiveRecord
from .tasks import archive_source_task


@receiver(post_save, sender=ArchiveRecord)
def trigger_archive_pipeline(sender, instance: ArchiveRecord, created: bool, **kwargs):
    if created and instance.status == ArchiveRecord.Status.PENDING:
        archive_source_task.delay(instance.id)
