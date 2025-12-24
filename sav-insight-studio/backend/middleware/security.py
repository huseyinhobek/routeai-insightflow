"""
Security middleware for headers and CSRF protection
"""
from typing import Callable
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

from auth.dependencies import CSRF_COOKIE_NAME, CSRF_HEADER_NAME


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    Middleware to add security headers to all responses.
    """
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        response = await call_next(request)
        
        # Security headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        
        # Cache control for API responses
        if request.url.path.startswith("/api/"):
            response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate"
            response.headers["Pragma"] = "no-cache"
        
        return response


class CSRFMiddleware(BaseHTTPMiddleware):
    """
    Middleware for CSRF protection on state-changing requests.
    """
    
    # Methods that require CSRF validation
    UNSAFE_METHODS = {"POST", "PUT", "PATCH", "DELETE"}
    
    # Paths exempt from CSRF (e.g., public APIs, webhooks)
    EXEMPT_PATHS = {
        "/api/auth/magic-link",
        "/api/auth/verify",
        "/health",
    }
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Skip CSRF for safe methods
        if request.method not in self.UNSAFE_METHODS:
            return await call_next(request)
        
        # Skip CSRF for exempt paths
        if request.url.path in self.EXEMPT_PATHS:
            return await call_next(request)
        
        # Skip CSRF if no session cookie (not logged in)
        from auth.dependencies import SESSION_COOKIE_NAME
        if not request.cookies.get(SESSION_COOKIE_NAME):
            return await call_next(request)
        
        # Validate CSRF token
        cookie_token = request.cookies.get(CSRF_COOKIE_NAME)
        header_token = request.headers.get(CSRF_HEADER_NAME)
        
        if not cookie_token or not header_token:
            from starlette.responses import JSONResponse
            return JSONResponse(
                status_code=403,
                content={"detail": "CSRF token missing"}
            )
        
        if cookie_token != header_token:
            from starlette.responses import JSONResponse
            return JSONResponse(
                status_code=403,
                content={"detail": "CSRF token mismatch"}
            )
        
        return await call_next(request)

