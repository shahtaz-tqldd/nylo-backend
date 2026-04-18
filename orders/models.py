import secrets
import string
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


class PaymentStatusChoice(models.TextChoices):
    UNPAID = "unpaid", "Unpaid"
    REQUIRES_ACTION = "requires_action", "Requires Action"
    PAID = "paid", "Paid"
    FAILED = "failed", "Failed"
    REFUNDED = "refunded", "Refunded"


TRACKING_NUMBER_ALPHABET = string.ascii_uppercase + string.digits


def generate_tracking_number(length=8):
    return "".join(secrets.choice(TRACKING_NUMBER_ALPHABET) for _ in range(length))


class Order(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid4, editable=False)
    customer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="orders",
    )
    coupon = models.ForeignKey(
        "coupons.Coupon",
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
    payment_status = models.CharField(
        max_length=20,
        choices=PaymentStatusChoice.choices,
        default=PaymentStatusChoice.UNPAID,
    )
    tracking_number = models.CharField(max_length=20, null=True, blank=True, unique=True)
    currency = models.CharField(max_length=10, default="usd")

    subtotal = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    discount_amount = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    shipping_charge = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    tax_amount = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    total_amount = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))

    coupon_code = models.CharField(max_length=100, null=True, blank=True)
    shipping_address = models.JSONField(default=dict, blank=True)
    stripe_checkout_session_id = models.CharField(max_length=255, null=True, blank=True, unique=True)
    stripe_payment_intent_id = models.CharField(max_length=255, null=True, blank=True)
    checkout_expires_at = models.DateTimeField(null=True, blank=True)

    notes = models.TextField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["status"]),
            models.Index(fields=["payment_status"]),
            models.Index(fields=["created_at"]),
        ]

    def __str__(self):
        return f"Order {self.tracking_number or self.id}"

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

    def save(self, *args, **kwargs):
        if not self.tracking_number:
            tracking_number = generate_tracking_number()
            while Order.objects.filter(tracking_number=tracking_number).exists():
                tracking_number = generate_tracking_number()
            self.tracking_number = tracking_number
        super().save(*args, **kwargs)


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
    source_cart_item_id = models.UUIDField(null=True, blank=True)
    product_title = models.CharField(max_length=256, default="")
    variant_description = models.CharField(max_length=255, null=True, blank=True)
    sku = models.CharField(max_length=100, null=True, blank=True)
    unit_price = models.DecimalField(max_digits=12, decimal_places=2)
    total_price = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["order"]),
            models.Index(fields=["source_cart_item_id"]),
            models.Index(fields=["product"]),
            models.Index(fields=["variant"]),
        ]

    def __str__(self):
        product_title = self.product_title or (self.product.title if self.product else "Deleted Product")
        return f"{product_title} x {self.quantity}"

    def save(self, *args, **kwargs):
        self.total_price = (self.unit_price or Decimal("0.00")) * self.quantity
        super().save(*args, **kwargs)


class StripeWebhookEvent(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid4, editable=False)
    stripe_event_id = models.CharField(max_length=255, unique=True)
    event_type = models.CharField(max_length=100)
    payload = models.JSONField(default=dict, blank=True)
    processed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-processed_at"]
        indexes = [
            models.Index(fields=["stripe_event_id"]),
            models.Index(fields=["event_type"]),
        ]

    def __str__(self):
        return f"{self.event_type} ({self.stripe_event_id})"
