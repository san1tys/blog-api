from __future__ import annotations

import logging

from django.utils.decorators import method_decorator 
from django_ratelimit.decorators import ratelimit
from rest_framework import status
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework_simplejwt.views import TokenObtainPairView

logger = logging.getLogger("users")
RATE_LIMIT_ERROR = {"detail": "Too many requests. Try again later."}


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