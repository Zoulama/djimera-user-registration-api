from pydantic import BaseModel, EmailStr, ConfigDict
from typing import Optional
from datetime import datetime

from src.domain.user.entities import UserStatus


class UserRegistrationRequest(BaseModel):
    """Request schema for user registration."""
    email: EmailStr
    password: str

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "email": "user@example.com",
                "password": "password123"
            }
        }
    )


class UserRegistrationResponse(BaseModel):
    """Response schema for user registration."""
    user_id: str
    email: str
    status: UserStatus
    message: str = "User registered successfully. Please check your email for activation code."

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "user_id": "123e4567-e89b-12d3-a456-426614174000",
                "email": "user@example.com",
                "status": "PENDING",
                "message": "User registered successfully. Please check your email for activation code."
            }
        }
    )


class ActivationRequest(BaseModel):
    """Request schema for account activation."""
    email: EmailStr
    password: str
    code: str

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "email": "user@example.com",
                "password": "password123",
                "code": "1234"
            }
        }
    )


class ActivationResponse(BaseModel):
    """Response schema for account activation."""
    user_id: str
    email: str
    status: UserStatus
    message: str = "Account activated successfully."
    activated_at: datetime

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "user_id": "123e4567-e89b-12d3-a456-426614174000",
                "email": "user@example.com",
                "status": "ACTIVE",
                "message": "Account activated successfully.",
                "activated_at": "2023-12-01T10:30:00"
            }
        }
    )


class ResendActivationRequest(BaseModel):
    """Request schema for resending activation code."""
    email: EmailStr
    password: str

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "email": "user@example.com",
                "password": "password123"
            }
        }
    )


class ApiResponse(BaseModel):
    """Generic API response wrapper."""
    status: str = "success"
    data: Optional[dict] = None

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "status": "success",
                "data": {
                    "user_id": "123e4567-e89b-12d3-a456-426614174000",
                    "email": "user@example.com",
                    "status": "PENDING"
                }
            }
        }
    )