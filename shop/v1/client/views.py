from rest_framework import generics
from rest_framework.permissions import AllowAny

from app.utils.response import APIResponse
from shop.models import AboutPageContent, FAQ, LegalPageContent, StoreConfiguration
from shop.services import ensure_singleton_defaults
from shop.v1.client.serializers import (
    AboutPageContentSerializer,
    FAQSerializer,
    LegalPageContentSerializer,
    StoreConfigurationSerializer,
)


class SingletonContentAPIView(generics.GenericAPIView):
    permission_classes = [AllowAny]
    model = None

    def get_instance(self):
        ensure_singleton_defaults()
        return self.model.objects.order_by("-created_at").first()

    def get(self, request, *args, **kwargs):
        instance = self.get_instance()
        return APIResponse.success(
            data=self.get_serializer(instance).data,
            message=self.success_get_message,
        )


class StoreConfigurationAPIView(SingletonContentAPIView):
    serializer_class = StoreConfigurationSerializer
    model = StoreConfiguration
    success_get_message = "Store configuration fetched successfully."


class LegalPageContentAPIView(SingletonContentAPIView):
    serializer_class = LegalPageContentSerializer
    model = LegalPageContent
    success_get_message = "Legal page content fetched successfully."


class AboutPageContentAPIView(SingletonContentAPIView):
    serializer_class = AboutPageContentSerializer
    model = AboutPageContent
    success_get_message = "About page content fetched successfully."


class FAQListAPIView(generics.GenericAPIView):
    permission_classes = [AllowAny]
    serializer_class = FAQSerializer

    def get(self, request, *args, **kwargs):
        serializer = self.get_serializer(FAQ.objects.all(), many=True)
        return APIResponse.success(data=serializer.data, message="FAQs fetched successfully.")
