from django.contrib import admin
from django.urls import reverse
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _

from .models import Definition, DefinitionAttachment, DefinitionVote, Entry, Epoch


@admin.register(Epoch)
class EpochAdmin(admin.ModelAdmin):
    list_display = ("name", "start_date", "end_date")
    search_fields = ("name",)


@admin.register(Entry)
class EntryAdmin(admin.ModelAdmin):
    list_display = ("headword", "display_epochs", "is_verified", "entry_page_link", "created_at")
    list_filter = ("is_verified", "epochs")
    search_fields = ("headword", "slug")
    filter_horizontal = ("epochs",)

    @admin.display(description="Epochs")
    def display_epochs(self, obj):
        return ", ".join(obj.epochs.values_list("name", flat=True))

    @admin.display(description=_("Entry page"))
    def entry_page_link(self, obj):
        url = reverse("lexicon:entry-detail", kwargs={"slug": obj.slug})
        return format_html('<a href="{}" target="_blank" rel="noopener noreferrer">{}</a>', url, _("Open"))


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
