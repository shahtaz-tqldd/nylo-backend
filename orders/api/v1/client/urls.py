from django.urls import path

from orders.api.v1.client.views import CheckoutAPIView, UserOrderAPIView


urlpatterns = [
    path("checkout/", CheckoutAPIView.as_view(), name="checkout"),
    path("", UserOrderAPIView.as_view(), name="user-orders"),
]
