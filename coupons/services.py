from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP

from django.utils import timezone
from rest_framework import serializers

from coupons.models import Coupon, CouponType


TWOPLACES = Decimal("0.01")


def quantize_amount(value):
    return Decimal(value).quantize(TWOPLACES, rounding=ROUND_HALF_UP)


@dataclass
class AppliedCoupon:
    coupon: Coupon
    subtotal: Decimal
    discount_amount: Decimal
    total_amount: Decimal


def get_coupon_by_code(code):
    normalized_code = (code or "").strip().upper()
    if not normalized_code:
        raise serializers.ValidationError({"code": "Coupon code is required."})

    coupon = Coupon.objects.filter(code__iexact=normalized_code).first()
    if coupon is None:
        raise serializers.ValidationError({"code": "Coupon not found."})
    return coupon


def validate_coupon_for_subtotal(*, coupon: Coupon, subtotal):
    subtotal = quantize_amount(subtotal)
    now = timezone.now()

    if not coupon.is_active:
        raise serializers.ValidationError({"code": "This coupon is inactive."})
    if coupon.valid_from and coupon.valid_from > now:
        raise serializers.ValidationError({"code": "This coupon is not active yet."})
    if coupon.valid_until and coupon.valid_until < now:
        raise serializers.ValidationError({"code": "This coupon has expired."})
    if coupon.usage_limit is not None and coupon.used_count >= coupon.usage_limit:
        raise serializers.ValidationError({"code": "This coupon has reached its usage limit."})
    if subtotal <= Decimal("0.00"):
        raise serializers.ValidationError({"code": "Coupon cannot be applied to an empty cart."})
    if subtotal < coupon.minimum_order_amount:
        raise serializers.ValidationError(
            {"code": f"Minimum order amount for this coupon is {coupon.minimum_order_amount}."}
        )
    if coupon.coupon_type == CouponType.PERCENTAGE and coupon.value > Decimal("100.00"):
        raise serializers.ValidationError({"value": "Percentage discount cannot exceed 100."})

    if coupon.coupon_type == CouponType.PERCENTAGE:
        discount_amount = quantize_amount(subtotal * coupon.value / Decimal("100"))
    else:
        discount_amount = quantize_amount(coupon.value)

    if coupon.maximum_discount_amount is not None:
        discount_amount = min(discount_amount, quantize_amount(coupon.maximum_discount_amount))

    discount_amount = min(discount_amount, subtotal)
    total_amount = quantize_amount(subtotal - discount_amount)

    return AppliedCoupon(
        coupon=coupon,
        subtotal=subtotal,
        discount_amount=discount_amount,
        total_amount=total_amount,
    )


def apply_coupon_code(*, code, subtotal):
    coupon = get_coupon_by_code(code)
    return validate_coupon_for_subtotal(coupon=coupon, subtotal=subtotal)


def allocate_discount_by_unit(line_sources, total_discount):
    total_discount = quantize_amount(total_discount)
    units = []
    for source in line_sources:
        quantity = source["quantity"]
        for _ in range(quantity):
            units.append(
                {
                    "product_data": source["product_data"],
                    "base_price": quantize_amount(source["unit_price"]),
                    "discount_share": Decimal("0.00"),
                }
            )

    if not units:
        return []
    if total_discount <= Decimal("0.00"):
        return units

    total_base = sum((unit["base_price"] for unit in units), Decimal("0.00"))
    if total_base <= Decimal("0.00"):
        return units

    remaining = total_discount
    for index, unit in enumerate(units):
        if index == len(units) - 1:
            share = remaining
        else:
            share = quantize_amount(total_discount * unit["base_price"] / total_base)
            share = min(share, remaining, unit["base_price"])
        unit["discount_share"] = share
        remaining = quantize_amount(remaining - share)

    if remaining > Decimal("0.00"):
        for unit in sorted(units, key=lambda item: item["base_price"], reverse=True):
            extra_capacity = quantize_amount(unit["base_price"] - unit["discount_share"])
            if extra_capacity <= Decimal("0.00"):
                continue
            extra = min(extra_capacity, remaining)
            unit["discount_share"] = quantize_amount(unit["discount_share"] + extra)
            remaining = quantize_amount(remaining - extra)
            if remaining <= Decimal("0.00"):
                break

    return units
