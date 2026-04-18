from uuid import uuid4

from django.conf import settings
from django.utils.text import slugify
from rest_framework import serializers

from app.utils.cloudinary import delete_image, upload_image
from shop.models import AboutPageContent, FAQ, LegalPageContent, StoreConfiguration


class CloudinaryImageOrURLField(serializers.Field):
    def to_internal_value(self, data):
        if data in (None, ""):
            return None

        if hasattr(data, "read"):
            return data

        if isinstance(data, str):
            return data

        raise serializers.ValidationError("Expected an uploaded image file or image URL.")

    def to_representation(self, value):
        return value


class CloudinaryUploadSerializerMixin:
    image_folder_name = None

    def _resolve_image_value(self, image_value, current_url, asset_name, suffix):
        if image_value is None:
            if current_url:
                delete_image(image_url=current_url)
            return None

        if isinstance(image_value, str):
            return image_value

        if current_url:
            delete_image(image_url=current_url)

        upload = upload_image(
            image_value,
            folder=f"{settings.CLOUDINARY_FOLDER}/{self.image_folder_name}",
            public_id=self._build_public_id(asset_name=asset_name, suffix=suffix),
        )
        return upload["url"]

    def _build_public_id(self, asset_name, suffix):
        slug = slugify(str(asset_name or "store-configuration"))
        base_name = slug or f"store-configuration-{uuid4().hex[:8]}"
        return f"{base_name}-{suffix}"


class StoreConfigurationSerializer(CloudinaryUploadSerializerMixin, serializers.ModelSerializer):
    image_folder_name = "store-configuration"
    logo = CloudinaryImageOrURLField(required=False, allow_null=True)
    favicon = CloudinaryImageOrURLField(required=False, allow_null=True)

    class Meta:
        model = StoreConfiguration
        fields = (
            "id",
            "name",
            "tagline",
            "description",
            "logo",
            "favicon",
            "primary_color",
            "accent_color",
            "email",
            "phone",
            "address",
            "currency",
            "timezone",
            "language",
            "tax",
            "facebook",
            "whatsapp",
            "instagram",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "created_at", "updated_at")

    def update(self, instance, validated_data):
        logo = validated_data.pop("logo", serializers.empty)
        favicon = validated_data.pop("favicon", serializers.empty)

        for attr, value in validated_data.items():
            setattr(instance, attr, value)

        if logo is not serializers.empty:
            instance.logo = self._resolve_image_value(
                image_value=logo,
                current_url=instance.logo,
                asset_name=validated_data.get("name", instance.name),
                suffix="logo",
            )

        if favicon is not serializers.empty:
            instance.favicon = self._resolve_image_value(
                image_value=favicon,
                current_url=instance.favicon,
                asset_name=validated_data.get("name", instance.name),
                suffix="favicon",
            )

        instance.save()
        return instance


class LegalPageContentSerializer(serializers.ModelSerializer):
    class Meta:
        model = LegalPageContent
        fields = ("id", "privacy_policy", "terms_and_conditions", "created_at", "updated_at")
        read_only_fields = ("id", "created_at", "updated_at")


class AboutPageContentSerializer(CloudinaryUploadSerializerMixin, serializers.ModelSerializer):
    image_folder_name = "about-page"
    cover_image = CloudinaryImageOrURLField(required=False, allow_null=True)
    store_image = CloudinaryImageOrURLField(required=False, allow_null=True)
    detail_1_image = CloudinaryImageOrURLField(required=False, allow_null=True)
    detail_2_image = CloudinaryImageOrURLField(required=False, allow_null=True)
    detail_3_image = CloudinaryImageOrURLField(required=False, allow_null=True)

    class Meta:
        model = AboutPageContent
        fields = (
            "id",
            "cover_image",
            "left_text_content",
            "right_text_content",
            "store_image",
            "story_title",
            "story_content",
            "served_customer_count",
            "sold_count",
            "styles_count",
            "detail_section_title",
            "detail_1_image",
            "detail_1_title",
            "detail_2_image",
            "detail_2_title",
            "detail_3_image",
            "detail_3_title",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "created_at", "updated_at")

    def update(self, instance, validated_data):
        image_fields = {
            "cover_image": "cover-image",
            "store_image": "store-image",
            "detail_1_image": "detail-1-image",
            "detail_2_image": "detail-2-image",
            "detail_3_image": "detail-3-image",
        }
        incoming_images = {
            field_name: validated_data.pop(field_name, serializers.empty)
            for field_name in image_fields
        }

        for attr, value in validated_data.items():
            setattr(instance, attr, value)

        asset_name = validated_data.get("story_title", instance.story_title) or "about-page"
        for field_name, suffix in image_fields.items():
            image_value = incoming_images[field_name]
            if image_value is serializers.empty:
                continue
            setattr(
                instance,
                field_name,
                self._resolve_image_value(
                    image_value=image_value,
                    current_url=getattr(instance, field_name),
                    asset_name=asset_name,
                    suffix=suffix,
                ),
            )

        instance.save()
        return instance


class FAQSerializer(serializers.ModelSerializer):
    class Meta:
        model = FAQ
        fields = ("id", "question", "answer", "created_at", "updated_at")
        read_only_fields = ("id", "created_at", "updated_at")


class AdminSalesOverviewSerializer(serializers.Serializer):
    date_from = serializers.DateField(allow_null=True)
    date_to = serializers.DateField(allow_null=True)
    total_revenue = serializers.DecimalField(max_digits=12, decimal_places=2)
    total_taxes = serializers.DecimalField(max_digits=12, decimal_places=2)
    total_discounts = serializers.DecimalField(max_digits=12, decimal_places=2)
    shipping_fees = serializers.DecimalField(max_digits=12, decimal_places=2)
    total_profit = serializers.DecimalField(max_digits=12, decimal_places=2)


class AdminSalesSummarySerializer(serializers.Serializer):
    total_revenue = serializers.DecimalField(max_digits=12, decimal_places=2)
    revenue_this_month = serializers.DecimalField(max_digits=12, decimal_places=2)
    previous_month_revenue = serializers.DecimalField(max_digits=12, decimal_places=2)
    revenue_growth_percentage = serializers.DecimalField(max_digits=8, decimal_places=2)
    total_orders = serializers.IntegerField()
    orders_placed_this_month = serializers.IntegerField()
    average_order_value = serializers.DecimalField(max_digits=12, decimal_places=2)
    previous_month_average_order_value = serializers.DecimalField(max_digits=12, decimal_places=2)
    average_order_value_growth_percentage = serializers.DecimalField(max_digits=8, decimal_places=2)
    sales_overview = AdminSalesOverviewSerializer()


class AdminSalesOverTimePointSerializer(serializers.Serializer):
    date = serializers.DateField()
    sales = serializers.DecimalField(max_digits=12, decimal_places=2)
    orders = serializers.IntegerField()


class AdminSalesOverTimeSerializer(serializers.Serializer):
    date_from = serializers.DateField()
    date_to = serializers.DateField()
    points = AdminSalesOverTimePointSerializer(many=True)


class AdminSalesByChannelItemSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    title = serializers.CharField()
    slug = serializers.CharField()
    total_sales = serializers.DecimalField(max_digits=12, decimal_places=2)
    orders = serializers.IntegerField()
    items_sold = serializers.IntegerField()


class AdminSalesByChannelSerializer(serializers.Serializer):
    date_from = serializers.DateField(allow_null=True)
    date_to = serializers.DateField(allow_null=True)
    collections = AdminSalesByChannelItemSerializer(many=True)
    brands = AdminSalesByChannelItemSerializer(many=True)
    categories = AdminSalesByChannelItemSerializer(many=True)


class AdminTopSellingVariantSerializer(serializers.Serializer):
    id = serializers.UUIDField(allow_null=True)
    title = serializers.CharField(allow_blank=True)
    image_url = serializers.URLField(allow_null=True, allow_blank=True)
    total_sales = serializers.DecimalField(max_digits=12, decimal_places=2)
    orders_placed = serializers.IntegerField()


class AdminTopSellingProductSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    name = serializers.CharField()
    image_url = serializers.URLField(allow_null=True, allow_blank=True)
    total_sales = serializers.DecimalField(max_digits=12, decimal_places=2)
    orders_placed = serializers.IntegerField()
    top_selling_variant = AdminTopSellingVariantSerializer()


class AdminTopCustomerSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    name = serializers.CharField()
    email = serializers.EmailField()
    total_purchased = serializers.DecimalField(max_digits=12, decimal_places=2)


class AdminTopPerformersSerializer(serializers.Serializer):
    date_from = serializers.DateField(allow_null=True)
    date_to = serializers.DateField(allow_null=True)
    top_products = AdminTopSellingProductSerializer(many=True)
    top_customers = AdminTopCustomerSerializer(many=True)
