from __future__ import annotations

from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _


class Notification(models.Model):
    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="notifications",
        verbose_name=_("Recipient"),
    )
    comment = models.ForeignKey(
        "blog.Comment",
        on_delete=models.CASCADE,
        related_name="notifications",
        verbose_name=_("Comment"),
    )
    is_read = models.BooleanField(_("Is read"), default=False)
    created_at = models.DateTimeField(_("Created at"), auto_now_add=True)

    class Meta:
        verbose_name = _("Notification")
        verbose_name_plural = _("Notifications")
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"Notification for {self.recipient} on comment {self.comment_id}"
