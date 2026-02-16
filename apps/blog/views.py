from __future__ import annotations

import json
import logging

from django.core.cache import cache
from django.shortcuts import get_object_or_404
from django.utils.decorators import method_decorator         
from django_ratelimit.decorators import ratelimit
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticatedOrReadOnly

from .models import Comment, Post, PostStatus
from .permissions import IsOwnerOrReadOnly
from .serializers import CommentSerializer, PostSerializer

logger = logging.getLogger("blog")

POSTS_LIST_CACHE_KEY = "posts:list:published"
POSTS_LIST_TTL_SECONDS = 60

RATE_LIMIT_ERROR = {"detail": "Too many requests. Try again later."}


class PostViewSet(viewsets.ModelViewSet):
    serializer_class = PostSerializer
    lookup_field = "slug"
    permission_classes = [IsAuthenticatedOrReadOnly, IsOwnerOrReadOnly]

    def get_queryset(self):
        qs = Post.objects.select_related("author", "category").prefetch_related("tags")
        if self.action in ("list", "retrieve", "comments"):
            return qs.filter(status=PostStatus.PUBLISHED).order_by("-created_at")
        return qs

    def list(self, request: Request, *args, **kwargs) -> Response:
        cached = cache.get(POSTS_LIST_CACHE_KEY)
        if cached is not None:
            return Response(cached)

        resp = super().list(request, *args, **kwargs)
        cache.set(POSTS_LIST_CACHE_KEY, resp.data, POSTS_LIST_TTL_SECONDS)
        return resp

    @method_decorator(ratelimit(key="user", rate="20/m", method="POST", block=False))
    def create(self, request: Request, *args, **kwargs) -> Response:
        if getattr(request, "limited", False):
            logger.warning("Post create rate limit exceeded for user/ip")
            return Response(RATE_LIMIT_ERROR, status=status.HTTP_429_TOO_MANY_REQUESTS)

        if not request.user.is_authenticated:
            return Response(
                {"detail": "Authentication required"},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        logger.info("Post creation attempt by user: %s", request.user.email)
        try:
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            post = serializer.save(author=request.user)
            cache.delete(POSTS_LIST_CACHE_KEY)
            logger.info("Post created: %s by %s", post.slug, request.user.email)
            return Response(
                self.get_serializer(post).data, status=status.HTTP_201_CREATED
            )
        except Exception:
            logger.exception(
                "Post creation exception by user: %s",
                getattr(request.user, "email", None),
            )
            raise

    def update(self, request: Request, *args, **kwargs) -> Response:
        resp = super().update(request, *args, **kwargs)
        cache.delete(POSTS_LIST_CACHE_KEY)
        logger.info("Post updated: %s by %s", kwargs.get("slug"), request.user.email)
        return resp

    def destroy(self, request: Request, *args, **kwargs) -> Response:
        slug = kwargs.get("slug")
        resp = super().destroy(request, *args, **kwargs)
        cache.delete(POSTS_LIST_CACHE_KEY)
        logger.info("Post deleted: %s by %s", slug, request.user.email)
        return resp

    @action(detail=True, methods=["get", "post"], url_path="comments")
    def comments(self, request: Request, slug: str | None = None) -> Response:
        post = get_object_or_404(Post, slug=slug, status=PostStatus.PUBLISHED)

        if request.method == "GET":
            qs = (
                Comment.objects.filter(post=post)
                .select_related("author")
                .order_by("-created_at")
            )
            return Response(CommentSerializer(qs, many=True).data)

        if not request.user.is_authenticated:
            return Response(
                {"detail": "Authentication required"},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        logger.info(
            "Comment creation attempt by user %s on post %s",
            request.user.email,
            post.slug,
        )
        serializer = CommentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        comment = Comment.objects.create(
            post=post,
            author=request.user,
            body=serializer.validated_data["body"],
        )
        logger.info("Comment created: %s on post %s", comment.id, post.slug)

        from redis import Redis
        from settings.conf import REDIS_URL

        event = {
            "type": "comment.created",
            "post": post.slug,
            "comment_id": comment.id,
            "author": request.user.email,
        }
        Redis.from_url(REDIS_URL).publish("comments", json.dumps(event))

        return Response(CommentSerializer(comment).data, status=status.HTTP_201_CREATED)