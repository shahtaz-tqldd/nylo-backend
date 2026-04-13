from rest_framework import serializers

from products.models import (
    Category,
    Collection,
    CollectionItem,
    Color,
    OfferProductItem,
    Product,
    ProductVariant,
    SignatureProductItem,
    Size,
    UserCartItem,
    UserFavouriteItem,
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


class FeaturedProductSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source="category.name", read_only=True)
    in_stock = serializers.SerializerMethodField()
    variants_count = serializers.SerializerMethodField()

    class Meta:
        model = Product
        fields = (
            "id",
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


class PublicCollectionListSerializer(serializers.ModelSerializer):
    total_products = serializers.IntegerField(read_only=True)

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
            "total_products",
        )
        read_only_fields = fields


class SignatureProductItemSerializer(serializers.ModelSerializer):
    product = FeaturedProductSerializer(read_only=True)

    class Meta:
        model = SignatureProductItem
        fields = ("id", "product", "created_at", "updated_at")
        read_only_fields = fields


class OfferProductItemSerializer(serializers.ModelSerializer):
    product = FeaturedProductSerializer(read_only=True)

    class Meta:
        model = OfferProductItem
        fields = ("id", "product", "offer_ends_at", "created_at", "updated_at")
        read_only_fields = fields


class FeaturedProductsSerializer(serializers.Serializer):
    signature_items = SignatureProductItemSerializer(many=True)
    offer_items = OfferProductItemSerializer(many=True)
    best_selling_products = FeaturedProductSerializer(many=True)


class GenderOptionSerializer(serializers.Serializer):
    value = serializers.CharField()
    label = serializers.CharField()


class ProductSettingsSerializer(serializers.Serializer):
    categories = CategorySerializer(many=True)
    sizes = SizeSerializer(many=True)
    colors = ColorSerializer(many=True)
    collections = CollectionSerializer(many=True)
    genders = GenderOptionSerializer(many=True)


class CartFavouriteActionSerializer(serializers.Serializer):
    ACTION_ADD = "add"
    ACTION_REMOVE = "remove"
    ACTION_CHOICES = (
        (ACTION_ADD, "Add"),
        (ACTION_REMOVE, "Remove"),
    )

    action = serializers.ChoiceField(choices=ACTION_CHOICES)


class AddToCartSerializer(CartFavouriteActionSerializer):
    product_id = serializers.UUIDField()
    variant_id = serializers.UUIDField()

    def validate(self, attrs):
        product = Product.objects.filter(id=attrs["product_id"], is_active=True).first()
        if product is None:
            raise serializers.ValidationError({"product_id": "Active product not found."})

        variant = (
            ProductVariant.objects.select_related("product", "size", "color")
            .filter(
                id=attrs["variant_id"],
                product_id=product.id,
                is_active=True,
            )
            .first()
        )
        if variant is None:
            raise serializers.ValidationError({"variant_id": "Active variant not found for this product."})

        attrs["product"] = product
        attrs["variant"] = variant
        return attrs


class AddToFavouriteSerializer(CartFavouriteActionSerializer):
    product_id = serializers.UUIDField()

    def validate(self, attrs):
        product = Product.objects.filter(id=attrs["product_id"], is_active=True).first()
        if product is None:
            raise serializers.ValidationError({"product_id": "Active product not found."})

        attrs["product"] = product
        return attrs


class CartProductSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source="category.name", read_only=True)

    class Meta:
        model = Product
        fields = (
            "id",
            "title",
            "brand",
            "image_url",
            "category_name",
            "gender",
            "price",
            "compare_price",
            "slug",
        )
        read_only_fields = fields


class UserCartItemSerializer(serializers.ModelSerializer):
    product = CartProductSerializer(read_only=True)
    variant = ProductVariantOutputSerializer(read_only=True)
    unit_price = serializers.DecimalField(source="product.price", max_digits=10, decimal_places=2, read_only=True)
    total_price = serializers.SerializerMethodField()

    class Meta:
        model = UserCartItem
        fields = (
            "id",
            "product",
            "variant",
            "quantity",
            "unit_price",
            "total_price",
            "created_at",
            "updated_at",
        )
        read_only_fields = fields

    def get_total_price(self, obj):
        return obj.product.price * obj.quantity


class UserFavouriteItemSerializer(serializers.ModelSerializer):
    product = CartProductSerializer(read_only=True)

    class Meta:
        model = UserFavouriteItem
        fields = (
            "id",
            "product",
            "created_at",
            "updated_at",
        )
        read_only_fields = fields
