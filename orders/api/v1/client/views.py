from datetime import datetime, timezone as dt_timezone
from decimal import Decimal, ROUND_HALF_UP
from importlib import import_module

from django.conf import settings
from django.db import transaction
from django.db.models import Prefetch
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt

from rest_framework import status
from rest_framework.generics import GenericAPIView
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.views import APIView

from app.base.pagination import CustomPagination
from app.utils.response import APIResponse
from orders.api.v1.client.serializers import CheckoutSessionCreateSerializer, OrderSerializer
from orders.models import Order, OrderItem, OrderStatusChoice, PaymentStatusChoice, StripeWebhookEvent
from products.models import ProductVariant, UserCartItem


TWOPLACES = Decimal("0.01")


def quantize_amount(value):
    return Decimal(value).quantize(TWOPLACES, rounding=ROUND_HALF_UP)


def amount_to_cents(value):
    return int((quantize_amount(value) * 100).to_integral_value())


def get_variant_description(variant):
    parts = []
    if variant.size:
        parts.append(f"Size: {variant.size.name}")
    if variant.color:
        parts.append(f"Color: {variant.color.name}")
    return ", ".join(parts)


def get_stripe_client():
    try:
        stripe = import_module("stripe")
    except ModuleNotFoundError as exc:
        raise RuntimeError("Stripe SDK is not installed.") from exc

    if not settings.STRIPE_SECRET_KEY:
        raise RuntimeError("Stripe secret key is not configured.")

    stripe.api_key = settings.STRIPE_SECRET_KEY
    return stripe


def normalize_shipping_address(shipping_address):
    return {
        "first_name": shipping_address["first_name"].strip(),
        "last_name": shipping_address["last_name"].strip(),
        "email": shipping_address["email"].strip().lower(),
        "phone": shipping_address["phone"].strip(),
        "address_line_1": shipping_address["address_line_1"].strip(),
        "address_line_2": shipping_address.get("address_line_2", "").strip(),
        "city": shipping_address["city"].strip(),
        "state_province": shipping_address["state_province"].strip(),
        "postal_code": shipping_address["postal_code"].strip(),
        "country": shipping_address["country"].strip(),
    }


def get_shipping_metadata(shipping_address):
    return {
        "shipping_name": f'{shipping_address["first_name"]} {shipping_address["last_name"]}'.strip(),
        "shipping_email": shipping_address["email"],
        "shipping_phone": shipping_address["phone"],
        "shipping_city": shipping_address["city"],
        "shipping_country": shipping_address["country"],
        "shipping_postal_code": shipping_address["postal_code"],
    }


def update_user_shipping_details(user, shipping_address):
    user.first_name = shipping_address["first_name"]
    user.last_name = shipping_address["last_name"]
    user.email = shipping_address["email"]
    user.phone = shipping_address["phone"]
    user.address_line_1 = shipping_address["address_line_1"]
    user.address_line_2 = shipping_address["address_line_2"]
    user.city = shipping_address["city"]
    user.state_province = shipping_address["state_province"]
    user.postal_code = shipping_address["postal_code"]
    user.country = shipping_address["country"]
    user.save(
        update_fields=[
            "first_name",
            "last_name",
            "email",
            "phone",
            "address_line_1",
            "address_line_2",
            "city",
            "state_province",
            "postal_code",
            "country",
            "updated_at",
        ]
    )


class CheckoutAPIView(GenericAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = CheckoutSessionCreateSerializer

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        success_url = serializer.validated_data.get("success_url") or settings.STRIPE_CHECKOUT_SUCCESS_URL
        cancel_url = serializer.validated_data.get("cancel_url") or settings.STRIPE_CHECKOUT_CANCEL_URL
        promo_code = serializer.validated_data.get("promo_code") or None
        shipping_address = normalize_shipping_address(serializer.validated_data["shipping_address"])

        if not success_url or not cancel_url:
            return APIResponse.error(
                message="Checkout success and cancel URLs must be provided.",
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            with transaction.atomic():
                update_user_shipping_details(request.user, shipping_address)

                cart_items = list(
                    UserCartItem.objects.select_for_update()
                    .filter(user=request.user)
                    .select_related(
                        "product__category",
                        "variant__product",
                    )
                    .order_by("created_at")
                )

                if not cart_items:
                    return APIResponse.error(
                        message="Your cart is empty.",
                        status=status.HTTP_400_BAD_REQUEST,
                    )

                variant_ids = [item.variant_id for item in cart_items]
                locked_variants = {
                    variant.id: variant
                    for variant in ProductVariant.objects.select_for_update()
                    .select_related("product")
                    .filter(id__in=variant_ids, is_active=True, product__is_active=True)
                }

                if len(locked_variants) != len(set(variant_ids)):
                    return APIResponse.error(
                        message="One or more cart items are no longer available.",
                        status=status.HTTP_400_BAD_REQUEST,
                    )

                line_items = []
                subtotal = Decimal("0.00")

                order = Order.objects.create(
                    customer=request.user,
                    status=OrderStatusChoice.PENDING,
                    payment_status=PaymentStatusChoice.UNPAID,
                    currency=settings.STRIPE_CURRENCY.lower(),
                    promo_code=promo_code,
                    shipping_address=shipping_address,
                )

                order_items = []
                for cart_item in cart_items:
                    variant = locked_variants[cart_item.variant_id]
                    product = variant.product

                    if cart_item.quantity > variant.stock:
                        return APIResponse.error(
                            message=f"Requested quantity for '{product.title}' exceeds available stock.",
                            status=status.HTTP_400_BAD_REQUEST,
                        )

                    unit_price = quantize_amount(product.price)
                    line_total = quantize_amount(unit_price * cart_item.quantity)
                    subtotal += line_total

                    variant_description = get_variant_description(variant)
                    order_items.append(
                        OrderItem(
                            order=order,
                            product=product,
                            variant=variant,
                            source_cart_item_id=cart_item.id,
                            product_title=product.title,
                            variant_description=variant_description,
                            sku=variant.sku or product.sku,
                            quantity=cart_item.quantity,
                            unit_price=unit_price,
                            total_price=line_total,
                        )
                    )

                    product_data = {
                        "name": product.title,
                        "metadata": {
                            "product_id": str(product.id),
                            "variant_id": str(variant.id),
                        },
                    }
                    if variant_description:
                        product_data["description"] = variant_description

                    line_items.append(
                        {
                            "price_data": {
                                "currency": settings.STRIPE_CURRENCY.lower(),
                                "unit_amount": amount_to_cents(unit_price),
                                "product_data": product_data,
                            },
                            "quantity": cart_item.quantity,
                        }
                    )

                OrderItem.objects.bulk_create(order_items)
                order.subtotal = quantize_amount(subtotal)
                order.discount_amount = Decimal("0.00")
                order.shipping_charge = Decimal("0.00")
                order.tax_amount = Decimal("0.00")
                order.total_amount = quantize_amount(subtotal)
                order.save(
                    update_fields=[
                        "subtotal",
                        "discount_amount",
                        "shipping_charge",
                        "tax_amount",
                        "total_amount",
                        "updated_at",
                    ]
                )

            stripe = get_stripe_client()
            checkout_session = stripe.checkout.Session.create(
                mode="payment",
                line_items=line_items,
                success_url=success_url,
                cancel_url=cancel_url,
                customer_email=request.user.email or None,
                metadata={
                    "order_id": str(order.id),
                    "user_id": str(request.user.id),
                    "promo_code": promo_code or "",
                    **get_shipping_metadata(shipping_address),
                },
                payment_intent_data={
                    "metadata": {
                        "order_id": str(order.id),
                        "user_id": str(request.user.id),
                        **get_shipping_metadata(shipping_address),
                    }
                },
            )
        except RuntimeError as exc:
            return APIResponse.error(message=str(exc), status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        except Exception as exc:
            if "order" in locals():
                order.payment_status = PaymentStatusChoice.FAILED
                order.notes = str(exc)
                order.save(update_fields=["payment_status", "notes", "updated_at"])
            return APIResponse.error(
                message="Unable to create Stripe checkout session.",
                errors={"detail": [str(exc)]},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        order.stripe_checkout_session_id = checkout_session.id
        order.checkout_expires_at = (
            datetime.fromtimestamp(checkout_session.expires_at, tz=dt_timezone.utc)
            if getattr(checkout_session, "expires_at", None)
            else None
        )
        order.save(update_fields=["stripe_checkout_session_id", "checkout_expires_at", "updated_at"])

        return APIResponse.success(
            data={
                "order": OrderSerializer(order).data,
                "session_id": checkout_session.id,
                "checkout_url": getattr(checkout_session, "url", None),
            },
            message="Checkout session created successfully.",
            status=status.HTTP_201_CREATED,
        )


class UserOrderAPIView(GenericAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = OrderSerializer
    pagination_class = CustomPagination

    def get_queryset(self):
        return (
            Order.objects.filter(customer=self.request.user)
            .prefetch_related(
                Prefetch(
                    "items",
                    queryset=OrderItem.objects.select_related("product", "variant").order_by("-created_at"),
                )
            )
            .order_by("-created_at")
        )

    def get(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        page = self.paginate_queryset(queryset)
        serializer = self.get_serializer(page if page is not None else queryset, many=True)

        meta = None
        if page is not None:
            meta = {
                "total": self.paginator.page.paginator.count,
                "page": self.paginator.page.number,
                "page_size": self.paginator.page.paginator.per_page,
            }

        return APIResponse.success(
            data=serializer.data,
            meta=meta,
            message="Orders fetched successfully.",
        )


@method_decorator(csrf_exempt, name="dispatch")
class StripeWebhookAPIView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        if not settings.STRIPE_WEBHOOK_SECRET:
            return APIResponse.error(
                message="Stripe webhook secret is not configured.",
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        try:
            stripe = get_stripe_client()
            payload = request.body
            signature = request.headers.get("Stripe-Signature", "")
            event = stripe.Webhook.construct_event(payload, signature, settings.STRIPE_WEBHOOK_SECRET)
        except RuntimeError as exc:
            return APIResponse.error(message=str(exc), status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        except Exception as exc:
            return APIResponse.error(
                message="Invalid Stripe webhook payload.",
                errors={"detail": [str(exc)]},
                status=status.HTTP_400_BAD_REQUEST,
            )

        event_payload = event.to_dict_recursive() if hasattr(event, "to_dict_recursive") else dict(event)

        if StripeWebhookEvent.objects.filter(stripe_event_id=event_payload["id"]).exists():
            return APIResponse.success(message="Event already processed.")

        event_type = event_payload["type"]
        data_object = event_payload["data"]["object"]

        with transaction.atomic():
            StripeWebhookEvent.objects.create(
                stripe_event_id=event_payload["id"],
                event_type=event_type,
                payload=event_payload,
            )

            if event_type == "checkout.session.completed":
                self.handle_checkout_completed(data_object)
            elif event_type == "checkout.session.expired":
                self.handle_checkout_expired(data_object)
            elif event_type == "payment_intent.payment_failed":
                self.handle_payment_failed(data_object)

        return APIResponse.success(message="Webhook processed successfully.")

    def handle_checkout_completed(self, session):
        order_id = session.get("metadata", {}).get("order_id")
        if not order_id:
            return

        order = (
            Order.objects.select_for_update()
            .prefetch_related("items__variant")
            .filter(id=order_id)
            .first()
        )
        if order is None or order.payment_status == PaymentStatusChoice.PAID:
            return

        for item in order.items.select_related("variant"):
            if item.variant is None:
                continue
            if item.variant.stock < item.quantity:
                order.payment_status = PaymentStatusChoice.FAILED
                order.notes = "Stock became unavailable before payment confirmation."
                order.save(update_fields=["payment_status", "notes", "updated_at"])
                return

        for item in order.items.select_related("variant"):
            if item.variant is None:
                continue
            item.variant.stock -= item.quantity
            item.variant.save(update_fields=["stock", "updated_at"])

        cart_item_ids = [item.source_cart_item_id for item in order.items.all() if item.source_cart_item_id]
        if cart_item_ids:
            UserCartItem.objects.filter(user=order.customer, id__in=cart_item_ids).delete()
        order.status = OrderStatusChoice.APPROVED
        order.payment_status = PaymentStatusChoice.PAID
        order.stripe_payment_intent_id = session.get("payment_intent") or order.stripe_payment_intent_id
        order.notes = None
        order.save(
            update_fields=[
                "status",
                "payment_status",
                "stripe_payment_intent_id",
                "notes",
                "updated_at",
            ]
        )

    def handle_checkout_expired(self, session):
        checkout_session_id = session.get("id")
        if not checkout_session_id:
            return

        (
            Order.objects.select_for_update()
            .filter(
                stripe_checkout_session_id=checkout_session_id,
                payment_status=PaymentStatusChoice.UNPAID,
            )
            .update(
                status=OrderStatusChoice.CANCELLED,
                notes="Stripe checkout session expired.",
                updated_at=timezone.now(),
            )
        )

    def handle_payment_failed(self, payment_intent):
        order_id = payment_intent.get("metadata", {}).get("order_id")
        if not order_id:
            return

        order = Order.objects.select_for_update().filter(id=order_id).first()
        if order is None or order.payment_status == PaymentStatusChoice.PAID:
            return

        order.payment_status = PaymentStatusChoice.FAILED
        order.stripe_payment_intent_id = payment_intent.get("id") or order.stripe_payment_intent_id
        order.notes = "Stripe reported that payment failed."
        order.save(update_fields=["payment_status", "stripe_payment_intent_id", "notes", "updated_at"])
