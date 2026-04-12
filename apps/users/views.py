from __future__ import annotations

import logging

from django.utils.decorators import method_decorator
from django.utils.translation import gettext_lazy as _
from django_ratelimit.decorators import ratelimit
from drf_spectacular.utils import OpenApiExample, OpenApiResponse, extend_schema
from rest_framework import status, viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from .serializers import (
    RegisterSerializer,
    UpdateLanguageSerializer,
    UpdateTimezoneSerializer,
)
from .tasks import send_welcome_email

logger = logging.getLogger("users")
RATE_LIMIT_ERROR = {"detail": _("Too many requests. Try again later.")}


@extend_schema(
    tags=["Auth"],
    summary="Register a new user",
    description=(
        "Creates a new user account, returns JWT tokens, and sends a welcome email rendered from templates. "
        "No authentication is required. The welcome email language is taken from the preferred_language field "
        "submitted during registration and is independent from the current request language. This endpoint is rate-limited."
    ),
    request=RegisterSerializer,
    responses={
        201: OpenApiResponse(description="User created successfully."),
        400: OpenApiResponse(description="Validation error."),
        429: OpenApiResponse(description="Too many registration attempts."),
    },
    examples=[
        OpenApiExample(
            "Register request",
            value={
                "email": "john@example.com",
                "first_name": "John",
                "last_name": "Doe",
                "password": "StrongPass123",
                "password2": "StrongPass123",
                "preferred_language": "ru",
                "timezone": "Asia/Almaty",
            },
            request_only=True,
        ),
        OpenApiExample(
            "Register response",
            value={
                "user": {
                    "email": "john@example.com",
                    "first_name": "John",
                    "last_name": "Doe",
                    "avatar": None,
                    "date_joined": "2026-03-13T14:00:00Z",
                    "preferred_language": "ru",
                    "timezone": "Asia/Almaty",
                },
                "tokens": {"refresh": "<refresh>", "access": "<access>"},
            },
            response_only=True,
            status_codes=["201"],
        ),
    ],
)
class RegisterViewSet(viewsets.ViewSet):
    serializer_class = RegisterSerializer

    @method_decorator(ratelimit(key="ip", rate="5/m", method="POST", block=False))
    def create(self, request: Request) -> Response:
        if getattr(request, "limited", False):
            logger.warning("Registration rate limit exceeded")
            return Response(RATE_LIMIT_ERROR, status=status.HTTP_429_TOO_MANY_REQUESTS)

        logger.info("Registration attempt for email: %s", request.data.get("email"))
        serializer = self.serializer_class(data=request.data)
        if not serializer.is_valid():
            logger.info(
                "Registration failed for email: %s; errors=%s",
                request.data.get("email"),
                serializer.errors,
            )
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        res = serializer.save()
        user = res.pop("instance")
        if user.email:
            send_welcome_email.delay(user.id)

        logger.info("User registered: %s", res["user"]["email"])
        return Response(res, status=status.HTTP_201_CREATED)


@extend_schema(
    tags=["Auth"],
    summary="Update preferred language",
    description=(
        "Updates the authenticated user's preferred language. Authentication is required. "
        "The language must be one of the supported values: en, ru, kk. The saved language "
        "takes top priority on future requests over query parameters and Accept-Language."
    ),
    request=UpdateLanguageSerializer,
    responses={
        200: OpenApiResponse(description="Language updated successfully."),
        400: OpenApiResponse(description="Unsupported language or malformed body."),
        401: OpenApiResponse(description="Authentication required."),
    },
    examples=[
        OpenApiExample("Language request", value={"language": "kk"}, request_only=True),
        OpenApiExample(
            "Language response",
            value={"detail": "Language preference updated successfully."},
            response_only=True,
            status_codes=["200"],
        ),
    ],
)
class UpdateLanguageView(APIView):
    permission_classes = [IsAuthenticated]
    serializer_class = UpdateLanguageSerializer

    def patch(self, request: Request) -> Response:
        serializer = UpdateLanguageSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        request.user.preferred_language = serializer.validated_data["language"]
        request.user.save(update_fields=["preferred_language"])
        return Response(
            {"detail": _("Language preference updated successfully.")},
            status=status.HTTP_200_OK,
        )


@extend_schema(
    tags=["Auth"],
    summary="Update preferred timezone",
    description=(
        "Updates the authenticated user's timezone. Authentication is required. "
        "The timezone must be a real IANA timezone identifier such as Asia/Almaty or Europe/Moscow. "
        "If the value is invalid, the endpoint returns HTTP 400 with a localized validation error."
    ),
    request=UpdateTimezoneSerializer,
    responses={
        200: OpenApiResponse(description="Timezone updated successfully."),
        400: OpenApiResponse(description="Invalid timezone identifier."),
        401: OpenApiResponse(description="Authentication required."),
    },
    examples=[
        OpenApiExample(
            "Timezone request", value={"timezone": "Asia/Almaty"}, request_only=True
        ),
        OpenApiExample(
            "Timezone response",
            value={"detail": "Timezone updated successfully."},
            response_only=True,
            status_codes=["200"],
        ),
    ],
)
class UpdateTimezoneView(APIView):
    permission_classes = [IsAuthenticated]
    serializer_class = UpdateTimezoneSerializer

    def patch(self, request: Request) -> Response:
        serializer = UpdateTimezoneSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        request.user.timezone = serializer.validated_data["timezone"]
        request.user.save(update_fields=["timezone"])
        return Response(
            {"detail": _("Timezone updated successfully.")}, status=status.HTTP_200_OK
        )
