from rest_framework.generics import ListAPIView
from auth.models import User, UserRole
from auth.permissions import IsAdmin
from auth.serializers import CustomerListSerializer
from app.utils.response import APIResponse


class CustomerListAPIView(ListAPIView):
    permission_classes = [IsAdmin]
    serializer_class = CustomerListSerializer

    def get_queryset(self):
        return User.objects.filter(role=UserRole.CUSTOMER).order_by("-created_at")

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)
        return APIResponse.success(
            data=serializer.data,
            message="Customers fetched successfully.",
        )
