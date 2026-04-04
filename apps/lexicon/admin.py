from django import forms
from django.contrib import admin, messages
from django.contrib.admin.widgets import AutocompleteSelect
from django.shortcuts import get_object_or_404, redirect
from django.template.response import TemplateResponse
from django.urls import path, reverse
from django.utils import timezone
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _

from apps.users.models import User

from .headwords import merge_entries
from .models import (
    Definition,
    DefinitionAttachment,
    DefinitionVote,
    Entry,
    EntryAlias,
    EntryCategory,
    EntrySlugRedirect,
    Epoch,
    Page,
    SimilarEntryLink,
    SuggestedHeadword,
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


class EntryAliasInline(admin.TabularInline):
    model = EntryAlias
    extra = 0
    fields = ("headword", "created_at", "created_by")
    readonly_fields = ("created_at", "created_by")
    autocomplete_fields = ()


class MergeEntryForm(forms.Form):
    secondary = forms.ModelChoiceField(
        label=_("Secondary entry"),
        queryset=Entry.objects.none(),
        required=True,
        help_text=_(
            "Search by headword or slug. That entry will be merged into the primary and removed."
        ),
    )

    def __init__(self, *args, admin_site, primary_pk, **kwargs):
        super().__init__(*args, **kwargs)
        fk = SimilarEntryLink._meta.get_field("similar_entry")
        self.fields["secondary"].widget = AutocompleteSelect(fk, admin_site, attrs={})
        self.fields["secondary"].queryset = Entry.objects.exclude(pk=primary_pk)


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
    change_form_template = "admin/lexicon/entry/change_form.html"
    list_display = (
        "headword",
        "category",
        "display_epochs",
        "is_verified",
        "is_featured",
        "verify_action",
        "entry_page_link",
        "created_at",
    )
    list_filter = ("is_verified", "is_featured", "category", "epochs")
    search_fields = ("headword", "slug", "aliases__headword")
    filter_horizontal = ("epochs",)
    list_editable = ("is_verified",)
    readonly_fields = ("entry_page_link", "created_at", )
    exclude = ("search_vector",)
    inlines = (EntryAliasInline, SimilarEntryLinkInline)

    @staticmethod
    def _is_lexicon_admin(request) -> bool:
        u = request.user
        if not u.is_authenticated:
            return False
        if u.is_superuser:
            return True
        return getattr(u, "role", None) == User.Roles.ADMIN

    def get_readonly_fields(self, request, obj=None):
        ro = list(super().get_readonly_fields(request, obj))
        if not self._is_lexicon_admin(request):
            ro.append("is_featured")
        return ro

    def get_urls(self):
        info = self.model._meta.app_label, self.model._meta.model_name
        custom = [
            path(
                "<path:object_id>/verify/",
                self.admin_site.admin_view(self.verify_entry_admin_view),
                name="%s_%s_verify" % info,
            ),
            path(
                "<path:object_id>/merge/",
                self.admin_site.admin_view(self.merge_entry_admin_view),
                name="%s_%s_merge" % info,
            ),
        ]
        return custom + super().get_urls()

    def change_view(self, request, object_id, form_url="", extra_context=None):
        extra_context = extra_context or {}
        extra_context["merge_entry_url"] = reverse("admin:lexicon_entry_merge", args=[str(object_id)])
        return super().change_view(request, object_id, form_url, extra_context=extra_context)

    def merge_entry_admin_view(self, request, object_id):
        primary = get_object_or_404(Entry, pk=object_id)
        if not self.has_change_permission(request, primary):
            messages.error(request, _("You do not have permission to merge entries."))
            return redirect("admin:lexicon_entry_changelist")

        if request.method == "POST":
            form = MergeEntryForm(
                request.POST,
                admin_site=self.admin_site,
                primary_pk=primary.pk,
            )
            if form.is_valid():
                secondary = form.cleaned_data["secondary"]
                try:
                    merge_entries(primary_id=primary.pk, secondary_id=secondary.pk)
                except ValueError as exc:
                    messages.error(request, str(exc))
                else:
                    messages.success(
                        request,
                        _("Merged “%(sec)s” into “%(pri)s”. Definitions and alternate headwords were moved.")
                        % {"sec": secondary.headword, "pri": primary.headword},
                    )
                    return redirect("admin:lexicon_entry_change", object_id=primary.pk)
        else:
            form = MergeEntryForm(admin_site=self.admin_site, primary_pk=primary.pk)

        context = {
            **self.admin_site.each_context(request),
            "title": _("Merge another entry into this one"),
            "primary": primary,
            "form": form,
            "opts": self.model._meta,
            "has_view_permission": self.has_view_permission(request, primary),
        }
        return TemplateResponse(request, "admin/lexicon/merge_entry.html", context)

    def verify_entry_admin_view(self, request, object_id):
        entry = get_object_or_404(Entry, pk=object_id)
        if not self.has_change_permission(request, entry):
            messages.error(request, _("You do not have permission to verify entries."))
            return redirect("admin:lexicon_entry_changelist")
        if not entry.is_verified:
            entry.is_verified = True
            entry.save(update_fields=["is_verified"])
            messages.success(request, _("Entry was verified."))
        redirect_to = request.META.get("HTTP_REFERER") or reverse("admin:lexicon_entry_changelist")
        return redirect(redirect_to)

    @admin.display(description="Epochs")
    def display_epochs(self, obj):
        return ", ".join(obj.epochs.values_list("name", flat=True))

    @admin.display(description=_("Entry page"))
    def entry_page_link(self, obj):
        url = reverse("lexicon:entry-detail", kwargs={"slug": obj.slug})
        return format_html('<a href="{}" target="_blank" rel="noopener noreferrer">{}</a>', url, _("Open"))

    @admin.display(description=_("Verify"))
    def verify_action(self, obj):
        if obj.is_verified:
            return format_html('<span style="color: #15803d; font-weight: 600;">{}</span>', _("Verified"))
        url = reverse("admin:lexicon_entry_verify", args=[obj.pk])
        return format_html(
            '<a class="button" style="background: #16a34a; border-color: #15803d; color: #ffffff;" href="{}">{}</a>',
            url,
            _("Verify"),
        )


@admin.register(EntrySlugRedirect)
class EntrySlugRedirectAdmin(admin.ModelAdmin):
    list_display = ("slug", "entry", "entry_slug")
    search_fields = ("slug", "entry__headword")
    autocomplete_fields = ("entry",)

    @admin.display(description=_("Canonical slug"))
    def entry_slug(self, obj):
        return obj.entry.slug


def _approve_headword_suggestions(modeladmin, request, queryset):
    approved = 0
    now = timezone.now()
    for suggestion in queryset.filter(status=SuggestedHeadword.Status.PENDING):
        suggestion.status = SuggestedHeadword.Status.APPROVED
        suggestion.reviewed_by = request.user
        suggestion.reviewed_at = now
        suggestion.save(update_fields=["status", "reviewed_by", "reviewed_at"])
        approved += 1
    if approved:
        messages.success(request, _("Approved %(n)d suggestion(s).") % {"n": approved})


def _reject_headword_suggestions(modeladmin, request, queryset):
    n = 0
    now = timezone.now()
    for suggestion in queryset.filter(status=SuggestedHeadword.Status.PENDING):
        suggestion.status = SuggestedHeadword.Status.REJECTED
        suggestion.reviewed_by = request.user
        suggestion.reviewed_at = now
        suggestion.save(update_fields=["status", "reviewed_by", "reviewed_at"])
        n += 1
    if n:
        messages.success(request, _("Rejected %(n)d suggestion(s).") % {"n": n})


_approve_headword_suggestions.short_description = _("Approve selected (creates aliases)")
_reject_headword_suggestions.short_description = _("Reject selected")


@admin.register(SuggestedHeadword)
class SuggestedHeadwordAdmin(admin.ModelAdmin):
    list_display = (
        "headword",
        "entry",
        "entry_public_link",
        "submitted_by",
        "status",
        "verify_action",
        "reviewed_by",
        "reviewed_at",
        "created_at",
    )
    list_filter = ("status", "created_at")
    search_fields = ("headword", "entry__headword", "submitted_by__email")
    autocomplete_fields = ("entry", "submitted_by")
    fields = (
        "entry",
        "entry_public_link",
        "headword",
        "submitted_by",
        "status",
        "reviewed_by",
        "reviewed_at",
        "created_at",
    )
    readonly_fields = ("created_at", "reviewed_at", "reviewed_by", "entry_public_link")
    actions = (_approve_headword_suggestions, _reject_headword_suggestions)

    def get_urls(self):
        info = self.model._meta.app_label, self.model._meta.model_name
        custom = [
            path(
                "<path:object_id>/verify/",
                self.admin_site.admin_view(self.verify_suggestion_admin_view),
                name="%s_%s_verify" % info,
            ),
        ]
        return custom + super().get_urls()

    @admin.display(description=_("View entry"))
    def entry_public_link(self, obj):
        if obj is None or not getattr(obj, "entry_id", None):
            return "---"
        url = reverse("lexicon:entry-detail", kwargs={"slug": obj.entry.slug})
        return format_html(
            '<a href="{}" target="_blank" rel="noopener noreferrer">{}</a>',
            url,
            _("Open on site"),
        )

    def verify_suggestion_admin_view(self, request, object_id):
        suggestion = get_object_or_404(SuggestedHeadword, pk=object_id)
        if not self.has_change_permission(request, suggestion):
            messages.error(request, _("You do not have permission to verify suggested headwords."))
            return redirect("admin:lexicon_suggestedheadword_changelist")
        if suggestion.status == SuggestedHeadword.Status.PENDING:
            suggestion.status = SuggestedHeadword.Status.APPROVED
            suggestion.reviewed_at = timezone.now()
            suggestion.reviewed_by = request.user if request.user.is_authenticated else None
            suggestion.save(update_fields=["status", "reviewed_at", "reviewed_by"])
            messages.success(request, _("Suggested headword was verified."))
        redirect_to = request.META.get("HTTP_REFERER") or reverse("admin:lexicon_suggestedheadword_changelist")
        return redirect(redirect_to)

    @admin.display(description=_("Verify"))
    def verify_action(self, obj):
        if obj.status != SuggestedHeadword.Status.PENDING:
            if obj.status == SuggestedHeadword.Status.APPROVED:
                return format_html('<span style="color: #15803d; font-weight: 600;">{}</span>', _("Verified"))
            return "---"
        url = reverse("admin:lexicon_suggestedheadword_verify", args=[obj.pk])
        return format_html(
            '<a class="button" style="background: #16a34a; border-color: #15803d; color: #ffffff;" href="{}">{}</a>',
            url,
            _("Verify"),
        )

    def save_model(self, request, obj, form, change):
        if obj.status == SuggestedHeadword.Status.PENDING:
            obj.reviewed_at = None
            obj.reviewed_by = None
        else:
            old_status = form.initial.get("status") if change else None
            needs_stamp = (
                not change
                or old_status == SuggestedHeadword.Status.PENDING
                or (old_status is not None and old_status != obj.status)
            )
            if needs_stamp or obj.reviewed_at is None:
                obj.reviewed_at = timezone.now()
            if request.user.is_authenticated and (needs_stamp or obj.reviewed_by_id is None):
                obj.reviewed_by = request.user
        super().save_model(request, obj, form, change)


@admin.register(Definition)
class DefinitionAdmin(admin.ModelAdmin):
    list_display = (
        "entry",
        "author",
        "is_featured",
        "is_ai_generated",
        "upvotes",
        "downvotes",
        "reputation_score",
        "hot_score_value",
        "created_at",
    )
    list_filter = ("is_featured", "is_ai_generated", "created_at")
    list_editable = ("is_featured", "is_ai_generated")
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
