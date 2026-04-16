from django.urls import path

from shop.v1.admin import views


urlpatterns = [
    path("store-configuration/", views.StoreConfigurationAPIView.as_view(), name="store-configuration"),
    path("legal-content/", views.LegalPageContentAPIView.as_view(), name="legal-content"),
    path("about-page/", views.AboutPageContentAPIView.as_view(), name="about-page"),
    path("faqs/", views.FAQListCreateAPIView.as_view(), name="faq-list-create"),
    path("faqs/update/<uuid:id>/", views.FAQUpdateAPIView.as_view(), name="faq-update"),
    path("faqs/delete/<uuid:id>/", views.FAQDeleteAPIView.as_view(), name="faq-delete"),
]
