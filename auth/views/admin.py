from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView


class PlaceholderAPIView(APIView):
    message = "Endpoint not implemented yet."

    def get(self, request, *args, **kwargs):
        return Response({"detail": self.message}, status=status.HTTP_501_NOT_IMPLEMENTED)

    def post(self, request, *args, **kwargs):
        return Response({"detail": self.message}, status=status.HTTP_501_NOT_IMPLEMENTED)

    def patch(self, request, *args, **kwargs):
        return Response({"detail": self.message}, status=status.HTTP_501_NOT_IMPLEMENTED)


class CreateNewUserView(PlaceholderAPIView):
    message = "User registration is not implemented yet."


class LoginView(PlaceholderAPIView):
    message = "Login is not implemented yet."


class RefreshTokenView(PlaceholderAPIView):
    message = "Token refresh is not implemented yet."


class UserDetailsView(PlaceholderAPIView):
    message = "User details retrieval is not implemented yet."


class UserDetailsUpdateView(PlaceholderAPIView):
    message = "User details update is not implemented yet."


class ForgetPasswordView(PlaceholderAPIView):
    message = "Forgot password is not implemented yet."


class ResetPasswordView(PlaceholderAPIView):
    message = "Reset password is not implemented yet."
