from rest_framework import serializers

from orders.models import Order, OrderItem


class AppliedCouponSerializer(serializers.Serializer):
    id = serializers.UUIDField(read_only=True)
    code = serializers.CharField(read_only=True)
    coupon_type = serializers.CharField(read_only=True)
    value = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)
    minimum_order_amount = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)
    maximum_discount_amount = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True, allow_null=True)


class ShippingAddressSerializer(serializers.Serializer):
    first_name = serializers.CharField(max_length=32)
    last_name = serializers.CharField(max_length=32)
    email = serializers.EmailField()
    phone = serializers.CharField(max_length=17)
    address_line_1 = serializers.CharField(max_length=100)
    address_line_2 = serializers.CharField(max_length=100, required=False, allow_blank=True)
    city = serializers.CharField(max_length=50)
    state_province = serializers.CharField(max_length=50)
    postal_code = serializers.CharField(max_length=20)
    country = serializers.CharField(max_length=50)


class CheckoutSessionCreateSerializer(serializers.Serializer):
    shipping_address = ShippingAddressSerializer()
    success_url = serializers.URLField(required=False, allow_blank=True)
    cancel_url = serializers.URLField(required=False, allow_blank=True)
    promo_code = serializers.CharField(required=False, allow_blank=True, max_length=100)


class OrderItemSerializer(serializers.ModelSerializer):
    product_id = serializers.UUIDField(source="product.id", read_only=True)
    variant_id = serializers.UUIDField(source="variant.id", read_only=True)

    class Meta:
        model = OrderItem
        fields = (
            "id",
            "product_id",
            "variant_id",
            "product_title",
            "variant_description",
            "sku",
            "quantity",
            "unit_price",
            "total_price",
        )
        read_only_fields = fields


class OrderSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True, read_only=True)
    shipping_address = ShippingAddressSerializer(read_only=True)
    coupon = AppliedCouponSerializer(read_only=True)

    class Meta:
        model = Order
        fields = (
            "id",
            "tracking_number",
            "status",
            "payment_status",
            "currency",
            "subtotal",
            "discount_amount",
            "shipping_charge",
            "tax_amount",
            "total_amount",
            "coupon",
            "promo_code",
            "shipping_address",
            "stripe_checkout_session_id",
            "stripe_payment_intent_id",
            "checkout_expires_at",
            "created_at",
            "updated_at",
            "items",
        )
        read_only_fields = fields
