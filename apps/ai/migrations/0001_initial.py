from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="EntryAIDraftJob",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("headword", models.CharField(max_length=255, verbose_name="Headword")),
                ("prompt", models.TextField(verbose_name="Prompt")),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("pending", "Pending"),
                            ("running", "Running"),
                            ("succeeded", "Succeeded"),
                            ("failed", "Failed"),
                        ],
                        db_index=True,
                        default="pending",
                        max_length=16,
                        verbose_name="Status",
                    ),
                ),
                ("result_payload", models.JSONField(blank=True, null=True, verbose_name="Result payload")),
                ("raw_response", models.TextField(blank=True, verbose_name="Raw response")),
                ("error_message", models.TextField(blank=True, verbose_name="Error message")),
                ("created_at", models.DateTimeField(auto_now_add=True, verbose_name="Created at")),
                ("started_at", models.DateTimeField(blank=True, null=True, verbose_name="Started at")),
                ("finished_at", models.DateTimeField(blank=True, null=True, verbose_name="Finished at")),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=models.deletion.CASCADE,
                        related_name="entry_ai_draft_jobs",
                        to=settings.AUTH_USER_MODEL,
                        verbose_name="User",
                    ),
                ),
            ],
            options={
                "verbose_name": "Entry AI draft job",
                "verbose_name_plural": "Entry AI draft jobs",
                "ordering": ["-created_at"],
                "indexes": [
                    models.Index(fields=["user", "created_at"], name="ai_entryaidr_user_id_665f8c_idx"),
                    models.Index(fields=["status", "created_at"], name="ai_entryaidr_status_a47345_idx"),
                ],
            },
        ),
    ]
