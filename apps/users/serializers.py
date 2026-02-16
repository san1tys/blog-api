from __future__ import annotations

import logging
from typing import Any

from django.contrib.auth import get_user_model
from rest_framework import serializers
from rest_framework_simplejwt.tokens import RefreshToken

logger = logging.getLogger("users")
User = get_user_model()


class UserOutSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ("email", "first_name", "last_name", "avatar", "date_joined")


class RegisterSerializer(serializers.Serializer):
    email = serializers.EmailField()
    first_name = serializers.CharField(max_length=50)
    last_name = serializers.CharField(max_length=50)
    password = serializers.CharField(write_only=True)
    password2 = serializers.CharField(write_only=True)

    def validate(self, attrs: dict[str, Any]) -> dict[str, Any]:
        if attrs["password"] != attrs["password2"]:
            raise serializers.ValidationError({"password2": "Passwords don't match"})
        return attrs

    def create(self, validated_data: dict[str, Any]) -> dict[str, Any]:
        password = validated_data.pop("password")
        validated_data.pop("password2")

        user = User.objects.create_user(password=password, **validated_data)
        refresh = RefreshToken.for_user(user)

        return {
            "user": UserOutSerializer(user).data,
            "tokens": {"refresh": str(refresh), "access": str(refresh.access_token)},
        }
