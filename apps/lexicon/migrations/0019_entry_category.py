import django.db.models.deletion
from django.db import migrations, models


def assign_default_entry_category(apps, schema_editor):
    EntryCategory = apps.get_model("lexicon", "EntryCategory")
    Entry = apps.get_model("lexicon", "Entry")
    cat, _ = EntryCategory.objects.get_or_create(
        slug="general",
        defaults={"name": "عمومی"},
    )
    Entry.objects.all().update(category=cat)


class Migration(migrations.Migration):

    dependencies = [
        ("lexicon", "0018_alter_definition_options_alter_entry_options_and_more"),
    ]

    operations = [
        migrations.CreateModel(
            name="EntryCategory",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=200, unique=True, verbose_name="Name")),
                ("slug", models.SlugField(allow_unicode=True, max_length=255, unique=True, verbose_name="Slug")),
            ],
            options={
                "verbose_name": "Entry category",
                "verbose_name_plural": "Entry categories",
                "ordering": ["name"],
            },
        ),
        migrations.AddField(
            model_name="entry",
            name="category",
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="entries",
                to="lexicon.entrycategory",
                verbose_name="Category",
            ),
        ),
        migrations.RunPython(assign_default_entry_category, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="entry",
            name="category",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                related_name="entries",
                to="lexicon.entrycategory",
                verbose_name="Category",
            ),
        ),
    ]
