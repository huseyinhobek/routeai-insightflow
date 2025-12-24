"""
FastAPI dependencies for authentication and authorization
"""
from functools import wraps
from typing import Optional, Callable, List, TYPE_CHECKING
from fastapi import Depends, HTTPException, Request, Response
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from database import get_db
from .jwt_handler import decode_token, TokenData
from .permissions import has_permission, get_user_permissions

if TYPE_CHECKING:
    from models import User

# HTTP Bearer scheme for Authorization header
security = HTTPBearer(auto_error=False)

# Cookie name for session token
SESSION_COOKIE_NAME = "session_token"
CSRF_COOKIE_NAME = "csrf_token"
CSRF_HEADER_NAME = "X-CSRF-Token"


def get_token_from_request(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = None,
) -> Optional[str]:
    """
    Extract JWT token from request (cookie or Authorization header).
    
    Priority:
    1. Authorization header (Bearer token)
    2. Session cookie
    
    Args:
        request: FastAPI request object
        credentials: Optional Bearer credentials from header
    
    Returns:
        JWT token string or None
    """
    # Try Authorization header first
    if credentials and credentials.credentials:
        return credentials.credentials
    
    # Try session cookie
    token = request.cookies.get(SESSION_COOKIE_NAME)
    if token:
        return token
    
    return None


async def get_current_user(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: Session = Depends(get_db),
) -> "User":
    """
    Get the current authenticated user.
    Raises HTTPException if not authenticated.
    
    Args:
        request: FastAPI request object
        credentials: Optional Bearer credentials
        db: Database session
    
    Returns:
        User object
    
    Raises:
        HTTPException: 401 if not authenticated
    """
    from models import User, Session as SessionModel
    
    token = get_token_from_request(request, credentials)
    
    if not token:
        raise HTTPException(
            status_code=401,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Decode and validate token
    token_data = decode_token(token)
    
    if not token_data:
        raise HTTPException(
            status_code=401,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Get user from database
    user = db.query(User).filter(User.id == token_data.user_id).first()
    
    if not user:
        raise HTTPException(
            status_code=401,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Check user status
    if user.status != "active":
        raise HTTPException(
            status_code=403,
            detail=f"User account is {user.status}",
        )
    
    # Store user and token data in request state for later use
    request.state.user = user
    request.state.token_data = token_data
    
    return user


async def get_current_user_optional(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: Session = Depends(get_db),
) -> Optional["User"]:
    """
    Get the current user if authenticated, None otherwise.
    Does not raise exception if not authenticated.
    
    Args:
        request: FastAPI request object
        credentials: Optional Bearer credentials
        db: Database session
    
    Returns:
        User object or None
    """
    from models import User
    
    token = get_token_from_request(request, credentials)
    
    if not token:
        return None
    
    token_data = decode_token(token)
    
    if not token_data:
        return None
    
    user = db.query(User).filter(User.id == token_data.user_id).first()
    
    if not user or user.status != "active":
        return None
    
    request.state.user = user
    request.state.token_data = token_data
    
    return user


def require_permission(permission: str):
    """
    Decorator/dependency to require a specific permission.
    
    Args:
        permission: Required permission string
    
    Returns:
        Dependency function
    
    Usage:
        @app.get("/admin")
        async def admin_endpoint(user: User = Depends(require_permission("users:manage"))):
            ...
    """
    async def permission_checker(
        request: Request,
        user: "User" = Depends(get_current_user),
        db: Session = Depends(get_db),
    ) -> "User":
        from models import Organization
        
        # Get org settings for conditional permissions
        org_settings = {}
        if user.org_id:
            org = db.query(Organization).filter(Organization.id == user.org_id).first()
            if org:
                org_settings = org.settings or {}
        
        # Check permission
        if not has_permission(user.role, permission, org_settings):
            raise HTTPException(
                status_code=403,
                detail=f"Permission denied: {permission} required",
            )
        
        return user
    
    return permission_checker


def require_role(roles: List[str]):
    """
    Decorator/dependency to require one of the specified roles.
    
    Args:
        roles: List of allowed role names
    
    Returns:
        Dependency function
    
    Usage:
        @app.get("/admin")
        async def admin_endpoint(user: User = Depends(require_role(["super_admin", "org_admin"]))):
            ...
    """
    async def role_checker(
        user: "User" = Depends(get_current_user),
    ) -> "User":
        if user.role not in roles:
            raise HTTPException(
                status_code=403,
                detail=f"Role not allowed. Required: {', '.join(roles)}",
            )
        
        return user
    
    return role_checker


def require_org_access(org_id_param: str = "org_id"):
    """
    Dependency to verify user has access to the specified organization.
    Super admins have access to all orgs.
    
    Args:
        org_id_param: Name of the path/query parameter containing org_id
    
    Returns:
        Dependency function
    """
    async def org_access_checker(
        request: Request,
        user: "User" = Depends(get_current_user),
    ) -> "User":
        # Super admin has access to all orgs
        if user.role == "super_admin":
            return user
        
        # Get org_id from path or query params
        target_org_id = request.path_params.get(org_id_param) or request.query_params.get(org_id_param)
        
        if target_org_id and target_org_id != user.org_id:
            raise HTTPException(
                status_code=403,
                detail="Access denied to this organization",
            )
        
        return user
    
    return org_access_checker


def set_auth_cookies(
    response: Response,
    access_token: str,
    csrf_token: str,
    secure: bool = True,
    domain: Optional[str] = None,
) -> None:
    """
    Set authentication cookies on response.
    
    Args:
        response: FastAPI response object
        access_token: JWT access token
        csrf_token: CSRF token
        secure: Whether to set Secure flag (HTTPS only)
        domain: Optional cookie domain
    """
    # Session cookie - httpOnly, not accessible via JavaScript
    response.set_cookie(
        key=SESSION_COOKIE_NAME,
        value=access_token,
        httponly=True,
        secure=secure,
        samesite="lax",
        max_age=60 * 60 * 24 * 7,  # 7 days
        path="/",
        domain=domain,
    )
    
    # CSRF cookie - accessible via JavaScript for AJAX requests
    response.set_cookie(
        key=CSRF_COOKIE_NAME,
        value=csrf_token,
        httponly=False,  # Must be readable by JavaScript
        secure=secure,
        samesite="lax",
        max_age=60 * 60 * 24 * 7,  # 7 days
        path="/",
        domain=domain,
    )


def clear_auth_cookies(
    response: Response,
    domain: Optional[str] = None,
) -> None:
    """
    Clear authentication cookies on logout.
    
    Args:
        response: FastAPI response object
        domain: Optional cookie domain
    """
    response.delete_cookie(
        key=SESSION_COOKIE_NAME,
        path="/",
        domain=domain,
    )
    response.delete_cookie(
        key=CSRF_COOKIE_NAME,
        path="/",
        domain=domain,
    )


def verify_csrf(request: Request) -> bool:
    """
    Verify CSRF token from request header against cookie.
    
    Args:
        request: FastAPI request object
    
    Returns:
        True if CSRF token is valid
    
    Raises:
        HTTPException: 403 if CSRF validation fails
    """
    # Skip CSRF for safe methods
    if request.method in ("GET", "HEAD", "OPTIONS"):
        return True
    
    cookie_token = request.cookies.get(CSRF_COOKIE_NAME)
    header_token = request.headers.get(CSRF_HEADER_NAME)
    
    if not cookie_token or not header_token:
        raise HTTPException(
            status_code=403,
            detail="CSRF token missing",
        )
    
    if cookie_token != header_token:
        raise HTTPException(
            status_code=403,
            detail="CSRF token mismatch",
        )
    
    return True

