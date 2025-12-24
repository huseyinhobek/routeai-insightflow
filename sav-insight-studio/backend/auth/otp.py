"""
OTP (One-Time Password) authentication - 6-digit code via email
"""
import uuid
import random
import string
from datetime import datetime, timedelta
from typing import Optional, Tuple
from sqlalchemy.orm import Session

from .password import hash_token, verify_token_hash

# OTP expiration time in minutes
OTP_EXPIRE_MINUTES = 10


def generate_otp_code(length: int = 6) -> str:
    """
    Generate a random numeric OTP code.
    
    Args:
        length: Number of digits (default 6)
    
    Returns:
        Numeric string OTP code
    """
    return ''.join(random.choices(string.digits, k=length))


def create_otp(
    db: Session,
    email: str,
) -> Tuple[str, str]:
    """
    Create an OTP code for email verification.
    
    Args:
        db: Database session
        email: User's email address
    
    Returns:
        Tuple of (otp_code, otp_id)
    """
    from models import MagicLink  # Reuse MagicLink table for OTP
    
    # Generate a 6-digit OTP code
    otp_code = generate_otp_code(6)
    otp_hash = hash_token(otp_code)
    
    # Calculate expiration time
    expires_at = datetime.utcnow() + timedelta(minutes=OTP_EXPIRE_MINUTES)
    
    # Invalidate any existing unused OTPs for this email
    db.query(MagicLink).filter(
        MagicLink.email == email.lower().strip(),
        MagicLink.used == False
    ).update({"used": True})
    
    # Create OTP record (using MagicLink table)
    otp_record = MagicLink(
        id=str(uuid.uuid4()),
        email=email.lower().strip(),
        token_hash=otp_hash,
        expires_at=expires_at,
        used=False,
    )
    
    db.add(otp_record)
    db.commit()
    
    return otp_code, otp_record.id


def verify_otp(
    db: Session,
    email: str,
    otp_code: str,
) -> Tuple[bool, Optional[str]]:
    """
    Verify an OTP code.
    
    Args:
        db: Database session
        email: User's email address
        otp_code: OTP code from user
    
    Returns:
        Tuple of (is_valid, error_message)
        - (True, None) if valid
        - (False, "error message") if invalid
    """
    from models import MagicLink
    
    email = email.lower().strip()
    otp_code = otp_code.strip()
    
    # Find recent unused OTPs for this email
    recent_otps = db.query(MagicLink).filter(
        MagicLink.email == email,
        MagicLink.used == False,
        MagicLink.expires_at > datetime.utcnow()
    ).order_by(MagicLink.created_at.desc()).limit(5).all()
    
    if not recent_otps:
        return False, "Doğrulama kodu bulunamadı veya süresi dolmuş"
    
    # Check each OTP
    for otp_record in recent_otps:
        if verify_token_hash(otp_code, otp_record.token_hash):
            # Mark as used
            otp_record.used = True
            otp_record.used_at = datetime.utcnow()
            db.commit()
            return True, None
    
    return False, "Geçersiz doğrulama kodu"


def cleanup_expired_otps(db: Session) -> int:
    """
    Clean up expired OTPs.
    
    Args:
        db: Database session
    
    Returns:
        Number of deleted records
    """
    from models import MagicLink
    
    cutoff_time = datetime.utcnow() - timedelta(days=1)
    
    deleted = db.query(MagicLink).filter(
        (MagicLink.expires_at < datetime.utcnow()) |
        ((MagicLink.used == True) & (MagicLink.created_at < cutoff_time))
    ).delete(synchronize_session=False)
    
    db.commit()
    
    return deleted

