from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("lexicon", "0013_page"),
    ]

    operations = [
        migrations.AddField(
            model_name="definition",
            name="is_featured",
            field=models.BooleanField(db_index=True, default=False, verbose_name="Featured"),
        ),
    ]
