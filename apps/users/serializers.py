from __future__ import annotations

import logging
from typing import Any
from zoneinfo import available_timezones

from django.conf import settings
from django.contrib.auth import get_user_model
from django.utils.translation import gettext_lazy as _
from rest_framework import serializers
from rest_framework_simplejwt.tokens import RefreshToken

logger = logging.getLogger("users")
User = get_user_model()


class UserOutSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = (
            "email",
            "first_name",
            "last_name",
            "avatar",
            "date_joined",
            "preferred_language",
            "timezone",
        )


class RegisterSerializer(serializers.Serializer):
    email = serializers.EmailField()
    first_name = serializers.CharField(max_length=50)
    last_name = serializers.CharField(max_length=50)
    password = serializers.CharField(write_only=True, min_length=8)
    password2 = serializers.CharField(write_only=True)
    preferred_language = serializers.ChoiceField(
        choices=[code for code, _ in settings.LANGUAGES],
        required=False,
        default="en",
        error_messages={
            "invalid_choice": _("Unsupported language."),
        },
    )
    timezone = serializers.CharField(required=False, default="UTC")

    def validate_timezone(self, value: str) -> str:
        if value not in available_timezones():
            raise serializers.ValidationError(_("Invalid timezone identifier."))
        return value

    def validate(self, attrs: dict[str, Any]) -> dict[str, Any]:
        if attrs["password"] != attrs["password2"]:
            raise serializers.ValidationError(
                {"password2": _("Passwords do not match.")}
            )
        return attrs

    def create(self, validated_data: dict[str, Any]) -> dict[str, Any]:
        password = validated_data.pop("password")
        validated_data.pop("password2")

        user = User.objects.create_user(password=password, **validated_data)
        refresh = RefreshToken.for_user(user)

        return {
            "user": UserOutSerializer(user).data,
            "tokens": {
                "refresh": str(refresh),
                "access": str(refresh.access_token),
            },
            "instance": user,
        }


class UpdateLanguageSerializer(serializers.Serializer):
    language = serializers.ChoiceField(
        choices=[code for code, _ in settings.LANGUAGES],
        error_messages={
            "invalid_choice": _("Unsupported language."),
            "required": _("This field is required."),
        },
    )


class UpdateTimezoneSerializer(serializers.Serializer):
    timezone = serializers.CharField()

    def validate_timezone(self, value: str) -> str:
        if value not in available_timezones():
            raise serializers.ValidationError(_("Invalid timezone identifier."))
        return value
