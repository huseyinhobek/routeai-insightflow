"""
Admin API endpoints for user and organization management
"""
import uuid
from datetime import datetime, timedelta
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Request, Query
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session
from sqlalchemy import desc

from database import get_db, DATABASE_AVAILABLE
from config import settings
from models import User, Organization, AuditLog
from auth.dependencies import get_current_user, require_permission, require_role
from auth.permissions import can_manage_role, get_role_hierarchy
from auth.magic_link import create_magic_link
from auth.email_service import send_invite_email, send_password_set_email
from auth.password import hash_password, generate_token

router = APIRouter(prefix="/api/admin", tags=["Admin"])


# =============================================================================
# REQUEST/RESPONSE MODELS
# =============================================================================

class UserInviteRequest(BaseModel):
    """Request to invite a new user"""
    email: EmailStr
    name: Optional[str] = None
    role: str = "viewer"


class UserUpdateRequest(BaseModel):
    """Request to update user"""
    name: Optional[str] = None
    role: Optional[str] = None
    status: Optional[str] = None


class OrganizationCreateRequest(BaseModel):
    """Request to create organization"""
    name: str
    slug: str


class OrganizationUpdateRequest(BaseModel):
    """Request to update organization settings"""
    name: Optional[str] = None
    settings: Optional[dict] = None


class UserListResponse(BaseModel):
    """User list item"""
    id: str
    email: str
    name: Optional[str]
    role: str
    status: str
    created_at: datetime
    last_login_at: Optional[datetime]


class AuditLogResponse(BaseModel):
    """Audit log entry"""
    id: int
    action: str
    entity_type: Optional[str]
    entity_id: Optional[str]
    user_email: Optional[str]
    ip_address: Optional[str]
    meta_json: Optional[dict]
    created_at: datetime


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def create_audit_log(
    db: Session,
    action: str,
    user: User,
    request: Request,
    entity_type: Optional[str] = None,
    entity_id: Optional[str] = None,
    meta: Optional[dict] = None,
) -> None:
    """Create an audit log entry"""
    if not DATABASE_AVAILABLE or db is None:
        return
    
    try:
        log = AuditLog(
            org_id=user.org_id,
            user_id=user.id,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent"),
            meta_json=meta,
        )
        db.add(log)
        db.commit()
    except Exception as e:
        print(f"[AUDIT] Failed to create audit log: {e}")
        db.rollback()


# =============================================================================
# USER MANAGEMENT ENDPOINTS
# =============================================================================

@router.get("/users", response_model=List[UserListResponse])
async def list_users(
    request: Request,
    user: User = Depends(require_permission("users:view")),
    db: Session = Depends(get_db),
):
    """
    List all users in the organization.
    Super admins see all users, org admins see only their org.
    """
    if not DATABASE_AVAILABLE or db is None:
        raise HTTPException(status_code=503, detail="Database not available")
    
    query = db.query(User)
    
    # Filter by org for non-super admins
    if user.role != "super_admin":
        query = query.filter(User.org_id == user.org_id)
    
    users = query.order_by(desc(User.created_at)).all()
    
    return [
        {
            "id": u.id,
            "email": u.email,
            "name": u.name,
            "role": u.role,
            "status": u.status,
            "created_at": u.created_at,
            "last_login_at": u.last_login_at,
        }
        for u in users
    ]


@router.post("/users/invite")
async def invite_user(
    request: Request,
    body: UserInviteRequest,
    user: User = Depends(require_permission("users:manage")),
    db: Session = Depends(get_db),
):
    """
    Invite a new user to the organization.
    Sends an email with a magic link.
    """
    if not DATABASE_AVAILABLE or db is None:
        raise HTTPException(status_code=503, detail="Database not available")
    
    email = body.email.lower().strip()
    
    # Check if user already exists
    existing = db.query(User).filter(User.email == email).first()
    if existing:
        raise HTTPException(status_code=400, detail="User with this email already exists")
    
    # Validate role assignment
    if not can_manage_role(user.role, body.role):
        raise HTTPException(
            status_code=403,
            detail=f"You cannot assign the role '{body.role}'"
        )
    
    # Create user with pending status
    new_user = User(
        id=str(uuid.uuid4()),
        email=email,
        name=body.name or email.split("@")[0],
        org_id=user.org_id,  # Same org as inviter
        role=body.role,
        status="pending",
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    # Get org name
    org_name = "Aletheia"
    if user.org_id:
        org = db.query(Organization).filter(Organization.id == user.org_id).first()
        if org:
            org_name = org.name
    
    # Create invite token for setting password
    base_url = settings.APP_BASE_URL
    invite_token = generate_token(32)
    
    # Store token hash in user record (reuse magic_link for now)
    from models import MagicLink
    invite_link = MagicLink(
        id=str(uuid.uuid4()),
        email=email,
        token_hash=hash_password(invite_token),
        expires_at=datetime.utcnow() + timedelta(hours=24),
        used=False,
    )
    db.add(invite_link)
    db.commit()
    
    # Build invite URL
    invite_url = f"{base_url}/#/set-password?token={invite_token}&email={email}"
    
    # Send invite email
    email_sent = send_invite_email(
        to_email=email,
        invite_url=invite_url,
        org_name=org_name,
        inviter_name=user.name or user.email,
        role=body.role,
    )
    
    # Audit log
    create_audit_log(
        db=db,
        action="user.invite",
        user=user,
        request=request,
        entity_type="user",
        entity_id=new_user.id,
        meta={
            "invited_email": email,
            "role": body.role,
            "email_sent": email_sent,
        },
    )
    
    return {
        "message": "User invited successfully",
        "user_id": new_user.id,
        "email": email,
        "invite_url": invite_url if settings.DEBUG else None,
    }


@router.put("/users/{user_id}")
async def update_user(
    request: Request,
    user_id: str,
    body: UserUpdateRequest,
    user: User = Depends(require_permission("users:manage")),
    db: Session = Depends(get_db),
):
    """
    Update a user's information.
    """
    if not DATABASE_AVAILABLE or db is None:
        raise HTTPException(status_code=503, detail="Database not available")
    
    # Get target user
    target_user = db.query(User).filter(User.id == user_id).first()
    if not target_user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Check org access
    if user.role != "super_admin" and target_user.org_id != user.org_id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    # Prevent self-demotion for admins
    if user.id == target_user.id and body.role and body.role != user.role:
        raise HTTPException(status_code=400, detail="Cannot change your own role")
    
    # Validate role change
    if body.role and not can_manage_role(user.role, body.role):
        raise HTTPException(
            status_code=403,
            detail=f"You cannot assign the role '{body.role}'"
        )
    
    # Update fields
    old_values = {}
    if body.name is not None:
        old_values["name"] = target_user.name
        target_user.name = body.name
    
    if body.role is not None:
        old_values["role"] = target_user.role
        target_user.role = body.role
    
    if body.status is not None:
        if body.status not in ["active", "pending", "disabled"]:
            raise HTTPException(status_code=400, detail="Invalid status")
        old_values["status"] = target_user.status
        target_user.status = body.status
    
    target_user.updated_at = datetime.utcnow()
    db.commit()
    
    # Audit log
    create_audit_log(
        db=db,
        action="user.update",
        user=user,
        request=request,
        entity_type="user",
        entity_id=target_user.id,
        meta={
            "old_values": old_values,
            "new_values": body.dict(exclude_none=True),
        },
    )
    
    return {
        "message": "User updated successfully",
        "user_id": target_user.id,
    }


@router.delete("/users/{user_id}")
async def delete_user(
    request: Request,
    user_id: str,
    user: User = Depends(require_permission("users:manage")),
    db: Session = Depends(get_db),
):
    """
    Delete a user from the organization.
    """
    if not DATABASE_AVAILABLE or db is None:
        raise HTTPException(status_code=503, detail="Database not available")
    
    # Get target user
    target_user = db.query(User).filter(User.id == user_id).first()
    if not target_user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Check org access
    if user.role != "super_admin" and target_user.org_id != user.org_id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    # Prevent self-deletion
    if user.id == target_user.id:
        raise HTTPException(status_code=400, detail="Cannot delete yourself")
    
    # Prevent deleting higher-privileged users
    if not can_manage_role(user.role, target_user.role):
        raise HTTPException(status_code=403, detail="Cannot delete this user")
    
    email = target_user.email
    
    # Audit log before deletion
    create_audit_log(
        db=db,
        action="user.delete",
        user=user,
        request=request,
        entity_type="user",
        entity_id=target_user.id,
        meta={"deleted_email": email, "deleted_role": target_user.role},
    )
    
    db.delete(target_user)
    db.commit()
    
    return {"message": "User deleted successfully", "email": email}


# =============================================================================
# ORGANIZATION MANAGEMENT ENDPOINTS
# =============================================================================

@router.get("/org")
async def get_organization(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Get current user's organization details.
    """
    if not DATABASE_AVAILABLE or db is None:
        raise HTTPException(status_code=503, detail="Database not available")
    
    if not user.org_id:
        return {"organization": None}
    
    org = db.query(Organization).filter(Organization.id == user.org_id).first()
    if not org:
        return {"organization": None}
    
    return {
        "organization": {
            "id": org.id,
            "name": org.name,
            "slug": org.slug,
            "settings": org.settings or {},
            "created_at": org.created_at,
        }
    }


@router.put("/org/settings")
async def update_organization_settings(
    request: Request,
    body: OrganizationUpdateRequest,
    user: User = Depends(require_permission("org:settings")),
    db: Session = Depends(get_db),
):
    """
    Update organization settings.
    """
    if not DATABASE_AVAILABLE or db is None:
        raise HTTPException(status_code=503, detail="Database not available")
    
    if not user.org_id:
        raise HTTPException(status_code=400, detail="User has no organization")
    
    org = db.query(Organization).filter(Organization.id == user.org_id).first()
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")
    
    old_values = {}
    
    if body.name is not None:
        old_values["name"] = org.name
        org.name = body.name
    
    if body.settings is not None:
        old_values["settings"] = org.settings
        # Merge settings instead of replacing
        current_settings = org.settings or {}
        current_settings.update(body.settings)
        org.settings = current_settings
    
    org.updated_at = datetime.utcnow()
    db.commit()
    
    # Audit log
    create_audit_log(
        db=db,
        action="org.settings_change",
        user=user,
        request=request,
        entity_type="organization",
        entity_id=org.id,
        meta={"old_values": old_values, "new_values": body.dict(exclude_none=True)},
    )
    
    return {
        "message": "Organization settings updated",
        "organization": {
            "id": org.id,
            "name": org.name,
            "settings": org.settings,
        }
    }


@router.post("/org/create")
async def create_organization(
    request: Request,
    body: OrganizationCreateRequest,
    user: User = Depends(require_role(["super_admin"])),
    db: Session = Depends(get_db),
):
    """
    Create a new organization. Super admin only.
    """
    if not DATABASE_AVAILABLE or db is None:
        raise HTTPException(status_code=503, detail="Database not available")
    
    # Check slug uniqueness
    existing = db.query(Organization).filter(Organization.slug == body.slug).first()
    if existing:
        raise HTTPException(status_code=400, detail="Organization slug already exists")
    
    org = Organization(
        id=str(uuid.uuid4()),
        name=body.name,
        slug=body.slug,
        settings={
            "export_allowed": True,
            "reviewer_can_export": False,
            "retention_days": 365,
        },
    )
    db.add(org)
    db.commit()
    db.refresh(org)
    
    # Audit log
    create_audit_log(
        db=db,
        action="org.create",
        user=user,
        request=request,
        entity_type="organization",
        entity_id=org.id,
        meta={"name": org.name, "slug": org.slug},
    )
    
    return {
        "message": "Organization created successfully",
        "organization": {
            "id": org.id,
            "name": org.name,
            "slug": org.slug,
        }
    }


# =============================================================================
# AUDIT LOG ENDPOINTS
# =============================================================================

@router.get("/audit-logs")
async def get_audit_logs(
    request: Request,
    offset: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    action: Optional[str] = None,
    entity_type: Optional[str] = None,
    user_id: Optional[str] = None,
    user: User = Depends(require_permission("audit:read")),
    db: Session = Depends(get_db),
):
    """
    Get audit logs for the organization.
    """
    if not DATABASE_AVAILABLE or db is None:
        raise HTTPException(status_code=503, detail="Database not available")
    
    query = db.query(AuditLog)
    
    # Filter by org for non-super admins
    if user.role != "super_admin":
        query = query.filter(AuditLog.org_id == user.org_id)
    
    # Apply filters
    if action:
        query = query.filter(AuditLog.action == action)
    if entity_type:
        query = query.filter(AuditLog.entity_type == entity_type)
    if user_id:
        query = query.filter(AuditLog.user_id == user_id)
    
    # Get total count
    total = query.count()
    
    # Get paginated results
    logs = query.order_by(desc(AuditLog.created_at)).offset(offset).limit(limit).all()
    
    # Get user emails for display
    user_ids = {log.user_id for log in logs if log.user_id}
    users_map = {}
    if user_ids:
        users = db.query(User).filter(User.id.in_(user_ids)).all()
        users_map = {u.id: u.email for u in users}
    
    return {
        "total": total,
        "offset": offset,
        "limit": limit,
        "logs": [
            {
                "id": log.id,
                "action": log.action,
                "entity_type": log.entity_type,
                "entity_id": log.entity_id,
                "user_email": users_map.get(log.user_id),
                "ip_address": log.ip_address,
                "meta_json": log.meta_json,
                "created_at": log.created_at,
            }
            for log in logs
        ],
    }


@router.get("/audit-logs/actions")
async def get_audit_log_actions(
    user: User = Depends(require_permission("audit:read")),
):
    """
    Get list of available audit log actions for filtering.
    """
    return {
        "actions": [
            "user.login",
            "user.logout",
            "user.login_failed",
            "user.magic_link_requested",
            "user.invite",
            "user.update",
            "user.delete",
            "dataset.upload",
            "dataset.delete",
            "dataset.export",
            "transform.start",
            "transform.pause",
            "transform.resume",
            "transform.export",
            "smart_filter.generate",
            "org.settings_change",
            "org.create",
        ]
    }


# =============================================================================
# SUPER ADMIN ENDPOINTS
# =============================================================================

@router.get("/organizations")
async def list_organizations(
    user: User = Depends(require_role(["super_admin"])),
    db: Session = Depends(get_db),
):
    """
    List all organizations. Super admin only.
    """
    if not DATABASE_AVAILABLE or db is None:
        raise HTTPException(status_code=503, detail="Database not available")
    
    orgs = db.query(Organization).order_by(desc(Organization.created_at)).all()
    
    # Get user counts for each org
    from sqlalchemy import func
    user_counts = dict(
        db.query(User.org_id, func.count(User.id))
        .group_by(User.org_id)
        .all()
    )
    
    return [
        {
            "id": org.id,
            "name": org.name,
            "slug": org.slug,
            "settings": org.settings or {},
            "created_at": org.created_at.isoformat() if org.created_at else None,
            "user_count": user_counts.get(org.id, 0),
        }
        for org in orgs
    ]


@router.get("/system-stats")
async def get_system_stats(
    user: User = Depends(require_role(["super_admin"])),
    db: Session = Depends(get_db),
):
    """
    Get system-wide statistics. Super admin only.
    """
    if not DATABASE_AVAILABLE or db is None:
        raise HTTPException(status_code=503, detail="Database not available")
    
    from sqlalchemy import func
    from models import Dataset, TransformJob, Session as SessionModel
    from datetime import datetime, timedelta
    
    # Count organizations
    total_organizations = db.query(func.count(Organization.id)).scalar() or 0
    
    # Count users
    total_users = db.query(func.count(User.id)).scalar() or 0
    
    # Count datasets
    try:
        total_datasets = db.query(func.count(Dataset.id)).scalar() or 0
    except:
        total_datasets = 0
    
    # Count transform jobs
    try:
        total_transforms = db.query(func.count(TransformJob.id)).scalar() or 0
    except:
        total_transforms = 0
    
    # Count active sessions (created in last 24 hours)
    try:
        active_sessions = db.query(func.count(SessionModel.id)).filter(
            SessionModel.expires_at > datetime.utcnow()
        ).scalar() or 0
    except:
        active_sessions = 0
    
    return {
        "total_organizations": total_organizations,
        "total_users": total_users,
        "total_datasets": total_datasets,
        "total_transforms": total_transforms,
        "active_sessions": active_sessions,
    }


# =============================================================================
# SEND CREDENTIALS ENDPOINTS (Super Admin Only)
# =============================================================================

class SendCredentialsRequest(BaseModel):
    """Request to send credentials to a user"""
    user_id: str
    temp_password: Optional[str] = None  # If not provided, generates one


class BulkSendCredentialsRequest(BaseModel):
    """Request to send credentials to multiple users"""
    user_ids: List[str]
    temp_password: Optional[str] = None  # Same password for all if provided


def generate_temp_password() -> str:
    """Generate a secure temporary password"""
    import secrets
    import string
    chars = string.ascii_letters + string.digits + "!@#$%"
    return ''.join(secrets.choice(chars) for _ in range(12))


@router.post("/users/{user_id}/send-credentials")
async def send_user_credentials(
    request: Request,
    user_id: str,
    body: SendCredentialsRequest,
    user: User = Depends(require_role(["super_admin"])),
    db: Session = Depends(get_db),
):
    """
    Send login credentials to a specific user. Super admin only.
    Sets a new password and emails the credentials.
    """
    if not DATABASE_AVAILABLE or db is None:
        raise HTTPException(status_code=503, detail="Database not available")
    
    from auth.email_service import send_credentials_email
    from config import settings
    
    # Get target user
    target_user = db.query(User).filter(User.id == user_id).first()
    if not target_user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Generate or use provided password
    temp_password = body.temp_password or generate_temp_password()
    
    # Update user password and set must_change_password flag
    target_user.password_hash = hash_password(temp_password)
    target_user.status = "active"
    target_user.must_change_password = True  # Force password change on first login
    target_user.updated_at = datetime.utcnow()
    db.commit()
    
    # Get organization name
    org_name = "Aletheia"
    if target_user.org_id:
        org = db.query(Organization).filter(Organization.id == target_user.org_id).first()
        if org:
            org_name = org.name
    
    # Build login URL
    login_url = f"{settings.APP_BASE_URL}/#/login"
    
    # Send email
    email_sent = send_credentials_email(
        to_email=target_user.email,
        user_name=target_user.name or target_user.email.split("@")[0],
        temp_password=temp_password,
        login_url=login_url,
        org_name=org_name,
        role=target_user.role,
    )
    
    # Audit log
    create_audit_log(
        db=db,
        action="user.credentials_sent",
        user=user,
        request=request,
        entity_type="user",
        entity_id=target_user.id,
        meta={
            "target_email": target_user.email,
            "email_sent": email_sent,
        },
    )
    
    return {
        "message": "Credentials sent successfully" if email_sent else "Password updated, but email failed",
        "user_id": target_user.id,
        "email": target_user.email,
        "email_sent": email_sent,
        "temp_password": temp_password if settings.DEBUG else None,
    }


@router.post("/users/bulk-send-credentials")
async def bulk_send_credentials(
    request: Request,
    body: BulkSendCredentialsRequest,
    user: User = Depends(require_role(["super_admin"])),
    db: Session = Depends(get_db),
):
    """
    Send login credentials to multiple users. Super admin only.
    """
    if not DATABASE_AVAILABLE or db is None:
        raise HTTPException(status_code=503, detail="Database not available")
    
    from auth.email_service import send_credentials_email
    from config import settings
    
    results = []
    success_count = 0
    failed_count = 0
    
    for user_id in body.user_ids:
        target_user = db.query(User).filter(User.id == user_id).first()
        if not target_user:
            results.append({"user_id": user_id, "success": False, "error": "User not found"})
            failed_count += 1
            continue
        
        # Generate password
        temp_password = body.temp_password or generate_temp_password()
        
        # Update user password and set must_change_password flag
        target_user.password_hash = hash_password(temp_password)
        target_user.status = "active"
        target_user.must_change_password = True  # Force password change on first login
        target_user.updated_at = datetime.utcnow()
        db.commit()
        
        # Get organization name
        org_name = "Aletheia"
        if target_user.org_id:
            org = db.query(Organization).filter(Organization.id == target_user.org_id).first()
            if org:
                org_name = org.name
        
        # Build login URL
        login_url = f"{settings.APP_BASE_URL}/#/login"
        
        # Send email
        email_sent = send_credentials_email(
            to_email=target_user.email,
            user_name=target_user.name or target_user.email.split("@")[0],
            temp_password=temp_password,
            login_url=login_url,
            org_name=org_name,
            role=target_user.role,
        )
        
        if email_sent:
            success_count += 1
            results.append({
                "user_id": target_user.id,
                "email": target_user.email,
                "success": True,
                "email_sent": True,
            })
        else:
            failed_count += 1
            results.append({
                "user_id": target_user.id,
                "email": target_user.email,
                "success": False,
                "error": "Email failed to send",
            })
        
        # Audit log
        create_audit_log(
            db=db,
            action="user.credentials_sent",
            user=user,
            request=request,
            entity_type="user",
            entity_id=target_user.id,
            meta={"target_email": target_user.email, "email_sent": email_sent},
        )
    
    return {
        "message": f"Sent credentials to {success_count} users, {failed_count} failed",
        "success_count": success_count,
        "failed_count": failed_count,
        "results": results,
    }


@router.get("/users/all")
async def list_all_users(
    user: User = Depends(require_role(["super_admin"])),
    db: Session = Depends(get_db),
):
    """
    List all users across all organizations. Super admin only.
    """
    if not DATABASE_AVAILABLE or db is None:
        raise HTTPException(status_code=503, detail="Database not available")
    
    users = db.query(User).order_by(desc(User.created_at)).all()
    
    # Get organization names
    org_ids = {u.org_id for u in users if u.org_id}
    orgs_map = {}
    if org_ids:
        orgs = db.query(Organization).filter(Organization.id.in_(org_ids)).all()
        orgs_map = {o.id: o.name for o in orgs}
    
    return [
        {
            "id": u.id,
            "email": u.email,
            "name": u.name,
            "role": u.role,
            "status": u.status,
            "org_id": u.org_id,
            "org_name": orgs_map.get(u.org_id, "Unknown"),
            "created_at": u.created_at.isoformat() if u.created_at else None,
            "last_login_at": u.last_login_at.isoformat() if u.last_login_at else None,
        }
        for u in users
    ]

