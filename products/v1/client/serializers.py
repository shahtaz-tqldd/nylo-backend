from rest_framework import serializers

from products.models import (
    Category,
    Collection,
    CollectionItem,
    Color,
    Product,
    ProductVariant,
    Size,
)


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ("id", "name", "slug")


class SizeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Size
        fields = ("id", "name", "order")


class ColorSerializer(serializers.ModelSerializer):
    class Meta:
        model = Color
        fields = ("id", "name", "color_code")


class VariantColorOutputSerializer(ColorSerializer):
    class Meta(ColorSerializer.Meta):
        fields = ("id", "name", "color_code")
        read_only_fields = fields


class VariantSizeOutputSerializer(SizeSerializer):
    class Meta(SizeSerializer.Meta):
        fields = ("id", "name", "order")
        read_only_fields = fields


class ProductVariantOutputSerializer(serializers.ModelSerializer):
    size = VariantSizeOutputSerializer(read_only=True)
    color = VariantColorOutputSerializer(read_only=True)

    class Meta:
        model = ProductVariant
        fields = (
            "id",
            "size",
            "color",
            "stock",
            "image_url",
            "sku",
            "slug",
            "is_active",
            "created_at",
            "updated_at",
        )
        read_only_fields = fields


class ProductCollectionItemSerializer(serializers.ModelSerializer):
    id = serializers.UUIDField(source="collection.id", read_only=True)
    title = serializers.CharField(source="collection.title", read_only=True)
    subtitle = serializers.CharField(source="collection.subtitle", read_only=True)
    type = serializers.CharField(source="collection.type", read_only=True)
    slug = serializers.CharField(source="collection.slug", read_only=True)
    image_url = serializers.URLField(source="collection.image_url", read_only=True)

    class Meta:
        model = CollectionItem
        fields = ("id", "title", "subtitle", "type", "slug", "image_url", "order")
        read_only_fields = fields


class ProductListSerializer(serializers.ModelSerializer):
    category = CategorySerializer(read_only=True)
    collections = serializers.SerializerMethodField()
    total_stock = serializers.SerializerMethodField()
    variants_count = serializers.SerializerMethodField()

    class Meta:
        model = Product
        fields = (
            "id",
            "title",
            "description",
            "brand",
            "image_url",
            "category",
            "gender",
            "price",
            "compare_price",
            "cost_price",
            "is_active",
            "sku",
            "slug",
            "collections",
            "total_stock",
            "variants_count",
            "created_at",
            "updated_at",
        )
        read_only_fields = fields

    def get_collections(self, obj):
        items = getattr(obj, "prefetched_collection_items", None)
        if items is None:
            items = obj.collectionitem_set.select_related("collection").all()
        return ProductCollectionItemSerializer(items, many=True).data

    def get_total_stock(self, obj):
        variants = getattr(obj, "prefetched_variants", None)
        if variants is None:
            variants = obj.variants.all()
        return sum(variant.stock for variant in variants)

    def get_variants_count(self, obj):
        variants = getattr(obj, "prefetched_variants", None)
        if variants is None:
            return obj.variants.count()
        return len(variants)


class PublicProductListSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source="category.name", read_only=True)
    in_stock = serializers.SerializerMethodField()
    variants_count = serializers.SerializerMethodField()

    class Meta:
        model = Product
        fields = (
            "title",
            "brand",
            "image_url",
            "category_name",
            "gender",
            "price",
            "compare_price",
            "slug",
            "in_stock",
            "variants_count",
        )
        read_only_fields = fields

    def get_in_stock(self, obj):
        variants = getattr(obj, "prefetched_variants", None)
        if variants is None:
            variants = obj.variants.filter(is_active=True)
        return any(variant.stock > 0 for variant in variants)

    def get_variants_count(self, obj):
        variants = getattr(obj, "prefetched_variants", None)
        if variants is None:
            return obj.variants.filter(is_active=True).count()
        return len([variant for variant in variants if variant.is_active])


class ProductDetailSerializer(ProductListSerializer):
    variants = serializers.SerializerMethodField()
    features = serializers.JSONField(read_only=True)
    specifications = serializers.JSONField(read_only=True)
    tags = serializers.JSONField(read_only=True)
    seo = serializers.SerializerMethodField()

    class Meta(ProductListSerializer.Meta):
        fields = ProductListSerializer.Meta.fields + (
            "features",
            "specifications",
            "tags",
            "seo",
            "variants",
        )

    def get_variants(self, obj):
        variants = getattr(obj, "prefetched_variants", None)
        if variants is None:
            variants = obj.variants.select_related("size", "color").all()
        return ProductVariantOutputSerializer(variants, many=True).data

    def get_seo(self, obj):
        return {
            "meta_title": obj.meta_title,
            "meta_description": obj.meta_description,
        }


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ("id", "name", "slug")


class SizeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Size
        fields = ("id", "name", "order")


class ColorSerializer(serializers.ModelSerializer):
    class Meta:
        model = Color
        fields = ("id", "name", "color_code")


class CollectionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Collection
        fields = (
            "id",
            "title",
            "subtitle",
            "type",
            "description",
            "image_url",
            "slug",
            "is_active",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "slug", "created_at", "updated_at")


class GenderOptionSerializer(serializers.Serializer):
    value = serializers.CharField()
    label = serializers.CharField()


class ProductSettingsSerializer(serializers.Serializer):
    categories = CategorySerializer(many=True)
    sizes = SizeSerializer(many=True)
    colors = ColorSerializer(many=True)
    collections = CollectionSerializer(many=True)
    genders = GenderOptionSerializer(many=True)
