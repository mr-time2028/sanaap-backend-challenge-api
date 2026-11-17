"""Domain events — the Observer seam.

Services publish; observers react (the audit recorder today, the WebSocket
broadcaster later). Events are frozen value objects — serializable, no ORM.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal, Protocol

DocumentAction = Literal["created", "updated", "deleted"]


@dataclass(frozen=True)
class DocumentEvent:
    action: DocumentAction
    document_id: int
    document_title: str
    user: Any = None
    changes: dict[str, Any] = field(default_factory=dict)


class DocumentObserver(Protocol):
    def on_document_event(self, event: DocumentEvent) -> None: ...
