"""
Organization scope middleware for multi-tenant isolation
"""
from typing import Optional, Callable
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

from auth.jwt_handler import decode_token
from auth.dependencies import SESSION_COOKIE_NAME


class OrgScopeMiddleware(BaseHTTPMiddleware):
    """
    Middleware to extract and attach org_id to request state.
    This enables automatic tenant isolation in database queries.
    """
    
    # Paths that don't require org scope
    EXEMPT_PATHS = {
        "/api/auth/magic-link",
        "/api/auth/verify",
        "/api/auth/check",
        "/api/auth/logout",
        "/health",
        "/api/config",
        "/docs",
        "/openapi.json",
        "/redoc",
    }
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process the request and attach org context"""
        
        # Initialize request state
        request.state.user = None
        request.state.org_id = None
        request.state.user_id = None
        request.state.role = None
        request.state.permissions = []
        
        # Skip auth for exempt paths
        path = request.url.path
        if self._is_exempt_path(path):
            return await call_next(request)
        
        # Try to extract token and decode user info
        token = self._get_token_from_request(request)
        
        if token:
            token_data = decode_token(token)
            
            if token_data:
                request.state.user_id = token_data.user_id
                request.state.org_id = token_data.org_id
                request.state.role = token_data.role
                request.state.permissions = token_data.permissions
        
        return await call_next(request)
    
    def _is_exempt_path(self, path: str) -> bool:
        """Check if path is exempt from org scope"""
        # Exact match
        if path in self.EXEMPT_PATHS:
            return True
        
        # Prefix match for static files and docs
        exempt_prefixes = ("/static/", "/docs", "/openapi", "/redoc")
        return any(path.startswith(prefix) for prefix in exempt_prefixes)
    
    def _get_token_from_request(self, request: Request) -> Optional[str]:
        """Extract JWT token from request"""
        # Try Authorization header first
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            return auth_header[7:]
        
        # Try session cookie
        return request.cookies.get(SESSION_COOKIE_NAME)


def get_org_id_from_request(request: Request) -> Optional[str]:
    """
    Helper function to get org_id from request state.
    Use this in endpoints to get the current user's org_id.
    """
    return getattr(request.state, "org_id", None)


def get_user_id_from_request(request: Request) -> Optional[str]:
    """
    Helper function to get user_id from request state.
    """
    return getattr(request.state, "user_id", None)


def require_org_scope(request: Request) -> str:
    """
    Dependency to require and return org_id.
    Raises 403 if no org scope is available.
    
    Usage:
        @app.get("/datasets")
        async def list_datasets(org_id: str = Depends(require_org_scope)):
            ...
    """
    from fastapi import HTTPException
    
    org_id = get_org_id_from_request(request)
    
    if not org_id:
        # Super admin might not have org_id
        role = getattr(request.state, "role", None)
        if role == "super_admin":
            return None  # Super admin can access all orgs
        
        raise HTTPException(
            status_code=403,
            detail="Organization scope required"
        )
    
    return org_id


def apply_org_filter(query, model_class, request: Request):
    """
    Apply org_id filter to a SQLAlchemy query.
    Super admins bypass this filter.
    
    Usage:
        query = db.query(Dataset)
        query = apply_org_filter(query, Dataset, request)
    """
    role = getattr(request.state, "role", None)
    
    # Super admin sees all
    if role == "super_admin":
        return query
    
    org_id = get_org_id_from_request(request)
    
    if org_id and hasattr(model_class, "org_id"):
        return query.filter(model_class.org_id == org_id)
    
    return query

