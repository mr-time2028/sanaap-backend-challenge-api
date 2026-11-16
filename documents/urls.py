"""Document routes."""

from django.urls import path

from documents.views import (
    DocumentDetailView,
    DocumentDownloadView,
    DocumentListCreateView,
    DocumentUrlView,
)

urlpatterns = [
    path("documents/", DocumentListCreateView.as_view(), name="document-list"),
    path("documents/<int:pk>/", DocumentDetailView.as_view(), name="document-detail"),
    path(
        "documents/<int:pk>/download/",
        DocumentDownloadView.as_view(),
        name="document-download",
    ),
    path("documents/<int:pk>/url/", DocumentUrlView.as_view(), name="document-url"),
]
