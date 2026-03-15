from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("archiver", "0003_archiverecord_file_hash_and_more"),
    ]

    operations = [
        migrations.AlterModelOptions(
            name="archiverecord",
            options={
                "ordering": ["-created_at"],
                "verbose_name": "Archive record",
                "verbose_name_plural": "Archive records",
            },
        ),
    ]
