from datetime import datetime, time, timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.db.models import Avg, Count, DecimalField, ExpressionWrapper, F, IntegerField, Q, Sum
from django.db.models.functions import Coalesce, TruncDate
from django.utils import timezone
from rest_framework import generics, status
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated

from app.utils.response import APIResponse
from auth.permissions import IsAdmin
from orders.models import Order, OrderStatusChoice, PaymentStatusChoice
from orders.api.v1.client.views import get_variant_description
from products.models import Brand, Category, Collection, Product, ProductVariant
from shop.models import AboutPageContent, FAQ, LegalPageContent, StoreConfiguration
from shop.services import ensure_singleton_defaults
from shop.v1.admin.serializers import (
    AdminSalesByChannelSerializer,
    AdminSalesOverTimeSerializer,
    AdminSalesSummarySerializer,
    AdminTopPerformersSerializer,
    AboutPageContentSerializer,
    FAQSerializer,
    LegalPageContentSerializer,
    StoreConfigurationSerializer,
)

User = get_user_model()


class AdminSingletonContentAPIView(generics.GenericAPIView):
    permission_classes = [IsAuthenticated, IsAdmin]
    model = None

    def get_instance(self):
        ensure_singleton_defaults()
        return self.model.objects.order_by("-created_at").first()

    def get(self, request, *args, **kwargs):
        instance = self.get_instance()
        return APIResponse.success(
            data=self.get_serializer(instance).data,
            message=self.success_get_message,
        )

    def patch(self, request, *args, **kwargs):
        instance = self.get_instance()
        serializer = self.get_serializer(instance, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save(updated_by=request.user)
        return APIResponse.success(
            data=self.get_serializer(instance).data,
            message=self.success_update_message,
        )


class StoreConfigurationAPIView(AdminSingletonContentAPIView):
    serializer_class = StoreConfigurationSerializer
    model = StoreConfiguration
    parser_classes = [MultiPartParser, FormParser, JSONParser]
    success_get_message = "Store configuration fetched successfully."
    success_update_message = "Store configuration updated successfully."


class LegalPageContentAPIView(AdminSingletonContentAPIView):
    serializer_class = LegalPageContentSerializer
    model = LegalPageContent
    success_get_message = "Legal page content fetched successfully."
    success_update_message = "Legal page content updated successfully."


class AboutPageContentAPIView(AdminSingletonContentAPIView):
    serializer_class = AboutPageContentSerializer
    model = AboutPageContent
    parser_classes = [MultiPartParser, FormParser, JSONParser]
    success_get_message = "About page content fetched successfully."
    success_update_message = "About page content updated successfully."


class FAQListCreateAPIView(generics.GenericAPIView):
    permission_classes = [IsAuthenticated, IsAdmin]
    serializer_class = FAQSerializer

    def get(self, request, *args, **kwargs):
        queryset = FAQ.objects.all()
        serializer = self.get_serializer(queryset, many=True)
        return APIResponse.success(data=serializer.data, message="FAQs fetched successfully.")

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        instance = serializer.save(created_by=request.user, updated_by=request.user)
        return APIResponse.success(
            data=self.get_serializer(instance).data,
            message="FAQ created successfully.",
            status=status.HTTP_201_CREATED,
        )


class FAQUpdateAPIView(generics.GenericAPIView):
    permission_classes = [IsAuthenticated, IsAdmin]
    serializer_class = FAQSerializer
    queryset = FAQ.objects.all()
    lookup_field = "id"

    def patch(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save(updated_by=request.user)
        return APIResponse.success(data=self.get_serializer(instance).data, message="FAQ updated successfully.")


class FAQDeleteAPIView(generics.DestroyAPIView):
    permission_classes = [IsAuthenticated, IsAdmin]
    queryset = FAQ.objects.all()
    lookup_field = "id"

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        instance.delete()
        return APIResponse.success(message="FAQ deleted successfully.")


class AdminAnalyticsMixin:
    permission_classes = [IsAuthenticated, IsAdmin]
    revenue_excluded_statuses = [
        OrderStatusChoice.CANCELLED,
        OrderStatusChoice.REJECTED,
        OrderStatusChoice.REFUND_ACCEPTED,
        OrderStatusChoice.REFUNDED,
    ]

    def get_order_queryset(self):
        return Order.objects.all()

    def get_paid_order_queryset(self):
        return self.get_order_queryset().filter(
            payment_status=PaymentStatusChoice.PAID,
        ).exclude(status__in=self.revenue_excluded_statuses)

    def _parse_date(self, value):
        if not value:
            return None
        try:
            return datetime.strptime(value, "%Y-%m-%d").date()
        except ValueError:
            return None

    def _coerce_date_range(self, *, default_days=None):
        today = timezone.localdate()
        time_range = (self.request.query_params.get("time_range") or self.request.query_params.get("range") or "").strip().lower()
        date_from = self._parse_date(self.request.query_params.get("date_from") or self.request.query_params.get("start_date"))
        date_to = self._parse_date(self.request.query_params.get("date_to") or self.request.query_params.get("end_date"))

        if not date_from and not date_to and time_range:
            if time_range == "all":
                return None, None
            if time_range == "today":
                return today, today
            if time_range in {"7d", "last_7_days"}:
                return today - timedelta(days=6), today
            if time_range in {"30d", "last_30_days"}:
                return today - timedelta(days=29), today
            if time_range in {"90d", "last_90_days"}:
                return today - timedelta(days=89), today
            if time_range == "this_month":
                return today.replace(day=1), today
            if time_range == "this_year":
                return today.replace(month=1, day=1), today

        if date_from and not date_to:
            date_to = today
        if date_to and not date_from:
            date_from = date_to

        if not date_from and not date_to and default_days is not None:
            date_to = today
            date_from = today - timedelta(days=default_days - 1)

        if date_from and date_to and date_from > date_to:
            date_from, date_to = date_to, date_from

        return date_from, date_to

    def _date_start(self, value):
        return timezone.make_aware(datetime.combine(value, time.min))

    def _date_end(self, value):
        return timezone.make_aware(datetime.combine(value, time.max))

    def _month_bounds(self, reference_date):
        current_start = reference_date.replace(day=1)
        previous_end = current_start - timedelta(days=1)
        previous_start = previous_end.replace(day=1)
        return current_start, previous_start, previous_end

    def _decimal_or_zero(self, value):
        return value if value is not None else Decimal("0.00")

    def _growth_percentage(self, current, previous):
        current = self._decimal_or_zero(current)
        previous = self._decimal_or_zero(previous)

        if previous == 0:
            return Decimal("100.00") if current > 0 else Decimal("0.00")

        return ((current - previous) / previous * Decimal("100")).quantize(Decimal("0.01"))

    def _apply_date_range(self, queryset, field_name, date_from, date_to):
        if date_from:
            queryset = queryset.filter(**{f"{field_name}__gte": self._date_start(date_from)})
        if date_to:
            queryset = queryset.filter(**{f"{field_name}__lte": self._date_end(date_to)})
        return queryset


class AdminSalesSummaryAPIView(AdminAnalyticsMixin, generics.GenericAPIView):
    serializer_class = AdminSalesSummarySerializer

    def get(self, request, *args, **kwargs):
        today = timezone.localdate()
        current_month_start, previous_month_start, previous_month_end = self._month_bounds(today)

        paid_orders = self.get_paid_order_queryset()
        current_month_paid_orders = paid_orders.filter(
            created_at__gte=self._date_start(current_month_start),
            created_at__lte=self._date_end(today),
        )
        previous_month_paid_orders = paid_orders.filter(
            created_at__gte=self._date_start(previous_month_start),
            created_at__lte=self._date_end(previous_month_end),
        )

        current_month_revenue = self._decimal_or_zero(
            current_month_paid_orders.aggregate(total=Sum("total_amount"))["total"]
        )
        previous_month_revenue = self._decimal_or_zero(
            previous_month_paid_orders.aggregate(total=Sum("total_amount"))["total"]
        )
        current_month_average_order_value = self._decimal_or_zero(
            current_month_paid_orders.aggregate(value=Avg("total_amount"))["value"]
        )
        previous_month_average_order_value = self._decimal_or_zero(
            previous_month_paid_orders.aggregate(value=Avg("total_amount"))["value"]
        )

        overview_date_from, overview_date_to = self._coerce_date_range()
        overview_orders = self._apply_date_range(paid_orders, "created_at", overview_date_from, overview_date_to)

        product_cost_expression = ExpressionWrapper(
            Coalesce(F("items__product__cost_price"), Decimal("0.00")) * F("items__quantity"),
            output_field=DecimalField(max_digits=12, decimal_places=2),
        )
        cost_of_goods = self._decimal_or_zero(
            overview_orders.aggregate(
                total=Sum(product_cost_expression)
            )["total"]
        )
        total_discounts = self._decimal_or_zero(
            overview_orders.aggregate(total=Sum("discount_amount"))["total"]
        )
        subtotal_revenue = self._decimal_or_zero(
            overview_orders.aggregate(total=Sum("subtotal"))["total"]
        )

        payload = {
            "total_revenue": self._decimal_or_zero(paid_orders.aggregate(total=Sum("total_amount"))["total"]),
            "revenue_this_month": current_month_revenue,
            "previous_month_revenue": previous_month_revenue,
            "revenue_growth_percentage": self._growth_percentage(current_month_revenue, previous_month_revenue),
            "total_orders": self.get_order_queryset().count(),
            "orders_placed_this_month": self.get_order_queryset().filter(
                created_at__gte=self._date_start(current_month_start),
                created_at__lte=self._date_end(today),
            ).count(),
            "average_order_value": current_month_average_order_value,
            "previous_month_average_order_value": previous_month_average_order_value,
            "average_order_value_growth_percentage": self._growth_percentage(
                current_month_average_order_value,
                previous_month_average_order_value,
            ),
            "sales_overview": {
                "date_from": overview_date_from,
                "date_to": overview_date_to,
                "total_revenue": self._decimal_or_zero(overview_orders.aggregate(total=Sum("total_amount"))["total"]),
                "total_taxes": self._decimal_or_zero(overview_orders.aggregate(total=Sum("tax_amount"))["total"]),
                "total_discounts": total_discounts,
                "shipping_fees": self._decimal_or_zero(overview_orders.aggregate(total=Sum("shipping_charge"))["total"]),
                "total_profit": subtotal_revenue - total_discounts - cost_of_goods,
            },
        }

        return APIResponse.success(
            data=self.get_serializer(payload).data,
            message="Sales summary fetched successfully.",
        )


class AdminSalesOverTimeAPIView(AdminAnalyticsMixin, generics.GenericAPIView):
    serializer_class = AdminSalesOverTimeSerializer

    def get(self, request, *args, **kwargs):
        date_from, date_to = self._coerce_date_range(default_days=7)
        queryset = self.get_paid_order_queryset().filter(
            created_at__gte=self._date_start(date_from),
            created_at__lte=self._date_end(date_to),
        )

        aggregated = {
            item["date"]: item
            for item in queryset.annotate(date=TruncDate("created_at"))
            .values("date")
            .annotate(
                sales=Coalesce(Sum("total_amount"), Decimal("0.00")),
                orders=Count("id"),
            )
            .order_by("date")
        }

        points = []
        cursor = date_from
        while cursor <= date_to:
            row = aggregated.get(cursor)
            points.append(
                {
                    "date": cursor,
                    "sales": self._decimal_or_zero(row["sales"]) if row else Decimal("0.00"),
                    "orders": row["orders"] if row else 0,
                }
            )
            cursor += timedelta(days=1)

        payload = {
            "date_from": date_from,
            "date_to": date_to,
            "points": points,
        }
        return APIResponse.success(
            data=self.get_serializer(payload).data,
            message="Sales over time fetched successfully.",
        )


class AdminSalesByChannelAPIView(AdminAnalyticsMixin, generics.GenericAPIView):
    serializer_class = AdminSalesByChannelSerializer

    def _serialize_sales_channel_items(self, queryset, *, title_field):
        return [
            {
                "id": item.id,
                "title": getattr(item, title_field),
                "slug": item.slug,
                "total_sales": self._decimal_or_zero(item.total_sales),
                "orders": item.orders,
                "items_sold": item.items_sold,
            }
            for item in queryset
        ]

    def get(self, request, *args, **kwargs):
        date_from, date_to = self._coerce_date_range()
        collection_order_item_filters = Q(items__product__order_items__order__payment_status=PaymentStatusChoice.PAID)
        collection_order_item_filters &= ~Q(items__product__order_items__order__status__in=self.revenue_excluded_statuses)
        brand_order_item_filters = Q(products__order_items__order__payment_status=PaymentStatusChoice.PAID)
        brand_order_item_filters &= ~Q(products__order_items__order__status__in=self.revenue_excluded_statuses)
        category_order_item_filters = Q(product__order_items__order__payment_status=PaymentStatusChoice.PAID)
        category_order_item_filters &= ~Q(product__order_items__order__status__in=self.revenue_excluded_statuses)

        if date_from:
            collection_order_item_filters &= Q(
                items__product__order_items__order__created_at__gte=self._date_start(date_from)
            )
            brand_order_item_filters &= Q(products__order_items__order__created_at__gte=self._date_start(date_from))
            category_order_item_filters &= Q(product__order_items__order__created_at__gte=self._date_start(date_from))
        if date_to:
            collection_order_item_filters &= Q(
                items__product__order_items__order__created_at__lte=self._date_end(date_to)
            )
            brand_order_item_filters &= Q(products__order_items__order__created_at__lte=self._date_end(date_to))
            category_order_item_filters &= Q(product__order_items__order__created_at__lte=self._date_end(date_to))

        collections = (
            Collection.objects.all()
            .annotate(
                total_sales=Coalesce(
                    Sum("items__product__order_items__total_price", filter=collection_order_item_filters),
                    Decimal("0.00"),
                ),
                orders=Count(
                    "items__product__order_items__order",
                    filter=collection_order_item_filters,
                    distinct=True,
                ),
                items_sold=Coalesce(
                    Sum(
                        "items__product__order_items__quantity",
                        filter=collection_order_item_filters,
                        output_field=IntegerField(),
                    ),
                    0,
                ),
            )
            .order_by("-total_sales", "title")
        )
        brands = (
            Brand.objects.annotate(
                total_sales=Coalesce(
                    Sum("products__order_items__total_price", filter=brand_order_item_filters),
                    Decimal("0.00"),
                ),
                orders=Count(
                    "products__order_items__order",
                    filter=brand_order_item_filters,
                    distinct=True,
                ),
                items_sold=Coalesce(
                    Sum(
                        "products__order_items__quantity",
                        filter=brand_order_item_filters,
                        output_field=IntegerField(),
                    ),
                    0,
                ),
            )
            .order_by("-total_sales", "name")
        )
        categories = (
            Category.objects.annotate(
                total_sales=Coalesce(
                    Sum("product__order_items__total_price", filter=category_order_item_filters),
                    Decimal("0.00"),
                ),
                orders=Count(
                    "product__order_items__order",
                    filter=category_order_item_filters,
                    distinct=True,
                ),
                items_sold=Coalesce(
                    Sum(
                        "product__order_items__quantity",
                        filter=category_order_item_filters,
                        output_field=IntegerField(),
                    ),
                    0,
                ),
            )
            .order_by("-total_sales", "name")
        )

        payload = {
            "date_from": date_from,
            "date_to": date_to,
            "collections": self._serialize_sales_channel_items(collections, title_field="title"),
            "brands": self._serialize_sales_channel_items(brands, title_field="name"),
            "categories": self._serialize_sales_channel_items(categories, title_field="name"),
        }
        return APIResponse.success(
            data=self.get_serializer(payload).data,
            message="Sales by channel fetched successfully.",
        )


class AdminTopPerformersAPIView(AdminAnalyticsMixin, generics.GenericAPIView):
    serializer_class = AdminTopPerformersSerializer

    def _serialize_top_variant(self, product, date_from, date_to):
        variant_queryset = ProductVariant.objects.filter(
            product=product,
            order_items__order__payment_status=PaymentStatusChoice.PAID,
        ).exclude(
            order_items__order__status__in=self.revenue_excluded_statuses,
        )
        variant_queryset = self._apply_date_range(
            variant_queryset,
            "order_items__order__created_at",
            date_from,
            date_to,
        )
        variant = (
            variant_queryset.annotate(
                total_sales=Coalesce(Sum("order_items__total_price"), Decimal("0.00")),
                orders_placed=Count("order_items__order", distinct=True),
            )
            .order_by("-total_sales", "-orders_placed", "created_at")
            .first()
        )

        if not variant:
            return {
                "id": None,
                "title": "",
                "image_url": None,
                "total_sales": Decimal("0.00"),
                "orders_placed": 0,
            }

        return {
            "id": variant.id,
            "title": get_variant_description(variant) or str(variant),
            "image_url": variant.image_url or product.image_url,
            "total_sales": self._decimal_or_zero(variant.total_sales),
            "orders_placed": variant.orders_placed,
        }

    def get(self, request, *args, **kwargs):
        date_from, date_to = self._coerce_date_range()

        top_products = (
            Product.objects.filter(order_items__order__payment_status=PaymentStatusChoice.PAID)
            .exclude(order_items__order__status__in=self.revenue_excluded_statuses)
        )
        top_products = self._apply_date_range(top_products, "order_items__order__created_at", date_from, date_to)
        top_products = (
            top_products.annotate(
                total_sales=Coalesce(Sum("order_items__total_price"), Decimal("0.00")),
                orders_placed=Count("order_items__order", distinct=True),
            )
            .order_by("-total_sales", "-orders_placed", "title")
            .distinct()[:3]
        )

        top_customers = (
            User.objects.filter(orders__payment_status=PaymentStatusChoice.PAID)
            .exclude(orders__status__in=self.revenue_excluded_statuses)
        )
        top_customers = self._apply_date_range(top_customers, "orders__created_at", date_from, date_to)
        top_customers = (
            top_customers.annotate(
                total_purchased=Coalesce(Sum("orders__total_amount"), Decimal("0.00")),
            )
            .order_by("-total_purchased", "email")
            .distinct()[:3]
        )

        payload = {
            "date_from": date_from,
            "date_to": date_to,
            "top_products": [
                {
                    "id": product.id,
                    "name": product.title,
                    "image_url": product.image_url,
                    "total_sales": self._decimal_or_zero(product.total_sales),
                    "orders_placed": product.orders_placed,
                    "top_selling_variant": self._serialize_top_variant(product, date_from, date_to),
                }
                for product in top_products
            ],
            "top_customers": [
                {
                    "id": customer.id,
                    "name": customer.full_name or customer.email,
                    "email": customer.email,
                    "total_purchased": self._decimal_or_zero(customer.total_purchased),
                }
                for customer in top_customers
            ],
        }
        return APIResponse.success(
            data=self.get_serializer(payload).data,
            message="Top performers fetched successfully.",
        )
