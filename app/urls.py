from django.contrib import admin
from django.urls import path, include
from django.conf.urls.static import static
from django.conf import settings
from orders.api.v1.client.views import StripeWebhookAPIView

v1_urls = [
    path("auth/", include("auth.urls")),
    path("products/", include("products.v1.client.urls")),
    path("orders/", include("orders.api.v1.client.urls")),
    path("admin/products/", include("products.v1.admin.urls")),
    path("admin/orders/", include("orders.api.v1.admin.urls")),
]

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/v1/", include(v1_urls)),
    path("payments/stripe/webhook/", StripeWebhookAPIView.as_view(), name="stripe-webhook"),
]


if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
