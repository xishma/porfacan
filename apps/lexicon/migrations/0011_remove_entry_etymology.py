from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("lexicon", "0010_entry_description_entry_epochs_remove_entry_epoch"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="entry",
            name="etymology",
        ),
    ]
