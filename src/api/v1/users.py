from fastapi import APIRouter, Depends, HTTPException, status

from src.schemas.user import (
    UserRegistrationRequest,
    UserRegistrationResponse,
    ActivationRequest,
    ActivationResponse,
    ResendActivationRequest,
    ApiResponse
)
from src.schemas.common.errors import ErrorHandling
from src.domain.user.service import UserService

router = APIRouter(
    prefix="/api/v1/users",
    tags=["User Registration"]
)

# Dependency injection will be set up in main.py
user_service = None


def get_user_service() -> UserService:
    """Dependency injection for UserService."""
    if user_service is None:
        raise HTTPException(
            status_code=500,
            detail="User service not initialized"
        )
    return user_service


@router.post(
    "/register",
    response_model=ApiResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        409: {"model": ErrorHandling, "description": "Email already exists"},
        422: {"model": ErrorHandling, "description": "Validation Error"},
        500: {"model": ErrorHandling, "description": "Internal Server Error"}
    }
)
async def register_user(
        request: UserRegistrationRequest,
        service: UserService = Depends(get_user_service)
) -> ApiResponse:
    """
    Register a new user.

    Creates a new user account and sends an activation code to the provided email address.
    The activation code expires in 1 minute.

    **Request Body:**
    - email: Valid email address
    - password: Password (minimum 8 characters, must contain letters and numbers)

    **Response:**
    - user_id: Unique identifier for the created user
    - email: User's email address
    - status: Account status ("PENDING" for new registrations)
    - message: Success message
    """
    user = await service.register_user(request.email, request.password)

    response_data = UserRegistrationResponse(
        user_id=str(user.user_id),
        email=user.email,
        status=user.status
    )

    return ApiResponse(
        status="success",
        data=response_data.model_dump()
    )


@router.post(
    "/activate",
    response_model=ApiResponse,
    responses={
        400: {"model": ErrorHandling, "description": "Invalid or expired activation code"},
        401: {"model": ErrorHandling, "description": "Invalid email or password"},
        404: {"model": ErrorHandling, "description": "User not found"},
        422: {"model": ErrorHandling, "description": "Validation Error"},
        500: {"model": ErrorHandling, "description": "Internal Server Error"}
    }
)
async def activate_user(
        request: ActivationRequest,
        service: UserService = Depends(get_user_service)
) -> ApiResponse:
    """
    Activate user account.

    Activates a user account using the 4-digit activation code sent via email.

    **Request Body:**
    - email: User's email address
    - password: User's password
    - code: 4-digit activation code received via email

    **Response:**
    - user_id: User's unique identifier
    - email: User's email address
    - status: Account status ("ACTIVE" after successful activation)
    - activated_at: Timestamp of activation
    - message: Success message

    **Notes:**
    - Activation code expires after 1 minute
    - Code can only be used once
    - User must not be already activated
    """
    user = await service.activate_user(request.email, request.password, request.code)

    response_data = ActivationResponse(
        user_id=str(user.user_id),
        email=user.email,
        status=user.status,
        activated_at=user.activated_at
    )

    return ApiResponse(
        status="success",
        data=response_data.model_dump()
    )


@router.post(
    "/resend-activation",
    response_model=ApiResponse,
    responses={
        400: {"model": ErrorHandling, "description": "User already activated"},
        401: {"model": ErrorHandling, "description": "Invalid email or password"},
        404: {"model": ErrorHandling, "description": "User not found"},
        422: {"model": ErrorHandling, "description": "Validation Error"},
        500: {"model": ErrorHandling, "description": "Internal Server Error"}
    }
)
async def resend_activation_code(
        request: ResendActivationRequest,
        service: UserService = Depends(get_user_service)
) -> ApiResponse:
    """
    Resend activation code.

    Generates and sends a new activation code to the user's email address.

    **Request Body:**
    - email: User's email address
    - password: User's password

    **Response:**
    - message: Success message confirming code was sent

    **Notes:**
    - Only works for users with PENDING status
    - Previously generated codes are invalidated
    - New code expires after 1 minute
    """
    await service.resend_activation_code(request.email, request.password)

    return ApiResponse(
        status="success",
        data={"message": "Activation code sent successfully"}
    )


@router.get(
    "/health",
    response_model=ApiResponse,
    summary="Health check endpoint"
)
async def health_check() -> ApiResponse:
    """
    Health check endpoint.

    Returns the health status of the user service.
    """
    return ApiResponse(
        status="success",
        data={"service": "user_registration", "status": "healthy"}
    )