from __future__ import annotations

import asyncio
import logging

from django.core.management.base import BaseCommand
from redis import Redis

from settings.conf import REDIS_URL

logger = logging.getLogger("blog")


class Command(BaseCommand):
    help = "Listen to REDIS 'comments'"

    async def listen(self) -> None:
        redis = Redis.from_url(REDIS_URL, decode_responses=True)
        pubsub = redis.pubsub()
        await pubsub.subscribe("comments")

        self.stdout.write(self.style.SUCCESS("Listening on REDIS channel: comments"))

        async for message in pubsub.listen():
            if message.get("type") != "message":
                continue
            self.stdout.write(str(message.get("data")))

    def handle(self, *args, **options):
        asyncio.run(self.listen())
