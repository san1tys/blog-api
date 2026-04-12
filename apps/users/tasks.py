from __future__ import annotations

import logging

from celery import shared_task

from apps.users import services

logger = logging.getLogger("users")


@shared_task(
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    max_retries=3,
    name="users.send_welcome_email",
)
def send_welcome_email(self, user_id: int) -> None:
    """Send a welcome email to a newly registered user.

    Accepts a primitive ``user_id`` instead of an ORM object so the
    task payload is fully JSON-serializable and safe to enqueue.
    """
    from apps.users.models import User

    logger.info(
        "Sending welcome email to user_id=%s (attempt %s)",
        user_id,
        self.request.retries + 1,
    )
    user = User.objects.get(pk=user_id)
    services.send_welcome_email(user)
    logger.info("Welcome email sent to user_id=%s", user_id)
