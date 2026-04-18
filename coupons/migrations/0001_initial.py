from decimal import Decimal
import uuid

import django.core.validators
from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="Coupon",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("code", models.CharField(max_length=50, unique=True)),
                ("coupon_type", models.CharField(choices=[("percentage", "Percentage"), ("fixed", "Fixed Amount")], max_length=20)),
                ("value", models.DecimalField(decimal_places=2, max_digits=12, validators=[django.core.validators.MinValueValidator(Decimal("0.01"))])),
                ("minimum_order_amount", models.DecimalField(decimal_places=2, default=Decimal("0.00"), max_digits=12)),
                ("maximum_discount_amount", models.DecimalField(blank=True, decimal_places=2, max_digits=12, null=True)),
                ("usage_limit", models.PositiveIntegerField(blank=True, null=True)),
                ("used_count", models.PositiveIntegerField(default=0)),
                ("valid_from", models.DateTimeField(blank=True, null=True)),
                ("valid_until", models.DateTimeField(blank=True, null=True)),
                ("is_active", models.BooleanField(default=True)),
                ("description", models.TextField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("created_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="coupons_coupon_created_records", to=settings.AUTH_USER_MODEL)),
                ("updated_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="coupons_coupon_updated_records", to=settings.AUTH_USER_MODEL)),
            ],
            options={
                "ordering": ["-created_at"],
            },
        ),
        migrations.AddIndex(
            model_name="coupon",
            index=models.Index(fields=["code"], name="coupons_cou_code_5106e8_idx"),
        ),
        migrations.AddIndex(
            model_name="coupon",
            index=models.Index(fields=["is_active"], name="coupons_cou_is_acti_e3c6b2_idx"),
        ),
        migrations.AddIndex(
            model_name="coupon",
            index=models.Index(fields=["valid_from", "valid_until"], name="coupons_cou_valid_f_d9861d_idx"),
        ),
    ]
