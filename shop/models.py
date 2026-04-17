from django.core.validators import MinValueValidator, RegexValidator
from django.db import models

from app.base.models import BaseModel


hex_color_validator = RegexValidator(
    regex=r"^#(?:[0-9a-fA-F]{3}){1,2}$",
    message="Enter a valid hex color code.",
)


class StoreConfiguration(BaseModel):
    name = models.CharField(max_length=120)
    tagline = models.CharField(max_length=255, null=True, blank=True)
    description = models.TextField(null=True, blank=True)
    logo = models.URLField(null=True, blank=True)
    favicon = models.URLField(null=True, blank=True)
    primary_color = models.CharField(
        max_length=7,
        validators=[hex_color_validator],
        null=True,
        blank=True,
    )
    accent_color = models.CharField(
        max_length=7,
        validators=[hex_color_validator],
        null=True,
        blank=True,
    )
    email = models.EmailField(null=True, blank=True)
    phone = models.CharField(max_length=30, null=True, blank=True)
    address = models.TextField(null=True, blank=True)
    currency = models.CharField(max_length=10, default="USD")
    timezone = models.CharField(max_length=64, default="UTC")
    language = models.CharField(max_length=20, default="en")
    tax = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0,
        validators=[MinValueValidator(0)],
    )
    facebook = models.URLField(null=True, blank=True)
    whatsapp = models.CharField(max_length=255, null=True, blank=True)
    instagram = models.URLField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Store Configuration"
        verbose_name_plural = "Store Configuration"

    def __str__(self):
        return self.name


class LegalPageContent(BaseModel):
    privacy_policy = models.TextField(default="Default privacy policy content.")
    terms_and_conditions = models.TextField(default="Default terms and conditions content.")

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Legal Page Content"
        verbose_name_plural = "Legal Page Content"

    def __str__(self):
        return "Legal Page Content"


class AboutPageContent(BaseModel):
    cover_image = models.URLField(null=True, blank=True)
    left_text_content = models.TextField(blank=True, default="")
    right_text_content = models.TextField(blank=True, default="")
    store_image = models.URLField(null=True, blank=True)
    story_title = models.CharField(max_length=255, blank=True, default="")
    story_content = models.TextField(blank=True, default="")
    served_customer_count = models.PositiveIntegerField(default=0)
    sold_count = models.PositiveIntegerField(default=0)
    styles_count = models.PositiveIntegerField(default=0)
    detail_section_title = models.CharField(max_length=255, blank=True, default="")
    detail_1_image = models.URLField(null=True, blank=True)
    detail_1_title = models.CharField(max_length=255, blank=True, default="")
    detail_2_image = models.URLField(null=True, blank=True)
    detail_2_title = models.CharField(max_length=255, blank=True, default="")
    detail_3_image = models.URLField(null=True, blank=True)
    detail_3_title = models.CharField(max_length=255, blank=True, default="")

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "About Page Content"
        verbose_name_plural = "About Page Content"

    def __str__(self):
        return "About Page Content"


class FAQ(BaseModel):
    question = models.CharField(max_length=500)
    answer = models.TextField()

    class Meta:
        ordering = ["created_at"]
        verbose_name = "FAQ"
        verbose_name_plural = "FAQs"

    def __str__(self):
        return self.question

