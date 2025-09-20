from pydantic import BaseModel, ConfigDict
from typing import Optional
from enum import Enum


class ErrorType(str, Enum):
    INVALID_REQUEST = "INVALID_REQUEST"
    AUTHENTICATION_FAILED = "AUTHENTICATION_FAILED"
    SERVER_NOT_AVAILABLE = "SERVER_NOT_AVAILABLE"
    INVALID_REQUEST_ERROR = "INVALID_REQUEST_ERROR"
    DUPLICATE_REQUEST = "DUPLICATE_REQUEST"
    OBJECT_NOT_FOUND = "OBJECT_NOT_FOUND"
    VALIDATION_ERROR = "VALIDATION_ERROR"
    PROCESSING_ERROR = "PROCESSING_ERROR"
    UNAUTHORIZED_ERROR = "UNAUTHORIZED_ERROR"
    UNEXPECTED_ERROR = "UNEXPECTED_ERROR"
    EXPIRED_ERROR = "EXPIRED_ERROR"


class ErrorStatusCode(int, Enum):
    STATUS_400 = 400
    STATUS_401 = 401
    STATUS_403 = 403
    STATUS_404 = 404
    STATUS_405 = 405
    STATUS_409 = 409
    STATUS_422 = 422
    STATUS_429 = 429
    STATUS_500 = 500
    STATUS_501 = 501
    STATUS_502 = 502
    STATUS_503 = 503
    STATUS_504 = 504


class DmErrorCode(str, Enum):
    DM_REG_0001 = "DM_REG_0001"  # Invalid email format
    DM_REG_0002 = "DM_REG_0002"  # Invalid password format
    DM_REG_0003 = "DM_REG_0003"  # Email already exists
    DM_REG_0004 = "DM_REG_0004"  # User not found
    DM_REG_0005 = "DM_REG_0005"  # Invalid activation code
    DM_REG_0006 = "DM_REG_0006"  # Activation code expired
    DM_REG_0007 = "DM_REG_0007"  # User already activated
    DM_REG_0008 = "DM_REG_0008"  # Database error
    DM_REG_0009 = "DM_REG_0009"  # Email service error
    DM_REG_0010 = "DM_REG_0010"  # Invalid credentials
    DM_REG_0050 = "DM_REG_0050"  # Unexpected error


class ErrorMessage(tuple, Enum):
    MESSAGE_REG_0001 = (
        "Invalid email format provided",
        "Please provide a valid email address"
    )
    MESSAGE_REG_0002 = (
        "Invalid password format",
        "Password must be at least 8 characters long and contain letters and numbers"
    )
    MESSAGE_REG_0003 = (
        "Email address already exists",
        "Please use a different email address or try logging in"
    )
    MESSAGE_REG_0004 = (
        "User not found",
        "Please check the email address and try again"
    )
    MESSAGE_REG_0005 = (
        "Invalid activation code",
        "Please check the 4-digit code and try again"
    )
    MESSAGE_REG_0006 = (
        "Activation code has expired",
        "Please request a new activation code"
    )
    MESSAGE_REG_0007 = (
        "User account is already activated",
        "No action required. You can now login to your account"
    )
    MESSAGE_REG_0008 = (
        "Database operation failed",
        "Please try again later or contact support"
    )
    MESSAGE_REG_0009 = (
        "Email service temporarily unavailable",
        "Please try again later or contact support"
    )
    MESSAGE_REG_0010 = (
        "Invalid authentication credentials",
        "Please check your email and password and try again"
    )
    MESSAGE_REG_0050 = (
        "An unexpected error occurred",
        "Please try again later or contact support"
    )


class ErrorResponse(BaseModel):
    err_code: str
    err_status_code: ErrorStatusCode
    err_type: Optional[ErrorType] = None
    err_message: str
    err_handling: Optional[str] = None
    
    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={
            "example": {
                "err_code": "DM_REG_0001",
                "err_status_code": 422,
                "err_type": "VALIDATION_ERROR",
                "err_message": "Invalid email format provided",
                "err_handling": "Please provide a valid email address"
            }
        }
    )

    def to_dict(self):
        return {
            "err_code": self.err_code,
            "err_status_code": self.err_status_code.value,
            "err_type": self.err_type.value if self.err_type else None,
            "err_message": self.err_message,
            "err_handling": self.err_handling
        }


class ErrorHandling(BaseModel):
    status: str
    data: ErrorResponse
    
    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={
            "example": {
                "status": "error",
                "data": {
                    "err_code": "DM_REG_0001",
                    "err_status_code": 422,
                    "err_type": "VALIDATION_ERROR",
                    "err_message": "Invalid email format provided",
                    "err_handling": "Please provide a valid email address"
                }
            }
        }
    )

    def to_dict(self):
        return {
            "status": self.status,
            "data": self.data.to_dict()
        }