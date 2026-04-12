from __future__ import annotations

import hashlib
import json
import logging

from asgiref.sync import async_to_sync, sync_to_async
from channels.layers import get_channel_layer
from django.core.cache import cache
from django.http import StreamingHttpResponse
from django.shortcuts import get_object_or_404
from django.utils.decorators import method_decorator
from django.utils.translation import gettext_lazy as _
from django_ratelimit.decorators import ratelimit
from drf_spectacular.utils import (
    OpenApiExample,
    OpenApiParameter,
    OpenApiResponse,
    extend_schema,
    extend_schema_view,
)
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticatedOrReadOnly
from rest_framework.request import Request
from rest_framework.response import Response

import redis.asyncio as aioredis
from redis import Redis

from settings.conf import REDIS_URL

from apps.notifications.tasks import process_new_comment

from .models import Comment, Post, PostStatus
from .permissions import IsOwnerOrReadOnly
from .serializers import CommentSerializer, PostSerializer

logger = logging.getLogger("blog")
POSTS_LIST_TTL_SECONDS = 60
POSTS_PUBLISHED_CHANNEL = "posts:published"


def _publish_post_event(post: Post) -> None:
    """Publish a post-published event to the Redis pub/sub channel."""
    event = {
        "post_id": post.id,
        "title": post.title,
        "slug": post.slug,
        "author": post.author_id,
        "published_at": post.created_at.isoformat(),
    }
    Redis.from_url(REDIS_URL).publish(
        POSTS_PUBLISHED_CHANNEL, json.dumps(event, ensure_ascii=False)
    )


RATE_LIMIT_ERROR = {"detail": _("Too many requests. Try again later.")}
SUPPORTED_LANGUAGES = ("en", "ru", "kk")


def get_posts_list_cache_key(request: Request) -> str:
    language = getattr(request, "LANGUAGE_CODE", "en")
    raw_query = request.META.get("QUERY_STRING", "")
    query_hash = hashlib.md5(raw_query.encode("utf-8")).hexdigest()
    return f"posts:list:published:{language}:{query_hash}"


def invalidate_posts_list_cache() -> None:
    for language in SUPPORTED_LANGUAGES:
        cache.delete_pattern(f"posts:list:published:{language}:*")


@extend_schema_view(
    list=extend_schema(
        tags=["Posts"],
        summary="List published posts",
        description=(
            "Returns a paginated list of published posts. No authentication is required. "
            "The response is cached in Redis with a language-aware and query-aware cache key, "
            "so different languages and query strings get separate cached responses. Post dates "
            "are localized and converted to the active timezone. Anonymous users see UTC."
        ),
        parameters=[
            OpenApiParameter(
                "lang",
                str,
                OpenApiParameter.QUERY,
                description="Force response language: en, ru, kk.",
            ),
            OpenApiParameter(
                "page",
                int,
                OpenApiParameter.QUERY,
                description="Pagination page number.",
            ),
        ],
        responses={
            200: OpenApiResponse(description="Paginated post list."),
            429: OpenApiResponse(description="Throttle limit reached."),
        },
        examples=[
            OpenApiExample(
                "Posts list response",
                value={
                    "count": 1,
                    "next": None,
                    "previous": None,
                    "results": [
                        {
                            "id": 1,
                            "title": "First Post",
                            "slug": "first-post",
                            "body": "Hello",
                            "status": "published",
                        }
                    ],
                },
                response_only=True,
                status_codes=["200"],
            )
        ],
    ),
    retrieve=extend_schema(
        tags=["Posts"],
        summary="Retrieve a published post",
        description=(
            "Returns one published post by slug. No authentication is required. "
            "Localized category names and locale-formatted timestamps are included in the response."
        ),
        parameters=[
            OpenApiParameter(
                "lang",
                str,
                OpenApiParameter.QUERY,
                description="Force response language: en, ru, kk.",
            )
        ],
        responses={
            200: PostSerializer,
            404: OpenApiResponse(description="Post not found."),
        },
    ),
    create=extend_schema(
        tags=["Posts"],
        summary="Create a post",
        description=(
            "Creates a new post for the authenticated user. Authentication is required. "
            "On success, the Redis cache for the posts list is invalidated for all languages. "
            "This endpoint is rate-limited."
        ),
        request=PostSerializer,
        responses={
            201: PostSerializer,
            400: OpenApiResponse(description="Validation error."),
            401: OpenApiResponse(description="Authentication required."),
            429: OpenApiResponse(description="Too many requests."),
        },
        examples=[
            OpenApiExample(
                "Create post request",
                value={
                    "title": "New post",
                    "slug": "new-post",
                    "body": "Body",
                    "status": "draft",
                },
                request_only=True,
            )
        ],
    ),
    update=extend_schema(
        tags=["Posts"],
        summary="Update a post",
        description="Updates an existing post owned by the authenticated user and invalidates the posts list cache for all languages.",
        request=PostSerializer,
        responses={
            200: PostSerializer,
            400: OpenApiResponse(description="Validation error."),
            401: OpenApiResponse(description="Authentication required."),
            403: OpenApiResponse(description="Permission denied."),
            404: OpenApiResponse(description="Post not found."),
        },
    ),
    partial_update=extend_schema(
        tags=["Posts"],
        summary="Partially update a post",
        description="Partially updates an existing post owned by the authenticated user and invalidates the posts list cache for all languages.",
        request=PostSerializer,
        responses={
            200: PostSerializer,
            400: OpenApiResponse(description="Validation error."),
            401: OpenApiResponse(description="Authentication required."),
            403: OpenApiResponse(description="Permission denied."),
            404: OpenApiResponse(description="Post not found."),
        },
    ),
    destroy=extend_schema(
        tags=["Posts"],
        summary="Delete a post",
        description="Deletes an existing post owned by the authenticated user and invalidates the posts list cache for all languages.",
        responses={
            204: OpenApiResponse(description="Post deleted."),
            401: OpenApiResponse(description="Authentication required."),
            403: OpenApiResponse(description="Permission denied."),
            404: OpenApiResponse(description="Post not found."),
        },
    ),
)
class PostViewSet(viewsets.ModelViewSet):
    serializer_class = PostSerializer
    lookup_field = "slug"
    permission_classes = [IsAuthenticatedOrReadOnly, IsOwnerOrReadOnly]

    def get_queryset(self):
        qs = Post.objects.select_related("author", "category").prefetch_related("tags")
        if self.action in ("list", "retrieve", "comments"):
            return qs.filter(status=PostStatus.PUBLISHED).order_by("-created_at")
        return qs

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context["request"] = self.request
        return context

    def list(self, request: Request, *args, **kwargs) -> Response:
        cache_key = get_posts_list_cache_key(request)
        cached = cache.get(cache_key)
        if cached is not None:
            return Response(cached)
        resp = super().list(request, *args, **kwargs)
        cache.set(cache_key, resp.data, POSTS_LIST_TTL_SECONDS)
        return resp

    @method_decorator(ratelimit(key="user", rate="20/m", method="POST", block=False))
    def create(self, request: Request, *args, **kwargs) -> Response:
        if getattr(request, "limited", False):
            logger.warning("Post create rate limit exceeded for user/ip")
            return Response(RATE_LIMIT_ERROR, status=status.HTTP_429_TOO_MANY_REQUESTS)
        if not request.user.is_authenticated:
            return Response(
                {"detail": _("Authentication required.")},
                status=status.HTTP_401_UNAUTHORIZED,
            )
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        post = serializer.save(author=request.user)
        if post.status == PostStatus.PUBLISHED:
            _publish_post_event(post)
        invalidate_posts_list_cache()
        return Response(self.get_serializer(post).data, status=status.HTTP_201_CREATED)

    def update(self, request: Request, *args, **kwargs) -> Response:
        instance = self.get_object()
        was_published = instance.status == PostStatus.PUBLISHED
        resp = super().update(request, *args, **kwargs)
        instance.refresh_from_db(fields=["status", "created_at"])
        if instance.status == PostStatus.PUBLISHED and not was_published:
            _publish_post_event(instance)
        invalidate_posts_list_cache()
        return resp

    def destroy(self, request: Request, *args, **kwargs) -> Response:
        resp = super().destroy(request, *args, **kwargs)
        invalidate_posts_list_cache()
        return resp

    @extend_schema(
        tags=["Comments"],
        summary="List or create comments for a post",
        description=(
            "GET returns comments for a published post. POST creates a new comment for the authenticated user. "
            "After a comment is created, a JSON event is published to Redis containing the post slug, author ID, and comment body."
        ),
        request=CommentSerializer,
        responses={
            200: CommentSerializer(many=True),
            201: CommentSerializer,
            400: OpenApiResponse(description="Validation error."),
            401: OpenApiResponse(description="Authentication required."),
            404: OpenApiResponse(description="Post not found."),
        },
        examples=[
            OpenApiExample(
                "Comment request", value={"body": "Great post!"}, request_only=True
            ),
            OpenApiExample(
                "Comment response",
                value={"id": 1, "body": "Great post!"},
                response_only=True,
                status_codes=["201"],
            ),
        ],
    )
    @action(detail=True, methods=["get", "post"], url_path="comments")
    def comments(self, request: Request, slug: str | None = None) -> Response:
        post = get_object_or_404(Post, slug=slug, status=PostStatus.PUBLISHED)
        if request.method == "GET":
            qs = (
                Comment.objects.filter(post=post)
                .select_related("author")
                .order_by("-created_at")
            )
            serializer = CommentSerializer(qs, many=True, context={"request": request})
            return Response(serializer.data)
        if not request.user.is_authenticated:
            return Response(
                {"detail": _("Authentication required.")},
                status=status.HTTP_401_UNAUTHORIZED,
            )
        serializer = CommentSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        comment = Comment.objects.create(
            post=post, author=request.user, body=serializer.validated_data["body"]
        )
        # Publish to the legacy Redis pub/sub channel (used by listen_comments).
        redis_event = {
            "type": "comment.created",
            "post_slug": post.slug,
            "author_id": request.user.id,
            "comment_body": comment.body,
        }
        Redis.from_url(REDIS_URL).publish(
            "comments", json.dumps(redis_event, ensure_ascii=False)
        )

        # Broadcast to Django Channels group so live WebSocket clients receive it.
        channel_layer = get_channel_layer()
        async_to_sync(channel_layer.group_send)(
            f"comments_{post.slug}",
            {
                "type": "comment.created",
                "payload": {
                    "comment_id": comment.id,
                    "author": {"id": request.user.id, "email": request.user.email},
                    "body": comment.body,
                    "created_at": comment.created_at.isoformat(),
                },
            },
        )

        # Enqueue async task: create an in-app Notification for the post author.
        process_new_comment.delay(comment.id)

        return Response(
            CommentSerializer(comment, context={"request": request}).data,
            status=status.HTTP_201_CREATED,
        )


# ---------------------------------------------------------------------------
# SSE endpoint: GET /api/posts/stream/
# ---------------------------------------------------------------------------

_KEEPALIVE_INTERVAL = 15  # seconds between SSE keepalive comments


def _format_sse(data: dict) -> str:
    """Encode a dict as a single SSE message."""
    return f"data: {json.dumps(data, ensure_ascii=False)}\n\n"


@sync_to_async
def _fetch_posts(after_id: int | None) -> list[dict]:
    """
    Return published posts as plain dicts, optionally only those with
    id > after_id (for incremental polling).
    """
    qs = (
        Post.objects.filter(status=PostStatus.PUBLISHED)
        .select_related("author")
        .order_by("id")
    )
    if after_id is not None:
        qs = qs.filter(id__gt=after_id)
    return [
        {
            "post_id": p.id,
            "title": p.title,
            "slug": p.slug,
            "author": p.author_id,
            "published_at": p.created_at.isoformat(),
        }
        for p in qs
    ]


async def _event_stream(request):
    """
    Async generator that yields SSE-formatted bytes.

    Flow:
    1. Send all currently published posts on connect (initial burst).
    2. Subscribe to the Redis ``posts:published`` pub/sub channel.
    3. Yield each incoming event immediately as it is published by the
       viewset (zero polling delay).
    4. Emit a keepalive comment every _KEEPALIVE_INTERVAL seconds while
       waiting, to prevent proxy / browser timeouts.
    """
    # Initial burst — all existing published posts
    posts = await _fetch_posts(after_id=None)
    for post in posts:
        yield _format_sse(post).encode()

    # Subscribe to the pub/sub channel for real-time events
    client = aioredis.from_url(REDIS_URL)
    pubsub = client.pubsub()
    await pubsub.subscribe(POSTS_PUBLISHED_CHANNEL)
    try:
        while True:
            message = await pubsub.get_message(
                ignore_subscribe_messages=True,
                timeout=float(_KEEPALIVE_INTERVAL),
            )
            if message is not None:
                data = json.loads(message["data"])
                yield _format_sse(data).encode()
            else:
                # timeout elapsed with no message — send keepalive
                yield b": keepalive\n\n"
    finally:
        await pubsub.unsubscribe(POSTS_PUBLISHED_CHANNEL)
        await client.aclose()


# ---------------------------------------------------------------------------
# SSE vs WebSockets — trade-off explanation
# ---------------------------------------------------------------------------
# SSE (Server-Sent Events):
#   - Unidirectional: server → client only. The browser cannot send data back
#     over the same connection.
#   - Works over plain HTTP/1.1; no protocol upgrade required.
#   - Automatic reconnect is built into the browser EventSource API.
#   - Lower complexity: no channel layer, no handshake, simple streaming view.
#   - Best for: read-only push streams (news feeds, live dashboards, this
#     endpoint — broadcasting newly published posts to subscribers).
#
# WebSockets:
#   - Bidirectional: both parties can send messages at any time.
#   - Requires an HTTP → WS upgrade handshake and a persistent TCP connection.
#   - Needs a channel layer (Redis) for multi-worker fanout.
#   - Higher complexity but essential for interactive real-time features
#     (live comment threads, collaborative editing, chat).
#   - Used in this project for the live comment feed on individual posts.
# ---------------------------------------------------------------------------


async def post_stream(request):
    """
    GET /api/posts/stream/

    Server-Sent Events stream of published posts.  On connect the client
    receives all currently published posts; new posts are pushed as they
    appear (polled every 5 s).  A keepalive comment is sent every 15 s.

    Event format::

        data: {"post_id": 1, "title": "Hello", "slug": "hello",
               "author": 2, "published_at": "2026-04-12T10:00:00+00:00"}

    No authentication required (mirrors the public posts list endpoint).
    """
    response = StreamingHttpResponse(
        _event_stream(request),
        content_type="text/event-stream",
    )
    response["Cache-Control"] = "no-cache"
    response["X-Accel-Buffering"] = "no"  # disable nginx buffering
    return response
