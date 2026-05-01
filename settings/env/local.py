from ..base import *

DEBUG = False

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        # In Docker: /app/data/ is a named volume (sqlite_data) so the DB
        # survives container restarts.  In bare-metal dev the directory is
        # created automatically on first migrate.
        "NAME": BASE_DIR / "data" / "db.sqlite3",
    }
}
