from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("lexicon", "0007_definitionattachment"),
    ]

    operations = [
        migrations.AddConstraint(
            model_name="definition",
            constraint=models.UniqueConstraint(
                fields=("entry", "author"),
                name="lexicon_one_definition_per_user_entry",
            ),
        ),
    ]
