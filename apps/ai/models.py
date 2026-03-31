from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _


class EntryAIDraftJob(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", _("Pending")
        RUNNING = "running", _("Running")
        SUCCEEDED = "succeeded", _("Succeeded")
        FAILED = "failed", _("Failed")

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="entry_ai_draft_jobs",
        verbose_name=_("User"),
    )
    headword = models.CharField(max_length=255, verbose_name=_("Headword"))
    prompt = models.TextField(verbose_name=_("Prompt"))
    status = models.CharField(
        max_length=16,
        choices=Status.choices,
        default=Status.PENDING,
        db_index=True,
        verbose_name=_("Status"),
    )
    result_payload = models.JSONField(null=True, blank=True, verbose_name=_("Result payload"))
    raw_response = models.TextField(blank=True, verbose_name=_("Raw response"))
    error_message = models.TextField(blank=True, verbose_name=_("Error message"))
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("Created at"))
    started_at = models.DateTimeField(null=True, blank=True, verbose_name=_("Started at"))
    finished_at = models.DateTimeField(null=True, blank=True, verbose_name=_("Finished at"))

    class Meta:
        ordering = ["-created_at"]
        verbose_name = _("Entry AI draft job")
        verbose_name_plural = _("Entry AI draft jobs")
        indexes = [
            models.Index(fields=["user", "created_at"]),
            models.Index(fields=["status", "created_at"]),
        ]

    def __str__(self) -> str:
        return f"{self.headword} ({self.status})"
