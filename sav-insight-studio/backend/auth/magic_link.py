"""
Magic link authentication - passwordless login via email
"""
import uuid
from datetime import datetime, timedelta
from typing import Optional, Tuple
from sqlalchemy.orm import Session

from .password import generate_token, hash_token, verify_token_hash

# Magic link expiration time in minutes
MAGIC_LINK_EXPIRE_MINUTES = 15


def create_magic_link(
    db: Session,
    email: str,
    base_url: str = "",
) -> Tuple[str, str]:
    """
    Create a magic link for passwordless authentication.
    
    Args:
        db: Database session
        email: User's email address
        base_url: Base URL for the magic link (e.g., https://app.example.com)
    
    Returns:
        Tuple of (full_magic_link_url, plain_token)
    """
    from models import MagicLink
    
    # Generate a secure random token
    token = generate_token(32)
    token_hash = hash_token(token)
    
    # Calculate expiration time
    expires_at = datetime.utcnow() + timedelta(minutes=MAGIC_LINK_EXPIRE_MINUTES)
    
    # Create magic link record
    magic_link = MagicLink(
        id=str(uuid.uuid4()),
        email=email.lower().strip(),
        token_hash=token_hash,
        expires_at=expires_at,
        used=False,
    )
    
    db.add(magic_link)
    db.commit()
    
    # Construct the magic link URL
    magic_link_url = f"{base_url}/#/verify?token={token}&email={email}"
    
    return magic_link_url, token


def verify_magic_link(
    db: Session,
    email: str,
    token: str,
) -> Tuple[bool, Optional[str]]:
    """
    Verify a magic link token.
    
    Args:
        db: Database session
        email: User's email address
        token: Magic link token from URL
    
    Returns:
        Tuple of (is_valid, error_message)
        - (True, None) if valid
        - (False, "error message") if invalid
    """
    from models import MagicLink
    
    email = email.lower().strip()
    token_hash = hash_token(token)
    
    # Find the magic link
    magic_link = db.query(MagicLink).filter(
        MagicLink.email == email,
        MagicLink.token_hash == token_hash,
    ).first()
    
    if not magic_link:
        return False, "Invalid or expired magic link"
    
    # Check if already used
    if magic_link.used:
        return False, "This magic link has already been used"
    
    # Check expiration
    if datetime.utcnow() > magic_link.expires_at:
        return False, "This magic link has expired"
    
    # Mark as used
    magic_link.used = True
    magic_link.used_at = datetime.utcnow()
    db.commit()
    
    return True, None


def cleanup_expired_magic_links(db: Session) -> int:
    """
    Clean up expired and used magic links.
    Should be called periodically (e.g., daily cron job).
    
    Args:
        db: Database session
    
    Returns:
        Number of deleted records
    """
    from models import MagicLink
    
    # Delete links that are either:
    # - Expired (regardless of used status)
    # - Used and older than 1 day
    cutoff_time = datetime.utcnow() - timedelta(days=1)
    
    deleted = db.query(MagicLink).filter(
        (MagicLink.expires_at < datetime.utcnow()) |
        ((MagicLink.used == True) & (MagicLink.created_at < cutoff_time))
    ).delete(synchronize_session=False)
    
    db.commit()
    
    return deleted

