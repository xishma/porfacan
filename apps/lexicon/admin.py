from django.contrib import admin

from .models import Definition, DefinitionVote, Entry, Epoch


@admin.register(Epoch)
class EpochAdmin(admin.ModelAdmin):
    list_display = ("name", "start_date", "end_date")
    search_fields = ("name",)


@admin.register(Entry)
class EntryAdmin(admin.ModelAdmin):
    list_display = ("headword", "epoch", "is_verified", "created_at")
    list_filter = ("is_verified", "epoch")
    search_fields = ("headword", "slug")


@admin.register(Definition)
class DefinitionAdmin(admin.ModelAdmin):
    list_display = ("entry", "author", "upvotes", "downvotes", "reputation_score", "hot_score_value", "created_at")
    list_filter = ("created_at",)
    search_fields = ("entry__headword", "content")


@admin.register(DefinitionVote)
class DefinitionVoteAdmin(admin.ModelAdmin):
    list_display = ("definition", "user", "value", "created_at", "updated_at")
    list_filter = ("value", "created_at")
    search_fields = ("definition__entry__headword", "user__email")
