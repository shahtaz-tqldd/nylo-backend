from uuid import uuid4
from decimal import Decimal

from django.db import models
from django.conf import settings


class OrderStatusChoice(models.TextChoices):
    PENDING = "pending", "Pending"
    APPROVED = "approved", "Approved"
    REJECTED = "rejected", "Rejected"
    SHIPPED = "shipped", "Shipped"
    DELIVERED = "delivered", "Delivered"
    CANCELLED = "cancelled", "Cancelled"
    REFUND_REQUESTED = "refund_requested", "Refund Requested"
    REFUND_ACCEPTED = "refund_accepted", "Refund Accepted"
    REFUND_REJECTED = "refund_rejected", "Refund Rejected"
    REFUNDED = "refunded", "Refunded"


class Order(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid4, editable=False)
    customer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="orders",
    )
    status = models.CharField(
        max_length=30,
        choices=OrderStatusChoice.choices,
        default=OrderStatusChoice.PENDING,
    )

    subtotal = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    discount_amount = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    shipping_charge = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    tax_amount = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    total_amount = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))

    notes = models.TextField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["status"]),
            models.Index(fields=["created_at"]),
        ]

    def __str__(self):
        return f"Order {self.id}"

    def calculate_totals(self, save=True):
        subtotal = sum(
            (item.unit_price * item.quantity for item in self.items.all()),
            Decimal("0.00"),
        )
        self.subtotal = subtotal
        self.total_amount = (
            self.subtotal
            - self.discount_amount
            + self.shipping_charge
            + self.tax_amount
        )

        if save:
            self.save(update_fields=["subtotal", "total_amount", "updated_at"])


class OrderItem(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid4, editable=False)

    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        related_name="items",
    )
    product = models.ForeignKey(
        "products.Product",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="order_items",
    )
    variant = models.ForeignKey(
        "products.ProductVariant",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="order_items",
    )

    quantity = models.PositiveIntegerField(default=1)
    unit_price = models.DecimalField(max_digits=12, decimal_places=2)
    total_price = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["order"]),
            models.Index(fields=["product"]),
            models.Index(fields=["variant"]),
        ]

    def __str__(self):
        product_title = self.product.title if self.product else "Deleted Product"
        return f"{product_title} x {self.quantity}"

    def save(self, *args, **kwargs):
        self.total_price = (self.unit_price or Decimal("0.00")) * self.quantity
        super().save(*args, **kwargs)