from django.db import models
from django.core.files.storage import default_storage
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

    definition = models.ForeignKey(
        "lexicon.Definition",
        on_delete=models.CASCADE,
        related_name="archive_records",
        verbose_name=_("Definition"),
    )
    source_url = models.URLField(verbose_name=_("Source URL"))
    s3_path = models.CharField(max_length=500, blank=True, verbose_name=_("S3 path"))
    file_hash = models.CharField(max_length=128, blank=True, verbose_name=_("File hash"))
    arweave_hash = models.CharField(max_length=200, blank=True, verbose_name=_("Arweave hash"))
    snapshot_type = models.CharField(
        max_length=20,
        choices=SnapshotType.choices,
        default=SnapshotType.SCREENSHOT,
        verbose_name=_("Snapshot type"),
    )
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING, verbose_name=_("Status"))
    is_source_available = models.BooleanField(default=True, verbose_name=_("Is source available"))
    link_rot_flagged_at = models.DateTimeField(blank=True, null=True, verbose_name=_("Link rot flagged at"))
    last_verified_at = models.DateTimeField(blank=True, null=True, verbose_name=_("Last verified at"))
    verification_error = models.CharField(max_length=300, blank=True, verbose_name=_("Verification error"))
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("Created at"))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_("Updated at"))

    class Meta:
        ordering = ["-created_at"]
        verbose_name = _("Archive record")
        verbose_name_plural = _("Archive records")
        indexes = [
            models.Index(fields=["status", "-created_at"]),
            models.Index(fields=["source_url"]),
        ]

    @property
    def artifact_url(self) -> str:
        if not self.s3_path:
            return ""
        return default_storage.url(self.s3_path)

    def __str__(self) -> str:
        return f"{self.definition_id}:{self.snapshot_type}:{self.status}"
