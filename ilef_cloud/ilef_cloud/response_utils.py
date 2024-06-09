from rest_framework.response import Response
from rest_framework import status


def success_response(data, message="Success", status_code=status.HTTP_200_OK):
    return Response({"message": message, "data": data}, status=status_code)


def error_response(error_message, status_code=status.HTTP_200_OK):
    return Response({"error": error_message}, status=status_code)
