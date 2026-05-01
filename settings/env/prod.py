from __future__ import annotations

from ..base import *
from ..conf import _CONFIG as config

DEBUG = False

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": config("BLOG_DB_NAME"),
        "USER": config("BLOG_DB_USER"),
        "PASSWORD": config("BLOG_DB_PASSWORD"),
        "HOST": config("BLOG_DB_HOST", default="localhost"),
        "PORT": config("BLOG_DB_PORT", default="5432"),
    }
}
