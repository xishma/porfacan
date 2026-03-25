from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("lexicon", "0012_entry_created_by"),
    ]

    operations = [
        migrations.CreateModel(
            name="Page",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("address", models.SlugField(allow_unicode=True, max_length=255, unique=True, verbose_name="Address")),
                ("title", models.CharField(max_length=255, verbose_name="Title")),
                ("content", models.TextField(verbose_name="Content")),
                ("display_order", models.PositiveSmallIntegerField(default=0, verbose_name="Display order")),
                ("is_published", models.BooleanField(default=True, verbose_name="Is published")),
                ("created_at", models.DateTimeField(auto_now_add=True, verbose_name="Created at")),
                ("updated_at", models.DateTimeField(auto_now=True, verbose_name="Updated at")),
            ],
            options={
                "verbose_name": "Page",
                "verbose_name_plural": "Pages",
                "ordering": ["display_order", "title"],
            },
        ),
    ]
