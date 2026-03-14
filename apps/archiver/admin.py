from django.contrib import admin

from .models import ArchiveRecord


@admin.register(ArchiveRecord)
class ArchiveRecordAdmin(admin.ModelAdmin):
    list_display = ("id", "definition", "snapshot_type", "status", "created_at")
    list_filter = ("snapshot_type", "status")
    search_fields = ("source_url", "s3_path", "arweave_hash")
