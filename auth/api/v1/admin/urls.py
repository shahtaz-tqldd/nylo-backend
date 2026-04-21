from django.urls import path

from auth.api.v1.admin.views import (
    AdminInvitationCreateAPIView,
    AdminUserListAPIView,
    AdminUserManageAPIView,
    CustomerListAPIView,
)


urlpatterns = [
    path("customers/", CustomerListAPIView.as_view(), name="customer-list"),
    path("admin-users/", AdminUserListAPIView.as_view(), name="admin-user-list"),
    path("admin-users/<uuid:admin_id>/", AdminUserManageAPIView.as_view(), name="admin-user-manage"),
    path("send-invitation/", AdminInvitationCreateAPIView.as_view(), name="admin-invitation-create"),
]
