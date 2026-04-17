from rest_framework import generics, status
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated

from app.utils.response import APIResponse
from auth.permissions import IsAdmin
from shop.models import AboutPageContent, FAQ, LegalPageContent, StoreConfiguration
from shop.services import ensure_singleton_defaults
from shop.v1.admin.serializers import (
    AboutPageContentSerializer,
    FAQSerializer,
    LegalPageContentSerializer,
    StoreConfigurationSerializer,
)


class AdminSingletonContentAPIView(generics.GenericAPIView):
    permission_classes = [IsAuthenticated, IsAdmin]
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

    def patch(self, request, *args, **kwargs):
        instance = self.get_instance()
        serializer = self.get_serializer(instance, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save(updated_by=request.user)
        return APIResponse.success(
            data=self.get_serializer(instance).data,
            message=self.success_update_message,
        )


class StoreConfigurationAPIView(AdminSingletonContentAPIView):
    serializer_class = StoreConfigurationSerializer
    model = StoreConfiguration
    parser_classes = [MultiPartParser, FormParser, JSONParser]
    success_get_message = "Store configuration fetched successfully."
    success_update_message = "Store configuration updated successfully."


class LegalPageContentAPIView(AdminSingletonContentAPIView):
    serializer_class = LegalPageContentSerializer
    model = LegalPageContent
    success_get_message = "Legal page content fetched successfully."
    success_update_message = "Legal page content updated successfully."


class AboutPageContentAPIView(AdminSingletonContentAPIView):
    serializer_class = AboutPageContentSerializer
    model = AboutPageContent
    parser_classes = [MultiPartParser, FormParser, JSONParser]
    success_get_message = "About page content fetched successfully."
    success_update_message = "About page content updated successfully."


class FAQListCreateAPIView(generics.GenericAPIView):
    permission_classes = [IsAuthenticated, IsAdmin]
    serializer_class = FAQSerializer

    def get(self, request, *args, **kwargs):
        queryset = FAQ.objects.all()
        serializer = self.get_serializer(queryset, many=True)
        return APIResponse.success(data=serializer.data, message="FAQs fetched successfully.")

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        instance = serializer.save(created_by=request.user, updated_by=request.user)
        return APIResponse.success(
            data=self.get_serializer(instance).data,
            message="FAQ created successfully.",
            status=status.HTTP_201_CREATED,
        )


class FAQUpdateAPIView(generics.GenericAPIView):
    permission_classes = [IsAuthenticated, IsAdmin]
    serializer_class = FAQSerializer
    queryset = FAQ.objects.all()
    lookup_field = "id"

    def patch(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save(updated_by=request.user)
        return APIResponse.success(data=self.get_serializer(instance).data, message="FAQ updated successfully.")


class FAQDeleteAPIView(generics.DestroyAPIView):
    permission_classes = [IsAuthenticated, IsAdmin]
    queryset = FAQ.objects.all()
    lookup_field = "id"

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        instance.delete()
        return APIResponse.success(message="FAQ deleted successfully.")
