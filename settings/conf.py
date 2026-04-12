from __future__ import annotations

from pathlib import Path
from decouple import AutoConfig

_CONFIG = AutoConfig(search_path=Path(__file__).resolve().parent)

BLOG_ENV_ID: str = _CONFIG("BLOG_ENV_ID", default="local")

SECRET_KEY: str = _CONFIG("BLOG_SECRET_KEY")
DEBUG: bool = _CONFIG("BLOG_DEBUG", default=False, cast=bool)

_ALLOWED_HOSTS_RAW: str = _CONFIG("BLOG_ALLOWED_HOSTS", default="")
ALLOWED_HOSTS: list[str] = [
    h.strip() for h in _ALLOWED_HOSTS_RAW.split(",") if h.strip()
]

REDIS_URL: str = _CONFIG("BLOG_REDIS_URL", default="redis://127.0.0.1:6379/1")
CELERY_BROKER_URL: str = _CONFIG(
    "BLOG_CELERY_BROKER_URL", default="redis://127.0.0.1:6379/2"
)
CELERY_RESULT_BACKEND_URL: str = _CONFIG(
    "BLOG_CELERY_RESULT_BACKEND_URL", default="redis://127.0.0.1:6379/3"
)
