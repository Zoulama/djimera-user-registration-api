import re
import uuid
import random
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Optional, Dict, Any
from dataclasses import dataclass, field

from src.domain.exceptions import ValidationException
from src.schemas.common.errors import DmErrorCode, ErrorMessage


def utc_now() -> datetime:
    """Get current UTC time as timezone-aware datetime."""
    return datetime.now(timezone.utc)


class UserStatus(str, Enum):
    PENDING = "PENDING"
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"
    SUSPENDED = "SUSPENDED"


@dataclass
class User:
    """User domain entity."""
    
    email: str
    password_hash: str
    status: UserStatus = UserStatus.PENDING
    user_id: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    activated_at: Optional[datetime] = None
    
    def __post_init__(self):
        """Validate user data after initialization."""
        self.validate_email()
        if not self.user_id:
            self.user_id = str(uuid.uuid4())
        if not self.created_at:
            self.created_at = utc_now()
        self.updated_at = utc_now()
    
    def validate_email(self) -> None:
        """Validate email format."""
        email_regex = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not self.email or not re.match(email_regex, self.email):
            raise ValidationException(
                err_message=ErrorMessage.MESSAGE_REG_0001[0],
                err_handling=ErrorMessage.MESSAGE_REG_0001[1],
                err_code=DmErrorCode.DM_REG_0001.value
            )
    
    def activate(self) -> None:
        """Activate the user account."""
        self.status = UserStatus.ACTIVE
        self.activated_at = utc_now()
        self.updated_at = utc_now()
    
    def is_active(self) -> bool:
        """Check if user is active."""
        return self.status == UserStatus.ACTIVE
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert user to dictionary."""
        return {
            'user_id': self.user_id,
            'email': self.email,
            'password_hash': self.password_hash,
            'status': self.status.value,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'activated_at': self.activated_at.isoformat() if self.activated_at else None,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'User':
        """Create user from dictionary."""
        return cls(
            user_id=data.get('user_id'),
            email=data['email'],
            password_hash=data['password_hash'],
            status=UserStatus(data.get('status', UserStatus.PENDING.value)),
            created_at=datetime.fromisoformat(data['created_at']) if data.get('created_at') else None,
            updated_at=datetime.fromisoformat(data['updated_at']) if data.get('updated_at') else None,
            activated_at=datetime.fromisoformat(data['activated_at']) if data.get('activated_at') else None,
        )
    
    @classmethod
    def from_db_row(cls, row: tuple) -> 'User':
        """Create user from database row."""
        return cls(
            user_id=row[0],
            email=row[1],
            password_hash=row[2],
            status=UserStatus(row[3]),
            created_at=row[4],
            updated_at=row[5],
            activated_at=row[6]
        )


@dataclass
class ActivationCode:
    """Activation code domain entity."""
    
    user_id: str
    code: str
    expires_at: datetime
    created_at: Optional[datetime] = None
    used_at: Optional[datetime] = None
    is_used: bool = False
    
    def __post_init__(self):
        """Initialize activation code."""
        if not self.created_at:
            self.created_at = utc_now()
    
    @classmethod
    def generate_for_user(cls, user_id: str) -> 'ActivationCode':
        """Generate a new activation code for user."""
        code = f"{random.randint(1000, 9999):04d}"
        expires_at = utc_now() + timedelta(minutes=1)
        
        return cls(
            user_id=user_id,
            code=code,
            expires_at=expires_at
        )
    
    def is_valid(self) -> bool:
        """Check if activation code is valid."""
        return (
            not self.is_used and 
            utc_now() < self.expires_at
        )
    
    def is_expired(self) -> bool:
        """Check if activation code is expired."""
        return utc_now() >= self.expires_at
    
    def mark_as_used(self) -> None:
        """Mark activation code as used."""
        self.is_used = True
        self.used_at = utc_now()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert activation code to dictionary."""
        return {
            'user_id': self.user_id,
            'code': self.code,
            'expires_at': self.expires_at.isoformat(),
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'used_at': self.used_at.isoformat() if self.used_at else None,
            'is_used': self.is_used,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ActivationCode':
        """Create activation code from dictionary."""
        return cls(
            user_id=data['user_id'],
            code=data['code'],
            expires_at=datetime.fromisoformat(data['expires_at']),
            created_at=datetime.fromisoformat(data['created_at']) if data.get('created_at') else None,
            used_at=datetime.fromisoformat(data['used_at']) if data.get('used_at') else None,
            is_used=data.get('is_used', False),
        )
    
    @classmethod
    def from_db_row(cls, row: tuple) -> 'ActivationCode':
        """Create activation code from database row."""
        return cls(
            user_id=row[0],
            code=row[1],
            expires_at=row[2],
            created_at=row[3],
            used_at=row[4],
            is_used=row[5]
        )


class PasswordValidator:
    """Password validation utility."""
    
    @staticmethod
    def validate(password: str) -> None:
        """Validate password strength."""
        if not password or len(password) < 8:
            raise ValidationException(
                err_message=ErrorMessage.MESSAGE_REG_0002[0],
                err_handling=ErrorMessage.MESSAGE_REG_0002[1],
                err_code=DmErrorCode.DM_REG_0002.value
            )
        
        has_letter = any(c.isalpha() for c in password)
        has_number = any(c.isdigit() for c in password)
        
        if not (has_letter and has_number):
            raise ValidationException(
                err_message=ErrorMessage.MESSAGE_REG_0002[0],
                err_handling=ErrorMessage.MESSAGE_REG_0002[1],
                err_code=DmErrorCode.DM_REG_0002.value
            )