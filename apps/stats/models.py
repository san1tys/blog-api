# Create your models here.
from __future__ import annotations

from django.db import models
from django.utils.translation import gettext_lazy as _


class DailyStats(models.Model):
    date = models.DateField(_("Date"), unique=True)
    total_posts = models.PositiveIntegerField(_("Total Posts"), default=0)
    total_comments = models.PositiveIntegerField(_("Total Comments"), default=0)
    total_users = models.PositiveIntegerField(_("Total Users"), default=0)
    published_posts = models.PositiveIntegerField(_("Published Posts"), default=0)
    new_comments = models.PositiveIntegerField(_("New Comments (last 24h)"), default=0)

    class Meta:
        verbose_name = _("Daily Stat")
        verbose_name_plural = _("Daily Stats")
        ordering = ["-date"]

    def __str__(self) -> str:
        return f"Stats for {self.date}"
