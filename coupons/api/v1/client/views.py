from decimal import Decimal

from rest_framework import serializers, status
from rest_framework.generics import GenericAPIView
from rest_framework.permissions import IsAuthenticated

from app.utils.response import APIResponse
from coupons.api.v1.client.serializers import ApplyCouponSerializer
from coupons.services import apply_coupon_code, quantize_amount
from products.models import UserCartItem


class ApplyCouponAPIView(GenericAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = ApplyCouponSerializer

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        cart_items = list(
            UserCartItem.objects.filter(user=request.user)
            .select_related("product", "variant")
            .order_by("created_at")
        )
        if not cart_items:
            return APIResponse.error(message="Your cart is empty.", status=status.HTTP_400_BAD_REQUEST)

        subtotal = sum(
            (quantize_amount(item.product.price) * item.quantity for item in cart_items),
            Decimal("0.00"),
        )

        try:
            applied_coupon = apply_coupon_code(code=serializer.validated_data["code"], subtotal=subtotal)
        except serializers.ValidationError as exc:
            return APIResponse.error(
                message="Coupon validation failed.",
                errors=exc.detail,
                status=status.HTTP_400_BAD_REQUEST,
            )
        coupon = applied_coupon.coupon

        return APIResponse.success(
            data={
                "coupon": {
                    "id": str(coupon.id),
                    "code": coupon.code,
                    "coupon_type": coupon.coupon_type,
                    "value": coupon.value,
                    "minimum_order_amount": coupon.minimum_order_amount,
                    "maximum_discount_amount": coupon.maximum_discount_amount,
                },
                "subtotal": applied_coupon.subtotal,
                "discount_amount": applied_coupon.discount_amount,
                "total_amount": applied_coupon.total_amount,
            },
            message="Coupon applied successfully.",
        )
