"""Auth and user-management views (thin — logic lives in services)."""

from django.contrib.auth import get_user_model
from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.serializers import (
    TokenObtainPairSerializer,
    TokenRefreshSerializer,
)
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from accounts.permissions import IsAdminRole
from accounts.serializers import (
    LogoutSerializer,
    PasswordResetConfirmSerializer,
    PasswordResetRequestSerializer,
    RoleUpdateSerializer,
    UserSerializer,
)
from accounts.services import request_password_reset, reset_password

User = get_user_model()


@extend_schema(
    auth=[],  # public endpoint
    tags=["Auth"],
    summary="Log in",
    description="Exchange a username/password for a JWT access + refresh pair.",
    request=TokenObtainPairSerializer,
    responses={200: TokenObtainPairSerializer},
)
class LoginView(TokenObtainPairView):
    """Username + password -> JWT access/refresh pair.

    No permission override: simplejwt's base view is already open.
    """

    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "auth"


@extend_schema(
    auth=[],
    tags=["Auth"],
    summary="Refresh the access token",
    request=TokenRefreshSerializer,
    responses={200: TokenRefreshSerializer},
)
class RefreshView(TokenRefreshView):
    """Exchange a refresh token for a new access token.

    No permission override: simplejwt's base view is already open.
    """

    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "auth"


@extend_schema(
    tags=["Auth"],
    summary="Log out",
    description="Blacklist the refresh token (irreversible).",
    request=LogoutSerializer,
    responses={204: OpenApiResponse(description="Refresh token blacklisted")},
)
class LogoutView(APIView):
    """Blacklist the refresh token so it can never be used again."""

    permission_classes = [IsAuthenticated]

    def post(self, request: Request) -> Response:
        serializer = LogoutSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            token = RefreshToken(serializer.validated_data["refresh"])
            token.blacklist()
        except TokenError:
            return Response(
                {"detail": "Invalid token."}, status=status.HTTP_400_BAD_REQUEST
            )
        return Response(status=status.HTTP_204_NO_CONTENT)


@extend_schema(
    auth=[],
    tags=["Password"],
    summary="Request a password reset",
    description="Sends a reset link by email. Unknown addresses get 200 (no leak).",
    request=PasswordResetRequestSerializer,
    responses={
        200: OpenApiResponse(description="If the account exists, an email was sent")
    },
)
class PasswordResetRequestView(APIView):
    """Request a password-reset link by email."""

    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "auth"

    def post(self, request: Request) -> Response:
        serializer = PasswordResetRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        request_password_reset(serializer.validated_data["email"])
        return Response({"detail": "If that email exists, a reset link was sent."})


@extend_schema(
    auth=[],
    tags=["Password"],
    summary="Confirm a password reset",
    description="Set a new password using the uid + token from the email link.",
    request=PasswordResetConfirmSerializer,
    responses={
        200: OpenApiResponse(description="Password updated"),
        400: OpenApiResponse(description="Invalid token or password"),
    },
)
class PasswordResetConfirmView(APIView):
    """Confirm a reset with uid/token and set the new password."""

    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "auth"

    def post(self, request: Request) -> Response:
        serializer = PasswordResetConfirmSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        if not reset_password(data["uid"], data["token"], data["new_password"]):
            return Response(
                {"detail": "Invalid or expired link."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return Response({"detail": "Password updated."})


class UserListCreateView(APIView):
    """Admin: list users (GET) and create users (POST)."""

    permission_classes = [IsAdminRole]

    @extend_schema(
        tags=["Users"],
        summary="List users (admin)",
        responses=UserSerializer(many=True),
    )
    def get(self, request: Request) -> Response:
        users = User.objects.all().order_by("id")
        return Response(UserSerializer(users, many=True).data)

    @extend_schema(
        tags=["Users"],
        summary="Create a user (admin)",
        request=UserSerializer,
        responses={201: UserSerializer},
    )
    def post(self, request: Request) -> Response:
        serializer = UserSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)


@extend_schema(
    tags=["Users"],
    summary="Change a user's role (admin)",
    request=RoleUpdateSerializer,
    responses={200: RoleUpdateSerializer},
)
class UserRoleView(APIView):
    """Admin: change a user's role (PATCH)."""

    permission_classes = [IsAdminRole]

    def patch(self, request: Request, pk: int) -> Response:
        user = User.objects.filter(pk=pk).first()
        if user is None:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        serializer = RoleUpdateSerializer(user, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)
