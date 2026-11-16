"""WebSocket side of document events."""

from __future__ import annotations

from typing import Any

from channels.generic.websocket import AsyncJsonWebsocketConsumer


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
