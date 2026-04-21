from django.core.exceptions import ValidationError
from rest_framework import status
from rest_framework.generics import CreateAPIView, GenericAPIView
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from rest_framework_simplejwt.views import TokenRefreshView

from app.utils.response import APIResponse
from auth.api.v1.client.serializers import (
    AdminInvitationRegistrationSerializer,
    AdminInvitationVerifySerializer,
    ChangePasswordSerializer,
    LoginSerializer,
    RegisterSerializer,
    UserSerializer,
    UserUpdateSerializer,
)
from auth.services import resolve_admin_invitation


class CreateNewUserView(CreateAPIView):
    serializer_class = RegisterSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        return APIResponse.success(
            data=UserSerializer(user).data,
            message="User created successfully.",
            status=status.HTTP_201_CREATED,
        )


class LoginView(GenericAPIView):
    serializer_class = LoginSerializer

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        return APIResponse.success(
            data=serializer.validated_data,
            message="User logged in.",
        )


class RefreshTokenView(TokenRefreshView):
    pass


class UserDetailsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        return APIResponse.success(data=UserSerializer(request.user).data)


class UserDetailsUpdateView(GenericAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = UserUpdateSerializer
    parser_classes = [MultiPartParser, FormParser]

    def patch(self, request, *args, **kwargs):
        serializer = self.get_serializer(request.user, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        return APIResponse.success(
            data=UserSerializer(user).data,
            message="User updated successfully.",
        )


class ChangePasswordView(GenericAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = ChangePasswordSerializer

    def patch(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return APIResponse.success(message="Password changed successfully.")


class AdminInvitationVerifyView(APIView):
    def get(self, request, *args, **kwargs):
        token = request.query_params.get("token", "").strip()
        if not token:
            return APIResponse.error(
                errors={"token": ["Invitation token is required."]},
                message="Invalid invitation token.",
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            invitation = resolve_admin_invitation(token)
        except ValidationError as exc:
            return APIResponse.error(
                errors={"token": [str(exc)]},
                message="Invitation verification failed.",
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = AdminInvitationVerifySerializer(invitation)
        return APIResponse.success(
            data=serializer.data,
            message="Invitation verified successfully.",
        )


class AdminInvitationRegistrationView(GenericAPIView):
    serializer_class = AdminInvitationRegistrationSerializer

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        result = serializer.save()
        return APIResponse.success(
            data={
                "user": UserSerializer(result["user"]).data,
                "access_token": result["access_token"],
                "refresh_token": result["refresh_token"],
            },
            message="Admin account created successfully.",
            status=status.HTTP_201_CREATED,
        )
