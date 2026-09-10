from typing import Any, Optional
from fastapi import Request, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel


class ErrorPayload(BaseModel):
    code: str
    message: str
    details: Optional[Any] = None


class ErrorResponse(BaseModel):
    error: ErrorPayload


class AppException(Exception):
    def __init__(
        self,
        message: str,
        code: str = "INTERNAL_SERVER_ERROR",
        status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR,
        details: Optional[Any] = None
    ):
        self.message = message
        self.code = code
        self.status_code = status_code
        self.details = details
        super().__init__(message)


class NotFoundError(AppException):
    def __init__(self, message: str = "Resource not found", details: Optional[Any] = None):
        super().__init__(message, code="NOT_FOUND", status_code=status.HTTP_404_NOT_FOUND, details=details)


class AuthenticationError(AppException):
    def __init__(self, message: str = "Authentication failed", details: Optional[Any] = None):
        super().__init__(message, code="AUTHENTICATION_FAILED", status_code=status.HTTP_401_UNAUTHORIZED, details=details)


class ForbiddenError(AppException):
    def __init__(self, message: str = "Access forbidden", details: Optional[Any] = None):
        super().__init__(message, code="FORBIDDEN", status_code=status.HTTP_403_FORBIDDEN, details=details)


class ConflictError(AppException):
    def __init__(self, message: str = "Resource conflict", details: Optional[Any] = None):
        super().__init__(message, code="CONFLICT", status_code=status.HTTP_409_CONFLICT, details=details)


class ValidationError(AppException):
    def __init__(self, message: str = "Validation error", details: Optional[Any] = None):
        super().__init__(message, code="VALIDATION_ERROR", status_code=status.HTTP_400_BAD_REQUEST, details=details)


class AIProviderUnavailableError(AppException):
    def __init__(self, message: str = "AI Provider unavailable", details: Optional[Any] = None):
        super().__init__(message, code="AI_PROVIDER_UNAVAILABLE", status_code=status.HTTP_503_SERVICE_UNAVAILABLE, details=details)



import uuid
from app.core.logging import logger


from fastapi.exceptions import RequestValidationError


async def app_exception_handler(request: Request, exc: AppException) -> JSONResponse:
    """Global handler for custom AppException."""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "code": exc.code,
                "message": exc.message,
                "details": exc.details
            }
        }
    )


async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    """Handler for FastAPI input validation & path parameter parsing errors."""
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={
            "error": {
                "code": "VALIDATION_ERROR",
                "message": "Invalid request parameters or payload format.",
                "details": exc.errors()
            }
        }
    )


async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Catch-all handler for unexpected system exceptions to ensure full observability without leaking stack traces."""
    ref_id = str(uuid.uuid4())
    logger.error(
        f"[Ref ID {ref_id}] Unhandled Exception on {request.method} {request.url.path}: {type(exc).__name__} - {str(exc)}",
        exc_info=True
    )
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": {
                "code": "INTERNAL_SERVER_ERROR",
                "message": "An internal server error occurred. Please try again.",
                "details": {"reference_id": ref_id}
            }
        }
    )
