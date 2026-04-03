# Generated manually for optional email notification preference

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("users", "0003_alter_user_email_alter_user_reputation_iq_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="user",
            name="receive_email_notifications",
            field=models.BooleanField(
                default=True,
                help_text="Entry updates, announcements, and other non-account messages we send by email.",
                verbose_name="Receive email notifications from Porfacan",
            ),
        ),
    ]
