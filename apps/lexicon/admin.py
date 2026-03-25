from django.contrib import admin

from .models import Definition, DefinitionAttachment, DefinitionVote, Entry, Epoch


@admin.register(Epoch)
class EpochAdmin(admin.ModelAdmin):
    list_display = ("name", "start_date", "end_date")
    search_fields = ("name",)


@admin.register(Entry)
class EntryAdmin(admin.ModelAdmin):
    list_display = ("headword", "display_epochs", "is_verified", "created_at")
    list_filter = ("is_verified", "epochs")
    search_fields = ("headword", "slug")

    @admin.display(description="Epochs")
    def display_epochs(self, obj):
        return ", ".join(obj.epochs.values_list("name", flat=True))


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


@admin.register(DefinitionAttachment)
class DefinitionAttachmentAdmin(admin.ModelAdmin):
    list_display = ("definition", "link", "created_at")
    list_filter = ("created_at",)
    search_fields = ("definition__entry__headword", "link")
