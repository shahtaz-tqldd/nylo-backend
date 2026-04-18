from datetime import datetime, time, timedelta
from decimal import Decimal

from django.db.models import Avg, Count, IntegerField, Q, Sum
from django.db.models.functions import Coalesce, TruncDate
from django.utils import timezone
from rest_framework import generics, status
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated

from app.utils.response import APIResponse
from auth.permissions import IsAdmin
from orders.models import Order, OrderStatusChoice, PaymentStatusChoice
from products.models import Collection
from shop.models import AboutPageContent, FAQ, LegalPageContent, StoreConfiguration
from shop.services import ensure_singleton_defaults
from shop.v1.admin.serializers import (
    AdminSalesByCollectionSerializer,
    AdminSalesOverTimeSerializer,
    AdminSalesSummarySerializer,
    AboutPageContentSerializer,
    FAQSerializer,
    LegalPageContentSerializer,
    StoreConfigurationSerializer,
)


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
        date_from = self._parse_date(self.request.query_params.get("date_from") or self.request.query_params.get("start_date"))
        date_to = self._parse_date(self.request.query_params.get("date_to") or self.request.query_params.get("end_date"))

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


class AdminSalesByCollectionAPIView(AdminAnalyticsMixin, generics.GenericAPIView):
    serializer_class = AdminSalesByCollectionSerializer

    def get(self, request, *args, **kwargs):
        date_from, date_to = self._coerce_date_range()
        order_item_filters = Q(items__product__order_items__order__payment_status=PaymentStatusChoice.PAID)
        order_item_filters &= ~Q(items__product__order_items__order__status__in=self.revenue_excluded_statuses)

        if date_from:
            order_item_filters &= Q(items__product__order_items__order__created_at__gte=self._date_start(date_from))
        if date_to:
            order_item_filters &= Q(items__product__order_items__order__created_at__lte=self._date_end(date_to))

        collections = (
            Collection.objects.filter(is_active=True)
            .annotate(
                total_sales=Coalesce(
                    Sum("items__product__order_items__total_price", filter=order_item_filters),
                    Decimal("0.00"),
                ),
                orders=Count(
                    "items__product__order_items__order",
                    filter=order_item_filters,
                    distinct=True,
                ),
                items_sold=Coalesce(
                    Sum(
                        "items__product__order_items__quantity",
                        filter=order_item_filters,
                        output_field=IntegerField(),
                    ),
                    0,
                ),
            )
            .order_by("-total_sales", "title")
        )

        payload = {
            "date_from": date_from,
            "date_to": date_to,
            "collections": [
                {
                    "id": collection.id,
                    "title": collection.title,
                    "slug": collection.slug,
                    "total_sales": self._decimal_or_zero(collection.total_sales),
                    "orders": collection.orders,
                    "items_sold": collection.items_sold,
                }
                for collection in collections
            ],
        }
        return APIResponse.success(
            data=self.get_serializer(payload).data,
            message="Sales by collection fetched successfully.",
        )
