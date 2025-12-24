"""
Token and password hashing utilities using SHA256.
For production, consider using bcrypt or argon2 for passwords.
"""
import hashlib
import secrets
import hmac
from typing import Tuple


def generate_token(length: int = 32) -> str:
    """
    Generate a cryptographically secure random token.
    
    Args:
        length: Number of bytes (will be hex encoded, so output is 2x length)
    
    Returns:
        Hex-encoded random token
    """
    return secrets.token_hex(length)


def hash_token(token: str) -> str:
    """
    Hash a token using SHA256.
    Used for storing magic link tokens and session tokens in the database.
    
    Args:
        token: Plain text token
    
    Returns:
        SHA256 hash of the token
    """
    return hashlib.sha256(token.encode()).hexdigest()


def hash_password(password: str) -> str:
    """
    Hash a password using SHA256.
    For production, consider using bcrypt or argon2.
    
    Args:
        password: Plain text password
    
    Returns:
        SHA256 hash of the password
    """
    return hashlib.sha256(password.encode()).hexdigest()


def verify_password(password: str, password_hash: str) -> bool:
    """
    Verify a password against its hash using constant-time comparison.
    
    Args:
        password: Plain text password to verify
        password_hash: Stored hash to compare against
    
    Returns:
        True if password matches hash, False otherwise
    """
    computed_hash = hash_password(password)
    return hmac.compare_digest(computed_hash, password_hash)


def verify_token_hash(token: str, token_hash: str) -> bool:
    """
    Verify a token against its hash using constant-time comparison.
    
    Args:
        token: Plain text token to verify
        token_hash: Stored hash to compare against
    
    Returns:
        True if token matches hash, False otherwise
    """
    computed_hash = hash_token(token)
    return hmac.compare_digest(computed_hash, token_hash)


def generate_csrf_token() -> str:
    """
    Generate a CSRF token.
    
    Returns:
        Random CSRF token
    """
    return secrets.token_urlsafe(32)


def verify_csrf_token(token: str, expected: str) -> bool:
    """
    Verify CSRF token using constant-time comparison.
    
    Args:
        token: Token from request
        expected: Expected token from session
    
    Returns:
        True if tokens match, False otherwise
    """
    if not token or not expected:
        return False
    return hmac.compare_digest(token, expected)

