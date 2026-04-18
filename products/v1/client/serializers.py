from rest_framework import serializers

from products.models import (
    Brand,
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


class BrandSerializer(serializers.ModelSerializer):
    class Meta:
        model = Brand
        fields = ("id", "name", "slug")


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


class PublicProductVariantOptionSerializer(serializers.ModelSerializer):
    size_name = serializers.CharField(source="size.name", read_only=True)
    color_name = serializers.CharField(source="color.name", read_only=True)
    color_code = serializers.CharField(source="color.color_code", read_only=True)
    image_url = serializers.URLField(read_only=True)
    added_to_cart = serializers.SerializerMethodField()
    quantity = serializers.SerializerMethodField()

    class Meta:
        model = ProductVariant
        fields = ("id", "size_name", "color_name", "color_code", "image_url", "added_to_cart", "quantity")
        read_only_fields = fields

    def get_added_to_cart(self, obj):
        cart_quantities = self.context.get("cart_quantities", {})
        return cart_quantities.get(obj.id, 0) > 0

    def get_quantity(self, obj):
        cart_quantities = self.context.get("cart_quantities", {})
        return cart_quantities.get(obj.id, 0)


class ProductDetailVariantOutputSerializer(ProductVariantOutputSerializer):
    added_to_cart = serializers.SerializerMethodField()
    cart_quantity = serializers.SerializerMethodField()

    class Meta(ProductVariantOutputSerializer.Meta):
        fields = ProductVariantOutputSerializer.Meta.fields + (
            "added_to_cart",
            "cart_quantity",
        )
        read_only_fields = fields

    def get_added_to_cart(self, obj):
        cart_quantities = self.context.get("cart_quantities", {})
        return cart_quantities.get(obj.id, 0) > 0

    def get_cart_quantity(self, obj):
        cart_quantities = self.context.get("cart_quantities", {})
        return cart_quantities.get(obj.id, 0)


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
    brand = BrandSerializer(read_only=True)
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
    brand = BrandSerializer(read_only=True)
    category_name = serializers.CharField(source="category.name", read_only=True)
    in_stock = serializers.SerializerMethodField()
    variants_count = serializers.SerializerMethodField()
    variant_options = serializers.SerializerMethodField()

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
            "variant_options",
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

    def get_variant_options(self, obj):
        variants = getattr(obj, "prefetched_variants", None)
        if variants is None:
            variants = obj.variants.select_related("size", "color").filter(is_active=True)
        else:
            variants = [variant for variant in variants if variant.is_active]
        cart_items = getattr(obj, "prefetched_user_cart_items", None)
        cart_quantities = (
            {item.variant_id: item.quantity for item in cart_items}
            if cart_items is not None
            else {}
        )
        return PublicProductVariantOptionSerializer(
            variants,
            many=True,
            context={**self.context, "cart_quantities": cart_quantities},
        ).data


class FeaturedProductSerializer(serializers.ModelSerializer):
    brand = BrandSerializer(read_only=True)
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
    added_to_favourite = serializers.BooleanField(read_only=True)

    class Meta(ProductListSerializer.Meta):
        fields = ProductListSerializer.Meta.fields + (
            "features",
            "specifications",
            "tags",
            "seo",
            "variants",
            "added_to_favourite",
        )

    def get_variants(self, obj):
        variants = getattr(obj, "prefetched_variants", None)
        if variants is None:
            variants = obj.variants.select_related("size", "color").all()

        cart_quantities = {}
        request = self.context.get("request")
        if request and request.user.is_authenticated:
            cart_quantities = {
                item["variant_id"]: item["quantity"]
                for item in UserCartItem.objects.filter(
                    user=request.user,
                    product=obj,
                    variant_id__in=[variant.id for variant in variants],
                ).values("variant_id", "quantity")
            }

        return ProductDetailVariantOutputSerializer(
            variants,
            many=True,
            context={**self.context, "cart_quantities": cart_quantities},
        ).data

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
    signature_items = SignatureProductItemSerializer(many=True, required=False, default=list)
    offer_items = OfferProductItemSerializer(many=True, required=False, default=list)
    best_selling_products = FeaturedProductSerializer(many=True, required=False, default=list)


class GenderOptionSerializer(serializers.Serializer):
    value = serializers.CharField()
    label = serializers.CharField()


class ProductSettingsSerializer(serializers.Serializer):
    brands = BrandSerializer(many=True)
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
    quantity = serializers.IntegerField(min_value=1, required=False, default=1)

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
    brand = BrandSerializer(read_only=True)
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
