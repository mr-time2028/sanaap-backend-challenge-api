"""Serializers for auth and user management."""

from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers


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
