"""Audit trail endpoint (admin only)."""

from __future__ import annotations

from drf_spectacular.utils import extend_schema
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from audit.models import AuditLog
from audit.permissions import AuditLogPermission
from audit.serializers import AuditLogSerializer
from config.pagination import StandardPagination


class AuditLogListView(APIView):
    permission_classes = [AuditLogPermission]

    @extend_schema(
        tags=["Audit"],
        summary="List audit log entries (admin only)",
        description="Every document create/update/delete with actor and change diff. Paginated.",
        responses=AuditLogSerializer(many=True),
    )
    def get(self, request: Request) -> Response:
        entries = AuditLog.objects.all()
        paginator = StandardPagination()
        page = paginator.paginate_queryset(entries, request)
        serializer = AuditLogSerializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)
