import django.db.models.deletion
import uuid
from django.db import migrations, models

import auth.models


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        ("auth", "0012_alter_user_first_name_max_length"),
    ]

    operations = [
        migrations.CreateModel(
            name="Action",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                (
                    "name",
                    models.CharField(
                        choices=[
                            ("VIEW", "View"),
                            ("CREATE", "Create"),
                            ("UPDATE", "Update"),
                            ("DELETE", "Delete"),
                            ("EXPORT", "Export"),
                        ],
                        max_length=50,
                        unique=True,
                        verbose_name="Action Name",
                    ),
                ),
                ("description", models.TextField(blank=True, verbose_name="Description")),
            ],
            options={"verbose_name": "Action", "verbose_name_plural": "Actions"},
        ),
        migrations.CreateModel(
            name="PermissionRole",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("name", models.CharField(max_length=100, unique=True, verbose_name="Role Name")),
                ("description", models.TextField(blank=True, verbose_name="Role Description")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={"verbose_name": "Permission Role", "verbose_name_plural": "Permission Roles"},
        ),
        migrations.CreateModel(
            name="Resource",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                (
                    "name",
                    models.CharField(
                        choices=[
                            ("PRODUCTS", "Products"),
                            ("CUSTOMERS", "Customers"),
                            ("ORDERS", "Orders"),
                            ("MESSAGES", "Messages"),
                            ("COUPONS", "Coupons"),
                            ("SALES", "Sales"),
                        ],
                        max_length=50,
                        unique=True,
                        verbose_name="Resource Name",
                    ),
                ),
                ("description", models.TextField(blank=True, verbose_name="Description")),
            ],
            options={"verbose_name": "Resource", "verbose_name_plural": "Resources"},
        ),
        migrations.CreateModel(
            name="User",
            fields=[
                ("password", models.CharField(max_length=128, verbose_name="password")),
                ("last_login", models.DateTimeField(blank=True, null=True, verbose_name="last login")),
                (
                    "is_superuser",
                    models.BooleanField(
                        default=False,
                        help_text="Designates that this user has all permissions without explicitly assigning them.",
                        verbose_name="superuser status",
                    ),
                ),
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                (
                    "email",
                    models.EmailField(
                        help_text="A valid email address is required.",
                        max_length=254,
                        unique=True,
                        verbose_name="Email Address",
                    ),
                ),
                ("first_name", models.CharField(max_length=32, verbose_name="First Name")),
                ("last_name", models.CharField(max_length=32, verbose_name="Last Name")),
                ("phone", models.CharField(blank=True, max_length=17, validators=[auth.models.phone_regex], verbose_name="Phone Number")),
                (
                    "role",
                    models.CharField(
                        choices=[("CUSTOMER", "Customer"), ("ADMIN", "Admin")],
                        default="CUSTOMER",
                        max_length=16,
                        verbose_name="User Role",
                    ),
                ),
                (
                    "status",
                    models.CharField(
                        choices=[("INACTIVE", "Inactive"), ("ACTIVE", "Active"), ("BLOCKED", "Blocked")],
                        default="INACTIVE",
                        max_length=16,
                        verbose_name="User Status",
                    ),
                ),
                ("address_line_1", models.CharField(blank=True, max_length=100, verbose_name="Address Line 1")),
                ("address_line_2", models.CharField(blank=True, max_length=100, verbose_name="Address Line 2")),
                ("city", models.CharField(blank=True, max_length=50, verbose_name="City")),
                ("state_province", models.CharField(blank=True, max_length=50, verbose_name="State/Province")),
                ("postal_code", models.CharField(blank=True, max_length=20, verbose_name="Postal/Zip Code")),
                ("country", models.CharField(blank=True, max_length=50, verbose_name="Country")),
                ("profile_picture_url", models.URLField(blank=True, verbose_name="Profile Picture URL")),
                ("is_active", models.BooleanField(default=True, verbose_name="Active")),
                ("is_staff", models.BooleanField(default=False, verbose_name="Staff Status")),
                ("date_joined", models.DateTimeField(auto_now_add=True, verbose_name="Date Joined")),
                ("created_at", models.DateTimeField(auto_now_add=True, verbose_name="Created At")),
                ("updated_at", models.DateTimeField(auto_now=True, verbose_name="Updated At")),
                (
                    "groups",
                    models.ManyToManyField(
                        blank=True,
                        help_text="The groups this user belongs to. A user will get all permissions granted to each of their groups.",
                        related_name="user_set",
                        related_query_name="user",
                        to="auth.group",
                        verbose_name="groups",
                    ),
                ),
                (
                    "user_permissions",
                    models.ManyToManyField(
                        blank=True,
                        help_text="Specific permissions for this user.",
                        related_name="user_set",
                        related_query_name="user",
                        to="auth.permission",
                        verbose_name="user permissions",
                    ),
                ),
            ],
            options={"verbose_name": "User", "verbose_name_plural": "Users", "ordering": ["-created_at"]},
            managers=[("objects", auth.models.UserManager())],
        ),
        migrations.CreateModel(
            name="AdminProfile",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("job_title", models.CharField(blank=True, max_length=100, verbose_name="Job Title")),
                ("department", models.CharField(blank=True, max_length=100, verbose_name="Department")),
                ("is_active", models.BooleanField(default=True, verbose_name="Active Status")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "assigned_by",
                    models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="assigned_admins", to="nylo_auth.user", verbose_name="Assigned By"),
                ),
                (
                    "user",
                    models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name="admin_profile", to="nylo_auth.user"),
                ),
            ],
            options={"verbose_name": "Admin Profile", "verbose_name_plural": "Admin Profiles"},
        ),
        migrations.CreateModel(
            name="RolePermission",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("action", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to="nylo_auth.action")),
                ("resource", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to="nylo_auth.resource")),
                ("role", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="role_permissions", to="nylo_auth.permissionrole")),
            ],
            options={"verbose_name": "Role Permission", "verbose_name_plural": "Role Permissions"},
        ),
        migrations.CreateModel(
            name="AdminRoleAssignment",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("assigned_at", models.DateTimeField(auto_now_add=True)),
                (
                    "admin_profile",
                    models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="role_assignments", to="nylo_auth.adminprofile"),
                ),
                (
                    "assigned_by",
                    models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="role_assignments_made", to="nylo_auth.user"),
                ),
                ("role", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to="nylo_auth.permissionrole")),
            ],
            options={"verbose_name": "Admin Role Assignment", "verbose_name_plural": "Admin Role Assignments"},
        ),
        migrations.CreateModel(
            name="AdminPermission",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("granted_at", models.DateTimeField(auto_now_add=True)),
                ("action", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to="nylo_auth.action", verbose_name="Action")),
                (
                    "admin_profile",
                    models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="permissions", to="nylo_auth.adminprofile"),
                ),
                (
                    "granted_by",
                    models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="granted_permissions", to="nylo_auth.user"),
                ),
                ("resource", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to="nylo_auth.resource", verbose_name="Resource")),
            ],
            options={"verbose_name": "Admin Permission", "verbose_name_plural": "Admin Permissions"},
        ),
        migrations.AddConstraint(
            model_name="rolepermission",
            constraint=models.UniqueConstraint(fields=("role", "resource", "action"), name="unique_role_permission"),
        ),
        migrations.AddConstraint(
            model_name="adminroleassignment",
            constraint=models.UniqueConstraint(fields=("admin_profile", "role"), name="unique_admin_role_assignment"),
        ),
        migrations.AddConstraint(
            model_name="adminpermission",
            constraint=models.UniqueConstraint(fields=("admin_profile", "resource", "action"), name="unique_admin_permission"),
        ),
        migrations.AddIndex(
            model_name="adminpermission",
            index=models.Index(fields=["admin_profile", "resource", "action"], name="nylo_auth_a_admin_p_6e42d0_idx"),
        ),
    ]
