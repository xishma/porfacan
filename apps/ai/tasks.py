from celery import shared_task
from django.utils import timezone

from .models import EntryAIDraftJob
from .services import generate_entry_draft


@shared_task
def generate_entry_ai_draft(job_id: int) -> None:
    job = EntryAIDraftJob.objects.filter(pk=job_id).first()
    if not job:
        return
    if job.status not in (EntryAIDraftJob.Status.PENDING, EntryAIDraftJob.Status.RUNNING):
        return

    job.status = EntryAIDraftJob.Status.RUNNING
    job.started_at = timezone.now()
    job.error_message = ""
    job.save(update_fields=["status", "started_at", "error_message"])

    try:
        result = generate_entry_draft(job.headword)
    except Exception as exc:
        job.status = EntryAIDraftJob.Status.FAILED
        job.error_message = str(exc)[:2000]
        job.finished_at = timezone.now()
        job.save(update_fields=["status", "error_message", "finished_at"])
        return

    job.status = EntryAIDraftJob.Status.SUCCEEDED
    job.prompt = result.prompt
    job.raw_response = result.raw_response
    job.result_payload = result.payload
    job.finished_at = timezone.now()
    job.save(update_fields=["status", "prompt", "raw_response", "result_payload", "finished_at"])
