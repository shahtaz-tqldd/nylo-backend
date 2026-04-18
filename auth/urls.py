from django.urls import include, path

from auth.views.admin import (
  CustomerListAPIView, 
#   UserActivationView, 
#   UserDetailsForAdminView
)
from auth.views.client import (
    ChangePasswordView,
    CreateNewUserView,
    # ForgetPasswordView,
    LoginView,
    RefreshTokenView,
    # ResetPasswordView,
    UserDetailsUpdateView,
    UserDetailsView,
)


client_urls = [
    path("register/", CreateNewUserView.as_view(), name="register"),
    path("login/", LoginView.as_view(), name="login"),
    path("refresh/", RefreshTokenView.as_view(), name="refresh-token"),
    path("me/", UserDetailsView.as_view(), name="user-details"),
    path("me/update/", UserDetailsUpdateView.as_view(), name="update-user"),
    path("change-password/", ChangePasswordView.as_view(), name="change-password"),
    # path("forget-password/", ForgetPasswordView.as_view(), name="forget-password"),
    # path("reset-password/", ResetPasswordView.as_view(), name="reset-password"),
]

admin_urls = [
    path("customers/", CustomerListAPIView.as_view(), name="customer-list"),
    # path("users/details/", UserDetailsForAdminView.as_view(), name="admin-user-details"),
    # path("users/activation/", UserActivationView.as_view(), name="user-activation"),
]

urlpatterns = [
    *client_urls,
    path("admin/", include((admin_urls, "auth_admin"))),
]
