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


class GetUserListView(PlaceholderAPIView):
    message = "Admin user list is not implemented yet."


class UserDetailsForAdminView(PlaceholderAPIView):
    message = "Admin user details are not implemented yet."


class UserActivationView(PlaceholderAPIView):
    message = "User activation is not implemented yet."
