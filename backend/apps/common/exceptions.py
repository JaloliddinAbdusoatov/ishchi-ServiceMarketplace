import logging
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import IntegrityError
from rest_framework import status
from rest_framework.exceptions import APIException
from rest_framework.response import Response
from rest_framework.views import exception_handler

logger = logging.getLogger(__name__)


class BusinessRuleViolation(APIException):
    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = "A business rule constraint was violated."
    default_code = "business_rule_violation"

    def __init__(self, detail=None, code=None, status_code=None):
        super().__init__(detail=detail, code=code or self.default_code)
        if status_code is not None:
            self.status_code = status_code


class ConflictError(BusinessRuleViolation):
    status_code = status.HTTP_409_CONFLICT
    default_detail = "Operation conflicted with current resource state."
    default_code = "conflict"


class ForbiddenActionError(BusinessRuleViolation):
    status_code = status.HTTP_403_FORBIDDEN
    default_detail = "You do not have permission to perform this action."
    default_code = "forbidden"


def custom_exception_handler(exc, context):
    """
    Standardizes all API error responses to:
    {
        "success": false,
        "error": {
            "code": "<error_code>",
            "message": "<human_readable_message>",
            "details": <dict | list | null>
        }
    }
    """
    if isinstance(exc, DjangoValidationError):
        details = exc.message_dict if hasattr(exc, "message_dict") else exc.messages
        return Response(
            {
                "success": False,
                "error": {
                    "code": "validation_error",
                    "message": "Validation failed.",
                    "details": details,
                },
            },
            status=status.HTTP_400_BAD_REQUEST,
        )

    response = exception_handler(exc, context)

    if response is not None:
        error_code = getattr(exc, "default_code", "error")
        if hasattr(exc, "get_codes"):
            codes = exc.get_codes()
            if isinstance(codes, str):
                error_code = codes

        message = "An error occurred while processing the request."
        details = response.data

        if isinstance(response.data, dict):
            if "detail" in response.data:
                message = str(response.data["detail"])
                details = None
            else:
                message = "Validation or processing error."
        elif isinstance(response.data, list):
            message = str(response.data[0]) if response.data else "Validation error."

        response.data = {
            "success": False,
            "error": {
                "code": error_code,
                "message": message,
                "details": details,
            },
        }
        return response

    if isinstance(exc, IntegrityError):
        logger.warning("Database integrity conflict in API view")
        return Response(
            {
                "success": False,
                "error": {
                    "code": "integrity_conflict",
                    "message": "Database integrity constraint violated (possible duplicate or invalid reference).",
                    "details": None,
                },
            },
            status=status.HTTP_409_CONFLICT,
        )

    logger.error("Unhandled server exception: %s", type(exc).__name__)
    return Response(
        {
            "success": False,
            "error": {
                "code": "internal_server_error",
                "message": "An internal server error occurred.",
                "details": None,
            },
        },
        status=status.HTTP_500_INTERNAL_SERVER_ERROR,
    )
