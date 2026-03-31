from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from auth.models import (
    Action,
    AdminPermission,
    AdminProfile,
    AdminRoleAssignment,
    PermissionRole,
    Resource,
    RolePermission,
    User,
)


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    ordering = ("-created_at",)
    list_display = ("email", "first_name", "last_name", "role", "status", "is_staff", "is_active")
    search_fields = ("email", "first_name", "last_name", "phone")
    readonly_fields = ("id", "date_joined", "created_at", "updated_at", "last_login")

    fieldsets = (
        ("Credentials", {"fields": ("email", "password")}),
        ("Profile", {"fields": ("first_name", "last_name", "phone", "profile_picture_url")}),
        (
            "Address",
            {
                "fields": (
                    "address_line_1",
                    "address_line_2",
                    "city",
                    "state_province",
                    "postal_code",
                    "country",
                )
            },
        ),
        ("Access", {"fields": ("role", "status", "is_active", "is_staff", "is_superuser", "groups", "user_permissions")}),
        ("Important dates", {"fields": ("last_login", "date_joined", "created_at", "updated_at")}),
    )

    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": ("email", "first_name", "last_name", "password1", "password2", "role", "status"),
            },
        ),
    )


admin.site.register(AdminProfile)
admin.site.register(Resource)
admin.site.register(Action)
admin.site.register(AdminPermission)
admin.site.register(PermissionRole)
admin.site.register(RolePermission)
admin.site.register(AdminRoleAssignment)
