from __future__ import annotations

import logging

from django_ratelimit.decorators import ratelimit
from django.utils.decorators import method_decorator

from rest_framework import status, viewsets
from rest_framework.request import Request
from rest_framework.response import Response

from .serializers import RegisterSerializer

logger = logging.getLogger("users")

RATE_LIMIT_ERROR = {"detail": "Too many requests. Try again later."}


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

        try:
            res = serializer.save()
        except Exception:
            logger.exception(
                "Registration exception for email: %s", request.data.get("email")
            )
            raise

        logger.info("User registered: %s", res["user"]["email"])
        return Response(res, status=status.HTTP_201_CREATED)
