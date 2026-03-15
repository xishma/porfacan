from django import forms
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _

from .models import Definition, DefinitionAttachment, Entry, Epoch
from .normalization import normalize_persian


class EntryForm(forms.ModelForm):
    class Meta:
        model = Entry
        fields = ("headword", "epoch", "etymology", "is_verified")
        labels = {
            "headword": _("Headword"),
            "epoch": _("Epoch"),
            "etymology": _("Etymology"),
            "is_verified": _("Verified"),
        }
        widgets = {
            "headword": forms.TextInput(attrs={"class": "w-full rounded-lg border border-slate-300 ps-3 pe-3 py-2"}),
            "epoch": forms.Select(attrs={"class": "w-full rounded-lg border border-slate-300 ps-3 pe-3 py-2"}),
            "etymology": forms.Textarea(
                attrs={"class": "w-full rounded-lg border border-slate-300 ps-3 pe-3 py-2", "rows": 4}
            ),
        }

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop("user", None)
        super().__init__(*args, **kwargs)
        self.fields["epoch"].queryset = Epoch.objects.filter(start_date__year__gte=2009, start_date__year__lte=2026)
        self.fields["epoch"].empty_label = _("Select epoch")
        if not self._can_manage_verification():
            self.fields.pop("is_verified", None)

    def _can_manage_verification(self) -> bool:
        user = self.user
        if not user or not getattr(user, "is_authenticated", False):
            return False
        role = getattr(user, "role", None)
        return bool(user.is_superuser or role == "admin")

    def clean(self):
        cleaned_data = super().clean()
        cleaned_data["headword"] = normalize_persian(cleaned_data.get("headword", ""))
        cleaned_data["etymology"] = normalize_persian(cleaned_data.get("etymology", ""))
        return cleaned_data

    def clean_epoch(self):
        epoch = self.cleaned_data["epoch"]
        if not (2009 <= epoch.start_date.year <= 2026):
            raise ValidationError(_("Epoch must be between 2009 and 2026."))
        return epoch


class DefinitionForm(forms.ModelForm):
    class Meta:
        model = Definition
        fields = ("content",)
        labels = {
            "content": _("Definition text"),
        }
        widgets = {
            "content": forms.Textarea(
                attrs={"class": "w-full rounded-lg border border-slate-300 ps-3 pe-3 py-2", "rows": 5}
            ),
        }

    def clean(self):
        cleaned_data = super().clean()
        cleaned_data["content"] = normalize_persian(cleaned_data.get("content", ""))
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
