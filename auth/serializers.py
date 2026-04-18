from django.contrib.auth import authenticate, get_user_model
from django.conf import settings
from django.utils import timezone
from django.utils.text import slugify
from rest_framework import serializers
from rest_framework_simplejwt.tokens import RefreshToken
from uuid import uuid4

from app.utils.cloudinary import delete_image, upload_image


User = get_user_model()


class UserSerializer(serializers.ModelSerializer):
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


class CustomerListSerializer(serializers.ModelSerializer):
    full_name = serializers.CharField(read_only=True)
    region = serializers.CharField(read_only=True)
    last_active_at = serializers.DateTimeField(source="last_login", read_only=True)

    class Meta:
        model = User
        fields = (
            "id",
            "email",
            "full_name",
            "region",
            "phone",
            "status",
            "last_active_at",
            "is_active",
            "date_joined",
        )
        read_only_fields = fields


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
