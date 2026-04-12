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
    name="notifications.process_new_comment",
)
def process_new_comment(self, comment_id: int) -> None:
    """Create an in-app Notification for the post author when a new comment arrives.

    Skips notification when the commenter and the post author are the same
    person to avoid self-notifications.
    """
    from apps.blog.models import Comment
    from apps.notifications.models import Notification

    logger.info(
        "Processing new comment comment_id=%s (attempt %s)",
        comment_id,
        self.request.retries + 1,
    )

    comment = Comment.objects.select_related("post__author", "author").get(
        pk=comment_id
    )
    post_author = comment.post.author

    if post_author == comment.author:
        logger.debug(
            "Skipping self-notification for user_id=%s on comment_id=%s",
            post_author.pk,
            comment_id,
        )
        return

    Notification.objects.create(recipient=post_author, comment=comment)
    logger.info(
        "Notification created for user_id=%s on comment_id=%s",
        post_author.pk,
        comment_id,
    )


_READ_EXPIRY_DAYS = 30
_UNREAD_EXPIRY_DAYS = 90


@shared_task(
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    max_retries=3,
    name="notifications.clear_expired_notifications",
)
def clear_expired_notifications(self) -> None:
    """Delete stale notifications.

    Rules (both applied in a single bulk DELETE per category):
    - Read notifications older than 30 days.
    - Unread notifications older than 90 days (user clearly will never read them).

    Runs daily at 03:00 via Celery Beat.
    """
    from apps.notifications.models import Notification

    now = timezone.now()
    read_cutoff = now - timedelta(days=_READ_EXPIRY_DAYS)
    unread_cutoff = now - timedelta(days=_UNREAD_EXPIRY_DAYS)

    logger.info(
        "Clearing expired notifications (attempt %s): read_cutoff=%s unread_cutoff=%s",
        self.request.retries + 1,
        read_cutoff.date(),
        unread_cutoff.date(),
    )

    deleted_read, _ = Notification.objects.filter(
        is_read=True, created_at__lt=read_cutoff
    ).delete()

    deleted_unread, _ = Notification.objects.filter(
        is_read=False, created_at__lt=unread_cutoff
    ).delete()

    logger.info(
        "Deleted %d read and %d unread expired notifications",
        deleted_read,
        deleted_unread,
    )
