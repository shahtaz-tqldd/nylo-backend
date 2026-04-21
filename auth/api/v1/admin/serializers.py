from datetime import timedelta

from django.conf import settings
from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework import serializers

from auth.models import AdminAction, AdminInvitation, AdminModule, AdminProfile
from auth.services import send_admin_invitation


User = get_user_model()


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


class AdminPermissionSummarySerializer(serializers.Serializer):
    module = serializers.CharField()
    actions = serializers.ListField(child=serializers.ChoiceField(choices=AdminAction.choices))


class AdminUserListSerializer(serializers.ModelSerializer):
    full_name = serializers.CharField(read_only=True)
    job_title = serializers.CharField(source="admin_profile.job_title", read_only=True)
    permissions = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = (
            "id",
            "email",
            "full_name",
            "phone",
            "status",
            "is_active",
            "is_superuser",
            "job_title",
            "permissions",
            "date_joined",
        )
        read_only_fields = fields

    def get_permissions(self, obj):
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


class InvitationPermissionSerializer(serializers.Serializer):
    module = serializers.ChoiceField(choices=AdminModule.choices)
    actions = serializers.ListField(
        child=serializers.ChoiceField(choices=AdminAction.choices),
        allow_empty=False,
    )

    def validate_actions(self, value):
        deduped_actions = list(dict.fromkeys(value))
        if not deduped_actions:
            raise serializers.ValidationError("At least one action is required.")
        return deduped_actions


class AdminInvitationSerializer(serializers.ModelSerializer):
    permissions = serializers.SerializerMethodField()
    status = serializers.CharField(read_only=True)
    registration_url = serializers.SerializerMethodField()

    class Meta:
        model = AdminInvitation
        fields = (
            "id",
            "email",
            "job_title",
            "permissions",
            "status",
            "expires_at",
            "accepted_at",
            "revoked_at",
            "registration_url",
            "created_at",
            "updated_at",
        )
        read_only_fields = fields

    def get_permissions(self, obj):
        return obj.direct_permissions

    def get_registration_url(self, obj):
        invite_payload = self.context.get("invite_payload") or {}
        return invite_payload.get("registration_url")


class AdminInvitationCreateSerializer(serializers.Serializer):
    email = serializers.EmailField()
    job_title = serializers.CharField(required=False, allow_blank=True, max_length=100)
    permissions = InvitationPermissionSerializer(many=True, required=False)
    expires_in_hours = serializers.IntegerField(required=False, min_value=1, max_value=24 * 30)

    def validate_email(self, value):
        if User.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError("A user with this email already exists.")
        return value.lower()

    def validate_permissions(self, value):
        normalized_permissions = []
        seen = {}
        for item in value:
            module = item["module"]
            deduped_actions = []
            for action in item["actions"]:
                if action in deduped_actions:
                    continue
                deduped_actions.append(action)
            if module in seen:
                seen[module] = list(dict.fromkeys([*seen[module], *deduped_actions]))
            else:
                seen[module] = deduped_actions
        for module, actions in seen.items():
            normalized_permissions.append({"module": module, "actions": actions})
        return normalized_permissions

    def validate(self, attrs):
        attrs["expires_in_hours"] = attrs.get(
            "expires_in_hours",
            settings.ADMIN_INVITATION_EXPIRY_HOURS,
        )
        return attrs

    def create(self, validated_data):
        permissions = validated_data.pop("permissions", [])
        expires_in_hours = validated_data.pop("expires_in_hours")
        inviter = self.context["request"].user

        AdminInvitation.objects.filter(
            email__iexact=validated_data["email"],
            accepted_at__isnull=True,
            revoked_at__isnull=True,
            expires_at__gt=timezone.now(),
        ).update(revoked_at=timezone.now())

        invitation = AdminInvitation.objects.create(
            invited_by=inviter,
            direct_permissions=permissions,
            expires_at=timezone.now() + timedelta(hours=expires_in_hours),
            **validated_data,
        )
        invite_payload = send_admin_invitation(invitation)
        self.context["invite_payload"] = invite_payload
        return invitation


class AdminUserUpdateSerializer(serializers.Serializer):
    job_title = serializers.CharField(required=False, allow_blank=True, max_length=100)
    permissions = InvitationPermissionSerializer(many=True, required=False)

    def validate_permissions(self, value):
        normalized_permissions = []
        seen = {}
        for item in value:
            module = item["module"]
            deduped_actions = []
            for action in item["actions"]:
                if action in deduped_actions:
                    continue
                deduped_actions.append(action)
            if module in seen:
                seen[module] = list(dict.fromkeys([*seen[module], *deduped_actions]))
            else:
                seen[module] = deduped_actions
        for module, actions in seen.items():
            normalized_permissions.append({"module": module, "actions": actions})
        return normalized_permissions
