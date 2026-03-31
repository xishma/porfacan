import django.db.models.deletion
from django.conf import settings
from django.contrib.postgres.indexes import GinIndex
from django.db import migrations, models
from django.db.models import Q


class Migration(migrations.Migration):

    dependencies = [
        ("lexicon", "0021_seed_contribution_guide_page"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="EntryAlias",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("headword", models.CharField(max_length=255, verbose_name="Headword")),
                ("created_at", models.DateTimeField(auto_now_add=True, verbose_name="Created at")),
                (
                    "created_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="entry_aliases_created",
                        to=settings.AUTH_USER_MODEL,
                        verbose_name="Created by",
                    ),
                ),
                (
                    "entry",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="aliases",
                        to="lexicon.entry",
                        verbose_name="Entry",
                    ),
                ),
            ],
            options={
                "verbose_name": "Entry headword alias",
                "verbose_name_plural": "Entry headword aliases",
                "ordering": ["headword"],
            },
        ),
        migrations.CreateModel(
            name="EntrySlugRedirect",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("slug", models.SlugField(allow_unicode=True, max_length=255, unique=True, verbose_name="Slug")),
                (
                    "entry",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="slug_redirects",
                        to="lexicon.entry",
                        verbose_name="Entry",
                    ),
                ),
            ],
            options={
                "verbose_name": "Entry slug redirect",
                "verbose_name_plural": "Entry slug redirects",
            },
        ),
        migrations.CreateModel(
            name="SuggestedHeadword",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("headword", models.CharField(max_length=255, verbose_name="Suggested headword")),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("pending", "Pending"),
                            ("approved", "Approved"),
                            ("rejected", "Rejected"),
                        ],
                        db_index=True,
                        default="pending",
                        max_length=16,
                        verbose_name="Status",
                    ),
                ),
                ("reviewed_at", models.DateTimeField(blank=True, null=True, verbose_name="Reviewed at")),
                ("created_at", models.DateTimeField(auto_now_add=True, verbose_name="Created at")),
                (
                    "entry",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="headword_suggestions",
                        to="lexicon.entry",
                        verbose_name="Entry",
                    ),
                ),
                (
                    "reviewed_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="headword_suggestions_reviewed",
                        to=settings.AUTH_USER_MODEL,
                        verbose_name="Reviewed by",
                    ),
                ),
                (
                    "submitted_by",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="headword_suggestions_submitted",
                        to=settings.AUTH_USER_MODEL,
                        verbose_name="Submitted by",
                    ),
                ),
            ],
            options={
                "verbose_name": "Suggested headword",
                "verbose_name_plural": "Suggested headwords",
                "ordering": ["-created_at"],
            },
        ),
        migrations.AddConstraint(
            model_name="entryalias",
            constraint=models.UniqueConstraint(fields=("headword",), name="lexicon_entryalias_headword_uniq"),
        ),
        migrations.AddIndex(
            model_name="entryalias",
            index=models.Index(fields=["entry"], name="lexicon_entryalias_entry_idx"),
        ),
        migrations.AddIndex(
            model_name="entryalias",
            index=GinIndex(fields=["headword"], name="lexicon_alias_headword_trgm", opclasses=["gin_trgm_ops"]),
        ),
        migrations.AddConstraint(
            model_name="suggestedheadword",
            constraint=models.UniqueConstraint(
                condition=Q(status="pending"),
                fields=("entry", "headword"),
                name="lexicon_suggested_hw_pending_uniq",
            ),
        ),
        migrations.AddIndex(
            model_name="suggestedheadword",
            index=models.Index(fields=["entry", "status"], name="lexicon_sugg_ent_stat_idx"),
        ),
    ]
