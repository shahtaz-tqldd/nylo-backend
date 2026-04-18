from rest_framework import serializers

from orders.models import Order, OrderItem


class AdminOrderCouponSerializer(serializers.Serializer):
    id = serializers.UUIDField(read_only=True)
    code = serializers.CharField(read_only=True)
    coupon_type = serializers.CharField(read_only=True)
    value = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)


class AdminOrderCustomerSerializer(serializers.Serializer):
    id = serializers.UUIDField(read_only=True)
    email = serializers.EmailField(read_only=True)
    first_name = serializers.CharField(read_only=True)
    last_name = serializers.CharField(read_only=True)
    phone = serializers.CharField(read_only=True)


class AdminOrderItemSerializer(serializers.ModelSerializer):
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


class AdminOrderItemSnapshotSerializer(serializers.ModelSerializer):
    name = serializers.SerializerMethodField()
    image = serializers.SerializerMethodField()
    color = serializers.SerializerMethodField()
    size = serializers.SerializerMethodField()

    class Meta:
        model = OrderItem
        fields = ("id", "name", "image", "color", "size", "quantity")
        read_only_fields = fields

    def get_name(self, obj):
        if obj.product and obj.product.title:
            return obj.product.title
        return obj.product_title

    def get_image(self, obj):
        if obj.variant and obj.variant.image_url:
            return obj.variant.image_url
        if obj.product and obj.product.image_url:
            return obj.product.image_url
        return None

    def get_color(self, obj):
        if obj.variant and obj.variant.color:
            return obj.variant.color.name
        return None

    def get_size(self, obj):
        if obj.variant and obj.variant.size:
            return obj.variant.size.name
        return None


class AdminOrderListSerializer(serializers.ModelSerializer):
    customer = AdminOrderCustomerSerializer(read_only=True)
    coupon = AdminOrderCouponSerializer(read_only=True)
    items_count = serializers.IntegerField(read_only=True)
    items_snapshot = AdminOrderItemSnapshotSerializer(source="items", many=True, read_only=True)

    class Meta:
        model = Order
        fields = (
            "id",
            "tracking_number",
            "customer",
            "status",
            "payment_status",
            "currency",
            "subtotal",
            "discount_amount",
            "shipping_charge",
            "tax_amount",
            "total_amount",
            "coupon",
            "coupon_code",
            "stripe_checkout_session_id",
            "stripe_payment_intent_id",
            "checkout_expires_at",
            "created_at",
            "updated_at",
            "items_count",
            "items_snapshot",
        )
        read_only_fields = fields


class AdminOrderDetailSerializer(serializers.ModelSerializer):
    customer = AdminOrderCustomerSerializer(read_only=True)
    coupon = AdminOrderCouponSerializer(read_only=True)
    items = AdminOrderItemSerializer(many=True, read_only=True)

    class Meta:
        model = Order
        fields = (
            "id",
            "tracking_number",
            "customer",
            "status",
            "payment_status",
            "currency",
            "subtotal",
            "discount_amount",
            "shipping_charge",
            "tax_amount",
            "total_amount",
            "coupon",
            "coupon_code",
            "shipping_address",
            "stripe_checkout_session_id",
            "stripe_payment_intent_id",
            "checkout_expires_at",
            "notes",
            "created_at",
            "updated_at",
            "items",
        )
        read_only_fields = fields


class AdminOrderUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Order
        fields = (
            "status",
            "payment_status",
            "discount_amount",
            "shipping_charge",
            "tax_amount",
            "notes",
        )

    def validate(self, attrs):
        monetary_fields = ("discount_amount", "shipping_charge", "tax_amount")
        for field in monetary_fields:
            value = attrs.get(field)
            if value is not None and value < 0:
                raise serializers.ValidationError({field: "This value cannot be negative."})
        return attrs

    def update(self, instance, validated_data):
        for attr, value in validated_data.items():
            setattr(instance, attr, value)

        instance.total_amount = (
            instance.subtotal
            - instance.discount_amount
            + instance.shipping_charge
            + instance.tax_amount
        )
        instance.save()
        return instance
