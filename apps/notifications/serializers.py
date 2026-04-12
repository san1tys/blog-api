from __future__ import annotations

from rest_framework import serializers

from .models import Notification


class NotificationSerializer(serializers.ModelSerializer):
    post_slug = serializers.SerializerMethodField()
    comment_preview = serializers.SerializerMethodField()

    class Meta:
        model = Notification
        fields = [
            "id",
            "comment_id",
            "post_slug",
            "comment_preview",
            "is_read",
            "created_at",
        ]
        read_only_fields = fields

    def get_post_slug(self, obj: Notification) -> str:
        return obj.comment.post.slug

    def get_comment_preview(self, obj: Notification) -> str:
        body = obj.comment.body.strip().replace("\n", " ")
        return body[:80] + ("…" if len(body) > 80 else "")
