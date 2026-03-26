import django.db.models.deletion
from django.db import migrations, models
from django.db.models import F, Q


class Migration(migrations.Migration):

    dependencies = [
        ("lexicon", "0016_entry_lex_ent_head_prefix_idx"),
    ]

    operations = [
        migrations.CreateModel(
            name="SimilarEntryLink",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("sort_order", models.PositiveSmallIntegerField(default=0, verbose_name="Display order")),
                (
                    "is_auto",
                    models.BooleanField(
                        default=False,
                        help_text="Refreshed when the entry is saved; manual links are kept.",
                        verbose_name="From automatic suggestions",
                    ),
                ),
                (
                    "entry",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="similar_links",
                        to="lexicon.entry",
                        verbose_name="Entry",
                    ),
                ),
                (
                    "similar_entry",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="incoming_similar_links",
                        to="lexicon.entry",
                        verbose_name="Similar entry",
                    ),
                ),
            ],
            options={
                "verbose_name": "Similar entry link",
                "verbose_name_plural": "Similar entry links",
                "ordering": ["sort_order", "id"],
            },
        ),
        migrations.AddConstraint(
            model_name="similarentrylink",
            constraint=models.UniqueConstraint(fields=("entry", "similar_entry"), name="lexicon_similar_entry_unique"),
        ),
        migrations.AddConstraint(
            model_name="similarentrylink",
            constraint=models.CheckConstraint(
                condition=~Q(entry_id=F("similar_entry_id")),
                name="lexicon_similar_entry_not_self",
            ),
        ),
        migrations.AddIndex(
            model_name="similarentrylink",
            index=models.Index(fields=["entry", "sort_order"], name="lex_similar_ent_order_idx"),
        ),
    ]
