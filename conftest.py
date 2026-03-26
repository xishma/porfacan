import pytest


@pytest.fixture(autouse=True)
def _celery_always_eager(settings):
    settings.CELERY_TASK_ALWAYS_EAGER = True
    settings.CELERY_TASK_EAGER_PROPAGATES = True
