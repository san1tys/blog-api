from __future__ import annotations

from django.utils import timezone
from django.utils.formats import date_format
from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from .models import Category, Tag, Post, Comment


def format_localized_datetime(dt):
    local_dt = timezone.localtime(dt)
    return date_format(local_dt, format="DATETIME_FORMAT", use_l10n=True)


class CategorySerializer(serializers.ModelSerializer):
    name = serializers.SerializerMethodField()

    class Meta:
        model = Category
        fields = ("name", "slug")

    def get_name(self, obj) -> str:
        request = self.context.get("request")
        language_code = getattr(request, "LANGUAGE_CODE", "en")
        return obj.get_localized_name(language_code)


class TagSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tag
        fields = ("name", "slug")


class PostSerializer(serializers.ModelSerializer):
    author = serializers.PrimaryKeyRelatedField(read_only=True)
    category = CategorySerializer(read_only=True)
    tags = TagSerializer(many=True, read_only=True)
    category_id = serializers.PrimaryKeyRelatedField(
        queryset=Category.objects.all(),
        source="category",
        write_only=True,
        required=False,
        allow_null=True,
    )
    tag_ids = serializers.PrimaryKeyRelatedField(
        queryset=Tag.objects.all(),
        source="tags",
        many=True,
        write_only=True,
        required=False,
    )
    created_at_display = serializers.SerializerMethodField()
    updated_at_display = serializers.SerializerMethodField()

    class Meta:
        model = Post
        fields = (
            "id",
            "author",
            "title",
            "slug",
            "body",
            "category",
            "category_id",
            "tags",
            "tag_ids",
            "status",
            "created_at",
            "updated_at",
            "created_at_display",
            "updated_at_display",
        )
        read_only_fields = ("id", "author", "created_at", "updated_at")

    def validate_title(self, value):
        if not value.strip():
            raise serializers.ValidationError(_("Title cannot be empty."))
        return value

    def validate_body(self, value):
        if not value.strip():
            raise serializers.ValidationError(_("Body cannot be empty."))
        return value

    def get_created_at_display(self, obj) -> str:
        return format_localized_datetime(obj.created_at)

    def get_updated_at_display(self, obj) -> str:
        return format_localized_datetime(obj.updated_at)


class CommentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Comment
        fields = ("id", "post", "author", "body", "created_at")
        read_only_fields = ("id", "created_at", "author", "post")

    def validate_body(self, value):
        if not value.strip():
            raise serializers.ValidationError(_("Comment body cannot be empty."))
        return value
