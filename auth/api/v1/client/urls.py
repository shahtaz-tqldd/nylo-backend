from django.urls import path

from auth.api.v1.client.views import (
    AdminInvitationRegistrationView,
    AdminInvitationVerifyView,
    ChangePasswordView,
    CreateNewUserView,
    LoginView,
    RefreshTokenView,
    UserDetailsUpdateView,
    UserDetailsView,
)


urlpatterns = [
    path("register/", CreateNewUserView.as_view(), name="register"),
    path("admin-register/", AdminInvitationRegistrationView.as_view(), name="admin-register"),
    path("admin-invitations/verify/", AdminInvitationVerifyView.as_view(), name="admin-invitation-verify"),
    path("login/", LoginView.as_view(), name="login"),
    path("refresh/", RefreshTokenView.as_view(), name="refresh-token"),
    path("me/", UserDetailsView.as_view(), name="user-details"),
    path("me/update/", UserDetailsUpdateView.as_view(), name="update-user"),
    path("change-password/", ChangePasswordView.as_view(), name="change-password"),
]
