import base64
import binascii
from typing import Tuple, Optional
from fastapi import HTTPException, Depends
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from starlette.status import HTTP_401_UNAUTHORIZED

from src.domain.exceptions import AuthenticationException

security = HTTPBasic()


def decode_basic_auth(auth_header: str) -> Tuple[str, str]:
    """
    Decode Basic Auth header.
    
    Args:
        auth_header: Authorization header value
        
    Returns:
        Tuple of (username, password)
        
    Raises:
        AuthenticationException: If header is invalid
    """
    try:
        if not auth_header.startswith("Basic "):
            raise AuthenticationException()

        # Remove "Basic " prefix
        encoded_credentials = auth_header[6:]

        # Decode base64
        decoded_bytes = base64.b64decode(encoded_credentials)
        decoded_str = decoded_bytes.decode('utf-8')

        # Split username:password
        if ':' not in decoded_str:
            raise AuthenticationException()

        username, password = decoded_str.split(':', 1)
        return username, password

    except (binascii.Error, UnicodeDecodeError, ValueError):
        raise AuthenticationException()


async def get_basic_auth_credentials(credentials: HTTPBasicCredentials = Depends(security)) -> Tuple[str, str]:
    """
    Extract credentials from FastAPI HTTPBasicCredentials.
    
    Args:
        credentials: FastAPI Basic Auth credentials
        
    Returns:
        Tuple of (email, password)
        
    Raises:
        HTTPException: If credentials are missing or invalid
    """
    if not credentials.username or not credentials.password:
        raise HTTPException(
            status_code=HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Basic"},
        )

    return credentials.username, credentials.password


def create_basic_auth_header(username: str, password: str) -> str:
    """
    Create Basic Auth header value.
    
    Args:
        username: Username (email)
        password: Password
        
    Returns:
        Authorization header value
    """
    credentials = f"{username}:{password}"
    encoded_credentials = base64.b64encode(credentials.encode('utf-8')).decode('ascii')
    return f"Basic {encoded_credentials}"
