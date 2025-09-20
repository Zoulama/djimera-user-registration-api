import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, MagicMock
from datetime import datetime, timedelta

from src.domain.user.entities import User, ActivationCode, UserStatus, utc_now
from src.domain.user.service import UserService
from src.domain.exceptions import (
    EmailAlreadyExistsException,
    UserNotFoundException,
    InvalidActivationCodeException,
    ActivationCodeExpiredException,
    UserAlreadyActivatedException,
    AuthenticationException,
    ValidationException
)


@pytest.fixture
def mock_user_repository():
    return AsyncMock()


@pytest.fixture
def mock_activation_code_repository():
    return AsyncMock()


@pytest.fixture
def mock_email_service():
    return AsyncMock()


@pytest.fixture
def user_service(mock_user_repository, mock_activation_code_repository, mock_email_service):
    return UserService(
        user_repository=mock_user_repository,
        activation_code_repository=mock_activation_code_repository,
        email_service=mock_email_service
    )


@pytest.fixture
def sample_user():
    return User(
        user_id="test-user-id",
        email="test@example.com",
        password_hash="hashed_password",
        status=UserStatus.PENDING,
        created_at=utc_now(),
        updated_at=utc_now()
    )


@pytest.fixture
def sample_active_user():
    return User(
        user_id="test-user-id",
        email="test@example.com", 
        password_hash="hashed_password",
        status=UserStatus.ACTIVE,
        created_at=utc_now(),
        updated_at=utc_now(),
        activated_at=utc_now()
    )


@pytest.fixture
def sample_activation_code():
    return ActivationCode(
        user_id="test-user-id",
        code="1234",
        expires_at=utc_now() + timedelta(minutes=1),
        created_at=utc_now()
    )


class TestUserRegistration:
    """Test user registration functionality."""

    @pytest.mark.asyncio
    async def test_register_user_success(self, user_service, mock_user_repository, sample_user):
        """Test successful user registration."""
        # Setup
        mock_user_repository.create_user.return_value = sample_user
        
        # Execute
        result = await user_service.register_user("test@example.com", "password123")
        
        # Assert
        assert result.email == "test@example.com"
        assert result.status == UserStatus.PENDING
        mock_user_repository.create_user.assert_called_once()

    @pytest.mark.asyncio
    async def test_register_user_invalid_password(self, user_service):
        """Test user registration with invalid password."""
        with pytest.raises(ValidationException):
            await user_service.register_user("test@example.com", "123")  # Too short

    @pytest.mark.asyncio
    async def test_register_user_email_exists(self, user_service, mock_user_repository):
        """Test user registration with existing email."""
        # Setup
        mock_user_repository.create_user.side_effect = EmailAlreadyExistsException()
        
        # Execute & Assert
        with pytest.raises(EmailAlreadyExistsException):
            await user_service.register_user("test@example.com", "password123")


class TestUserActivation:
    """Test user activation functionality."""

    @pytest.mark.asyncio
    async def test_activate_user_success(
        self, 
        user_service, 
        mock_user_repository, 
        mock_activation_code_repository,
        sample_user,
        sample_active_user,
        sample_activation_code
    ):
        """Test successful user activation."""
        # Setup
        mock_user_repository.get_user_by_email.return_value = sample_user
        mock_user_repository.verify_password.return_value = True
        mock_activation_code_repository.get_activation_code.return_value = sample_activation_code
        mock_user_repository.update_user_status.return_value = sample_active_user
        
        # Execute
        result = await user_service.activate_user("test@example.com", "password123", "1234")
        
        # Assert
        assert result.status == UserStatus.ACTIVE
        mock_activation_code_repository.mark_code_as_used.assert_called_once()

    @pytest.mark.asyncio
    async def test_activate_user_invalid_credentials(self, user_service, mock_user_repository):
        """Test activation with invalid credentials."""
        # Setup
        mock_user_repository.get_user_by_email.return_value = None
        
        # Execute & Assert
        with pytest.raises(AuthenticationException):
            await user_service.activate_user("test@example.com", "wrong_password", "1234")

    @pytest.mark.asyncio
    async def test_activate_user_already_active(
        self,
        user_service,
        mock_user_repository,
        sample_active_user
    ):
        """Test activation of already active user."""
        # Setup
        mock_user_repository.get_user_by_email.return_value = sample_active_user
        mock_user_repository.verify_password.return_value = True
        
        # Execute & Assert
        with pytest.raises(UserAlreadyActivatedException):
            await user_service.activate_user("test@example.com", "password123", "1234")

    @pytest.mark.asyncio
    async def test_activate_user_invalid_code(
        self,
        user_service,
        mock_user_repository,
        mock_activation_code_repository,
        sample_user
    ):
        """Test activation with invalid code."""
        # Setup
        mock_user_repository.get_user_by_email.return_value = sample_user
        mock_user_repository.verify_password.return_value = True
        mock_activation_code_repository.get_activation_code.return_value = None
        
        # Execute & Assert
        with pytest.raises(InvalidActivationCodeException):
            await user_service.activate_user("test@example.com", "password123", "9999")

    @pytest.mark.asyncio
    async def test_activate_user_expired_code(
        self,
        user_service,
        mock_user_repository,
        mock_activation_code_repository,
        sample_user
    ):
        """Test activation with expired code."""
        # Setup
        expired_code = ActivationCode(
            user_id="test-user-id",
            code="1234",
            expires_at=utc_now() - timedelta(minutes=1),  # Expired
            created_at=utc_now()
        )
        
        mock_user_repository.get_user_by_email.return_value = sample_user
        mock_user_repository.verify_password.return_value = True
        mock_activation_code_repository.get_activation_code.return_value = expired_code
        
        # Execute & Assert
        with pytest.raises(ActivationCodeExpiredException):
            await user_service.activate_user("test@example.com", "password123", "1234")


class TestResendActivationCode:
    """Test resend activation code functionality."""

    @pytest.mark.asyncio
    async def test_resend_activation_code_success(
        self,
        user_service,
        mock_user_repository,
        sample_user
    ):
        """Test successful resend of activation code."""
        # Setup
        mock_user_repository.get_user_by_email.return_value = sample_user
        mock_user_repository.verify_password.return_value = True
        
        # Execute
        await user_service.resend_activation_code("test@example.com", "password123")
        
        # Assert - should not raise exception
        assert True

    @pytest.mark.asyncio
    async def test_resend_activation_code_already_active(
        self,
        user_service,
        mock_user_repository,
        sample_active_user
    ):
        """Test resend activation code for already active user."""
        # Setup
        mock_user_repository.get_user_by_email.return_value = sample_active_user
        mock_user_repository.verify_password.return_value = True
        
        # Execute & Assert
        with pytest.raises(UserAlreadyActivatedException):
            await user_service.resend_activation_code("test@example.com", "password123")


class TestPasswordValidation:
    """Test password validation."""

    @pytest.mark.asyncio
    async def test_valid_passwords(self, user_service, mock_user_repository, sample_user):
        """Test various valid password formats."""
        valid_passwords = [
            "password123",
            "mySecure1",
            "test12345",
            "abcdefgh1"
        ]
        
        mock_user_repository.create_user.return_value = sample_user
        
        for password in valid_passwords:
            await user_service.register_user("test@example.com", password)

    @pytest.mark.asyncio
    async def test_invalid_passwords(self, user_service):
        """Test various invalid password formats."""
        invalid_passwords = [
            "123",           # Too short
            "1234567",       # Too short
            "password",      # No numbers
            "12345678",      # No letters
            "",              # Empty
        ]
        
        for password in invalid_passwords:
            with pytest.raises(ValidationException):
                await user_service.register_user("test@example.com", password)