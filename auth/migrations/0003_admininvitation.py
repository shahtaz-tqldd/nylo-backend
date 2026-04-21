import django.db.models.deletion
import uuid
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("nylo_auth", "0002_rename_nylo_auth_a_admin_p_6e42d0_idx_nylo_auth_a_admin_p_d7b148_idx"),
    ]

    operations = [
        migrations.CreateModel(
            name="AdminInvitation",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("email", models.EmailField(max_length=254, verbose_name="Email Address")),
                ("first_name", models.CharField(blank=True, max_length=32, verbose_name="First Name")),
                ("last_name", models.CharField(blank=True, max_length=32, verbose_name="Last Name")),
                ("job_title", models.CharField(blank=True, max_length=100, verbose_name="Job Title")),
                ("department", models.CharField(blank=True, max_length=100, verbose_name="Department")),
                ("direct_permissions", models.JSONField(blank=True, default=list, verbose_name="Direct Permissions")),
                ("expires_at", models.DateTimeField(verbose_name="Expires At")),
                ("accepted_at", models.DateTimeField(blank=True, null=True, verbose_name="Accepted At")),
                ("revoked_at", models.DateTimeField(blank=True, null=True, verbose_name="Revoked At")),
                ("created_at", models.DateTimeField(auto_now_add=True, verbose_name="Created At")),
                ("updated_at", models.DateTimeField(auto_now=True, verbose_name="Updated At")),
                (
                    "invited_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="admin_invitations_sent",
                        to=settings.AUTH_USER_MODEL,
                        verbose_name="Invited By",
                    ),
                ),
                (
                    "roles",
                    models.ManyToManyField(
                        blank=True,
                        related_name="admin_invitations",
                        to="nylo_auth.permissionrole",
                        verbose_name="Assigned Roles",
                    ),
                ),
            ],
            options={
                "verbose_name": "Admin Invitation",
                "verbose_name_plural": "Admin Invitations",
                "ordering": ["-created_at"],
                "indexes": [models.Index(fields=["email", "expires_at"], name="nylo_auth_a_email_a982d1_idx")],
            },
        ),
    ]
