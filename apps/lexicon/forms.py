from django import forms
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _

from apps.archiver.models import ArchiveRecord

from .models import Definition, Entry, Epoch
from .normalization import normalize_persian


class EntryForm(forms.ModelForm):
    class Meta:
        model = Entry
        fields = ("headword", "epoch", "etymology", "is_verified")
        widgets = {
            "headword": forms.TextInput(attrs={"class": "w-full rounded-lg border border-slate-300 ps-3 pe-3 py-2"}),
            "epoch": forms.Select(attrs={"class": "w-full rounded-lg border border-slate-300 ps-3 pe-3 py-2"}),
            "etymology": forms.Textarea(
                attrs={"class": "w-full rounded-lg border border-slate-300 ps-3 pe-3 py-2", "rows": 4}
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["epoch"].queryset = Epoch.objects.filter(start_date__year__gte=2009, start_date__year__lte=2026)
        self.fields["epoch"].empty_label = _("انتخاب دوره")

    def clean(self):
        cleaned_data = super().clean()
        cleaned_data["headword"] = normalize_persian(cleaned_data.get("headword", ""))
        cleaned_data["etymology"] = normalize_persian(cleaned_data.get("etymology", ""))
        return cleaned_data

    def clean_epoch(self):
        epoch = self.cleaned_data["epoch"]
        if not (2009 <= epoch.start_date.year <= 2026):
            raise ValidationError(_("دوره باید بین سال‌های ۲۰۰۹ تا ۲۰۲۶ باشد."))
        return epoch


class DefinitionForm(forms.ModelForm):
    source_url = forms.URLField(
        required=False,
        label=_("لینک منبع"),
        widget=forms.URLInput(attrs={"class": "w-full rounded-lg border border-slate-300 ps-3 pe-3 py-2"}),
    )

    class Meta:
        model = Definition
        fields = ("content", "context_annotation")
        widgets = {
            "content": forms.Textarea(
                attrs={"class": "w-full rounded-lg border border-slate-300 ps-3 pe-3 py-2", "rows": 5}
            ),
            "context_annotation": forms.Textarea(
                attrs={"class": "w-full rounded-lg border border-slate-300 ps-3 pe-3 py-2", "rows": 3}
            ),
        }

    def clean(self):
        cleaned_data = super().clean()
        cleaned_data["content"] = normalize_persian(cleaned_data.get("content", ""))
        cleaned_data["context_annotation"] = normalize_persian(cleaned_data.get("context_annotation", ""))
        return cleaned_data

    def save(self, author, entry, commit=True):
        definition = super().save(commit=False)
        definition.author = author
        definition.entry = entry
        if commit:
            definition.save()
            source_url = self.cleaned_data.get("source_url")
            if source_url:
                ArchiveRecord.objects.create(definition=definition, source_url=source_url)
        return definition
