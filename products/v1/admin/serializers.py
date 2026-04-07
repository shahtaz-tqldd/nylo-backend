from django.db import transaction
from django.conf import settings
from django.utils.text import slugify
from rest_framework import serializers

from app.utils.cloudinary import delete_image, upload_image
from products.models import (
    Category,
    Collection,
    CollectionItem,
    Color,
    GenderChoice,
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


class CollectionSerializer(serializers.ModelSerializer):
    image = serializers.FileField(write_only=True, required=False, allow_null=True)

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
            "image",
        )
        read_only_fields = ("id", "image_url", "slug", "created_at", "updated_at")

    def create(self, validated_data):
        image_file = validated_data.pop("image", None)
        if image_file:
            validated_data["image_url"] = self._upload_collection_image(
                image_file=image_file,
                title=validated_data.get("title"),
            )
        return Collection.objects.create(**validated_data)

    def update(self, instance, validated_data):
        image_file = validated_data.pop("image", None)

        for attr, value in validated_data.items():
            setattr(instance, attr, value)

        if image_file:
            instance.image_url = self._upload_collection_image(
                image_file=image_file,
                title=validated_data.get("title", instance.title),
                current_url=instance.image_url,
            )

        instance.save()
        return instance

    def _upload_collection_image(self, image_file, title, current_url=None):
        if current_url:
            delete_image(image_url=current_url)

        upload = upload_image(
            image_file,
            folder=f"{settings.CLOUDINARY_FOLDER}/collections",
            public_id=self._build_slug(title, "collection"),
        )
        return upload["url"]

    def _build_slug(self, title, fallback):
        slug = slugify(str(title or ""))
        return slug or fallback


class GenderOptionSerializer(serializers.Serializer):
    value = serializers.CharField()
    label = serializers.CharField()


class ProductSettingsSerializer(serializers.Serializer):
    categories = CategorySerializer(many=True)
    sizes = SizeSerializer(many=True)
    colors = ColorSerializer(many=True)
    collections = CollectionSerializer(many=True)
    genders = GenderOptionSerializer(many=True)


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


class ProductDetailsInputSerializer(serializers.Serializer):
    title = serializers.CharField(max_length=256)
    sku = serializers.CharField(max_length=100, required=False, allow_blank=True, allow_null=True)
    brand = serializers.CharField(max_length=100, required=False, allow_blank=True, allow_null=True)
    category_id = serializers.UUIDField(required=False)
    category = serializers.UUIDField(required=False)
    collection_ids = serializers.ListField(
        child=serializers.UUIDField(),
        required=False,
        allow_empty=True,
    )
    collection = serializers.ListField(
        child=serializers.UUIDField(),
        required=False,
        allow_empty=True,
    )
    collections = serializers.ListField(
        child=serializers.UUIDField(),
        required=False,
        allow_empty=True,
    )
    gender = serializers.ChoiceField(choices=GenderChoice.choices)
    description = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    pricing = serializers.DictField(required=False)
    features = serializers.ListField(required=False, allow_empty=True)
    specifications = serializers.JSONField(required=False)
    tags = serializers.ListField(
        child=serializers.CharField(),
        required=False,
        allow_empty=True,
    )
    seo = serializers.DictField(required=False)
    image = serializers.JSONField(required=False, allow_null=True)

    def validate(self, attrs):
        category_id = attrs.get("category_id") or attrs.get("category")
        if not category_id:
            raise serializers.ValidationError({"category_id": "This field is required."})
        attrs["category_id"] = category_id

        collection_ids = (
            attrs.get("collection_ids")
            or attrs.get("collections")
            or attrs.get("collection")
            or []
        )
        attrs["collection_ids"] = collection_ids
        return attrs


class VariantConfigurationInputSerializer(serializers.Serializer):
    size_ids = serializers.ListField(
        child=serializers.UUIDField(),
        required=False,
        allow_empty=True,
    )
    color_ids = serializers.ListField(
        child=serializers.UUIDField(),
        required=False,
        allow_empty=True,
    )
    sizes = serializers.ListField(required=False, allow_empty=True)
    colors = serializers.ListField(required=False, allow_empty=True)


class ProductVariantInputSerializer(serializers.Serializer):
    combination_key = serializers.CharField(required=False, allow_blank=True)
    size_id = serializers.UUIDField(required=False, allow_null=True)
    color_id = serializers.UUIDField(required=False, allow_null=True)
    size = serializers.UUIDField(required=False, allow_null=True)
    color = serializers.UUIDField(required=False, allow_null=True)
    sku = serializers.CharField(max_length=100, required=False, allow_blank=True, allow_null=True)
    name = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    stock = serializers.IntegerField(required=False, min_value=0, default=0)
    image = serializers.JSONField(required=False, allow_null=True)
    is_active = serializers.BooleanField(required=False, default=True)

    def validate(self, attrs):
        attrs["size_id"] = attrs.get("size_id", attrs.get("size"))
        attrs["color_id"] = attrs.get("color_id", attrs.get("color"))
        return attrs


class ProductUpsertSerializer(serializers.Serializer):
    product_details = ProductDetailsInputSerializer()
    variant_configuration = VariantConfigurationInputSerializer(required=False)
    variants = ProductVariantInputSerializer(many=True, required=False)

    def validate(self, attrs):
        product_details = attrs.get("product_details")
        if product_details:
            category = Category.objects.filter(id=product_details["category_id"]).first()
            if not category:
                raise serializers.ValidationError(
                    {"product_details": {"category_id": "Selected category does not exist."}}
                )
            product_details["category_obj"] = category

            collection_ids = product_details.get("collection_ids", [])
            collections = list(Collection.objects.filter(id__in=collection_ids))
            if len(collections) != len(set(collection_ids)):
                raise serializers.ValidationError(
                    {"product_details": {"collection_ids": "One or more collections do not exist."}}
                )
            product_details["collection_objs"] = collections

        variants = attrs.get("variants", [])
        size_ids = {item["size_id"] for item in variants if item.get("size_id")}
        color_ids = {item["color_id"] for item in variants if item.get("color_id")}

        configured_sizes = set(attrs.get("variant_configuration", {}).get("size_ids", []))
        configured_colors = set(attrs.get("variant_configuration", {}).get("color_ids", []))

        if configured_sizes and not size_ids.issubset(configured_sizes):
            raise serializers.ValidationError(
                {"variants": "Every variant size_id must exist in variant_configuration.size_ids."}
            )
        if configured_colors and not color_ids.issubset(configured_colors):
            raise serializers.ValidationError(
                {"variants": "Every variant color_id must exist in variant_configuration.color_ids."}
            )

        size_map = {size.id: size for size in Size.objects.filter(id__in=size_ids | configured_sizes)}
        color_map = {color.id: color for color in Color.objects.filter(id__in=color_ids | configured_colors)}

        if len(size_map) != len(size_ids | configured_sizes):
            raise serializers.ValidationError({"variants": "One or more size_id values do not exist."})
        if len(color_map) != len(color_ids | configured_colors):
            raise serializers.ValidationError({"variants": "One or more color_id values do not exist."})

        seen = set()
        for item in variants:
            pair = (item.get("size_id"), item.get("color_id"))
            if pair in seen:
                raise serializers.ValidationError(
                    {"variants": "Duplicate variants are not allowed for the same size and color."}
                )
            seen.add(pair)
            item["size_obj"] = size_map.get(item.get("size_id"))
            item["color_obj"] = color_map.get(item.get("color_id"))

        return attrs

    @transaction.atomic
    def create(self, validated_data):
        request = self.context["request"]
        product_details = validated_data["product_details"]
        product_image_url = self._upload_product_image(product_details, None)
        product = Product.objects.create(
            title=product_details["title"],
            description=product_details.get("description"),
            brand=product_details.get("brand"),
            image_url=product_image_url,
            category=product_details["category_obj"],
            gender=product_details["gender"],
            price=(product_details.get("pricing") or {}).get("price") or 0,
            compare_price=(product_details.get("pricing") or {}).get("compare_price"),
            cost_price=(product_details.get("pricing") or {}).get("cost_per_item"),
            features=product_details.get("features") or [],
            specifications=product_details.get("specifications") or {},
            tags=product_details.get("tags") or [],
            meta_title=(product_details.get("seo") or {}).get("meta_title"),
            meta_description=(product_details.get("seo") or {}).get("meta_description"),
            sku=product_details.get("sku"),
            created_by=request.user,
            updated_by=request.user,
        )

        self._sync_collections(product, product_details.get("collection_objs", []), request.user)
        self._sync_variants(product, validated_data.get("variants", []), request.user)
        return product

    @transaction.atomic
    def update(self, instance, validated_data):
        request = self.context["request"]
        product_details = validated_data.get("product_details", {})
        pricing = product_details.get("pricing") or {}
        seo = product_details.get("seo") or {}

        instance.title = product_details.get("title", instance.title)
        instance.description = product_details.get("description", instance.description)
        instance.brand = product_details.get("brand", instance.brand)
        if product_details:
            instance.image_url = self._upload_product_image(product_details, instance.image_url)
        instance.category = product_details.get("category_obj", instance.category)
        instance.gender = product_details.get("gender", instance.gender)
        instance.price = pricing.get("price", instance.price)
        instance.compare_price = pricing.get("compare_price", instance.compare_price)
        instance.cost_price = pricing.get("cost_per_item", instance.cost_price)
        instance.features = product_details.get("features", instance.features)
        instance.specifications = product_details.get("specifications", instance.specifications)
        instance.tags = product_details.get("tags", instance.tags)
        instance.meta_title = seo.get("meta_title", instance.meta_title)
        instance.meta_description = seo.get("meta_description", instance.meta_description)
        instance.sku = product_details.get("sku", instance.sku)
        instance.updated_by = request.user
        instance.save()

        if "collection_objs" in product_details:
            self._sync_collections(instance, product_details["collection_objs"], request.user)
        if "variants" in validated_data:
            self._sync_variants(instance, validated_data.get("variants", []), request.user)
        return instance

    def _sync_collections(self, product, collections, user):
        product.collectionitem_set.all().delete()
        CollectionItem.objects.bulk_create(
            [
                CollectionItem(
                    collection=collection,
                    product=product,
                    order=index,
                    created_by=user,
                    updated_by=user,
                )
                for index, collection in enumerate(collections, start=1)
            ]
        )

    def _sync_variants(self, product, variants, user):
        for existing_variant in product.variants.exclude(image_url__isnull=True).exclude(image_url=""):
            delete_image(image_url=existing_variant.image_url)
        product.variants.all().delete()
        for item in variants:
            image_url = self._upload_variant_image(item)
            ProductVariant.objects.create(
                product=product,
                size=item.get("size_obj"),
                color=item.get("color_obj"),
                stock=item.get("stock", 0),
                image_url=image_url,
                sku=item.get("sku"),
                is_active=item.get("is_active", True),
                created_by=user,
                updated_by=user,
            )

    def _upload_product_image(self, product_details, current_url):
        request = self.context["request"]
        file_obj = request.FILES.get("product_image")
        if not file_obj:
            return current_url

        if current_url:
            delete_image(image_url=current_url)

        product_slug = self._build_slug(product_details.get("title"), product_details.get("sku"), "product")
        upload = upload_image(
            file_obj,
            folder=f"{settings.CLOUDINARY_FOLDER}/products",
            public_id=product_slug,
        )
        return upload["url"]

    def _upload_variant_image(self, variant_data):
        request = self.context["request"]
        combination_key = variant_data.get("combination_key")
        if not combination_key:
            return None

        file_obj = request.FILES.get(f"variant_image.{combination_key}")
        if not file_obj:
            return None

        product_title = (
            self.validated_data.get("product_details", {}).get("title")
            or self.initial_data.get("product_details", {}).get("title")
            or "product"
        )
        variant_slug = self._build_slug(product_title, combination_key, "variant")
        upload = upload_image(
            file_obj,
            folder=f"{settings.CLOUDINARY_FOLDER}/variants",
            public_id=variant_slug,
        )
        return upload["url"]

    def _build_slug(self, first_part, second_part, fallback):
        parts = [slugify(str(part)) for part in [first_part, second_part] if part]
        if not parts:
            return fallback
        return "-".join(parts)
