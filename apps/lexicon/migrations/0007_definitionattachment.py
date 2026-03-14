from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("lexicon", "0006_alter_entry_slug"),
    ]

    operations = [
        migrations.CreateModel(
            name="DefinitionAttachment",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("link", models.URLField(blank=True)),
                ("image", models.ImageField(blank=True, upload_to="lexicon/definition_attachments/%Y/%m/%d")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "definition",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="attachments",
                        to="lexicon.definition",
                    ),
                ),
            ],
            options={
                "ordering": ["created_at"],
                "constraints": [
                    models.CheckConstraint(
                        condition=~(models.Q(link="", image="")),
                        name="lexicon_attachment_link_or_image_required",
                    )
                ],
            },
        ),
    ]
