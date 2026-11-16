"""WebSocket side of document events."""

from __future__ import annotations

from typing import Any

from asgiref.sync import async_to_sync
from channels.generic.websocket import AsyncJsonWebsocketConsumer
from channels.layers import get_channel_layer

from documents.events import DocumentEvent


class DocumentEventsConsumer(AsyncJsonWebsocketConsumer):
    """Pushes document events to every connected, authenticated client."""

    GROUP = "documents"

    async def connect(self) -> None:
        user = self.scope.get("user")
        if user is None or user.is_anonymous:
            await self.close()
            return
        await self.channel_layer.group_add(self.GROUP, self.channel_name)
        await self.accept()

    async def disconnect(self, code: int) -> None:
        await self.channel_layer.group_discard(self.GROUP, self.channel_name)

    async def document_event(self, event: dict[str, Any]) -> None:
        await self.send_json(
            {
                "action": event["action"],
                "document_id": event["document_id"],
                "document_title": event["document_title"],
                "username": event["username"],
                "changes": event["changes"],
            }
        )


class WebSocketObserver:
    """Observer that broadcasts document events to the channel-layer group."""

    def on_document_event(self, event: DocumentEvent) -> None:
        async_to_sync(self._broadcast)(event)

    async def _broadcast(self, event: DocumentEvent) -> None:
        channel_layer = get_channel_layer()
        if channel_layer is None:
            return
        await channel_layer.group_send(
            DocumentEventsConsumer.GROUP,
            {
                "type": "document.event",
                "action": event.action,
                "document_id": event.document_id,
                "document_title": event.document_title,
                "username": getattr(event.user, "username", None),
                "changes": event.changes,
            },
        )
