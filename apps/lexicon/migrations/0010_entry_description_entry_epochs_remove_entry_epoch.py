from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("lexicon", "0009_alter_definition_author_alter_definition_content_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="entry",
            name="description",
            field=models.TextField(blank=True, verbose_name="Description"),
        ),
        migrations.RemoveField(
            model_name="entry",
            name="epoch",
        ),
        migrations.AddField(
            model_name="entry",
            name="epochs",
            field=models.ManyToManyField(related_name="entries", to="lexicon.epoch", verbose_name="Epochs"),
        ),
    ]
