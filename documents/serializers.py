"""Serializers for the documents API."""

from django.core.files.uploadedfile import UploadedFile
from rest_framework import serializers

from documents.models import Document
from documents.validation import validate_upload


class DocumentSerializer(serializers.ModelSerializer):
    uploaded_by = serializers.CharField(source="uploaded_by.username", read_only=True)

    class Meta:
        model = Document
        fields = [
            "id",
            "title",
            "description",
            "file_name",
            "content_type",
            "size",
            "storage_key",
            "uploaded_by",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields


class DocumentCreateSerializer(serializers.Serializer):
    file = serializers.FileField()
    title = serializers.CharField(max_length=255)
    description = serializers.CharField(required=False, allow_blank=True, default="")

    def validate_file(self, value: UploadedFile) -> UploadedFile:
        validate_upload(
            file_name=value.name or "",
            content_type=value.content_type or "",
            size=value.size or 0,
        )
        return value


class DocumentUpdateSerializer(serializers.Serializer):
    title = serializers.CharField(max_length=255, required=False)
    description = serializers.CharField(required=False, allow_blank=True)
    file = serializers.FileField(required=False)

    def validate_file(self, value: UploadedFile) -> UploadedFile:
        validate_upload(
            file_name=value.name or "",
            content_type=value.content_type or "",
            size=value.size or 0,
        )
        return value


class DocumentUrlSerializer(serializers.Serializer):
    url = serializers.CharField()
    expires_in = serializers.IntegerField()


class DocumentFilterSerializer(serializers.Serializer):
    """Query-string filters for the document list."""

    title = serializers.CharField(required=False, allow_blank=True)
    content_type = serializers.CharField(required=False, allow_blank=True)
    uploaded_by = serializers.CharField(required=False, allow_blank=True)
    created_after = serializers.DateField(required=False)
    created_before = serializers.DateField(required=False)
