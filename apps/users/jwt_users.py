from __future__ import annotations

import logging

from django.utils.decorators import method_decorator
from django.utils.translation import gettext_lazy as _
from django_ratelimit.decorators import ratelimit
from drf_spectacular.utils import OpenApiExample, OpenApiResponse, extend_schema
from rest_framework import status
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework_simplejwt.serializers import TokenRefreshSerializer
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

logger = logging.getLogger("users")
RATE_LIMIT_ERROR = {"detail": _("Too many requests. Try again later.")}


@extend_schema(
    tags=["Auth"],
    summary="Log in and get JWT tokens",
    description=(
        "Authenticates a user by email and password and returns a refresh/access token pair. "
        "No prior authentication is required. This endpoint is rate-limited. "
        "When the limit is exceeded, it returns HTTP 429 with a localized message."
    ),
    request={
        "application/json": {
            "type": "object",
            "properties": {
                "email": {"type": "string", "format": "email"},
                "password": {"type": "string", "format": "password"},
            },
            "required": ["email", "password"],
        }
    },
    responses={
        200: OpenApiResponse(
            response={
                "type": "object",
                "properties": {
                    "refresh": {"type": "string"},
                    "access": {"type": "string"},
                },
            },
            description="JWT tokens returned successfully.",
        ),
        400: OpenApiResponse(
            description="Invalid credentials or malformed request body."
        ),
        429: OpenApiResponse(description="Too many login attempts."),
    },
    examples=[
        OpenApiExample(
            "Login request",
            value={"email": "john@example.com", "password": "StrongPass123"},
            request_only=True,
        ),
        OpenApiExample(
            "Login response",
            value={"refresh": "<refresh>", "access": "<access>"},
            response_only=True,
            status_codes=["200"],
        ),
    ],
)
class RateLimitedTokenObtainPairView(TokenObtainPairView):
    @method_decorator(ratelimit(key="ip", rate="10/m", method="POST", block=False))
    def post(self, request: Request, *args, **kwargs) -> Response:
        if getattr(request, "limited", False):
            logger.warning("Login rate limit exceeded for IP")
            return Response(RATE_LIMIT_ERROR, status=status.HTTP_429_TOO_MANY_REQUESTS)

        logger.info("Login attempt for email: %s", request.data.get("email"))
        resp = super().post(request, *args, **kwargs)
        if resp.status_code == 200:
            logger.info("Login success for email: %s", request.data.get("email"))
        else:
            logger.info("Login failed for email: %s", request.data.get("email"))
        return resp


@extend_schema(
    tags=["Auth"],
    summary="Refresh JWT access token",
    description=(
        "Accepts a valid refresh token and returns a new access token. "
        "No authentication header is required because the refresh token itself is used as proof."
    ),
    request=TokenRefreshSerializer,
    responses={
        200: OpenApiResponse(
            response={"type": "object", "properties": {"access": {"type": "string"}}},
            description="A new access token was issued.",
        ),
        400: OpenApiResponse(
            description="The refresh token is missing, expired, or invalid."
        ),
    },
    examples=[
        OpenApiExample(
            "Refresh request", value={"refresh": "<refresh>"}, request_only=True
        ),
        OpenApiExample(
            "Refresh response",
            value={"access": "<new-access>"},
            response_only=True,
            status_codes=["200"],
        ),
    ],
)
class DocumentedTokenRefreshView(TokenRefreshView):
    pass
