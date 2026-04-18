from django.urls import path

from coupons.api.v1.admin import views


urlpatterns = [
    path("create/", views.AdminCouponCreateAPIView.as_view(), name="coupon-create"),
    path("list/", views.AdminCouponListAPIView.as_view(), name="coupon-list"),
    path("<uuid:id>/", views.AdminCouponDetailsAPIView.as_view(), name="coupon-details"),
    path("update/<uuid:id>/", views.AdminCouponUpdateAPIView.as_view(), name="coupon-update"),
    path("delete/<uuid:id>/", views.AdminCouponDeleteAPIView.as_view(), name="coupon-delete"),
]

