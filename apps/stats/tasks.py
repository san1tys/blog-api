from __future__ import annotations

import logging
from datetime import timedelta

from celery import shared_task
from django.utils import timezone

logger = logging.getLogger("django")


@shared_task(
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    max_retries=3,
    name="stats.generate_daily_stats",
)
def generate_daily_stats(self) -> None:
    """Snapshot blog counters into ``DailyStats`` for yesterday.

    Runs at 00:00 via Celery Beat, so it captures the full previous day.
    Uses ``update_or_create`` to be idempotent — safe to re-run manually.
    """
    from django.contrib.auth import get_user_model

    from apps.blog.models import Comment, Post, PostStatus
    from apps.stats.models import DailyStats

    User = get_user_model()

    yesterday = (timezone.now() - timedelta(days=1)).date()
    day_start = timezone.datetime.combine(
        yesterday, timezone.datetime.min.time()
    ).replace(tzinfo=timezone.utc)
    day_end = day_start + timedelta(days=1)

    logger.info(
        "Generating daily stats for %s (attempt %s)",
        yesterday,
        self.request.retries + 1,
    )

    total_posts = Post.objects.count()
    total_comments = Comment.objects.count()
    total_users = User.objects.count()
    published_posts = Post.objects.filter(status=PostStatus.PUBLISHED).count()
    new_comments = Comment.objects.filter(
        created_at__gte=day_start, created_at__lt=day_end
    ).count()

    obj, created = DailyStats.objects.update_or_create(
        date=yesterday,
        defaults={
            "total_posts": total_posts,
            "total_comments": total_comments,
            "total_users": total_users,
            "published_posts": published_posts,
            "new_comments": new_comments,
        },
    )

    action = "Created" if created else "Updated"
    logger.info(
        "%s DailyStats for %s: posts=%d comments=%d users=%d published=%d new_comments=%d",
        action,
        yesterday,
        total_posts,
        total_comments,
        total_users,
        published_posts,
        new_comments,
    )
