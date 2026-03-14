from django.conf import settings
from django.contrib.postgres.indexes import GinIndex
from django.contrib.postgres.search import SearchQuery, SearchRank, SearchVector, SearchVectorField, TrigramSimilarity
from django.core.exceptions import ValidationError
from django.db.models import Case, Count, F, FloatField, IntegerField, Max, Q, QuerySet, Value, When
from django.db.models.functions import Coalesce
from django.db import models
from django.utils.text import slugify
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from .normalization import normalize_persian
from .ranking import hot_score


class EntryQuerySet(QuerySet):
    def with_hot_rank(self):
        return self.annotate(hot_rank=Coalesce(Max("definitions__hot_score_value"), Value(0.0), output_field=FloatField()))

    def search(self, query: str):
        normalized_query = normalize_persian(query or "").strip()
        if not normalized_query:
            return self

        query_expr = SearchQuery(normalized_query, search_type="websearch", config="simple")
        vector = (
            SearchVector("headword", weight="A", config="simple")
            + SearchVector("etymology", weight="B", config="simple")
            + SearchVector("definitions__content", weight="B", config="simple")
            + SearchVector("definitions__context_annotation", weight="C", config="simple")
        )
        return (
            self.annotate(
                search_rank=SearchRank(vector, query_expr),
                trigram_similarity=TrigramSimilarity("headword", normalized_query),
                starts_with=Case(
                    When(headword__istartswith=normalized_query, then=Value(1)),
                    default=Value(0),
                    output_field=IntegerField(),
                ),
            )
            .filter(
                Q(search_rank__gt=0)
                | Q(headword__icontains=normalized_query)
                | Q(trigram_similarity__gte=0.12)
            )
            .order_by("-starts_with", "-search_rank", "-trigram_similarity", "-created_at")
            .distinct()
        )

    def suggestions(self, query: str, limit: int = 8):
        normalized_query = normalize_persian(query or "").strip()
        if not normalized_query:
            return self.none()

        return (
            self.annotate(
                trigram_similarity=TrigramSimilarity("headword", normalized_query),
                starts_with=Case(
                    When(headword__istartswith=normalized_query, then=Value(1)),
                    default=Value(0),
                    output_field=IntegerField(),
                ),
            )
            .filter(
                Q(headword__icontains=normalized_query)
                | Q(trigram_similarity__gte=0.15)
            )
            .order_by("-starts_with", "-trigram_similarity", "-created_at")
            .values("headword", "slug")[:limit]
        )


class EntryManager(models.Manager.from_queryset(EntryQuerySet)):
    pass


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
    slug = models.SlugField(max_length=255, unique=True, allow_unicode=True)
    epoch = models.ForeignKey(Epoch, on_delete=models.PROTECT, related_name="entries")
    etymology = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    is_verified = models.BooleanField(default=False)
    search_vector = SearchVectorField(blank=True, null=True)

    objects = EntryManager()

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            GinIndex(fields=["search_vector"]),
            GinIndex(fields=["headword"], opclasses=["gin_trgm_ops"], name="lexicon_ent_headword_trgm"),
        ]

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
    hot_score_value = models.FloatField(default=0.0, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-hot_score_value", "-created_at"]
        indexes = [
            models.Index(fields=["entry", "-created_at"]),
            models.Index(fields=["upvotes", "downvotes"]),
            models.Index(fields=["hot_score_value"]),
        ]
        constraints = [
            models.UniqueConstraint(fields=["entry", "author"], name="lexicon_one_definition_per_user_entry"),
        ]

    def clean(self):
        super().clean()
        self.content = normalize_persian(self.content)
        self.context_annotation = normalize_persian(self.context_annotation)

    @property
    def hot_score(self) -> float:
        return float(self.hot_score_value or 0.0)

    def save(self, *args, **kwargs):
        self.content = normalize_persian(self.content)
        self.context_annotation = normalize_persian(self.context_annotation)
        created_at = self.created_at or timezone.now()
        self.hot_score_value = hot_score(self.upvotes, self.downvotes, created_at)
        super().save(*args, **kwargs)

    def refresh_vote_metrics(self):
        old_reputation = int(self.reputation_score)
        vote_counts = self.votes.aggregate(
            upvotes=Count("id", filter=Q(value=DefinitionVote.VoteValue.UPVOTE)),
            downvotes=Count("id", filter=Q(value=DefinitionVote.VoteValue.DOWNVOTE)),
        )
        new_upvotes = int(vote_counts["upvotes"] or 0)
        new_downvotes = int(vote_counts["downvotes"] or 0)
        new_reputation = new_upvotes - new_downvotes
        new_hot_score = hot_score(new_upvotes, new_downvotes, self.created_at or timezone.now())

        Definition.objects.filter(pk=self.pk).update(
            upvotes=new_upvotes,
            downvotes=new_downvotes,
            reputation_score=new_reputation,
            hot_score_value=new_hot_score,
        )

        delta = new_reputation - old_reputation
        if delta:
            from apps.users.models import User

            User.objects.filter(pk=self.author_id).update(
                reputation_iq=F("reputation_iq") + Value(delta, output_field=IntegerField())
            )

        self.upvotes = new_upvotes
        self.downvotes = new_downvotes
        self.reputation_score = new_reputation
        self.hot_score_value = new_hot_score

    def __str__(self) -> str:
        return f"{self.entry.headword} ({self.author})"


class DefinitionAttachment(models.Model):
    definition = models.ForeignKey(Definition, on_delete=models.CASCADE, related_name="attachments")
    link = models.URLField(blank=True)
    image = models.ImageField(upload_to="lexicon/definition_attachments/%Y/%m/%d", blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]
        constraints = [
            models.CheckConstraint(
                condition=~(Q(link="") & Q(image="")),
                name="lexicon_attachment_link_or_image_required",
            )
        ]

    def clean(self):
        super().clean()
        if not self.link and not self.image:
            raise ValidationError(_("At least one of link or image is required."))

    def __str__(self) -> str:
        return f"{self.definition_id}:{self.pk}"


class DefinitionVote(models.Model):
    class VoteValue(models.IntegerChoices):
        DOWNVOTE = -1, _("Downvote")
        UPVOTE = 1, _("Upvote")

    definition = models.ForeignKey(Definition, on_delete=models.CASCADE, related_name="votes")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="definition_votes")
    value = models.SmallIntegerField(choices=VoteValue.choices)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("definition", "user")
        indexes = [models.Index(fields=["definition", "value"])]

    def __str__(self) -> str:
        return f"{self.definition_id}:{self.user_id}:{self.value}"
