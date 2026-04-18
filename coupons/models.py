from decimal import Decimal

from django.core.validators import MinValueValidator
from django.db import models
from django.utils import timezone

from app.base.models import BaseModel


class CouponType(models.TextChoices):
    PERCENTAGE = "percentage", "Percentage"
    FIXED = "fixed", "Fixed Amount"


class Coupon(BaseModel):
    code = models.CharField(max_length=50, unique=True)
    coupon_type = models.CharField(max_length=20, choices=CouponType.choices)
    value = models.DecimalField(max_digits=12, decimal_places=2, validators=[MinValueValidator(Decimal("0.01"))])
    minimum_order_amount = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    maximum_discount_amount = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    usage_limit = models.PositiveIntegerField(null=True, blank=True)
    used_count = models.PositiveIntegerField(default=0)
    valid_from = models.DateTimeField(null=True, blank=True)
    valid_until = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    description = models.TextField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["code"]),
            models.Index(fields=["is_active"]),
            models.Index(fields=["valid_from", "valid_until"]),
        ]

    def __str__(self):
        return self.code

    @property
    def is_currently_valid(self):
        now = timezone.now()
        if not self.is_active:
            return False
        if self.valid_from and self.valid_from > now:
            return False
        if self.valid_until and self.valid_until < now:
            return False
        if self.usage_limit is not None and self.used_count >= self.usage_limit:
            return False
        return True

