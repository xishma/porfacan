from django.apps import AppConfig


class ArchiverConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.archiver"
    label = "archiver"

    def ready(self):
        from . import signals  # noqa: F401
