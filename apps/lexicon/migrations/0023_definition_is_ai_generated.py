from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("lexicon", "0022_entry_alias_slug_redirect_suggested_headword"),
    ]

    operations = [
        migrations.AddField(
            model_name="definition",
            name="is_ai_generated",
            field=models.BooleanField(db_index=True, default=False, verbose_name="AI-generated"),
        ),
    ]
