from __future__ import annotations

import logging
from django.core.management.base import BaseCommand
from redis import Redis

from settings.conf import REDIS_URL

logger = logging.getLogger("blog")


class Command(BaseCommand):
    help = "Listen to REDIS 'comments'"

    def handle(self, *args, **options):
        r = Redis.from_url(REDIS_URL)
        pubsub = r.pubsub()
        pubsub.subscribe("comments")

        self.stdout.write("Listening on REDIS channel: comments")

        for message in pubsub.listen():
            if message.get("type") != "message":
                continue
            data = message.get("data")
            try:
                text = (
                    data.decode("utf-8")
                    if isinstance(data, (bytes, bytearray))
                    else str(data)
                )
            except Exception:
                text = str(data)
            self.stdout.write(text)
