from __future__ import annotations

from pathlib import Path
import os

from celery.schedules import crontab

from .conf import (
    SECRET_KEY,
    DEBUG,
    ALLOWED_HOSTS,
    REDIS_URL,
    CELERY_BROKER_URL,
    CELERY_RESULT_BACKEND_URL,
)

BASE_DIR = Path(__file__).resolve().parent.parent
LOG_DIR = BASE_DIR / "logs"
os.makedirs(LOG_DIR, exist_ok=True)

SECRET_KEY = SECRET_KEY
DEBUG = DEBUG
ALLOWED_HOSTS = ALLOWED_HOSTS

ROOT_URLCONF = "settings.urls"
WSGI_APPLICATION = "settings.wsgi.application"
ASGI_APPLICATION = "settings.asgi.application"

AUTH_USER_MODEL = "users.User"

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "filters": {
        "require_debug_true": {"()": "django.utils.log.RequireDebugTrue"},
    },
    "formatters": {
        "simple": {"format": "%(levelname)s %(message)s"},
        "verbose": {
            "format": "%(asctime)s %(levelname)s %(name)s %(module)s %(message)s"
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "level": "DEBUG",
            "formatter": "simple",
        },
        "file": {
            "class": "logging.handlers.RotatingFileHandler",
            "level": "WARNING",
            "formatter": "verbose",
            "filename": str(LOG_DIR / "app.log"),
            "maxBytes": 5 * 1024 * 1024,
            "backupCount": 3,
        },
        "debug_requests": {
            "class": "logging.handlers.RotatingFileHandler",
            "level": "DEBUG",
            "formatter": "verbose",
            "filename": str(LOG_DIR / "debug_requests.log"),
            "maxBytes": 5 * 1024 * 1024,
            "backupCount": 1,
            "filters": ["require_debug_true"],
        },
    },
    "loggers": {
        "users": {
            "level": "DEBUG",
            "handlers": ["console", "file"],
            "propagate": False,
        },
        "blog": {
            "level": "DEBUG",
            "handlers": ["console", "file"],
            "propagate": False,
        },
        "django.request": {
            "level": "WARNING",
            "handlers": ["file"],
            "propagate": False,
        },
        "django.server": {
            "level": "DEBUG",
            "handlers": ["debug_requests"],
            "propagate": False,
        },
    },
}

DJANGO_APPS = [
    "daphne",  # must be first to override manage.py runserver with Daphne's ASGI server
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
]

THIRD_PARTY_APPS = [
    "channels",
    "rest_framework",
    "rest_framework_simplejwt",
    "drf_spectacular",
]

PROJECT_APPS = [
    "apps.users.apps.UsersConfig",
    "apps.blog.apps.BlogConfig",
    "apps.core.apps.CoreConfig",
    "apps.stats.apps.StatsConfig",
    "apps.notifications.apps.NotificationsConfig",
]

INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + PROJECT_APPS

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "apps.core.middleware.UserLocaleMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
]

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"
    },
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "en"

LANGUAGES = [
    ("en", "English"),
    ("ru", "Russian"),
    ("kk", "Kazakh"),
]

LOCALE_PATHS = [
    BASE_DIR / "locale",
]

TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"

MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"
DEFAULT_FROM_EMAIL = "noreply@example.com"

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ),
    "DEFAULT_PERMISSION_CLASSES": ("rest_framework.permissions.AllowAny",),
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 10,
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "DEFAULT_THROTTLE_CLASSES": [
        "rest_framework.throttling.AnonRateThrottle",
        "rest_framework.throttling.UserRateThrottle",
    ],
    "DEFAULT_THROTTLE_RATES": {
        "anon": "100/day",
        "user": "1000/day",
    },
}

SPECTACULAR_SETTINGS = {
    "TITLE": "Blog API",
    "DESCRIPTION": "Homework 2 API documentation",
    "VERSION": "2.0.0",
    "SERVE_INCLUDE_SCHEMA": False,
}

CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels_redis.core.RedisChannelLayer",
        "CONFIG": {
            "hosts": [REDIS_URL],
        },
    }
}


# Celery
CELERY_BROKER_URL = CELERY_BROKER_URL
CELERY_RESULT_BACKEND = CELERY_RESULT_BACKEND_URL  # dedicated DB 3 — isolated from cache (DB 1) and broker (DB 2)
CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"
CELERY_TIMEZONE = TIME_ZONE
CELERY_TASK_TRACK_STARTED = True
CELERY_TASK_TIME_LIMIT = 5 * 60  # hard kill after 5 min
CELERY_TASK_SOFT_TIME_LIMIT = 4 * 60  # SoftTimeLimitExceeded raised at 4 min

CELERY_BEAT_SCHEDULE = {
    # Check for scheduled posts every minute.
    "publish-scheduled-posts": {
        "task": "blog.publish_scheduled_posts",
        "schedule": 60,  # seconds
    },
    # Delete stale notifications at 03:00 UTC every day.
    "clear-expired-notifications": {
        "task": "notifications.clear_expired_notifications",
        "schedule": crontab(hour=3, minute=0),
    },
    # Snapshot daily blog counters at 00:00 UTC every day.
    "generate-daily-stats": {
        "task": "stats.generate_daily_stats",
        "schedule": crontab(hour=0, minute=0),
    },
}

CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": REDIS_URL,
        "OPTIONS": {
            "CLIENT_CLASS": "django_redis.client.DefaultClient",
        },
    }
}
