"""Serializers for the audit API."""

from rest_framework import serializers

from audit.models import AuditLog


class AuditLogSerializer(serializers.ModelSerializer):
    username = serializers.SerializerMethodField()

    class Meta:
        model = AuditLog
        fields = [
            "id",
            "action",
            "username",
            "document_pk",
            "document_title",
            "changes",
            "created_at",
        ]
        read_only_fields = fields

    def get_username(self, obj: AuditLog) -> str | None:
        return obj.user.username if obj.user else None
