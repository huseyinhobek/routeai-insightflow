"""
JWT Token handling for authentication
"""
import jwt
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
import os

# Configuration from environment
JWT_SECRET = os.getenv("JWT_SECRET", "dev-secret-change-in-production-min-32-chars!")
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
JWT_EXPIRE_HOURS = int(os.getenv("JWT_EXPIRE_HOURS", "168"))  # 7 days default


class TokenData:
    """Decoded token data structure"""
    def __init__(
        self,
        user_id: str,
        email: str,
        org_id: Optional[str],
        role: str,
        permissions: list,
        exp: datetime,
        iat: datetime,
    ):
        self.user_id = user_id
        self.email = email
        self.org_id = org_id
        self.role = role
        self.permissions = permissions
        self.exp = exp
        self.iat = iat


def create_access_token(
    user_id: str,
    email: str,
    org_id: Optional[str],
    role: str,
    permissions: list,
    expires_delta: Optional[timedelta] = None,
) -> str:
    """
    Create a JWT access token.
    
    Args:
        user_id: User's unique identifier
        email: User's email address
        org_id: Organization ID (None for super_admin)
        role: User's role
        permissions: List of permission strings
        expires_delta: Optional custom expiration time
    
    Returns:
        Encoded JWT token string
    """
    now = datetime.utcnow()
    
    if expires_delta:
        expire = now + expires_delta
    else:
        expire = now + timedelta(hours=JWT_EXPIRE_HOURS)
    
    payload = {
        "sub": user_id,
        "email": email,
        "org_id": org_id,
        "role": role,
        "permissions": permissions,
        "exp": expire,
        "iat": now,
        "type": "access",
    }
    
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def verify_token(token: str) -> bool:
    """
    Verify if a token is valid (not expired, correct signature).
    
    Args:
        token: JWT token string
    
    Returns:
        True if valid, False otherwise
    """
    try:
        jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return True
    except jwt.ExpiredSignatureError:
        return False
    except jwt.InvalidTokenError:
        return False


def decode_token(token: str) -> Optional[TokenData]:
    """
    Decode and validate a JWT token.
    
    Args:
        token: JWT token string
    
    Returns:
        TokenData object if valid, None otherwise
    """
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        
        return TokenData(
            user_id=payload.get("sub"),
            email=payload.get("email"),
            org_id=payload.get("org_id"),
            role=payload.get("role", "viewer"),
            permissions=payload.get("permissions", []),
            exp=datetime.fromtimestamp(payload.get("exp", 0)),
            iat=datetime.fromtimestamp(payload.get("iat", 0)),
        )
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None


def create_refresh_token(user_id: str) -> str:
    """
    Create a refresh token with longer expiration.
    
    Args:
        user_id: User's unique identifier
    
    Returns:
        Encoded refresh token string
    """
    now = datetime.utcnow()
    expire = now + timedelta(days=30)  # 30 days for refresh token
    
    payload = {
        "sub": user_id,
        "exp": expire,
        "iat": now,
        "type": "refresh",
    }
    
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def decode_refresh_token(token: str) -> Optional[str]:
    """
    Decode a refresh token and return user_id if valid.
    
    Args:
        token: Refresh token string
    
    Returns:
        User ID if valid, None otherwise
    """
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        
        if payload.get("type") != "refresh":
            return None
        
        return payload.get("sub")
    except jwt.InvalidTokenError:
        return None

