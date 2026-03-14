import logging
from hashlib import sha256
from io import BytesIO
from urllib.error import URLError, HTTPError
from urllib.request import Request, urlopen
from urllib.parse import urlparse

from celery import shared_task
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.db import transaction
from django.utils import timezone
from PIL import Image, ImageDraw

from .models import ArchiveRecord

logger = logging.getLogger(__name__)


def _capture_screenshot_bytes(url: str) -> bytes:
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        sync_playwright = None

    if sync_playwright:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=True)
            page = browser.new_page(viewport={"width": 1440, "height": 2048})
            page.goto(url, wait_until="domcontentloaded", timeout=30000)
            payload = page.screenshot(full_page=True, type="png")
            browser.close()
            return payload

    # Fallback image keeps the pipeline operational when Playwright is unavailable.
    image = Image.new("RGB", (1440, 900), color=(241, 245, 249))
    draw = ImageDraw.Draw(image)
    draw.text((40, 40), f"Playwright unavailable\nSource URL: {url}", fill=(15, 23, 42))
    buffer = BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()


def _send_hash_to_arweave_placeholder(file_hash: str):
    logger.info("Arweave placeholder invoked for hash=%s", file_hash)
    return ""


@shared_task(bind=True, autoretry_for=(Exception,), retry_backoff=True, retry_kwargs={"max_retries": 3})
def archive_source_task(self, archive_record_id: int):
    record = ArchiveRecord.objects.select_related("definition").get(id=archive_record_id)
    record.status = ArchiveRecord.Status.PROCESSING
    record.updated_at = timezone.now()
    record.save(update_fields=["status", "updated_at"])

    screenshot_bytes = _capture_screenshot_bytes(record.source_url)
    digest = sha256(screenshot_bytes).hexdigest()
    host = urlparse(record.source_url).netloc or "source"
    file_name = f"archives/{record.id}/{host}-{timezone.now().strftime('%Y%m%d%H%M%S')}.png"
    storage_path = default_storage.save(file_name, ContentFile(screenshot_bytes))
    arweave_hash = _send_hash_to_arweave_placeholder(digest)

    record.s3_path = storage_path
    record.file_hash = digest
    record.arweave_hash = arweave_hash
    record.status = ArchiveRecord.Status.SUCCESS
    record.updated_at = timezone.now()
    record.save(update_fields=["s3_path", "file_hash", "arweave_hash", "status", "updated_at"])
    return record.id


@shared_task(bind=True)
def reverify_archive_links_task(self):
    now = timezone.now()
    stale_records = ArchiveRecord.objects.filter(status=ArchiveRecord.Status.SUCCESS)
    for record in stale_records.iterator():
        available = True
        verification_error = ""
        try:
            request = Request(record.source_url, method="HEAD")
            with urlopen(request, timeout=10) as response:  # noqa: S310
                status_code = int(getattr(response, "status", 0))
                if status_code >= 400:
                    available = False
                    verification_error = f"HTTP status {status_code}"
        except (HTTPError, URLError) as exc:
            available = False
            verification_error = str(exc)

        update_fields = {
            "is_source_available": available,
            "last_verified_at": now,
            "verification_error": verification_error,
            "link_rot_flagged_at": None if available else now,
            "updated_at": now,
        }
        with transaction.atomic():
            ArchiveRecord.objects.filter(pk=record.pk).update(**update_fields)
