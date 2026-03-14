from django.db import models
from django.utils.translation import gettext_lazy as _


class ArchiveRecord(models.Model):
    class SnapshotType(models.TextChoices):
        SCREENSHOT = "screenshot", _("Screenshot")
        HTML = "html", _("HTML")

    class Status(models.TextChoices):
        PENDING = "pending", _("Pending")
        PROCESSING = "processing", _("Processing")
        SUCCESS = "success", _("Success")
        FAILED = "failed", _("Failed")

    definition = models.ForeignKey("lexicon.Definition", on_delete=models.CASCADE, related_name="archive_records")
    source_url = models.URLField()
    s3_path = models.CharField(max_length=500, blank=True)
    file_hash = models.CharField(max_length=128, blank=True)
    arweave_hash = models.CharField(max_length=200, blank=True)
    snapshot_type = models.CharField(max_length=20, choices=SnapshotType.choices, default=SnapshotType.SCREENSHOT)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    is_source_available = models.BooleanField(default=True)
    link_rot_flagged_at = models.DateTimeField(blank=True, null=True)
    last_verified_at = models.DateTimeField(blank=True, null=True)
    verification_error = models.CharField(max_length=300, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["status", "-created_at"]),
            models.Index(fields=["source_url"]),
        ]

    def __str__(self) -> str:
        return f"{self.definition_id}:{self.snapshot_type}:{self.status}"
