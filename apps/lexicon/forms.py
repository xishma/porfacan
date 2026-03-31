from django import forms
from django.core.exceptions import ValidationError
from django.urls import reverse
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _

from .headwords import headword_reserved_for_other_entry
from .models import Definition, DefinitionAttachment, Entry, EntryAlias, EntryCategory, Epoch, SuggestedHeadword
from .normalization import normalize_persian


class EntryForm(forms.ModelForm):
    class Meta:
        model = Entry
        fields = ("headword", "category", "epochs", "description", "is_verified")
        labels = {
            "headword": _("Headword"),
            "category": _("Category"),
            "epochs": _("Epochs"),
            "description": _("Description"),
            "is_verified": _("Verified"),
        }
        widgets = {
            "headword": forms.TextInput(
                attrs={
                    "class": "w-full rounded-lg border border-slate-300 ps-3 pe-3 py-2",
                    "autocomplete": "off",
                    "autocorrect": "off",
                    "autocapitalize": "off",
                    "spellcheck": "false",
                }
            ),
            "category": forms.Select(
                attrs={
                    "class": (
                        "entry-category-select block w-full cursor-pointer rounded-lg border border-slate-300 "
                        "bg-white py-2.5 ps-3 pe-10 text-sm text-slate-900 shadow-sm transition-colors "
                        "hover:border-slate-400 "
                        "focus:border-slate-900 focus:outline-none focus:ring-2 focus:ring-slate-900/10 "
                        "disabled:cursor-not-allowed disabled:bg-slate-50 disabled:text-slate-500 "
                        "[appearance:none] [-webkit-appearance:none]"
                    ),
                }
            ),
            "epochs": forms.CheckboxSelectMultiple(),
            "description": forms.Textarea(
                attrs={"class": "w-full rounded-lg border border-slate-300 ps-3 pe-3 py-2", "rows": 4}
            ),
        }

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop("user", None)
        super().__init__(*args, **kwargs)
        self.fields["category"].queryset = EntryCategory.objects.all()
        self.fields["epochs"].queryset = Epoch.objects.all()
        if self._is_create_form() or not self._can_manage_verification():
            self.fields.pop("is_verified", None)
        if not self._can_manage_entry_description():
            self.fields.pop("description", None)

    def _is_create_form(self) -> bool:
        return not bool(getattr(self.instance, "pk", None))

    def _can_manage_verification(self) -> bool:
        user = self.user
        if not user or not getattr(user, "is_authenticated", False):
            return False
        role = getattr(user, "role", None)
        return bool(user.is_superuser or role == "admin")

    def _can_manage_entry_description(self) -> bool:
        return self._can_manage_verification()

    def clean(self):
        cleaned_data = super().clean()
        headword = normalize_persian(cleaned_data.get("headword", ""))
        cleaned_data["headword"] = headword
        if "description" in cleaned_data:
            cleaned_data["description"] = normalize_persian(cleaned_data.get("description", ""))

        if headword:
            exclude_pk = getattr(self.instance, "pk", None)
            if headword_reserved_for_other_entry(headword, exclude_entry_id=exclude_pk):
                other = Entry.objects.filter(headword=headword).exclude(pk=exclude_pk).first()
                if not other:
                    alias = EntryAlias.objects.filter(headword=headword).select_related("entry").first()
                    other = alias.entry if alias else None
                if other:
                    if other.is_verified:
                        url = reverse("lexicon:entry-detail", kwargs={"slug": other.slug})
                        raise ValidationError(
                            {
                                "headword": format_html(
                                    '{} <a href="{}" class="font-medium text-blue-700 underline hover:text-blue-900">{}</a>',
                                    _("This headword is already used (primary or alternate) on another entry."),
                                    url,
                                    _("View entry"),
                                ),
                            }
                        )
                    if not self._is_create_form():
                        raise ValidationError(
                            {
                                "headword": _(
                                    "This headword is already used on another entry that is pending verification."
                                ),
                            },
                        )

        return cleaned_data

    def clean_epochs(self):
        epochs = self.cleaned_data["epochs"]
        if not epochs:
            raise ValidationError(_("At least one epoch is required."))
        return epochs


class DefinitionForm(forms.ModelForm):
    class Meta:
        model = Definition
        fields = ("content", "context_annotation", "usage_example")
        labels = {
            "content": _("Meaning"),
            "context_annotation": _("Background and context"),
            "usage_example": _("Example of usage"),
        }
        help_texts = {
            "context_annotation": _("Optional."),
            "usage_example": _("Optional."),
        }
        widgets = {
            "content": forms.Textarea(
                attrs={"class": "w-full rounded-lg border border-slate-300 ps-3 pe-3 py-2", "rows": 5}
            ),
            "context_annotation": forms.Textarea(
                attrs={"class": "w-full rounded-lg border border-slate-300 ps-3 pe-3 py-2", "rows": 4}
            ),
            "usage_example": forms.Textarea(
                attrs={"class": "w-full rounded-lg border border-slate-300 ps-3 pe-3 py-2", "rows": 3}
            ),
        }

    def clean(self):
        cleaned_data = super().clean()
        cleaned_data["content"] = normalize_persian(cleaned_data.get("content", ""))
        cleaned_data["context_annotation"] = normalize_persian(cleaned_data.get("context_annotation", ""))
        cleaned_data["usage_example"] = normalize_persian(cleaned_data.get("usage_example", ""))
        return cleaned_data

    def save(self, author, entry, attachment_formset=None, commit=True):
        definition = super().save(commit=False)
        definition.author = author
        definition.entry = entry
        if commit:
            definition.save()
            if attachment_formset is not None:
                attachment_formset.save(definition=definition)
        return definition


class EntryInitialDefinitionForm(DefinitionForm):
    class Meta(DefinitionForm.Meta):
        pass

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["content"].required = False


class DefinitionAttachmentForm(forms.ModelForm):
    class Meta:
        model = DefinitionAttachment
        fields = ("link", "image")
        labels = {
            "link": _("Example link"),
            "image": _("Example image"),
        }
        widgets = {
            "link": forms.URLInput(attrs={"class": "w-full rounded-lg border border-slate-300 ps-3 pe-3 py-2"}),
            "image": forms.ClearableFileInput(attrs={"class": "w-full rounded-lg border border-slate-300 ps-3 pe-3 py-2"}),
        }

    def clean(self):
        cleaned_data = super().clean()
        link = cleaned_data.get("link")
        image = cleaned_data.get("image")
        if self.has_changed() and not link and not image:
            raise ValidationError(_("Each example must include at least a link or an image."))
        return cleaned_data


class DefinitionAttachmentBaseFormSet(forms.BaseFormSet):
    max_attachments = 5

    def clean(self):
        super().clean()
        if any(self.errors):
            return
        used_forms = 0
        for form in self.forms:
            if not hasattr(form, "cleaned_data"):
                continue
            if form.cleaned_data.get("link") or form.cleaned_data.get("image"):
                used_forms += 1
        if used_forms > self.max_attachments:
            raise ValidationError(_("A maximum of %(max)d examples is allowed."), params={"max": self.max_attachments})

    def save(self, definition):
        attachments = []
        for form in self.forms:
            if not form.cleaned_data:
                continue
            if not (form.cleaned_data.get("link") or form.cleaned_data.get("image")):
                continue
            attachment = form.save(commit=False)
            attachment.definition = definition
            attachment.save()
            attachments.append(attachment)
        return attachments


DefinitionAttachmentFormSet = forms.formset_factory(
    DefinitionAttachmentForm,
    formset=DefinitionAttachmentBaseFormSet,
    extra=1,
    max_num=5,
    validate_max=True,
)


class SuggestedHeadwordForm(forms.ModelForm):
    class Meta:
        model = SuggestedHeadword
        fields = ("headword",)
        labels = {"headword": _("Alternate headword")}
        widgets = {
            "headword": forms.TextInput(
                attrs={
                    "class": "w-full rounded-lg border border-slate-300 ps-3 pe-3 py-2",
                    "autocomplete": "off",
                    "autocorrect": "off",
                    "autocapitalize": "off",
                    "spellcheck": "false",
                    "placeholder": _("Also known as…"),
                }
            ),
        }

    def __init__(self, *args, entry: Entry, user, **kwargs):
        self.entry = entry
        self.user = user
        super().__init__(*args, **kwargs)

    def clean_headword(self):
        text = normalize_persian(self.cleaned_data.get("headword", "")).strip()
        if not text:
            raise ValidationError(_("Headword is required."))
        primary = normalize_persian(self.entry.headword or "")
        if text == primary:
            raise ValidationError(_("This matches the primary headword."))
        if EntryAlias.objects.filter(entry=self.entry, headword=text).exists():
            raise ValidationError(_("This alternate headword is already listed for this entry."))
        if headword_reserved_for_other_entry(text, exclude_entry_id=self.entry.pk):
            other = Entry.objects.filter(headword=text).first()
            if not other:
                alias = EntryAlias.objects.filter(headword=text).select_related("entry").first()
                other = alias.entry if alias else None
            if other:
                url = reverse("lexicon:entry-detail", kwargs={"slug": other.slug})
                raise ValidationError(
                    format_html(
                        '{} <a href="{}" class="font-medium text-blue-700 underline hover:text-blue-900">{}</a>',
                        _("This headword is already used elsewhere."),
                        url,
                        _("View entry"),
                    )
                )
            raise ValidationError(_("This headword is already used elsewhere."))
        if SuggestedHeadword.objects.filter(
            entry=self.entry,
            headword=text,
            status=SuggestedHeadword.Status.PENDING,
        ).exists():
            raise ValidationError(_("A pending suggestion already exists for this headword."))
        return text

    def save(self, commit=True):
        suggestion = super().save(commit=False)
        suggestion.entry = self.entry
        suggestion.submitted_by = self.user
        suggestion.status = SuggestedHeadword.Status.PENDING
        if commit:
            suggestion.save()
        return suggestion
