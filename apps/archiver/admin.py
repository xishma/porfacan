from django.contrib import admin

from .models import ArchiveRecord


@admin.register(ArchiveRecord)
class ArchiveRecordAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "definition",
        "snapshot_type",
        "status",
        "is_source_available",
        "last_verified_at",
        "created_at",
    )
    list_filter = ("snapshot_type", "status", "is_source_available")
    search_fields = ("source_url", "s3_path", "file_hash", "arweave_hash")
