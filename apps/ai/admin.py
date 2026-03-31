from django.contrib import admin

from .models import EntryAIDraftJob


@admin.register(EntryAIDraftJob)
class EntryAIDraftJobAdmin(admin.ModelAdmin):
    list_display = ("id", "headword", "user", "status", "created_at", "finished_at")
    list_filter = ("status", "created_at")
    search_fields = ("headword", "user__email")
    readonly_fields = ("created_at", "started_at", "finished_at")
