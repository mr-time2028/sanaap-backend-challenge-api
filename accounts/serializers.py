"""Serializers for auth and user management."""

from typing import Any

from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers

from accounts.models import User


class LogoutSerializer(serializers.Serializer):
    """Payload for logout: the refresh token to blacklist."""

    refresh = serializers.CharField()


class PasswordResetRequestSerializer(serializers.Serializer):
    email = serializers.EmailField()


class PasswordResetConfirmSerializer(serializers.Serializer):
    uid = serializers.CharField()
    token = serializers.CharField()
    new_password = serializers.CharField(
        write_only=True, validators=[validate_password]
    )


class UserSerializer(serializers.ModelSerializer):
    """Create and list users (admin-only)."""

    password = serializers.CharField(write_only=True, validators=[validate_password])

    class Meta:
        model = User
        fields = ["id", "username", "email", "role", "password"]

    def create(self, validated_data: dict[str, Any]) -> User:
        return User.objects.create_user(**validated_data)


class RoleUpdateSerializer(serializers.ModelSerializer):
    """Change a user's role (admin-only)."""

    class Meta:
        model = User
        fields = ["role"]
