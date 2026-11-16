"""Tests for WebSocket document notifications."""

from __future__ import annotations

from channels.db import database_sync_to_async
from channels.testing import WebsocketCommunicator
from rest_framework_simplejwt.tokens import RefreshToken

from accounts.models import User
from config.asgi import application


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
