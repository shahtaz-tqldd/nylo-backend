from django.urls import path

from coupons.api.v1.client.views import ApplyCouponAPIView


urlpatterns = [
    path("apply/", ApplyCouponAPIView.as_view(), name="coupon-apply"),
]

