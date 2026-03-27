import django.contrib.postgres.indexes
import django.contrib.postgres.search
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("lexicon", "0019_entry_category"),
    ]

    operations = [
        migrations.AddField(
            model_name="definition",
            name="usage_example",
            field=models.TextField(blank=True, verbose_name="Example of usage"),
        ),
        migrations.AlterField(
            model_name="definition",
            name="content",
            field=models.TextField(verbose_name="Meaning"),
        ),
        migrations.AlterField(
            model_name="definition",
            name="context_annotation",
            field=models.TextField(blank=True, verbose_name="Background and context"),
        ),
        migrations.RemoveIndex(
            model_name="definition",
            name="lexicon_def_search_vector_gin",
        ),
        migrations.AddIndex(
            model_name="definition",
            index=django.contrib.postgres.indexes.GinIndex(
                django.contrib.postgres.search.SearchVector(
                    "content", "context_annotation", "usage_example", config="simple"
                ),
                name="lexicon_def_search_vector_gin",
            ),
        ),
    ]
