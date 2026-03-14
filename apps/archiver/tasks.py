import logging

from celery import shared_task
from django.utils import timezone

from .models import ArchiveRecord

logger = logging.getLogger(__name__)


@shared_task(bind=True, autoretry_for=(Exception,), retry_backoff=True, retry_kwargs={"max_retries": 3})
def capture_and_archive(self, archive_record_id: int):
    """
    Pipeline hook:
    1) capture source via Playwright/SingleFile
    2) upload artifact to S3
    3) submit payload to Arweave
    """
    record = ArchiveRecord.objects.get(id=archive_record_id)
    record.status = ArchiveRecord.Status.PROCESSING
    record.updated_at = timezone.now()
    record.save(update_fields=["status", "updated_at"])

    logger.info("Archive pipeline placeholder executed for record=%s", archive_record_id)

    record.status = ArchiveRecord.Status.SUCCESS
    record.updated_at = timezone.now()
    record.save(update_fields=["status", "updated_at"])
    return record.id
