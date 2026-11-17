"""WebSocket routes."""

from typing import Any, cast

from django.urls import path

from documents.consumers import DocumentEventsConsumer

# django-stubs types path() for HTTP views; Channels' URLRouter accepts ASGI
# apps here — the cast bridges the two stub packages.
websocket_urlpatterns: list[Any] = [
    path("ws/documents/", cast(Any, DocumentEventsConsumer.as_asgi())),
]
