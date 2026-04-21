from django.contrib.auth import authenticate, get_user_model
from django.conf import settings
from django.db import transaction
from django.utils import timezone
from django.utils.text import slugify
from rest_framework import serializers
from rest_framework_simplejwt.tokens import RefreshToken
from uuid import uuid4

from app.utils.cloudinary import delete_image, upload_image
from auth.models import (
    AdminAction,
    AdminModule,
    AdminInvitation,
    UserRole,
    UserStatus,
)
from auth.services import assign_admin_access, resolve_admin_invitation


User = get_user_model()


class UserSerializer(serializers.ModelSerializer):
    job_title = serializers.CharField(source="admin_profile.job_title", read_only=True)
    permissions = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = (
            "id",
            "email",
            "first_name",
            "last_name",
            "phone",
            "role",
            "status",
            "job_title",
            "permissions",
            "address_line_1",
            "address_line_2",
            "city",
            "state_province",
            "postal_code",
            "country",
            "profile_picture_url",
            "is_active",
            "date_joined",
        )
        read_only_fields = ("id", "role", "status", "is_active", "date_joined")

    def get_permissions(self, obj):
        if not obj.is_admin_user:
            return []

        if obj.is_superuser:
            return [
                {
                    "module": module,
                    "actions": [action for action, _ in AdminAction.choices],
                }
                for module, _ in AdminModule.choices
            ]

        admin_profile = getattr(obj, "admin_profile", None)
        if not admin_profile:
            return []

        permissions = []
        for admin_permission in admin_profile.permissions.select_related("permission").all():
            permissions.append(
                {
                    "module": admin_permission.permission.module,
                    "actions": admin_permission.actions,
                }
            )
        return permissions


class UserUpdateSerializer(serializers.ModelSerializer):
    profile_picture = serializers.FileField(write_only=True, required=False, allow_null=True)

    class Meta:
        model = User
        fields = (
            "email",
            "first_name",
            "last_name",
            "phone",
            "address_line_1",
            "address_line_2",
            "city",
            "state_province",
            "postal_code",
            "country",
            "profile_picture",
            "profile_picture_url",
        )
        read_only_fields = ("profile_picture_url",)

    def update(self, instance, validated_data):
        profile_picture = validated_data.pop("profile_picture", serializers.empty)

        for attr, value in validated_data.items():
            setattr(instance, attr, value)

        if profile_picture is not serializers.empty:
            if profile_picture is None:
                if instance.profile_picture_url:
                    delete_image(image_url=instance.profile_picture_url)
                instance.profile_picture_url = ""
            else:
                if instance.profile_picture_url:
                    delete_image(image_url=instance.profile_picture_url)
                upload = upload_image(
                    profile_picture,
                    folder=f"{settings.CLOUDINARY_FOLDER}/users",
                    public_id=self._build_profile_picture_public_id(instance),
                )
                instance.profile_picture_url = upload["url"]

        instance.save()
        return instance

    def _build_profile_picture_public_id(self, user):
        base_name = slugify(user.full_name or user.email or "user-profile")
        return base_name or f"user-profile-{uuid4().hex[:8]}"


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=8)
    confirm_password = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = (
            "email",
            "first_name",
            "last_name",
            "phone",
            "password",
            "confirm_password",
        )

    def validate(self, attrs):
        if attrs["password"] != attrs["confirm_password"]:
            raise serializers.ValidationError({"confirm_password": "Passwords do not match."})
        return attrs

    def create(self, validated_data):
        validated_data.pop("confirm_password")
        password = validated_data.pop("password")
        user = User.objects.create_user(password=password, **validated_data)
        return user


class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)

    def validate(self, data):
        email = data.get("email")
        password = data.get("password")
        request = self.context.get("request")

        user = authenticate(request=request, email=email, password=password)

        if not user:
            raise serializers.ValidationError({"error": "Invalid credentials."})

        if not user.is_active:
            raise serializers.ValidationError({"error": "User is disabled."})

        user.last_login = timezone.now()
        user.save(update_fields=["last_login"])

        refresh = RefreshToken.for_user(user)

        return {
            "access_token": str(refresh.access_token),
            "refresh_token": str(refresh),
        }


class ChangePasswordSerializer(serializers.Serializer):
    current_password = serializers.CharField(write_only=True)
    new_password = serializers.CharField(write_only=True, min_length=8)
    confirm_password = serializers.CharField(write_only=True)

    def validate_current_password(self, value):
        user = self.context["request"].user
        if not user.check_password(value):
            raise serializers.ValidationError("Current password is incorrect.")
        return value

    def validate(self, attrs):
        if attrs["new_password"] != attrs["confirm_password"]:
            raise serializers.ValidationError({"confirm_password": "Passwords do not match."})
        if attrs["current_password"] == attrs["new_password"]:
            raise serializers.ValidationError(
                {"new_password": "New password must be different from the current password."}
            )
        return attrs

    def save(self, **kwargs):
        user = self.context["request"].user
        user.set_password(self.validated_data["new_password"])
        user.save(update_fields=["password"])
        return user


class PermissionAssignmentSerializer(serializers.Serializer):
    module = serializers.ChoiceField(choices=AdminModule.choices)
    actions = serializers.ListField(child=serializers.ChoiceField(choices=AdminAction.choices))


class AdminInvitationVerifySerializer(serializers.ModelSerializer):
    permissions = serializers.SerializerMethodField()

    class Meta:
        model = AdminInvitation
        fields = (
            "email",
            "job_title",
            "permissions",
            "expires_at",
        )
        read_only_fields = fields

    def get_permissions(self, obj):
        return obj.direct_permissions


class AdminInvitationRegistrationSerializer(serializers.Serializer):
    token = serializers.CharField()
    first_name = serializers.CharField(max_length=32)
    last_name = serializers.CharField(max_length=32)
    phone = serializers.CharField(required=False, allow_blank=True, max_length=17)
    password = serializers.CharField(write_only=True, min_length=8)
    confirm_password = serializers.CharField(write_only=True)

    def validate(self, attrs):
        if attrs["password"] != attrs["confirm_password"]:
            raise serializers.ValidationError({"confirm_password": "Passwords do not match."})

        try:
            invitation = resolve_admin_invitation(attrs["token"])
        except Exception as exc:
            raise serializers.ValidationError({"token": [str(exc)]}) from exc

        if User.objects.filter(email__iexact=invitation.email).exists():
            raise serializers.ValidationError({"email": "A user with this email already exists."})

        attrs["invitation"] = invitation
        return attrs

    @transaction.atomic
    def save(self, **kwargs):
        invitation = self.validated_data["invitation"]
        user = User.objects.create_user(
            email=invitation.email,
            password=self.validated_data["password"],
            first_name=self.validated_data["first_name"],
            last_name=self.validated_data["last_name"],
            phone=self.validated_data.get("phone", ""),
            role=UserRole.ADMIN,
            status=UserStatus.ACTIVE,
            is_staff=True,
            is_active=True,
        )

        assign_admin_access(
            user=user,
            permissions=invitation.direct_permissions,
            assigned_by=invitation.invited_by,
            job_title=invitation.job_title,
        )

        invitation.accepted_at = timezone.now()
        invitation.save(update_fields=["accepted_at", "updated_at"])

        refresh = RefreshToken.for_user(user)
        return {
            "user": user,
            "access_token": str(refresh.access_token),
            "refresh_token": str(refresh),
        }
