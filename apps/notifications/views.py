from __future__ import annotations

from rest_framework import mixins, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response

from .models import Notification
from .serializers import NotificationSerializer


# ---------------------------------------------------------------------------
# HTTP Polling — trade-off explanation
# ---------------------------------------------------------------------------
# HTTP Polling (this implementation):
#   - Simple to implement: standard REST endpoints, no persistent connections.
#   - Client polls /api/notifications/count/ on a fixed interval (e.g. 30 s).
#   - Latency equals the polling interval — notifications may arrive up to
#     30 s late from the recipient's perspective.
#   - Every poll is a full HTTP request/response cycle, even when there is
#     nothing new, wasting bandwidth and server resources at scale.
#
# Alternatives and their trade-offs:
#   - WebSockets: bidirectional, zero-latency push, but requires a persistent
#     connection and a channel layer — higher infrastructure complexity.
#   - SSE: server-push with zero latency, simpler than WebSockets (HTTP only),
#     but unidirectional; the client cannot acknowledge over the same stream.
#
# HTTP Polling is chosen here for its simplicity and broad compatibility.
# It is appropriate when slight notification delay is acceptable.
# ---------------------------------------------------------------------------
class NotificationViewSet(mixins.ListModelMixin, viewsets.GenericViewSet):
    serializer_class = NotificationSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Notification.objects.filter(recipient=self.request.user).select_related(
            "comment__post"
        )

    @action(detail=False, methods=["get"], url_path="count")
    def count(self, request: Request) -> Response:
        unread = self.get_queryset().filter(is_read=False).count()
        return Response({"unread": unread})

    @action(detail=False, methods=["post"], url_path="read")
    def read(self, request: Request) -> Response:
        ids = request.data.get("ids")
        qs = self.get_queryset().filter(is_read=False)
        if ids:
            qs = qs.filter(pk__in=ids)
        updated = qs.update(is_read=True)
        return Response({"marked_read": updated})
