from django.contrib import admin
from django import forms
from django.urls import reverse
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _

from .models import (
    Definition,
    DefinitionAttachment,
    DefinitionVote,
    Entry,
    EntryCategory,
    Epoch,
    Page,
    SimilarEntryLink,
)


class SimilarEntryLinkInline(admin.TabularInline):
    model = SimilarEntryLink
    fk_name = "entry"
    extra = 0
    fields = ("similar_entry", "sort_order", "is_auto")
    readonly_fields = ("is_auto",)
    autocomplete_fields = ("similar_entry",)
    verbose_name = _("Similar entry")
    verbose_name_plural = _("Similar entries")


@admin.register(Epoch)
class EpochAdmin(admin.ModelAdmin):
    list_display = ("name", "start_date", "end_date")
    search_fields = ("name",)


@admin.register(EntryCategory)
class EntryCategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "slug")
    search_fields = ("name", "slug")
    prepopulated_fields = {"slug": ("name",)}


@admin.register(Entry)
class EntryAdmin(admin.ModelAdmin):
    list_display = ("headword", "category", "display_epochs", "is_verified", "entry_page_link", "created_at")
    list_filter = ("is_verified", "category", "epochs")
    search_fields = ("headword", "slug")
    filter_horizontal = ("epochs",)
    list_editable = ("is_verified",)
    inlines = (SimilarEntryLinkInline,)

    @admin.display(description="Epochs")
    def display_epochs(self, obj):
        return ", ".join(obj.epochs.values_list("name", flat=True))

    @admin.display(description=_("Entry page"))
    def entry_page_link(self, obj):
        url = reverse("lexicon:entry-detail", kwargs={"slug": obj.slug})
        return format_html('<a href="{}" target="_blank" rel="noopener noreferrer">{}</a>', url, _("Open"))


@admin.register(Definition)
class DefinitionAdmin(admin.ModelAdmin):
    list_display = (
        "entry",
        "author",
        "is_featured",
        "upvotes",
        "downvotes",
        "reputation_score",
        "hot_score_value",
        "created_at",
    )
    list_filter = ("is_featured", "created_at")
    list_editable = ("is_featured",)
    search_fields = ("entry__headword", "content", "context_annotation", "usage_example")


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


class PageAdminForm(forms.ModelForm):
    class Meta:
        model = Page
        fields = "__all__"
        widgets = {
            "content": forms.Textarea(attrs={"class": "js-page-wysiwyg", "rows": 18}),
        }

    class Media:
        css = {
            "all": ("css/admin/page_wysiwyg.css",),
        }
        js = (
            "https://cdn.ckeditor.com/ckeditor5/41.4.2/classic/ckeditor.js",
            "js/admin/page_wysiwyg.js",
        )


@admin.register(Page)
class PageAdmin(admin.ModelAdmin):
    form = PageAdminForm
    list_display = ("title", "address", "display_order", "is_published", "updated_at")
    list_filter = ("is_published",)
    search_fields = ("title", "address", "content")
    prepopulated_fields = {"address": ("title",)}
