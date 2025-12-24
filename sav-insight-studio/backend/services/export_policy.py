"""
Export policy service for controlling data export permissions
"""
from typing import Optional
from fastapi import HTTPException
from sqlalchemy.orm import Session

from models import User, Organization
from auth.permissions import has_permission


def check_export_permission(
    db: Session,
    user: Optional[User],
    export_type: str = "data",
) -> bool:
    """
    Check if a user has permission to export data.
    
    Args:
        db: Database session
        user: Current user (None if not authenticated)
        export_type: Type of export (data, transform, etc.)
    
    Returns:
        True if export is allowed
    
    Raises:
        HTTPException: 403 if export is not allowed
    """
    # If no user (not authenticated), allow for backward compatibility
    # This will be removed once auth is fully enforced
    if user is None:
        return True
    
    # Get organization settings
    org_settings = {}
    if user.org_id and db:
        org = db.query(Organization).filter(Organization.id == user.org_id).first()
        if org:
            org_settings = org.settings or {}
    
    # Check org-level export permission
    if not org_settings.get("export_allowed", True):
        raise HTTPException(
            status_code=403,
            detail="Export is disabled for this organization"
        )
    
    # Check role-level export permission
    if user.role == "viewer":
        raise HTTPException(
            status_code=403,
            detail="Viewers cannot export data. Contact your administrator for access."
        )
    
    # Check reviewer export permission (configurable per org)
    if user.role == "reviewer":
        if not org_settings.get("reviewer_can_export", False):
            raise HTTPException(
                status_code=403,
                detail="Reviewers cannot export data in this organization. Contact your administrator."
            )
    
    # Check explicit export permission
    if not has_permission(user.role, "export:download", org_settings):
        raise HTTPException(
            status_code=403,
            detail="You don't have permission to export data"
        )
    
    return True


def get_export_warning(user: Optional[User]) -> Optional[str]:
    """
    Get a warning message to display before export.
    
    Args:
        user: Current user
    
    Returns:
        Warning message or None
    """
    if user is None:
        return None
    
    return "Bu dosya gizli müşteri verisi içerebilir. Yalnızca yetkili kişilerle paylaşın."


def should_add_watermark(user: Optional[User], org_settings: dict) -> bool:
    """
    Check if exported files should have a watermark.
    
    Args:
        user: Current user
        org_settings: Organization settings
    
    Returns:
        True if watermark should be added
    """
    if user is None:
        return False
    
    return org_settings.get("watermark_exports", False)


def get_watermark_text(user: User) -> str:
    """
    Generate watermark text for exported files.
    
    Args:
        user: Current user
    
    Returns:
        Watermark text
    """
    from datetime import datetime
    
    return f"Exported by {user.email} on {datetime.now().strftime('%Y-%m-%d %H:%M')}"

