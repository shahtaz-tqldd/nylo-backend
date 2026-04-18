from datetime import datetime, time
from uuid import UUID

from django.db.models import Count, Prefetch, Q
from django.utils import timezone

from rest_framework import generics
from rest_framework.permissions import IsAuthenticated

from app.base.pagination import CustomPagination
from app.utils.response import APIResponse
from auth.permissions import IsAdmin
from orders.api.v1.admin.serializers import (
    AdminOrderDetailSerializer,
    AdminOrderListSerializer,
    AdminOrderUpdateSerializer,
)
from orders.models import Order, OrderItem


class AdminOrderResponseMixin:
    permission_classes = [IsAuthenticated, IsAdmin]
    lookup_field = "id"


class OrderAdminQuerysetMixin:
    pagination_class = CustomPagination

    def get_base_queryset(self):
        return (
            Order.objects.select_related("customer", "coupon")
            .prefetch_related(
                Prefetch(
                    "items",
                    queryset=OrderItem.objects.select_related(
                        "product",
                        "variant__size",
                        "variant__color",
                    ).order_by("-created_at"),
                )
            )
            .annotate(items_count=Count("items"))
            .order_by("-created_at")
        )

    def _parse_date_start(self, value):
        if not value:
            return None
        parsed = datetime.strptime(value, "%Y-%m-%d").date()
        return timezone.make_aware(datetime.combine(parsed, time.min))

    def _parse_date_end(self, value):
        if not value:
            return None
        parsed = datetime.strptime(value, "%Y-%m-%d").date()
        return timezone.make_aware(datetime.combine(parsed, time.max))

    def get_queryset(self):
        queryset = self.get_base_queryset()
        params = self.request.query_params

        text = (params.get("search") or params.get("text") or "").strip()
        if text:
            filters = (
                Q(customer__email__icontains=text)
                | Q(customer__first_name__icontains=text)
                | Q(customer__last_name__icontains=text)
                | Q(customer__phone__icontains=text)
                | Q(items__product_title__icontains=text)
                | Q(tracking_number__icontains=text)
                | Q(stripe_checkout_session_id__icontains=text)
                | Q(stripe_payment_intent_id__icontains=text)
            )
            try:
                filters = Q(id=UUID(text)) | filters
            except (ValueError, TypeError):
                pass
            queryset = queryset.filter(filters)

        status_value = (params.get("status") or "").strip()
        if status_value:
            queryset = queryset.filter(status=status_value)

        date_from = params.get("date_from") or params.get("start_date")
        date_to = params.get("date_to") or params.get("end_date")

        try:
            parsed_from = self._parse_date_start(date_from)
        except ValueError:
            parsed_from = None
        try:
            parsed_to = self._parse_date_end(date_to)
        except ValueError:
            parsed_to = None

        if parsed_from:
            queryset = queryset.filter(created_at__gte=parsed_from)
        if parsed_to:
            queryset = queryset.filter(created_at__lte=parsed_to)

        return queryset.distinct().order_by("-created_at")


class AdminOrderListAPIView(OrderAdminQuerysetMixin, AdminOrderResponseMixin, generics.ListAPIView):
    serializer_class = AdminOrderListSerializer

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
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


class AdminOrderDetailsAPIView(OrderAdminQuerysetMixin, AdminOrderResponseMixin, generics.RetrieveAPIView):
    serializer_class = AdminOrderDetailSerializer

    def retrieve(self, request, *args, **kwargs):
        serializer = self.get_serializer(self.get_object())
        return APIResponse.success(data=serializer.data, message="Order fetched successfully.")


class AdminOrderUpdateAPIView(AdminOrderResponseMixin, generics.UpdateAPIView):
    queryset = Order.objects.select_related("customer", "coupon").prefetch_related(
        Prefetch(
            "items",
            queryset=OrderItem.objects.select_related(
                "product",
                "variant__size",
                "variant__color",
            ).order_by("-created_at"),
        )
    )
    serializer_class = AdminOrderUpdateSerializer

    def partial_update(self, request, *args, **kwargs):
        serializer = self.get_serializer(self.get_object(), data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        order = serializer.save()
        output = AdminOrderDetailSerializer(order, context=self.get_serializer_context())
        return APIResponse.success(
            data=output.data,
            message="Order updated successfully.",
        )
