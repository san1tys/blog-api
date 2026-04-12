from __future__ import annotations

import json
import logging

from celery import shared_task
from django.utils import timezone

logger = logging.getLogger("blog")


@shared_task(
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    max_retries=3,
    name="blog.invalidate_posts_cache",
)
def invalidate_posts_cache(self, post_id: int | None = None) -> None:
    """Wipe all language variants of the posts-list Redis cache.

    ``post_id`` is optional context only (used for log tracing); the
    cache is always invalidated for all languages because a single write
    affects every cached variant.
    """
    from apps.blog.views import invalidate_posts_list_cache

    logger.info(
        "Invalidating posts list cache (triggered by post_id=%s, attempt %s)",
        post_id,
        self.request.retries + 1,
    )
    invalidate_posts_list_cache()
    logger.info("Posts list cache invalidated")


@shared_task(
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    max_retries=3,
    name="blog.publish_scheduled_posts",
)
def publish_scheduled_posts(self) -> None:
    """Publish every draft post whose ``publish_at`` is in the past.

    Runs every minute via Celery Beat.  Each post is published atomically:
    status is flipped, the Redis pub/sub event is fired, and the posts-list
    cache is invalidated once after all posts are processed.
    """
    from redis import Redis

    from apps.blog.models import Post, PostStatus
    from apps.blog.views import POSTS_PUBLISHED_CHANNEL, invalidate_posts_list_cache
    from settings.conf import REDIS_URL

    now = timezone.now()
    due = Post.objects.filter(status=PostStatus.DRAFT, publish_at__lte=now)
    ids = list(due.values_list("id", flat=True))

    if not ids:
        return

    logger.info(
        "Auto-publishing %d scheduled post(s) (attempt %s): ids=%s",
        len(ids),
        self.request.retries + 1,
        ids,
    )

    redis = Redis.from_url(REDIS_URL)
    for post in Post.objects.filter(id__in=ids).select_related("author"):
        post.status = PostStatus.PUBLISHED
        post.save(update_fields=["status", "updated_at"])
        event = {
            "post_id": post.id,
            "title": post.title,
            "slug": post.slug,
            "author": post.author_id,
            "published_at": post.updated_at.isoformat(),
        }
        redis.publish(POSTS_PUBLISHED_CHANNEL, json.dumps(event, ensure_ascii=False))
        logger.info("Published post id=%s slug=%s", post.id, post.slug)

    invalidate_posts_list_cache()
