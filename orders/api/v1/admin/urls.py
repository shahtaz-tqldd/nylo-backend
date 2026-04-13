from django.urls import path

from orders.api.v1.admin import views


urlpatterns = [
    path("list/", views.AdminOrderListAPIView.as_view(), name="order-list"),
    path("<uuid:id>/", views.AdminOrderDetailsAPIView.as_view(), name="order-details"),
    path("update/<uuid:id>/", views.AdminOrderUpdateAPIView.as_view(), name="order-update"),
]
