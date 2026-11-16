"""Auth and user-management routes."""

from django.urls import path

from accounts.views import LoginView, LogoutView, RefreshView

urlpatterns = [
    path("auth/login/", LoginView.as_view(), name="login"),
    path("auth/refresh/", RefreshView.as_view(), name="token-refresh"),
    path("auth/logout/", LogoutView.as_view(), name="logout"),
]
