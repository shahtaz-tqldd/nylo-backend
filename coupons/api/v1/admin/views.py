from django.db.models import Q
from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated

from app.base.pagination import CustomPagination
from app.utils.response import APIResponse
from auth.permissions import IsAdmin
from coupons.api.v1.admin.serializers import AdminCouponSerializer
from coupons.models import Coupon


class AdminCouponResponseMixin:
    permission_classes = [IsAuthenticated, IsAdmin]
    lookup_field = "id"


class CouponAdminQuerysetMixin:
    pagination_class = CustomPagination

    def get_queryset(self):
        queryset = Coupon.objects.all().order_by("-created_at")
        text = (self.request.query_params.get("text") or self.request.query_params.get("search") or "").strip()
        if text:
            queryset = queryset.filter(Q(code__icontains=text) | Q(description__icontains=text))

        is_active = self.request.query_params.get("is_active")
        if is_active is not None and is_active != "":
            queryset = queryset.filter(is_active=is_active.lower() == "true")

        return queryset


class AdminCouponListAPIView(CouponAdminQuerysetMixin, AdminCouponResponseMixin, generics.ListAPIView):
    serializer_class = AdminCouponSerializer

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

        return APIResponse.success(data=serializer.data, meta=meta, message="Coupons fetched successfully.")


class AdminCouponDetailsAPIView(CouponAdminQuerysetMixin, AdminCouponResponseMixin, generics.RetrieveAPIView):
    serializer_class = AdminCouponSerializer

    def retrieve(self, request, *args, **kwargs):
        serializer = self.get_serializer(self.get_object())
        return APIResponse.success(data=serializer.data, message="Coupon fetched successfully.")


class AdminCouponCreateAPIView(AdminCouponResponseMixin, generics.CreateAPIView):
    queryset = Coupon.objects.all()
    serializer_class = AdminCouponSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        coupon = serializer.save(created_by=request.user, updated_by=request.user)
        return APIResponse.success(
            data=self.get_serializer(coupon).data,
            message="Coupon created successfully.",
            status=status.HTTP_201_CREATED,
        )


class AdminCouponUpdateAPIView(AdminCouponResponseMixin, generics.UpdateAPIView):
    queryset = Coupon.objects.all()
    serializer_class = AdminCouponSerializer

    def partial_update(self, request, *args, **kwargs):
        serializer = self.get_serializer(self.get_object(), data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        coupon = serializer.save(updated_by=request.user)
        return APIResponse.success(data=self.get_serializer(coupon).data, message="Coupon updated successfully.")


class AdminCouponDeleteAPIView(AdminCouponResponseMixin, generics.DestroyAPIView):
    queryset = Coupon.objects.all()
    serializer_class = AdminCouponSerializer

    def destroy(self, request, *args, **kwargs):
        self.get_object().delete()
        return APIResponse.success(message="Coupon deleted successfully.")

