from __future__ import annotations

import json
import logging
from urllib.parse import parse_qs

from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer
from django.contrib.auth import get_user_model
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError
from rest_framework_simplejwt.tokens import AccessToken

from .models import Post, PostStatus

logger = logging.getLogger("blog")
User = get_user_model()


class CommentConsumer(AsyncWebsocketConsumer):
    """
    WebSocket consumer for live comment delivery on a single post.

    Endpoint:  ws/posts/<slug>/comments/?token=<jwt_access_token>

    On connect:
      1. Extract JWT from ?token= query param → close 4001 if missing/invalid.
      2. Verify the post slug exists and is published → close 4004 if not.
      3. Accept the connection and join the channel group ``comments_<slug>``.

    On comment creation (triggered via PostViewSet):
      channel_layer.group_send sends a ``comment.created`` event;
      ``comment_created()`` forwards the payload as JSON to every connected client.

    Close codes:
      4001 — unauthenticated (no token, invalid token, inactive user)
      4004 — post not found or not published
    """

    # ------------------------------------------------------------------ #
    # Lifecycle                                                            #
    # ------------------------------------------------------------------ #

    async def connect(self) -> None:
        self.slug: str = self.scope["url_route"]["kwargs"]["slug"]
        self.group_name: str = f"comments_{self.slug}"

        # Step 1 — JWT authentication
        self.user = await self._authenticate()
        if self.user is None:
            await self.accept()
            await self.close(code=4001)
            return

        # Step 2 — slug / post validation
        if not await self._post_exists():
            await self.accept()
            await self.close(code=4004)
            return

        # Step 3 — join group and accept
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()
        logger.debug(
            "WS connected: user=%s group=%s channel=%s",
            self.user.email,
            self.group_name,
            self.channel_name,
        )

    async def disconnect(self, code: int) -> None:
        # group_name may not be set if connect() bailed out early.
        if hasattr(self, "group_name"):
            await self.channel_layer.group_discard(self.group_name, self.channel_name)
            logger.debug(
                "WS disconnected: code=%s group=%s channel=%s",
                code,
                self.group_name,
                self.channel_name,
            )

    async def receive(
        self,
        text_data: str | None = None,
        bytes_data: bytes | None = None,
    ) -> None:
        # This is a server-push–only channel; inbound messages are ignored.
        pass

    # ------------------------------------------------------------------ #
    # Channel-layer event handler                                          #
    # ------------------------------------------------------------------ #

    async def comment_created(self, event: dict) -> None:
        """
        Invoked by the channel layer when PostViewSet broadcasts a new comment
        to this group.  Forwards the serialised payload to the WebSocket client.

        Expected event shape (set by PostViewSet):
            {
                "type": "comment.created",   ← maps to this method
                "payload": {
                    "comment_id": int,
                    "author": {"id": int, "email": str},
                    "body": str,
                    "created_at": str,        ← ISO-8601
                },
            }
        """
        await self.send(text_data=json.dumps(event["payload"]))

    # ------------------------------------------------------------------ #
    # Helpers                                                              #
    # ------------------------------------------------------------------ #

    async def _authenticate(self):
        """
        Parse ?token= from the ASGI query string, validate it as a
        SimpleJWT AccessToken, and return the matching active User.

        Returns None on any failure (missing token, expired, bad sig,
        inactive/deleted user).
        """
        raw_qs = self.scope.get("query_string", b"").decode()
        params = parse_qs(raw_qs)
        token_list = params.get("token")
        if not token_list:
            logger.warning(
                "WS auth: no token in query string (group=%s)", self.group_name
            )
            return None

        raw_token = token_list[0]
        try:
            validated_token = AccessToken(raw_token)
            user_id = validated_token["user_id"]
        except (TokenError, InvalidToken, KeyError) as exc:
            logger.warning("WS auth: token validation failed — %s", exc)
            return None

        user = await self._get_user(user_id)
        if user is None:
            logger.warning("WS auth: user_id=%s not found or inactive", user_id)
        return user

    @database_sync_to_async
    def _get_user(self, user_id: int):
        try:
            return User.objects.get(pk=user_id, is_active=True)
        except User.DoesNotExist:
            return None

    @database_sync_to_async
    def _post_exists(self) -> bool:
        return Post.objects.filter(slug=self.slug, status=PostStatus.PUBLISHED).exists()
