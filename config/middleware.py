"""WebSocket authentication — the JWT travels as a ?token= query parameter."""

from __future__ import annotations

from typing import Any
from urllib.parse import parse_qs

from channels.db import database_sync_to_async
from channels.middleware import BaseMiddleware
from django.contrib.auth.models import AnonymousUser
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import AccessToken

from accounts.models import User


class JWTAuthMiddleware(BaseMiddleware):
    async def __call__(self, scope: Any, receive: Any, send: Any) -> Any:
        scope["user"] = AnonymousUser()
        token = (
            parse_qs(scope.get("query_string", b"").decode()).get("token") or [None]
        )[0]
        if token:
            try:
                payload = AccessToken(token)
                scope["user"] = await database_sync_to_async(User.objects.get)(
                    pk=payload["user_id"]
                )
            except (TokenError, User.DoesNotExist, KeyError):
                pass
        return await super().__call__(scope, receive, send)
