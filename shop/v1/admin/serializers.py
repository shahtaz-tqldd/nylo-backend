from rest_framework import serializers

from shop.models import AboutPageContent, FAQ, LegalPageContent, StoreConfiguration


class StoreConfigurationSerializer(serializers.ModelSerializer):
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


class LegalPageContentSerializer(serializers.ModelSerializer):
    class Meta:
        model = LegalPageContent
        fields = ("id", "privacy_policy", "terms_and_conditions", "created_at", "updated_at")
        read_only_fields = ("id", "created_at", "updated_at")


class AboutPageContentSerializer(serializers.ModelSerializer):
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


class FAQSerializer(serializers.ModelSerializer):
    class Meta:
        model = FAQ
        fields = ("id", "question", "answer", "created_at", "updated_at")
        read_only_fields = ("id", "created_at", "updated_at")
