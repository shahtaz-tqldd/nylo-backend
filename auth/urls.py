from django.urls import path
from auth.views.admin import (
    CreateNewUserView,
    LoginView,
    RefreshTokenView,
    UserDetailsView,
    UserDetailsUpdateView,
    ForgetPasswordView,
    ResetPasswordView
)
from auth.views.client import (
    GetUserListView,
    UserDetailsForAdminView,
    UserActivationView,
)

client_urls = [
    path("register/", CreateNewUserView.as_view(), name="create-user"),
    path("login/", LoginView.as_view(), name="login"),
    path("refresh/", RefreshTokenView.as_view(), name="refresh token"),
    path("user-details/", UserDetailsView.as_view(), name="user-details"),
    path("user-details/update/", UserDetailsUpdateView.as_view(), name="update-user"),
    path("forget-password/", ForgetPasswordView.as_view(), name="forget-password"),
    path("reset-password/", ResetPasswordView.as_view(), name="reset-password"),
]

admin_urls = [
    path("admin/user-list/", GetUserListView.as_view(), name="user-list"),
    path("admin/user-details/", UserDetailsForAdminView.as_view(), name="user-details"),
    path(
        "admin/user-activation/", UserActivationView.as_view(), name="user-activation"
    ),
]


urlpatterns = client_urls + admin_urls
