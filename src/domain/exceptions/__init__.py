import logging
from typing import Optional
from fastapi import Request
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError, ResponseValidationError
from pydantic_core import ValidationError

from src.schemas.common.errors import (
    ErrorHandling,
    ErrorResponse,
    ErrorType,
    DmErrorCode,
    ErrorMessage,
    ErrorStatusCode
)

logger = logging.getLogger(__name__)


def get_error_type(status_code: ErrorStatusCode) -> ErrorType:
    """Map status codes to error types."""
    error_mapping = {
        (400, 405, 500): ErrorType.INVALID_REQUEST_ERROR,
        (401,): ErrorType.UNAUTHORIZED_ERROR,
        (403,): ErrorType.AUTHENTICATION_FAILED,
        (404,): ErrorType.OBJECT_NOT_FOUND,
        (409,): ErrorType.DUPLICATE_REQUEST,
        (422,): ErrorType.VALIDATION_ERROR,
        (429,): ErrorType.PROCESSING_ERROR,
        (501, 502, 503, 504): ErrorType.SERVER_NOT_AVAILABLE,
    }

    for codes, error_type in error_mapping.items():
        if status_code.value in codes:
            return error_type
    return ErrorType.UNEXPECTED_ERROR


class BaseServiceException(Exception):
    """Base exception class for all service exceptions."""

    def __init__(
            self,
            err_code: str,
            err_status_code: ErrorStatusCode,
            err_type: Optional[ErrorType] = None,
            err_message: Optional[str] = None,
            err_handling: Optional[str] = None,
    ):
        self.err_code = err_code
        self.err_status_code = err_status_code
        self.err_type = err_type or get_error_type(err_status_code)
        self.err_message = err_message
        self.err_handling = err_handling
        super().__init__(self.err_code, self.err_status_code, self.err_type,
                         self.err_message, self.err_handling)

    def to_dict(self) -> dict:
        return ErrorResponse(**self.__dict__).to_dict()

    def to_error_response(self) -> ErrorResponse:
        return ErrorResponse(**self.__dict__)


class ValidationException(BaseServiceException):
    """Exception for validation errors."""

    def __init__(
            self,
            status_code: ErrorStatusCode = ErrorStatusCode.STATUS_422,
            err_type: ErrorType = ErrorType.VALIDATION_ERROR,
            err_message: str = ErrorMessage.MESSAGE_REG_0001[0],
            err_handling: str = ErrorMessage.MESSAGE_REG_0001[1],
            err_code: str = DmErrorCode.DM_REG_0001.value
    ):
        super().__init__(
            err_code=err_code,
            err_status_code=status_code,
            err_type=err_type,
            err_message=err_message,
            err_handling=err_handling
        )


class UserNotFoundException(BaseServiceException):
    """Exception for when user is not found."""

    def __init__(self):
        super().__init__(
            err_code=DmErrorCode.DM_REG_0004.value,
            err_status_code=ErrorStatusCode.STATUS_404,
            err_type=ErrorType.OBJECT_NOT_FOUND,
            err_message=ErrorMessage.MESSAGE_REG_0004[0],
            err_handling=ErrorMessage.MESSAGE_REG_0004[1]
        )


class EmailAlreadyExistsException(BaseServiceException):
    """Exception for when email already exists."""

    def __init__(self):
        super().__init__(
            err_code=DmErrorCode.DM_REG_0003.value,
            err_status_code=ErrorStatusCode.STATUS_409,
            err_type=ErrorType.DUPLICATE_REQUEST,
            err_message=ErrorMessage.MESSAGE_REG_0003[0],
            err_handling=ErrorMessage.MESSAGE_REG_0003[1]
        )


class InvalidActivationCodeException(BaseServiceException):
    """Exception for invalid activation codes."""

    def __init__(self):
        super().__init__(
            err_code=DmErrorCode.DM_REG_0005.value,
            err_status_code=ErrorStatusCode.STATUS_400,
            err_type=ErrorType.VALIDATION_ERROR,
            err_message=ErrorMessage.MESSAGE_REG_0005[0],
            err_handling=ErrorMessage.MESSAGE_REG_0005[1]
        )


class ActivationCodeExpiredException(BaseServiceException):
    """Exception for expired activation codes."""

    def __init__(self):
        super().__init__(
            err_code=DmErrorCode.DM_REG_0006.value,
            err_status_code=ErrorStatusCode.STATUS_400,
            err_type=ErrorType.EXPIRED_ERROR,
            err_message=ErrorMessage.MESSAGE_REG_0006[0],
            err_handling=ErrorMessage.MESSAGE_REG_0006[1]
        )


class UserAlreadyActivatedException(BaseServiceException):
    """Exception for when user is already activated."""

    def __init__(self):
        super().__init__(
            err_code=DmErrorCode.DM_REG_0007.value,
            err_status_code=ErrorStatusCode.STATUS_400,
            err_type=ErrorType.PROCESSING_ERROR,
            err_message=ErrorMessage.MESSAGE_REG_0007[0],
            err_handling=ErrorMessage.MESSAGE_REG_0007[1]
        )


class DatabaseException(BaseServiceException):
    """Exception for database errors."""

    def __init__(self, message: str = None):
        super().__init__(
            err_code=DmErrorCode.DM_REG_0008.value,
            err_status_code=ErrorStatusCode.STATUS_500,
            err_type=ErrorType.SERVER_NOT_AVAILABLE,
            err_message=message or ErrorMessage.MESSAGE_REG_0008[0],
            err_handling=ErrorMessage.MESSAGE_REG_0008[1]
        )


class EmailServiceException(BaseServiceException):
    """Exception for email service errors."""

    def __init__(self):
        super().__init__(
            err_code=DmErrorCode.DM_REG_0009.value,
            err_status_code=ErrorStatusCode.STATUS_503,
            err_type=ErrorType.SERVER_NOT_AVAILABLE,
            err_message=ErrorMessage.MESSAGE_REG_0009[0],
            err_handling=ErrorMessage.MESSAGE_REG_0009[1]
        )


class AuthenticationException(BaseServiceException):
    """Exception for authentication errors."""

    def __init__(self):
        super().__init__(
            err_code=DmErrorCode.DM_REG_0010.value,
            err_status_code=ErrorStatusCode.STATUS_401,
            err_type=ErrorType.UNAUTHORIZED_ERROR,
            err_message=ErrorMessage.MESSAGE_REG_0010[0],
            err_handling=ErrorMessage.MESSAGE_REG_0010[1]
        )


# Exception Handlers
async def service_exception_handler(
        request: Request,
        exc: BaseServiceException
) -> JSONResponse:
    """Handle BaseServiceException and return formatted JSON response."""
    logger.error(f'Exception in {request.method} {request.url}: {exc.err_message}')
    return JSONResponse(
        status_code=exc.err_status_code.value,
        content=ErrorHandling(
            status="error",
            data=exc.to_error_response()
        ).to_dict()
    )


async def validation_exception_handler(
        request: Request,
        exc: RequestValidationError
) -> JSONResponse:
    """Handle FastAPI validation errors."""
    logger.error(f'Validation error in {request.method} {request.url}: {exc.errors()}')
    return JSONResponse(
        status_code=422,
        content=ErrorHandling(
            status="error",
            data=ErrorResponse(
                err_code=DmErrorCode.DM_REG_0001.value,
                err_status_code=ErrorStatusCode.STATUS_422,
                err_type=ErrorType.VALIDATION_ERROR,
                err_message="Request validation failed",
                err_handling="Please check your request data and try again"
            )
        ).to_dict()
    )


async def generic_exception_handler(
        request: Request,
        exc: Exception
) -> JSONResponse:
    """Handle unexpected exceptions."""
    logger.error(f'Unexpected error in {request.method} {request.url}: {str(exc)}', exc_info=True)
    return JSONResponse(
        status_code=500,
        content=ErrorHandling(
            status="error",
            data=ErrorResponse(
                err_code=DmErrorCode.DM_REG_0050.value,
                err_status_code=ErrorStatusCode.STATUS_500,
                err_type=ErrorType.UNEXPECTED_ERROR,
                err_message=ErrorMessage.MESSAGE_REG_0050[0],
                err_handling=ErrorMessage.MESSAGE_REG_0050[1]
            )
        ).to_dict()
    )