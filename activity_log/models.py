from django.db import models
from django.conf import settings
from django.utils.translation import gettext_lazy as _

# example
# created new admin account
# products
#   - created new
#   - updated 
#   - deleted
# orders
#   - update status
# coupons
#   - create
#   - update
#   - delete

class Category(models.TextChoices):
    PRODUCT = "PRODUCT", _("Product")
    CUSTOMER = "CUSTOMER", _("Customer")
    ORDER = "ORDER", _("Order")
    COUPON = "COUPON", _("Coupon")
    CHAT_SUPPORT = "CHAT_SUPPORT", _("Chat Support")
    PROFILE = "PROFILE", _("Profile")
    OTHER = "OTHER", _("Other")


class ActivityLog(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True, blank=True,
        on_delete=models.CASCADE,
        related_name="activity_logs",
    )
    action = models.CharField(max_length=255)
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.email} - {self.action} at {self.timestamp}" 