"""Tests for WebSocket document notifications."""

from __future__ import annotations

from channels.db import database_sync_to_async
from channels.testing import WebsocketCommunicator
from rest_framework_simplejwt.tokens import RefreshToken

from accounts.models import User
from config.asgi import application
from documents.consumers import WebSocketObserver
from documents.repositories import InMemoryDocumentRepository
from documents.services import DocumentService
from documents.storage import InMemoryDocumentStorage


async def _make_user_and_token() -> tuple[User, str]:
    user = await database_sync_to_async(User.objects.create_user)(
        "hamid", "hamid@example.com", "secret123"
    )
    token = await database_sync_to_async(
        lambda: str(RefreshToken.for_user(user).access_token)
    )()
    return user, token


async def test_anonymous_connection_is_rejected() -> None:
    communicator = WebsocketCommunicator(application, "/ws/documents/")
    connected, _ = await communicator.connect()
    assert connected is False
    await communicator.disconnect()


async def test_invalid_token_is_rejected() -> None:
    communicator = WebsocketCommunicator(application, "/ws/documents/?token=garbage")
    connected, _ = await communicator.connect()
    assert connected is False
    await communicator.disconnect()


async def test_authenticated_connection_is_accepted(db: None) -> None:
    _, token = await _make_user_and_token()
    communicator = WebsocketCommunicator(application, f"/ws/documents/?token={token}")
    connected, _ = await communicator.connect()
    assert connected is True
    await communicator.disconnect()


async def test_document_event_is_broadcast_to_clients(db: None) -> None:
    user, token = await _make_user_and_token()
    communicator = WebsocketCommunicator(application, f"/ws/documents/?token={token}")
    connected, _ = await communicator.connect()
    assert connected is True

    service = DocumentService(
        InMemoryDocumentRepository(),
        InMemoryDocumentStorage(),
        observers=[WebSocketObserver()],
    )
    await database_sync_to_async(service.create)(
        user=user,
        title="Doc",
        description="",
        file_name="doc.txt",
        content_type="text/plain",
        data=b"body",
    )

    message = await communicator.receive_json_from()
    assert message["action"] == "created"
    assert message["document_title"] == "Doc"
    assert message["username"] == "hamid"

    await communicator.disconnect()
