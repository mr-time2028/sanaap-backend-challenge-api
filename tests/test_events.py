"""Tests for document events — the Observer seam."""

from __future__ import annotations

from documents.events import DocumentEvent
from documents.models import Document
from documents.repositories import InMemoryDocumentRepository
from documents.services import DocumentService
from documents.storage import InMemoryDocumentStorage


class RecordingObserver:
    def __init__(self) -> None:
        self.events: list[DocumentEvent] = []

    def on_document_event(self, event: DocumentEvent) -> None:
        self.events.append(event)


def make_service(observer: RecordingObserver | None = None) -> DocumentService:
    observers = (observer,) if observer is not None else ()
    return DocumentService(
        InMemoryDocumentRepository(), InMemoryDocumentStorage(), observers=observers
    )


def create_doc(service: DocumentService) -> Document:
    return service.create(
        user=None,
        title="Doc",
        description="",
        file_name="doc.txt",
        content_type="text/plain",
        data=b"body",
    )


def test_create_publishes_created_event() -> None:
    observer = RecordingObserver()
    service = make_service(observer)
    document = create_doc(service)
    assert observer.events[0].action == "created"
    assert observer.events[0].document_id == document.pk
    assert observer.events[0].changes["file_name"] == "doc.txt"


def test_update_publishes_event_with_diff() -> None:
    observer = RecordingObserver()
    service = make_service(observer)
    document = create_doc(service)
    observer.events.clear()
    service.update(document, title="New")
    assert observer.events[0].action == "updated"
    assert observer.events[0].changes["title"] == {"old": "Doc", "new": "New"}


def test_update_without_changes_publishes_nothing() -> None:
    observer = RecordingObserver()
    service = make_service(observer)
    document = create_doc(service)
    observer.events.clear()
    service.update(document, title="Doc")
    assert observer.events == []


def test_delete_publishes_deleted_event() -> None:
    observer = RecordingObserver()
    service = make_service(observer)
    document = create_doc(service)
    document_id = document.pk
    observer.events.clear()
    service.delete(document)
    assert observer.events[0].action == "deleted"
    assert observer.events[0].document_id == document_id


def test_no_observers_is_fine() -> None:
    service = make_service()
    document = create_doc(service)
    service.delete(document)
    assert service.list() == []
