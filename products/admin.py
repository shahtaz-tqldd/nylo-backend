from django.contrib import admin

from .models import (
    Brand,
    Category,
    Collection,
    CollectionItem,
    Color,
    Product,
    ProductVariant,
    Size,
)


class ProductVariantInline(admin.TabularInline):
    model = ProductVariant
    extra = 0


class CollectionItemInline(admin.TabularInline):
    model = CollectionItem
    extra = 0


@admin.register(Collection)
class CollectionAdmin(admin.ModelAdmin):
    list_display = ("title", "type", "is_active", "slug", "created_at")
    list_filter = ("is_active", "type", "created_at")
    search_fields = ("title", "subtitle", "description", "slug")
    prepopulated_fields = {"slug": ("title",)}
    inlines = [CollectionItemInline]


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "created_at")
    search_fields = ("name", "slug")
    prepopulated_fields = {"slug": ("name",)}


@admin.register(Brand)
class BrandAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "created_at")
    search_fields = ("name", "slug")
    prepopulated_fields = {"slug": ("name",)}


@admin.register(Size)
class SizeAdmin(admin.ModelAdmin):
    list_display = ("name", "order", "created_at")
    ordering = ("order", "name")
    search_fields = ("name",)


@admin.register(Color)
class ColorAdmin(admin.ModelAdmin):
    list_display = ("name", "color_code", "created_at")
    search_fields = ("name", "color_code")


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "brand",
        "category",
        "gender",
        "price",
        "is_active",
        "slug",
        "created_at",
    )
    list_filter = ("is_active", "gender", "brand", "category", "created_at")
    search_fields = ("title", "brand__name", "sku", "slug")
    prepopulated_fields = {"slug": ("title",)}
    inlines = [ProductVariantInline, CollectionItemInline]


@admin.register(ProductVariant)
class ProductVariantAdmin(admin.ModelAdmin):
    list_display = (
        "product",
        "size",
        "color",
        "stock",
        "sku",
        "is_active",
        "slug",
        "created_at",
    )
    list_filter = ("is_active", "size", "color", "created_at")
    search_fields = ("product__title", "sku", "slug")


@admin.register(CollectionItem)
class CollectionItemAdmin(admin.ModelAdmin):
    list_display = ("collection", "product", "order", "created_at")
    list_filter = ("collection", "created_at")
    search_fields = ("collection__title", "product__title")
    ordering = ("collection", "order")
