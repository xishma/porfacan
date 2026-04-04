from django.apps import apps
from django.conf import settings
from django.contrib.postgres.indexes import GinIndex, OpClass
from django.contrib.postgres.search import SearchQuery, SearchRank, SearchVector, SearchVectorField, TrigramSimilarity
from django.core.exceptions import ValidationError
from django.db.models import Case, Count, Exists, F, FloatField, IntegerField, Max, OuterRef, Q, QuerySet, Subquery, Value, When
from django.db.models.functions import Coalesce, Greatest
from django.db import models
from django.utils.text import slugify
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from .normalization import normalize_persian
from .ranking import hot_score


class EntryQuerySet(QuerySet):
    SEARCH_TRIGRAM_THRESHOLD = 0.32
    SUGGESTION_TRIGRAM_THRESHOLD = 0.2

    def with_hot_rank(self):
        return self.annotate(hot_rank=Coalesce(Max("definitions__hot_score_value"), Value(0.0), output_field=FloatField()))

    def search(self, query: str):
        EntryAlias = apps.get_model("lexicon", "EntryAlias")

        normalized_query = normalize_persian(query or "").strip()
        if not normalized_query:
            return self

        query_expr = SearchQuery(normalized_query, search_type="websearch", config="simple")
        definition_match_subquery = (
            Definition.objects.filter(entry_id=OuterRef("pk"))
            .annotate(
                definition_vector=SearchVector("content", weight="B", config="simple")
                + SearchVector("context_annotation", weight="C", config="simple")
                + SearchVector("usage_example", weight="C", config="simple")
            )
            .filter(definition_vector=query_expr)
        )
        alias_trigram_subq = Subquery(
            EntryAlias.objects.filter(entry_id=OuterRef("pk"))
            .annotate(t=TrigramSimilarity("headword", normalized_query))
            .order_by("-t")
            .values("t")[:1],
            output_field=FloatField(),
        )
        alias_icontains = Exists(
            EntryAlias.objects.filter(entry_id=OuterRef("pk"), headword__icontains=normalized_query)
        )
        alias_starts_with = Exists(
            EntryAlias.objects.filter(entry_id=OuterRef("pk"), headword__istartswith=normalized_query)
        )
        return (
            self.annotate(_alias_head_starts=alias_starts_with)
            .annotate(
                search_rank=Coalesce(SearchRank(F("search_vector"), query_expr), Value(0.0), output_field=FloatField()),
                has_definition_match=Exists(definition_match_subquery),
                trigram_similarity=TrigramSimilarity("headword", normalized_query),
                _alias_trg=Coalesce(alias_trigram_subq, Value(0.0), output_field=FloatField()),
                starts_with=Case(
                    When(
                        Q(headword__istartswith=normalized_query) | Q(_alias_head_starts=True),
                        then=Value(1),
                    ),
                    default=Value(0),
                    output_field=IntegerField(),
                ),
            )
            .annotate(combined_trigram=Greatest(F("trigram_similarity"), F("_alias_trg")))
            .filter(
                Q(search_rank__gt=0)
                | Q(has_definition_match=True)
                | Q(headword__icontains=normalized_query)
                | alias_icontains
                | Q(combined_trigram__gte=self.SEARCH_TRIGRAM_THRESHOLD)
            )
            .order_by(
                "-starts_with",
                "-has_definition_match",
                "-search_rank",
                "-combined_trigram",
                "-created_at",
            )
        )

    def suggestions(self, query: str, limit: int = 8):
        EntryAlias = apps.get_model("lexicon", "EntryAlias")

        normalized_query = normalize_persian(query or "").strip()
        if not normalized_query:
            return self.none()

        alias_overlap = Exists(
            EntryAlias.objects.filter(entry_id=OuterRef("pk")).filter(
                Q(headword__istartswith=normalized_query) | Q(headword__trigram_similar=normalized_query)
            )
        )
        alias_starts = Exists(
            EntryAlias.objects.filter(entry_id=OuterRef("pk"), headword__istartswith=normalized_query)
        )
        alias_trigram_subq = Subquery(
            EntryAlias.objects.filter(entry_id=OuterRef("pk"))
            .annotate(t=TrigramSimilarity("headword", normalized_query))
            .order_by("-t")
            .values("t")[:1],
            output_field=FloatField(),
        )
        return (
            self.filter(
                Q(headword__istartswith=normalized_query)
                | Q(headword__trigram_similar=normalized_query)
                | alias_overlap
            )
            .annotate(_alias_starts=alias_starts)
            .annotate(
                trigram_similarity=TrigramSimilarity("headword", normalized_query),
                _alias_trg=Coalesce(alias_trigram_subq, Value(0.0), output_field=FloatField()),
                starts_with=Case(
                    When(
                        Q(headword__istartswith=normalized_query) | Q(_alias_starts=True),
                        then=Value(1),
                    ),
                    default=Value(0),
                    output_field=IntegerField(),
                ),
            )
            .annotate(combined_trigram=Greatest(F("trigram_similarity"), F("_alias_trg")))
            .filter(
                Q(starts_with=1)
                | Q(combined_trigram__gte=self.SUGGESTION_TRIGRAM_THRESHOLD)
            )
            .order_by("-starts_with", "-combined_trigram", "-created_at")
            .values("headword", "slug")[:limit]
        )


class EntryManager(models.Manager.from_queryset(EntryQuerySet)):
    pass


class Epoch(models.Model):
    name = models.CharField(max_length=200, unique=True, verbose_name=_("Name"))
    start_date = models.DateField(verbose_name=_("Start date"))
    end_date = models.DateField(blank=True, null=True, verbose_name=_("End date"))
    description = models.TextField(verbose_name=_("Description"))

    class Meta:
        ordering = ["start_date"]
        verbose_name = _("Epoch")
        verbose_name_plural = _("Epochs")

    def clean(self):
        super().clean()
        if self.end_date and self.end_date < self.start_date:
            raise ValidationError(_("End date cannot be before start date."))

    def __str__(self) -> str:
        return self.name


class EntryCategory(models.Model):
    name = models.CharField(max_length=200, unique=True, verbose_name=_("Name"))
    slug = models.SlugField(max_length=255, unique=True, allow_unicode=True, verbose_name=_("Slug"))

    class Meta:
        ordering = ["name"]
        verbose_name = _("Entry category")
        verbose_name_plural = _("Entry categories")

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name, allow_unicode=True)
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        return self.name


class Page(models.Model):
    address = models.SlugField(max_length=255, unique=True, allow_unicode=True, verbose_name=_("Address"))
    title = models.CharField(max_length=255, verbose_name=_("Title"))
    content = models.TextField(verbose_name=_("Content"))
    display_order = models.PositiveSmallIntegerField(default=0, verbose_name=_("Display order"))
    is_published = models.BooleanField(default=True, verbose_name=_("Is published"))
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("Created at"))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_("Updated at"))

    class Meta:
        ordering = ["display_order", "title"]
        verbose_name = _("Page")
        verbose_name_plural = _("Pages")

    def __str__(self) -> str:
        return self.title


class Entry(models.Model):
    headword = models.CharField(max_length=255, db_index=True, verbose_name=_("Headword"))
    slug = models.SlugField(max_length=255, unique=True, allow_unicode=True, verbose_name=_("Slug"))
    category = models.ForeignKey(
        "EntryCategory",
        on_delete=models.PROTECT,
        related_name="entries",
        verbose_name=_("Category"),
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="entries",
        verbose_name=_("Created by"),
    )
    epochs = models.ManyToManyField(
        Epoch,
        related_name="entries",
        verbose_name=_("Epochs"),
        blank=True,
        help_text=_("Epochs that the entry belongs to. This is only visible to admins."),
    )
    description = models.TextField(
        blank=True,
        verbose_name=_("Description"),
        max_length=1024,
        help_text=_("A short description of the entry, this will be only visible to admins to know the context of the entry."),
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("Created at"))
    is_verified = models.BooleanField(default=False, verbose_name=_("Is verified"))
    search_vector = SearchVectorField(blank=True, null=True, verbose_name=_("Search vector"))

    objects = EntryManager()

    class Meta:
        ordering = ["headword"]
        verbose_name = _("Entry")
        verbose_name_plural = _("Entries")
        indexes = [
            GinIndex(fields=["search_vector"]),
            GinIndex(fields=["headword"], opclasses=["gin_trgm_ops"], name="lexicon_ent_headword_trgm"),
            models.Index(OpClass("headword", name="varchar_pattern_ops"), name="lex_ent_head_prefix_idx"),
            models.Index(fields=["is_verified", "headword"], name="lex_ent_ver_cr_idx"),
        ]

    def clean(self):
        super().clean()
        self.headword = normalize_persian(self.headword)

    def save(self, *args, **kwargs):
        self.headword = normalize_persian(self.headword)
        if not self.slug:
            self.slug = slugify(self.headword, allow_unicode=True)
        super().save(*args, **kwargs)
        from .headwords import refresh_entry_search_vector

        refresh_entry_search_vector(self.pk)

    def __str__(self) -> str:
        return self.headword


class EntryAlias(models.Model):
    entry = models.ForeignKey(
        Entry,
        on_delete=models.CASCADE,
        related_name="aliases",
        verbose_name=_("Entry"),
    )
    headword = models.CharField(max_length=255, verbose_name=_("Headword"))
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("Created at"))
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="entry_aliases_created",
        verbose_name=_("Created by"),
    )

    class Meta:
        ordering = ["headword"]
        verbose_name = _("Entry headword alias")
        verbose_name_plural = _("Entry headword aliases")
        constraints = [
            models.UniqueConstraint(fields=["headword"], name="lexicon_entryalias_headword_uniq"),
        ]
        indexes = [
            models.Index(fields=["entry"], name="lexicon_entryalias_entry_idx"),
            GinIndex(fields=["headword"], opclasses=["gin_trgm_ops"], name="lexicon_alias_headword_trgm"),
        ]

    def clean(self):
        super().clean()
        self.headword = normalize_persian(self.headword or "").strip()
        if not self.headword:
            raise ValidationError({"headword": _("Headword is required.")})
        if self.entry_id:
            entry = self.entry
            if self.headword == normalize_persian(entry.headword or ""):
                raise ValidationError({"headword": _("Alias must differ from the primary headword.")})
        qs_entry = Entry.objects.filter(headword=self.headword)
        qs_alias = EntryAlias.objects.filter(headword=self.headword)
        if self.pk:
            qs_alias = qs_alias.exclude(pk=self.pk)
        if qs_entry.exists():
            raise ValidationError({"headword": _("This headword is already a primary entry title.")})
        if qs_alias.exists():
            raise ValidationError({"headword": _("This headword is already used as an alias elsewhere.")})

    def save(self, *args, **kwargs):
        self.headword = normalize_persian(self.headword or "").strip()
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        return self.headword


class EntrySlugRedirect(models.Model):
    slug = models.SlugField(max_length=255, unique=True, allow_unicode=True, verbose_name=_("Slug"))
    entry = models.ForeignKey(
        Entry,
        on_delete=models.CASCADE,
        related_name="slug_redirects",
        verbose_name=_("Entry"),
    )

    class Meta:
        verbose_name = _("Entry slug redirect")
        verbose_name_plural = _("Entry slug redirects")

    def __str__(self) -> str:
        return f"{self.slug} → {self.entry_id}"


class SuggestedHeadword(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", _("Pending")
        APPROVED = "approved", _("Approved")
        REJECTED = "rejected", _("Rejected")

    entry = models.ForeignKey(
        Entry,
        on_delete=models.CASCADE,
        related_name="headword_suggestions",
        verbose_name=_("Entry"),
    )
    headword = models.CharField(max_length=255, verbose_name=_("Suggested headword"))
    submitted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="headword_suggestions_submitted",
        verbose_name=_("Submitted by"),
    )
    status = models.CharField(
        max_length=16,
        choices=Status.choices,
        default=Status.PENDING,
        db_index=True,
        verbose_name=_("Status"),
    )
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="headword_suggestions_reviewed",
        verbose_name=_("Reviewed by"),
    )
    reviewed_at = models.DateTimeField(null=True, blank=True, verbose_name=_("Reviewed at"))
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("Created at"))

    class Meta:
        ordering = ["-created_at"]
        verbose_name = _("Suggested headword")
        verbose_name_plural = _("Suggested headwords")
        constraints = [
            models.UniqueConstraint(
                fields=["entry", "headword"],
                condition=Q(status="pending"),
                name="lexicon_suggested_hw_pending_uniq",
            ),
        ]
        indexes = [
            models.Index(fields=["entry", "status"], name="lexicon_sugg_ent_stat_idx"),
        ]

    def clean(self):
        super().clean()
        self.headword = normalize_persian(self.headword or "").strip()
        if not self.headword:
            raise ValidationError({"headword": _("Headword is required.")})

    def save(self, *args, **kwargs):
        self.headword = normalize_persian(self.headword or "").strip()
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        return f"{self.headword} ({self.get_status_display()})"


class SimilarEntryLink(models.Model):
    entry = models.ForeignKey(
        Entry,
        on_delete=models.CASCADE,
        related_name="similar_links",
        verbose_name=_("Entry"),
    )
    similar_entry = models.ForeignKey(
        Entry,
        on_delete=models.CASCADE,
        related_name="incoming_similar_links",
        verbose_name=_("Similar entry"),
    )
    sort_order = models.PositiveSmallIntegerField(default=0, verbose_name=_("Display order"))
    is_auto = models.BooleanField(
        default=False,
        verbose_name=_("From automatic suggestions"),
        help_text=_("Refreshed when the entry is saved; manual links are kept."),
    )

    class Meta:
        ordering = ["sort_order", "id"]
        verbose_name = _("Similar entry link")
        verbose_name_plural = _("Similar entry links")
        constraints = [
            models.UniqueConstraint(fields=["entry", "similar_entry"], name="lexicon_similar_entry_unique"),
            models.CheckConstraint(
                condition=~Q(entry_id=F("similar_entry_id")),
                name="lexicon_similar_entry_not_self",
            ),
        ]
        indexes = [
            models.Index(fields=["entry", "sort_order"], name="lex_similar_ent_order_idx"),
        ]

    def clean(self):
        super().clean()
        if self.entry_id and self.similar_entry_id and self.entry_id == self.similar_entry_id:
            raise ValidationError(_("An entry cannot be similar to itself."))

    def __str__(self) -> str:
        return f"{self.entry_id} → {self.similar_entry_id}"


class Definition(models.Model):
    entry = models.ForeignKey(
        Entry,
        on_delete=models.CASCADE,
        related_name="definitions",
        verbose_name=_("Entry"),
    )
    content = models.TextField(verbose_name=_("Meaning"))
    context_annotation = models.TextField(blank=True, verbose_name=_("Background and context"))
    usage_example = models.TextField(blank=True, verbose_name=_("Example of usage"))
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="definitions",
        verbose_name=_("Author"),
    )
    is_featured = models.BooleanField(default=False, db_index=True, verbose_name=_("Featured"))
    is_ai_generated = models.BooleanField(default=False, db_index=True, verbose_name=_("AI-generated"))
    reputation_score = models.IntegerField(default=0, verbose_name=_("Reputation score"))
    upvotes = models.PositiveIntegerField(default=0, verbose_name=_("Upvotes"))
    downvotes = models.PositiveIntegerField(default=0, verbose_name=_("Downvotes"))
    hot_score_value = models.FloatField(default=0.0, db_index=True, verbose_name=_("Hot score value"))
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("Created at"))

    class Meta:
        ordering = ["-is_featured", "-hot_score_value", "created_at"]
        verbose_name = _("Definition")
        verbose_name_plural = _("Definitions")
        indexes = [
            models.Index(fields=["entry", "created_at"]),
            models.Index(fields=["upvotes", "downvotes"]),
            models.Index(fields=["hot_score_value"]),
            GinIndex(
                SearchVector("content", "context_annotation", "usage_example", config="simple"),
                name="lexicon_def_search_vector_gin",
            ),
        ]

    def clean(self):
        super().clean()
        self.content = normalize_persian(self.content)
        self.context_annotation = normalize_persian(self.context_annotation)
        self.usage_example = normalize_persian(self.usage_example)

    @property
    def hot_score(self) -> float:
        return float(self.hot_score_value or 0.0)

    def save(self, *args, **kwargs):
        self.content = normalize_persian(self.content)
        self.context_annotation = normalize_persian(self.context_annotation)
        self.usage_example = normalize_persian(self.usage_example)
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
    definition = models.ForeignKey(
        Definition,
        on_delete=models.CASCADE,
        related_name="attachments",
        verbose_name=_("Definition"),
    )
    link = models.URLField(blank=True, verbose_name=_("Link"))
    image = models.ImageField(
        upload_to="lexicon/definition_attachments/%Y/%m/%d",
        blank=True,
        verbose_name=_("Image"),
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("Created at"))

    class Meta:
        ordering = ["created_at"]
        verbose_name = _("Definition attachment")
        verbose_name_plural = _("Definition attachments")
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

    definition = models.ForeignKey(
        Definition,
        on_delete=models.CASCADE,
        related_name="votes",
        verbose_name=_("Definition"),
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="definition_votes",
        verbose_name=_("User"),
    )
    value = models.SmallIntegerField(choices=VoteValue.choices, verbose_name=_("Value"))
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("Created at"))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_("Updated at"))

    class Meta:
        unique_together = ("definition", "user")
        verbose_name = _("Definition vote")
        verbose_name_plural = _("Definition votes")
        indexes = [models.Index(fields=["definition", "value"])]

    def __str__(self) -> str:
        return f"{self.definition_id}:{self.user_id}:{self.value}"
