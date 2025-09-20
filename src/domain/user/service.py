import logging
from datetime import datetime
from typing import Optional

from src.domain.user.entities import User, ActivationCode, UserStatus, PasswordValidator, utc_now
from src.domain.user.repository import UserRepository, ActivationCodeRepository
from src.infrastructure.email.email_service import EmailService
from src.domain.exceptions import (
    UserNotFoundException,
    EmailAlreadyExistsException,
    InvalidActivationCodeException,
    ActivationCodeExpiredException,
    UserAlreadyActivatedException,
    AuthenticationException,
    ValidationException
)

logger = logging.getLogger(__name__)


class UserService:
    """Service layer for user registration and activation operations."""

    def __init__(
            self,
            user_repository: UserRepository,
            activation_code_repository: ActivationCodeRepository,
            email_service: EmailService
    ):
        self.user_repository = user_repository
        self.activation_code_repository = activation_code_repository
        self.email_service = email_service

    async def register_user(self, email: str, password: str) -> User:
        """
        Register a new user.
        
        Args:
            email: User email address
            password: User password
            
        Returns:
            User: Created user entity
            
        Raises:
            ValidationException: If email or password is invalid
            EmailAlreadyExistsException: If email already exists
        """
        logger.info(f"Starting user registration for email: {email}")

        # Validate password
        PasswordValidator.validate(password)

        # Create user in database
        user = await self.user_repository.create_user(email, password)

        # Generate and send activation code
        await self._generate_and_send_activation_code(user)

        logger.info(f"User registered successfully: {user.user_id}")
        return user

    async def activate_user(self, email: str, password: str, activation_code: str) -> User:
        """
        Activate user account with activation code.
        
        Args:
            email: User email address
            password: User password (for Basic Auth)
            activation_code: 4-digit activation code
            
        Returns:
            User: Activated user entity
            
        Raises:
            AuthenticationException: If credentials are invalid
            UserNotFoundException: If user not found
            UserAlreadyActivatedException: If user is already active
            InvalidActivationCodeException: If code is invalid
            ActivationCodeExpiredException: If code is expired
        """
        logger.info(f"Starting user activation for email: {email}")

        # Authenticate user with Basic Auth
        user = await self._authenticate_user(email, password)

        # Check if user is already activated
        if user.is_active():
            raise UserAlreadyActivatedException()

        # Verify activation code
        await self._verify_activation_code(user.user_id, activation_code)

        # Activate user
        activated_user = await self.user_repository.update_user_status(
            user.user_id,
            UserStatus.ACTIVE,
            utc_now()
        )

        # Mark activation code as used
        await self.activation_code_repository.mark_code_as_used(user.user_id, activation_code)

        logger.info(f"User activated successfully: {user.user_id}")
        return activated_user

    async def resend_activation_code(self, email: str, password: str) -> None:
        """
        Resend activation code to user.
        
        Args:
            email: User email address
            password: User password (for Basic Auth)
            
        Raises:
            AuthenticationException: If credentials are invalid
            UserNotFoundException: If user not found
            UserAlreadyActivatedException: If user is already active
        """
        logger.info(f"Resending activation code for email: {email}")

        # Authenticate user
        user = await self._authenticate_user(email, password)

        # Check if user is already activated
        if user.is_active():
            raise UserAlreadyActivatedException()

        # Generate and send new activation code
        await self._generate_and_send_activation_code(user)

        logger.info(f"Activation code resent successfully for user: {user.user_id}")

    async def get_user_by_email(self, email: str) -> Optional[User]:
        """
        Get user by email address.
        
        Args:
            email: User email address
            
        Returns:
            User or None
        """
        return await self.user_repository.get_user_by_email(email, raise_if_not_found=False)

    async def _authenticate_user(self, email: str, password: str) -> User:
        """
        Authenticate user with email and password.
        
        Args:
            email: User email
            password: User password
            
        Returns:
            User: Authenticated user
            
        Raises:
            AuthenticationException: If authentication fails
            UserNotFoundException: If user not found
        """
        try:
            # Get user by email
            user = await self.user_repository.get_user_by_email(email)

            # Check if user exists
            if user is None:
                raise AuthenticationException()

            # Verify password
            if not await self.user_repository.verify_password(user, password):
                raise AuthenticationException()

            return user

        except UserNotFoundException:
            # Don't reveal whether user exists or not
            raise AuthenticationException()

    async def _generate_and_send_activation_code(self, user: User) -> None:
        """
        Generate and send activation code to user.
        
        Args:
            user: User entity
        """
        # Generate activation code
        activation_code = ActivationCode.generate_for_user(user.user_id)

        # Save activation code to database
        await self.activation_code_repository.create_activation_code(activation_code)

        # Send activation code via email service
        await self.email_service.send_activation_code(
            email=user.email,
            activation_code=activation_code.code,
            user_id=user.user_id
        )

    async def _verify_activation_code(self, user_id: str, code: str) -> None:
        """
        Verify activation code.
        
        Args:
            user_id: User ID
            code: Activation code to verify
            
        Raises:
            InvalidActivationCodeException: If code is invalid
            ActivationCodeExpiredException: If code is expired
        """
        # Get activation code from database
        activation_code = await self.activation_code_repository.get_activation_code(user_id, code)

        if not activation_code:
            raise InvalidActivationCodeException()

        # Check if code is already used
        if activation_code.is_used:
            raise InvalidActivationCodeException()

        # Check if code is expired
        if activation_code.is_expired():
            raise ActivationCodeExpiredException()

    async def cleanup_expired_codes(self) -> int:
        """
        Clean up expired activation codes.
        
        Returns:
            Number of codes cleaned up
        """
        try:
            count = await self.activation_code_repository.cleanup_expired_codes()
            logger.info(f"Cleaned up {count} expired activation codes")
            return count
        except Exception as e:
            logger.error(f"Failed to cleanup expired codes: {str(e)}")
            return 0

    async def get_user_stats(self) -> dict:
        """
        Get user registration statistics.
        
        Returns:
            Dictionary with user statistics
        """
        # This would require additional repository methods
        # For now, return placeholder data
        return {
            "total_users": 0,
            "active_users": 0,
            "pending_users": 0
        }
