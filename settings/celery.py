from __future__ import annotations

import os

from celery import Celery
from celery.signals import setup_logging

from settings.conf import BLOG_ENV_ID

os.environ.setdefault("DJANGO_SETTINGS_MODULE", f"settings.env.{BLOG_ENV_ID}")

app = Celery("blog")

# Pull all CELERY_* keys from Django settings automatically.
app.config_from_object("django.conf:settings", namespace="CELERY")

# Auto-discover tasks.py in every INSTALLED_APP.
app.autodiscover_tasks()


@setup_logging.connect
def config_logging(**kwargs):
    """Delegate Celery logging to Django's LOGGING config."""
    from logging.config import dictConfig
    from django.conf import settings

    dictConfig(settings.LOGGING)
