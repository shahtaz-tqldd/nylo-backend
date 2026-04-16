from django.urls import path

from shop.v1.client.views import (
    AboutPageContentAPIView,
    FAQListAPIView,
    LegalPageContentAPIView,
    StoreConfigurationAPIView,
)


urlpatterns = [
    path("store-configuration/", StoreConfigurationAPIView.as_view(), name="store-configuration"),
    path("legal-content/", LegalPageContentAPIView.as_view(), name="legal-content"),
    path("about-page/", AboutPageContentAPIView.as_view(), name="about-page"),
    path("faqs/", FAQListAPIView.as_view(), name="faq-list"),
]
