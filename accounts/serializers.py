"""Serializers for auth and user management."""

from rest_framework import serializers


class LogoutSerializer(serializers.Serializer):
    """Payload for logout: the refresh token to blacklist."""

    refresh = serializers.CharField()
