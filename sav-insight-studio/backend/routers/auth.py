"""
Authentication API endpoints
"""
import uuid
from datetime import datetime, timedelta
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session

from database import get_db, DATABASE_AVAILABLE
from config import settings
from models import User, Organization, Session as SessionModel, MagicLink, AuditLog
from auth.jwt_handler import create_access_token, decode_token, create_refresh_token, decode_refresh_token
from auth.otp import create_otp, verify_otp
from auth.password import generate_token, hash_token, generate_csrf_token
from auth.dependencies import (
    get_current_user,
    get_current_user_optional,
    set_auth_cookies,
    clear_auth_cookies,
    SESSION_COOKIE_NAME,
)
from auth.permissions import get_user_permissions

router = APIRouter(prefix="/api/auth", tags=["Authentication"])


# =============================================================================
# REQUEST/RESPONSE MODELS
# =============================================================================

class LoginRequest(BaseModel):
    """Request to login with email and password"""
    email: EmailStr
    password: str


class LoginResponse(BaseModel):
    """Response after password verification - OTP sent or direct login"""
    message: str
    email: str
    requires_otp: bool = True
    # In dev mode, include the OTP for testing
    otp_code: Optional[str] = None
    # For direct login (demo accounts), include user info
    user: Optional[dict] = None
    access_token: Optional[str] = None


class VerifyRequest(BaseModel):
    """Request to verify OTP code"""
    email: EmailStr
    code: str  # 6-digit OTP code


class VerifyResponse(BaseModel):
    """Response after successful verification"""
    message: str
    user: dict
    access_token: Optional[str] = None  # Only included if not using cookies


class UserResponse(BaseModel):
    """Current user information"""
    id: str
    email: str
    name: Optional[str]
    org_id: Optional[str]
    org_name: Optional[str]
    role: str
    permissions: list
    status: str
    must_change_password: bool = False


class RefreshResponse(BaseModel):
    """Token refresh response"""
    message: str
    access_token: Optional[str] = None


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def create_audit_log(
    db: Session,
    action: str,
    user_id: Optional[str] = None,
    org_id: Optional[str] = None,
    entity_type: Optional[str] = None,
    entity_id: Optional[str] = None,
    request: Optional[Request] = None,
    meta: Optional[dict] = None,
) -> None:
    """Create an audit log entry"""
    if not DATABASE_AVAILABLE or db is None:
        return
    
    try:
        log = AuditLog(
            org_id=org_id,
            user_id=user_id,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            ip_address=request.client.host if request else None,
            user_agent=request.headers.get("user-agent") if request else None,
            meta_json=meta,
        )
        db.add(log)
        db.commit()
    except Exception as e:
        print(f"[AUDIT] Failed to create audit log: {e}")
        db.rollback()


def get_user_by_email(db: Session, email: str) -> Optional[User]:
    """Get user by email"""
    email = email.lower().strip()
    return db.query(User).filter(User.email == email).first()


def create_session(
    db: Session,
    user: User,
    token: str,
    request: Request,
) -> SessionModel:
    """Create a new session record"""
    session = SessionModel(
        id=str(uuid.uuid4()),
        user_id=user.id,
        token_hash=hash_token(token),
        expires_at=datetime.utcnow() + timedelta(hours=settings.JWT_EXPIRE_HOURS),
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )
    db.add(session)
    db.commit()
    return session


# =============================================================================
# HELPER: Complete Login (shared between OTP verify and demo direct login)
# =============================================================================

async def _complete_login(
    request: Request,
    response: Response,
    user: User,
    db: Session,
    skip_otp: bool = False,
) -> dict:
    """
    Complete the login process - create session, set cookies, return user info.
    Used by both OTP verification and demo account direct login.
    """
    # Get org settings for permissions
    org_settings = {}
    org_name = None
    if user.org_id:
        org = db.query(Organization).filter(Organization.id == user.org_id).first()
        if org:
            org_settings = org.settings or {}
            org_name = org.name
    
    # Get user permissions
    permissions = get_user_permissions(user.role, org_settings)
    
    # Create JWT token
    access_token = create_access_token(
        user_id=user.id,
        email=user.email,
        org_id=user.org_id,
        role=user.role,
        permissions=permissions,
    )
    
    # Create session record
    create_session(db, user, access_token, request)
    
    # Update last login
    user.last_login_at = datetime.utcnow()
    db.commit()
    
    # Generate CSRF token
    csrf_token = generate_csrf_token()
    
    # Set cookies
    set_auth_cookies(
        response=response,
        access_token=access_token,
        csrf_token=csrf_token,
        secure=settings.SESSION_COOKIE_SECURE,
        domain=settings.SESSION_COOKIE_DOMAIN,
    )
    
    # Audit log
    create_audit_log(
        db=db,
        action="user.login",
        user_id=user.id,
        org_id=user.org_id,
        entity_type="user",
        entity_id=user.id,
        request=request,
        meta={"skip_otp": skip_otp},
    )
    
    # Check if user must change password
    must_change = getattr(user, 'must_change_password', False) or False
    
    user_data = {
        "id": user.id,
        "email": user.email,
        "name": user.name,
        "org_id": user.org_id,
        "org_name": org_name,
        "role": user.role,
        "permissions": permissions,
        "status": user.status,
        "must_change_password": must_change,
    }
    
    return {
        "message": "Login successful",
        "email": user.email,
        "requires_otp": False,
        "user": user_data,
        "access_token": access_token if settings.DEBUG else None,
    }


# =============================================================================
# ENDPOINTS
# =============================================================================

@router.post("/login", response_model=LoginResponse)
async def login_with_password(
    request: Request,
    response: Response,
    body: LoginRequest,
    db: Session = Depends(get_db),
):
    """
    Login with email and password.
    If credentials are valid, sends a 6-digit OTP code to email.
    """
    if not DATABASE_AVAILABLE or db is None:
        raise HTTPException(status_code=503, detail="Database not available")
    
    email = body.email.lower().strip()
    
    # Find user
    user = db.query(User).filter(User.email == email).first()
    
    if not user:
        # Don't reveal if user exists
        raise HTTPException(status_code=401, detail="Invalid email or password")
    
    if user.status == "disabled":
        raise HTTPException(status_code=403, detail="Your account has been disabled")
    
    # Verify password
    from auth.password import verify_password
    if not user.password_hash or not verify_password(body.password, user.password_hash):
        create_audit_log(
            db=db,
            action="user.login_failed",
            entity_type="user",
            entity_id=user.id,
            request=request,
            meta={"email": email, "reason": "invalid_password"},
        )
        raise HTTPException(status_code=401, detail="Invalid email or password")
    
    # Check if this is a demo account (skip OTP for demo example.com domains)
    is_demo_account = email.endswith('@demo1.example.com') or email.endswith('@demo2.example.com') or email.endswith('.example.com')
    
    if is_demo_account:
        # Skip OTP for demo accounts - direct login
        return await _complete_login(request, response, user, db, skip_otp=True)
    
    # Password is correct - now send OTP
    otp_code, otp_id = create_otp(db, email)
    
    # Send OTP email
    from auth.email_service import send_otp_email
    email_sent = send_otp_email(email, otp_code, user.name)
    
    # Audit log
    create_audit_log(
        db=db,
        action="user.otp_sent",
        entity_type="user",
        entity_id=user.id,
        request=request,
        meta={"email": email, "email_sent": email_sent},
    )
    
    response_data = {
        "message": "Verification code sent to your email" if email_sent else "Verification code created (email disabled)",
        "email": email,
        "requires_otp": True,
    }
    
    # Include OTP in dev mode for testing
    if settings.DEBUG and not settings.EMAIL_ENABLED:
        response_data["otp_code"] = otp_code
    
    return response_data


# Backward compatibility endpoint
@router.post("/send-code", response_model=LoginResponse)
async def send_code_legacy(
    request: Request,
    body: LoginRequest,
    db: Session = Depends(get_db),
):
    """Legacy endpoint - redirects to login"""
    return await login_with_password(request, body, db)


@router.post("/verify", response_model=VerifyResponse)
async def verify_otp_code(
    request: Request,
    response: Response,
    body: VerifyRequest,
    db: Session = Depends(get_db),
):
    """
    Verify OTP code and create a session.
    Sets authentication cookies on success.
    """
    if not DATABASE_AVAILABLE or db is None:
        raise HTTPException(status_code=503, detail="Database not available")
    
    # Verify the OTP code
    is_valid, error_message = verify_otp(db, body.email, body.code)
    
    if not is_valid:
        create_audit_log(
            db=db,
            action="user.login_failed",
            request=request,
            meta={"email": body.email, "reason": error_message},
        )
        raise HTTPException(status_code=401, detail=error_message)
    
    # Get user (must exist since we checked in send-code)
    user = get_user_by_email(db, body.email)
    if not user:
        raise HTTPException(status_code=404, detail="Kullanıcı bulunamadı")
    
    # Check user status
    if user.status == "disabled":
        raise HTTPException(status_code=403, detail="User account is disabled")
    
    # Get org settings for permissions
    org_settings = {}
    org_name = None
    if user.org_id:
        org = db.query(Organization).filter(Organization.id == user.org_id).first()
        if org:
            org_settings = org.settings or {}
            org_name = org.name
    
    # Get user permissions
    permissions = get_user_permissions(user.role, org_settings)
    
    # Create JWT token
    access_token = create_access_token(
        user_id=user.id,
        email=user.email,
        org_id=user.org_id,
        role=user.role,
        permissions=permissions,
    )
    
    # Create session record
    create_session(db, user, access_token, request)
    
    # Update last login
    user.last_login_at = datetime.utcnow()
    db.commit()
    
    # Generate CSRF token
    csrf_token = generate_csrf_token()
    
    # Set cookies
    set_auth_cookies(
        response=response,
        access_token=access_token,
        csrf_token=csrf_token,
        secure=settings.SESSION_COOKIE_SECURE,
        domain=settings.SESSION_COOKIE_DOMAIN,
    )
    
    # Audit log
    create_audit_log(
        db=db,
        action="user.login",
        user_id=user.id,
        org_id=user.org_id,
        entity_type="user",
        entity_id=user.id,
        request=request,
    )
    
    # Check if user must change password
    must_change = getattr(user, 'must_change_password', False) or False
    
    return {
        "message": "Login successful",
        "user": {
            "id": user.id,
            "email": user.email,
            "name": user.name,
            "org_id": user.org_id,
            "org_name": org_name,
            "role": user.role,
            "permissions": permissions,
            "status": user.status,
            "must_change_password": must_change,
        },
        "access_token": access_token if settings.DEBUG else None,  # Only in dev mode
    }


@router.post("/logout")
async def logout(
    request: Request,
    response: Response,
    user: User = Depends(get_current_user_optional),
    db: Session = Depends(get_db),
):
    """
    Logout the current user.
    Clears authentication cookies and invalidates session.
    """
    if user and db and DATABASE_AVAILABLE:
        # Get token from cookie
        token = request.cookies.get(SESSION_COOKIE_NAME)
        if token:
            token_hash = hash_token(token)
            # Delete session
            db.query(SessionModel).filter(
                SessionModel.user_id == user.id,
                SessionModel.token_hash == token_hash,
            ).delete()
            db.commit()
        
        # Audit log
        create_audit_log(
            db=db,
            action="user.logout",
            user_id=user.id,
            org_id=user.org_id,
            entity_type="user",
            entity_id=user.id,
            request=request,
        )
    
    # Clear cookies
    clear_auth_cookies(response, domain=settings.SESSION_COOKIE_DOMAIN)
    
    return {"message": "Logged out successfully"}


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Get current authenticated user information.
    """
    # Get org info
    org_name = None
    org_settings = {}
    if user.org_id and db and DATABASE_AVAILABLE:
        org = db.query(Organization).filter(Organization.id == user.org_id).first()
        if org:
            org_name = org.name
            org_settings = org.settings or {}
    
    # Get permissions
    permissions = get_user_permissions(user.role, org_settings)
    
    # Check if user must change password
    must_change = getattr(user, 'must_change_password', False) or False
    
    return {
        "id": user.id,
        "email": user.email,
        "name": user.name,
        "org_id": user.org_id,
        "org_name": org_name,
        "role": user.role,
        "permissions": permissions,
        "status": user.status,
        "must_change_password": must_change,
    }


@router.post("/refresh", response_model=RefreshResponse)
async def refresh_token(
    request: Request,
    response: Response,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Refresh the access token.
    Extends the session with a new token.
    """
    if not DATABASE_AVAILABLE or db is None:
        raise HTTPException(status_code=503, detail="Database not available")
    
    # Get org settings
    org_settings = {}
    if user.org_id:
        org = db.query(Organization).filter(Organization.id == user.org_id).first()
        if org:
            org_settings = org.settings or {}
    
    # Get permissions
    permissions = get_user_permissions(user.role, org_settings)
    
    # Create new access token
    access_token = create_access_token(
        user_id=user.id,
        email=user.email,
        org_id=user.org_id,
        role=user.role,
        permissions=permissions,
    )
    
    # Update session
    old_token = request.cookies.get(SESSION_COOKIE_NAME)
    if old_token:
        old_token_hash = hash_token(old_token)
        session = db.query(SessionModel).filter(
            SessionModel.user_id == user.id,
            SessionModel.token_hash == old_token_hash,
        ).first()
        
        if session:
            session.token_hash = hash_token(access_token)
            session.expires_at = datetime.utcnow() + timedelta(hours=settings.JWT_EXPIRE_HOURS)
            session.last_used_at = datetime.utcnow()
            db.commit()
    
    # Generate new CSRF token
    csrf_token = generate_csrf_token()
    
    # Set new cookies
    set_auth_cookies(
        response=response,
        access_token=access_token,
        csrf_token=csrf_token,
        secure=settings.SESSION_COOKIE_SECURE,
        domain=settings.SESSION_COOKIE_DOMAIN,
    )
    
    return {
        "message": "Token refreshed",
        "access_token": access_token if settings.DEBUG else None,
    }


@router.get("/check")
async def check_auth(
    user: User = Depends(get_current_user_optional),
):
    """
    Check if the current request is authenticated.
    Returns user info if authenticated, null otherwise.
    """
    if user:
        return {
            "authenticated": True,
            "user": {
                "id": user.id,
                "email": user.email,
                "name": user.name,
                "role": user.role,
            }
        }
    
    return {"authenticated": False, "user": None}


# =============================================================================
# SET PASSWORD (for invited users)
# =============================================================================

class SetPasswordRequest(BaseModel):
    """Request to set password for invited user"""
    email: EmailStr
    token: str
    password: str


@router.post("/set-password")
async def set_password(
    request: Request,
    response: Response,
    body: SetPasswordRequest,
    db: Session = Depends(get_db),
):
    """
    Set password for an invited user.
    Validates the invite token and sets the user's password.
    """
    if not DATABASE_AVAILABLE or db is None:
        raise HTTPException(status_code=503, detail="Database not available")
    
    email = body.email.lower().strip()
    
    # Find user
    user = db.query(User).filter(User.email == email).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Verify invite token
    from auth.password import verify_password
    
    # Find valid token
    token_valid = False
    magic_links = db.query(MagicLink).filter(
        MagicLink.email == email,
        MagicLink.used == False,
        MagicLink.expires_at > datetime.utcnow()
    ).all()
    
    for link in magic_links:
        if verify_password(body.token, link.token_hash):
            link.used = True
            link.used_at = datetime.utcnow()
            token_valid = True
            break
    
    if not token_valid:
        raise HTTPException(status_code=401, detail="Invalid or expired invitation link")
    
    # Set password
    from auth.password import hash_password
    user.password_hash = hash_password(body.password)
    user.status = "active"
    db.commit()
    
    # Audit log
    create_audit_log(
        db=db,
        action="user.password_set",
        user_id=user.id,
        org_id=user.org_id,
        entity_type="user",
        entity_id=user.id,
        request=request,
    )
    
    return {
        "message": "Password set successfully. You can now log in.",
        "email": email,
    }


# =============================================================================
# CHANGE PASSWORD (for authenticated users)
# =============================================================================

class ChangePasswordRequest(BaseModel):
    """Request to change password"""
    current_password: str
    new_password: str


@router.post("/change-password")
async def change_password(
    request: Request,
    body: ChangePasswordRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Change password for the authenticated user.
    Requires current password verification.
    """
    if not DATABASE_AVAILABLE or db is None:
        raise HTTPException(status_code=503, detail="Database not available")
    
    from auth.password import verify_password, hash_password
    
    # Verify current password
    if not user.password_hash or not verify_password(body.current_password, user.password_hash):
        create_audit_log(
            db=db,
            action="user.password_change_failed",
            user_id=user.id,
            org_id=user.org_id,
            entity_type="user",
            entity_id=user.id,
            request=request,
            meta={"reason": "invalid_current_password"},
        )
        raise HTTPException(status_code=401, detail="Current password is incorrect")
    
    # Validate new password
    if len(body.new_password) < 8:
        raise HTTPException(status_code=400, detail="New password must be at least 8 characters")
    
    if body.new_password == body.current_password:
        raise HTTPException(status_code=400, detail="New password must be different from current password")
    
    # Update password
    user.password_hash = hash_password(body.new_password)
    user.must_change_password = False  # Clear the flag
    user.updated_at = datetime.utcnow()
    db.commit()
    
    # Audit log
    create_audit_log(
        db=db,
        action="user.password_changed",
        user_id=user.id,
        org_id=user.org_id,
        entity_type="user",
        entity_id=user.id,
        request=request,
    )
    
    return {
        "message": "Password changed successfully",
    }

