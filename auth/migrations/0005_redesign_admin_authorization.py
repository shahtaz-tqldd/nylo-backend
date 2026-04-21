import django.db.models.deletion
import uuid
from django.db import migrations, models


RESOURCE_TO_MODULE = {
    "PRODUCTS": "PRODUCT_MANAGEMENT",
    "CUSTOMERS": "CUSTOMER_MANAGEMENT",
    "ORDERS": "ORDER_MANAGEMENT",
    "COUPONS": "COUPON_MANAGEMENT",
    "SALES": "SALES",
    "MESSAGES": "CHAT_SUPPORT",
}

SUPPORTED_ACTIONS = {"VIEW", "CREATE", "UPDATE", "DELETE"}


def migrate_permissions_forward(apps, schema_editor):
    Permission = apps.get_model("nylo_auth", "Permission")
    AdminPermission = apps.get_model("nylo_auth", "AdminPermission")
    AdminInvitation = apps.get_model("nylo_auth", "AdminInvitation")

    for module, label in (
        ("PRODUCT_MANAGEMENT", "Product Management"),
        ("CUSTOMER_MANAGEMENT", "Customer Management"),
        ("ORDER_MANAGEMENT", "Order Management"),
        ("COUPON_MANAGEMENT", "Coupon Management"),
        ("SALES", "Sales"),
        ("CHAT_SUPPORT", "Chat Support"),
    ):
        Permission.objects.update_or_create(
            module=module,
            defaults={"description": f"Access to {label.lower()}."},
        )

    grouped_permissions = {}
    for permission in AdminPermission.objects.select_related("resource", "action").order_by("granted_at", "id"):
        module = RESOURCE_TO_MODULE.get(permission.resource.name)
        action = permission.action.name
        if not module or action not in SUPPORTED_ACTIONS:
            continue

        key = (permission.admin_profile_id, module)
        grouped_permissions.setdefault(
            key,
            {
                "anchor_id": permission.id,
                "granted_by_id": permission.granted_by_id,
                "granted_at": permission.granted_at,
                "actions": [],
            },
        )
        if action not in grouped_permissions[key]["actions"]:
            grouped_permissions[key]["actions"].append(action)

    kept_ids = set()
    for (admin_profile_id, module), payload in grouped_permissions.items():
        permission_obj = Permission.objects.get(module=module)
        row = AdminPermission.objects.get(id=payload["anchor_id"])
        row.permission_id = permission_obj.id
        row.actions = payload["actions"]
        row.granted_by_id = payload["granted_by_id"]
        row.save(update_fields=["permission", "actions", "granted_by"])
        kept_ids.add(row.id)

    AdminPermission.objects.exclude(id__in=kept_ids).delete()

    for invitation in AdminInvitation.objects.all():
        normalized = {}
        for item in invitation.direct_permissions or []:
            module = RESOURCE_TO_MODULE.get(item.get("resource"))
            action = item.get("action")
            if not module or action not in SUPPORTED_ACTIONS:
                continue
            normalized.setdefault(module, [])
            if action not in normalized[module]:
                normalized[module].append(action)

        invitation.direct_permissions = [
            {"module": module, "actions": actions}
            for module, actions in normalized.items()
        ]
        invitation.save(update_fields=["direct_permissions", "updated_at"])


def migrate_permissions_backward(apps, schema_editor):
    Permission = apps.get_model("nylo_auth", "Permission")
    AdminPermission = apps.get_model("nylo_auth", "AdminPermission")
    AdminInvitation = apps.get_model("nylo_auth", "AdminInvitation")
    Resource = apps.get_model("nylo_auth", "Resource")
    Action = apps.get_model("nylo_auth", "Action")

    module_to_resource = {value: key for key, value in RESOURCE_TO_MODULE.items()}

    existing_rows = list(
        AdminPermission.objects.exclude(permission_id__isnull=True).order_by("granted_at", "id")
    )
    for row in existing_rows:
        resource_name = module_to_resource.get(row.permission.module)
        if not resource_name:
            continue
        resource, _ = Resource.objects.get_or_create(name=resource_name)
        actions = [action for action in row.actions if action in SUPPORTED_ACTIONS]
        if not actions:
            continue

        first_action = Action.objects.get(name=actions[0])
        row.resource_id = resource.id
        row.action_id = first_action.id
        row.save(update_fields=["resource", "action"])

        for extra_action in actions[1:]:
            action_obj = Action.objects.get(name=extra_action)
            AdminPermission.objects.create(
                admin_profile_id=row.admin_profile_id,
                resource_id=resource.id,
                action_id=action_obj.id,
                granted_by_id=row.granted_by_id,
            )

    for invitation in AdminInvitation.objects.all():
        flattened = []
        for item in invitation.direct_permissions or []:
            resource_name = module_to_resource.get(item.get("module"))
            if not resource_name:
                continue
            for action in item.get("actions", []):
                if action in SUPPORTED_ACTIONS:
                    flattened.append({"resource": resource_name, "action": action})
        invitation.direct_permissions = flattened
        invitation.save(update_fields=["direct_permissions", "updated_at"])

    Permission.objects.all().delete()


class Migration(migrations.Migration):

    dependencies = [
        ("nylo_auth", "0004_rename_nylo_auth_a_email_a982d1_idx_nylo_auth_a_email_823f03_idx"),
    ]

    operations = [
        migrations.CreateModel(
            name="Permission",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                (
                    "module",
                    models.CharField(
                        choices=[
                            ("PRODUCT_MANAGEMENT", "Product Management"),
                            ("CUSTOMER_MANAGEMENT", "Customer Management"),
                            ("ORDER_MANAGEMENT", "Order Management"),
                            ("COUPON_MANAGEMENT", "Coupon Management"),
                            ("SALES", "Sales"),
                            ("CHAT_SUPPORT", "Chat Support"),
                        ],
                        max_length=50,
                        unique=True,
                        verbose_name="Module",
                    ),
                ),
                ("description", models.TextField(blank=True, verbose_name="Description")),
            ],
            options={"verbose_name": "Permission", "verbose_name_plural": "Permissions"},
        ),
        migrations.AddField(
            model_name="admininvitation",
            name="role",
            field=models.CharField(
                blank=True,
                choices=[
                    ("PRODUCT_MANAGER", "Product Manager"),
                    ("CUSTOMER_MANAGER", "Customer Manager"),
                    ("ORDER_MANAGER", "Order Manager"),
                    ("COUPON_MANAGER", "Coupon Manager"),
                    ("SALES_MANAGER", "Sales Manager"),
                    ("CHAT_SUPPORT_AGENT", "Chat Support Agent"),
                ],
                max_length=32,
                verbose_name="Admin Role",
            ),
        ),
        migrations.AddField(
            model_name="adminprofile",
            name="role",
            field=models.CharField(
                blank=True,
                choices=[
                    ("PRODUCT_MANAGER", "Product Manager"),
                    ("CUSTOMER_MANAGER", "Customer Manager"),
                    ("ORDER_MANAGER", "Order Manager"),
                    ("COUPON_MANAGER", "Coupon Manager"),
                    ("SALES_MANAGER", "Sales Manager"),
                    ("CHAT_SUPPORT_AGENT", "Chat Support Agent"),
                ],
                max_length=32,
                verbose_name="Admin Role",
            ),
        ),
        migrations.AddField(
            model_name="adminpermission",
            name="actions",
            field=models.JSONField(blank=True, default=list, verbose_name="Allowed Actions"),
        ),
        migrations.AddField(
            model_name="adminpermission",
            name="permission",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="admin_permissions",
                to="nylo_auth.permission",
                verbose_name="Permission",
            ),
        ),
        migrations.RunPython(migrate_permissions_forward, migrate_permissions_backward),
        migrations.RemoveIndex(
            model_name="adminpermission",
            name="nylo_auth_a_admin_p_d7b148_idx",
        ),
        migrations.RemoveConstraint(
            model_name="adminpermission",
            name="unique_admin_permission",
        ),
        migrations.RemoveField(
            model_name="admininvitation",
            name="roles",
        ),
        migrations.RemoveField(
            model_name="adminpermission",
            name="action",
        ),
        migrations.RemoveField(
            model_name="adminpermission",
            name="resource",
        ),
        migrations.AlterField(
            model_name="adminpermission",
            name="permission",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="admin_permissions",
                to="nylo_auth.permission",
                verbose_name="Permission",
            ),
        ),
        migrations.AddConstraint(
            model_name="adminpermission",
            constraint=models.UniqueConstraint(fields=("admin_profile", "permission"), name="unique_admin_permission"),
        ),
        migrations.AddIndex(
            model_name="adminpermission",
            index=models.Index(fields=["admin_profile", "permission"], name="nylo_auth_a_admin_p_9a1435_idx"),
        ),
        migrations.DeleteModel(
            name="AdminRoleAssignment",
        ),
        migrations.DeleteModel(
            name="RolePermission",
        ),
        migrations.DeleteModel(
            name="PermissionRole",
        ),
        migrations.DeleteModel(
            name="Action",
        ),
        migrations.DeleteModel(
            name="Resource",
        ),
    ]
