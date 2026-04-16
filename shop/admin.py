from django.contrib import admin

from shop.models import AboutPageContent, FAQ, LegalPageContent, StoreConfiguration


@admin.register(StoreConfiguration)
class StoreConfigurationAdmin(admin.ModelAdmin):
    list_display = ("name", "email", "phone", "currency", "timezone", "updated_at")
    search_fields = ("name", "tagline", "email", "phone")


@admin.register(LegalPageContent)
class LegalPageContentAdmin(admin.ModelAdmin):
    list_display = ("id", "updated_at")


@admin.register(AboutPageContent)
class AboutPageContentAdmin(admin.ModelAdmin):
    list_display = ("id", "story_title", "served_customer_count", "sold_count", "styles_count", "updated_at")


@admin.register(FAQ)
class FAQAdmin(admin.ModelAdmin):
    list_display = ("question", "updated_at")
    search_fields = ("question", "answer")
