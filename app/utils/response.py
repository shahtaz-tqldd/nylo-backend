from rest_framework.response import Response


class APIResponse:
    @staticmethod
    def success(data=None, message="Success", status=200):

        response = {"status": status, "success": True, "message": message}

        if data is not None:
            response["data"] = data

        return Response(response, status=status)

    @staticmethod
    def error(errors=None, message="An error occured!", status=400):

        response = {"status": status, "success": False, "message": message}

        if errors is not None:
            response["errors"] = errors

        return Response(response, status=status)
