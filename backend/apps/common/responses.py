from rest_framework import status
from rest_framework.response import Response


def success_response(data=None, message=None, status_code=status.HTTP_200_OK, extra=None):
    payload = {"success": True}
    if message is not None:
        payload["message"] = message
    if data is not None:
        payload["data"] = data
    if extra:
        payload.update(extra)
    return Response(payload, status=status_code)


def error_response(code, message, details=None, status_code=status.HTTP_400_BAD_REQUEST):
    return Response(
        {
            "success": False,
            "error": {
                "code": code,
                "message": message,
                "details": details,
            },
        },
        status=status_code,
    )
