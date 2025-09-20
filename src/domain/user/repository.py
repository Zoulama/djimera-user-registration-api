import logging
from typing import Optional, List
from datetime import datetime
import bcrypt

from src.infrastructure.database.postgresql_client import PostgreSQLClient
from src.domain.user.entities import User, ActivationCode, UserStatus
from src.domain.exceptions import (
    DatabaseException,
    UserNotFoundException,
    EmailAlreadyExistsException
)

logger = logging.getLogger(__name__)


class UserRepository:
    """Repository for user-related database operations."""

    def __init__(self, db_client: PostgreSQLClient):
        self.db_client = db_client

    async def create_user(self, email: str, password: str) -> User:
        """
        Create a new user in the database.
        
        Args:
            email: User email
            password: Plain text password (will be hashed)
            
        Returns:
            User: Created user entity
            
        Raises:
            EmailAlreadyExistsException: If email already exists
            DatabaseException: For database errors
        """
        # Check if email already exists
        existing_user = await self.get_user_by_email(email, raise_if_not_found=False)
        if existing_user:
            raise EmailAlreadyExistsException()

        # Hash password
        password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt(rounds=12)).decode('utf-8')

        # Create user entity
        user = User(email=email, password_hash=password_hash)

        # Insert into database
        query = """
            INSERT INTO users (user_id, email, password_hash, status, created_at, updated_at)
            VALUES ($1, $2, $3, $4, $5, $6)
        """
        
        try:
            await self.db_client.execute_query(
                query,
                user.user_id,
                user.email,
                user.password_hash,
                user.status.value,
                user.created_at,
                user.updated_at
            )
            logger.info(f"User created successfully: {user.user_id}")
            return user
        except Exception as e:
            logger.error(f"Failed to create user: {str(e)}")
            raise DatabaseException(f"Failed to create user: {str(e)}")

    async def get_user_by_email(self, email: str, raise_if_not_found: bool = True) -> Optional[User]:
        """
        Get user by email address.
        
        Args:
            email: User email
            raise_if_not_found: Whether to raise exception if not found
            
        Returns:
            User or None
            
        Raises:
            UserNotFoundException: If user not found and raise_if_not_found is True
        """
        query = """
            SELECT user_id, email, password_hash, status, created_at, updated_at, activated_at
            FROM users WHERE email = $1
        """
        
        try:
            result = await self.db_client.execute_query(query, email, fetch='one')
            
            if not result:
                if raise_if_not_found:
                    raise UserNotFoundException()
                return None
            
            return User(
                user_id=str(result['user_id']),
                email=result['email'],
                password_hash=result['password_hash'],
                status=UserStatus(result['status']),
                created_at=result['created_at'],
                updated_at=result['updated_at'],
                activated_at=result['activated_at']
            )
        except UserNotFoundException:
            raise
        except Exception as e:
            logger.error(f"Failed to get user by email: {str(e)}")
            raise DatabaseException(f"Failed to get user by email: {str(e)}")

    async def get_user_by_id(self, user_id: str) -> User:
        """
        Get user by ID.
        
        Args:
            user_id: User ID
            
        Returns:
            User
            
        Raises:
            UserNotFoundException: If user not found
        """
        query = """
            SELECT user_id, email, password_hash, status, created_at, updated_at, activated_at
            FROM users WHERE user_id = $1
        """
        
        try:
            result = await self.db_client.execute_query(query, user_id, fetch='one')
            
            if not result:
                raise UserNotFoundException()
            
            return User(
                user_id=str(result['user_id']),
                email=result['email'],
                password_hash=result['password_hash'],
                status=UserStatus(result['status']),
                created_at=result['created_at'],
                updated_at=result['updated_at'],
                activated_at=result['activated_at']
            )
        except UserNotFoundException:
            raise
        except Exception as e:
            logger.error(f"Failed to get user by ID: {str(e)}")
            raise DatabaseException(f"Failed to get user by ID: {str(e)}")

    async def update_user_status(self, user_id: str, status: UserStatus, activated_at: Optional[datetime] = None) -> User:
        """
        Update user status.
        
        Args:
            user_id: User ID
            status: New status
            activated_at: Activation timestamp (for ACTIVE status)
            
        Returns:
            Updated user
        """
        query = """
            UPDATE users 
            SET status = $2, updated_at = $3, activated_at = $4
            WHERE user_id = $1
        """
        
        try:
            updated_at = datetime.utcnow()
            await self.db_client.execute_query(
                query, 
                user_id, 
                status.value, 
                updated_at,
                activated_at
            )
            
            # Return updated user
            return await self.get_user_by_id(user_id)
        except Exception as e:
            logger.error(f"Failed to update user status: {str(e)}")
            raise DatabaseException(f"Failed to update user status: {str(e)}")

    async def verify_password(self, user: User, password: str) -> bool:
        """
        Verify user password.
        
        Args:
            user: User entity
            password: Plain text password
            
        Returns:
            True if password is correct
        """
        try:
            return bcrypt.checkpw(password.encode('utf-8'), user.password_hash.encode('utf-8'))
        except Exception as e:
            logger.error(f"Password verification failed: {str(e)}")
            return False


class ActivationCodeRepository:
    """Repository for activation code operations."""

    def __init__(self, db_client: PostgreSQLClient):
        self.db_client = db_client

    async def create_activation_code(self, activation_code: ActivationCode) -> ActivationCode:
        """
        Create activation code in database.
        
        Args:
            activation_code: ActivationCode entity
            
        Returns:
            Created activation code
        """
        # First, invalidate any existing unused codes for this user
        await self.invalidate_user_codes(activation_code.user_id)
        
        query = """
            INSERT INTO activation_codes (user_id, code, expires_at, created_at, is_used)
            VALUES ($1, $2, $3, $4, $5)
        """
        
        try:
            await self.db_client.execute_query(
                query,
                activation_code.user_id,
                activation_code.code,
                activation_code.expires_at,
                activation_code.created_at,
                activation_code.is_used
            )
            logger.info(f"Activation code created for user: {activation_code.user_id}")
            return activation_code
        except Exception as e:
            logger.error(f"Failed to create activation code: {str(e)}")
            raise DatabaseException(f"Failed to create activation code: {str(e)}")

    async def get_activation_code(self, user_id: str, code: str) -> Optional[ActivationCode]:
        """
        Get activation code by user ID and code.
        
        Args:
            user_id: User ID
            code: Activation code
            
        Returns:
            ActivationCode or None
        """
        query = """
            SELECT user_id, code, expires_at, created_at, used_at, is_used
            FROM activation_codes 
            WHERE user_id = $1 AND code = $2
        """
        
        try:
            result = await self.db_client.execute_query(query, user_id, code, fetch='one')
            
            if not result:
                return None
            
            return ActivationCode(
                user_id=str(result['user_id']),
                code=result['code'],
                expires_at=result['expires_at'],
                created_at=result['created_at'],
                used_at=result['used_at'],
                is_used=result['is_used']
            )
        except Exception as e:
            logger.error(f"Failed to get activation code: {str(e)}")
            raise DatabaseException(f"Failed to get activation code: {str(e)}")

    async def mark_code_as_used(self, user_id: str, code: str) -> None:
        """
        Mark activation code as used.
        
        Args:
            user_id: User ID
            code: Activation code
        """
        query = """
            UPDATE activation_codes 
            SET is_used = TRUE, used_at = $3
            WHERE user_id = $1 AND code = $2
        """
        
        try:
            used_at = datetime.utcnow()
            await self.db_client.execute_query(query, user_id, code, used_at)
            logger.info(f"Activation code marked as used: {user_id}")
        except Exception as e:
            logger.error(f"Failed to mark activation code as used: {str(e)}")
            raise DatabaseException(f"Failed to mark activation code as used: {str(e)}")

    async def invalidate_user_codes(self, user_id: str) -> None:
        """
        Invalidate all unused codes for a user.
        
        Args:
            user_id: User ID
        """
        query = """
            UPDATE activation_codes 
            SET is_used = TRUE, used_at = $2
            WHERE user_id = $1 AND is_used = FALSE
        """
        
        try:
            used_at = datetime.utcnow()
            await self.db_client.execute_query(query, user_id, used_at)
        except Exception as e:
            logger.error(f"Failed to invalidate user codes: {str(e)}")
            raise DatabaseException(f"Failed to invalidate user codes: {str(e)}")

    async def cleanup_expired_codes(self) -> int:
        """
        Clean up expired activation codes.
        
        Returns:
            Number of codes cleaned up
        """
        query = """
            DELETE FROM activation_codes 
            WHERE expires_at < NOW() OR is_used = TRUE
        """
        
        try:
            result = await self.db_client.execute_query(query)
            # Extract number from result string like "DELETE 5"
            count = int(result.split()[-1]) if result and result.split()[-1].isdigit() else 0
            logger.info(f"Cleaned up {count} expired activation codes")
            return count
        except Exception as e:
            logger.error(f"Failed to cleanup expired codes: {str(e)}")
            raise DatabaseException(f"Failed to cleanup expired codes: {str(e)}")