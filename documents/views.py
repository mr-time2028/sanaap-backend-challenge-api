"""Document endpoints (plain APIViews — logic lives in DocumentService)."""

from __future__ import annotations

from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from documents.serializers import (
    DocumentCreateSerializer,
    DocumentSerializer,
    DocumentUpdateSerializer,
)
from documents.services import get_document_service


class DocumentListCreateView(APIView):
    @extend_schema(
        tags=["Documents"],
        summary="List documents",
        responses=DocumentSerializer(many=True),
    )
    def get(self, request: Request) -> Response:
        documents = get_document_service().list()
        return Response(DocumentSerializer(documents, many=True).data)

    @extend_schema(
        tags=["Documents"],
        summary="Upload a document",
        description="Multipart form: file, title, optional description.",
        request=DocumentCreateSerializer,
        responses={201: DocumentSerializer},
    )
    def post(self, request: Request) -> Response:
        serializer = DocumentCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        file = serializer.validated_data["file"]
        document = get_document_service().create(
            user=request.user,
            title=serializer.validated_data["title"],
            description=serializer.validated_data.get("description", ""),
            file_name=file.name,
            content_type=file.content_type or "",
            data=file.read(),
        )
        return Response(
            DocumentSerializer(document).data, status=status.HTTP_201_CREATED
        )


class DocumentDetailView(APIView):
    @extend_schema(tags=["Documents"], summary="Get document metadata")
    def get(self, request: Request, pk: int) -> Response:
        document = get_document_service().get(pk)
        if document is None:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        return Response(DocumentSerializer(document).data)

    @extend_schema(
        tags=["Documents"],
        summary="Update a document",
        description="Update title, description and/or replace the file.",
        request=DocumentUpdateSerializer,
        responses={200: DocumentSerializer},
    )
    def patch(self, request: Request, pk: int) -> Response:
        service = get_document_service()
        document = service.get(pk)
        if document is None:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        serializer = DocumentUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        file = data.get("file")
        updated = service.update(
            document,
            title=data.get("title"),
            description=data.get("description"),
            file_name=file.name if file is not None else None,
            content_type=(file.content_type or "") if file is not None else None,
            data=file.read() if file is not None else None,
        )
        return Response(DocumentSerializer(updated).data)

    @extend_schema(
        tags=["Documents"], summary="Delete a document (metadata + stored file)"
    )
    def delete(self, request: Request, pk: int) -> Response:
        service = get_document_service()
        document = service.get(pk)
        if document is None:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        service.delete(document)
        return Response(status=status.HTTP_204_NO_CONTENT)
