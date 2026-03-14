from django.conf import settings
from django.contrib.postgres.indexes import GinIndex
from django.contrib.postgres.search import SearchVectorField
from django.core.exceptions import ValidationError
from django.db import models
from django.utils.text import slugify
from django.utils.translation import gettext_lazy as _

from .normalization import normalize_persian
from .ranking import hot_score


class Epoch(models.Model):
    name = models.CharField(max_length=200, unique=True)
    start_date = models.DateField()
    end_date = models.DateField(blank=True, null=True)
    description = models.TextField()

    class Meta:
        ordering = ["start_date"]

    def clean(self):
        super().clean()
        if self.end_date and self.end_date < self.start_date:
            raise ValidationError(_("End date cannot be before start date."))

    def __str__(self) -> str:
        return self.name


class Entry(models.Model):
    headword = models.CharField(max_length=255, db_index=True)
    slug = models.SlugField(max_length=255, unique=True)
    epoch = models.ForeignKey(Epoch, on_delete=models.PROTECT, related_name="entries")
    created_at = models.DateTimeField(auto_now_add=True)
    is_verified = models.BooleanField(default=False)
    search_vector = SearchVectorField(blank=True, null=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [GinIndex(fields=["search_vector"])]

    def clean(self):
        super().clean()
        self.headword = normalize_persian(self.headword)

    def save(self, *args, **kwargs):
        self.headword = normalize_persian(self.headword)
        if not self.slug:
            self.slug = slugify(self.headword, allow_unicode=True)
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        return self.headword


class Definition(models.Model):
    entry = models.ForeignKey(Entry, on_delete=models.CASCADE, related_name="definitions")
    content = models.TextField()
    context_annotation = models.TextField(blank=True)
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="definitions")
    reputation_score = models.IntegerField(default=0)
    upvotes = models.PositiveIntegerField(default=0)
    downvotes = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["entry", "-created_at"]),
            models.Index(fields=["upvotes", "downvotes"]),
        ]

    def clean(self):
        super().clean()
        self.content = normalize_persian(self.content)
        self.context_annotation = normalize_persian(self.context_annotation)

    @property
    def hot_score(self) -> float:
        if self.created_at is None:
            return 0.0
        return hot_score(self.upvotes, self.downvotes, self.created_at)

    def sync_reputation_score(self):
        new_score = int(self.upvotes) - int(self.downvotes)
        delta = new_score - int(self.reputation_score)
        self.reputation_score = new_score
        self.save(update_fields=["reputation_score"])
        self.author.reputation_iq = self.author.reputation_iq + delta
        self.author.save(update_fields=["reputation_iq"])

    def __str__(self) -> str:
        return f"{self.entry.headword} ({self.author})"
