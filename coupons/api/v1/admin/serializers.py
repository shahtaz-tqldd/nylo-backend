from decimal import Decimal

from rest_framework import serializers

from coupons.models import Coupon, CouponType


class AdminCouponSerializer(serializers.ModelSerializer):
    class Meta:
        model = Coupon
        fields = (
            "id",
            "code",
            "coupon_type",
            "value",
            "minimum_order_amount",
            "maximum_discount_amount",
            "usage_limit",
            "used_count",
            "valid_from",
            "valid_until",
            "is_active",
            "description",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "used_count", "created_at", "updated_at")

    def validate_code(self, value):
        return value.strip().upper()

    def validate(self, attrs):
        coupon_type = attrs.get("coupon_type", getattr(self.instance, "coupon_type", None))
        value = attrs.get("value", getattr(self.instance, "value", None))
        minimum_order_amount = attrs.get(
            "minimum_order_amount",
            getattr(self.instance, "minimum_order_amount", Decimal("0.00")),
        )
        maximum_discount_amount = attrs.get(
            "maximum_discount_amount",
            getattr(self.instance, "maximum_discount_amount", None),
        )
        valid_from = attrs.get("valid_from", getattr(self.instance, "valid_from", None))
        valid_until = attrs.get("valid_until", getattr(self.instance, "valid_until", None))

        if minimum_order_amount is not None and minimum_order_amount < Decimal("0.00"):
            raise serializers.ValidationError({"minimum_order_amount": "This value cannot be negative."})
        if maximum_discount_amount is not None and maximum_discount_amount <= Decimal("0.00"):
            raise serializers.ValidationError({"maximum_discount_amount": "This value must be greater than zero."})
        if valid_from and valid_until and valid_from > valid_until:
            raise serializers.ValidationError({"valid_until": "Valid until must be later than valid from."})
        if coupon_type == CouponType.PERCENTAGE and value is not None and value > Decimal("100.00"):
            raise serializers.ValidationError({"value": "Percentage discount cannot exceed 100."})
        return attrs

