from __future__ import annotations

from rest_framework.permissions import BasePermission
from rest_framework.request import Request
from rest_framework.views import View


class IsOwnerOrReadOnly(BasePermission):
    def has_object_permission(self, request: Request, view: View, obj: object) -> bool:
        if request.method in ("GET", "HEAD", "OPTIONS"):
            return True

        return getattr(obj, "author_id", None) == getattr(request.user, "id", None)
