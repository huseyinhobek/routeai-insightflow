"""
Audit logging service for tracking critical actions
"""
from typing import Optional, Dict, Any
from datetime import datetime
from sqlalchemy.orm import Session
from fastapi import Request
import logging

logger = logging.getLogger(__name__)


def create_audit_log(
    db: Session,
    action: str,
    request: Optional[Request] = None,
    user_id: Optional[str] = None,
    org_id: Optional[str] = None,
    entity_type: Optional[str] = None,
    entity_id: Optional[str] = None,
    meta: Optional[Dict[str, Any]] = None,
) -> bool:
    """
    Create an audit log entry for tracking critical actions.
    
    Args:
        db: Database session
        action: Action identifier (e.g., "dataset.upload", "transform.export")
        request: FastAPI request object (for IP and user agent)
        user_id: ID of the user performing the action
        org_id: Organization ID
        entity_type: Type of entity being acted upon (e.g., "dataset", "transform_job")
        entity_id: ID of the entity
        meta: Additional metadata as JSON
    
    Returns:
        True if audit log was created successfully, False otherwise
    """
    from database import DATABASE_AVAILABLE
    from models import AuditLog
    
    if not DATABASE_AVAILABLE or db is None:
        logger.debug(f"[AUDIT] Skipped (no DB): {action}")
        return False
    
    try:
        # Extract user info from request state if not provided
        if request:
            if not user_id and hasattr(request.state, "user_id"):
                user_id = request.state.user_id
            if not org_id and hasattr(request.state, "org_id"):
                org_id = request.state.org_id
        
        log = AuditLog(
            org_id=org_id,
            user_id=user_id,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            ip_address=request.client.host if request and request.client else None,
            user_agent=request.headers.get("user-agent") if request else None,
            meta_json=meta,
        )
        
        db.add(log)
        db.commit()
        
        logger.info(f"[AUDIT] {action} | user={user_id} | entity={entity_type}:{entity_id}")
        return True
        
    except Exception as e:
        logger.error(f"[AUDIT] Failed to create audit log: {e}")
        try:
            db.rollback()
        except:
            pass
        return False


def audit_dataset_upload(
    db: Session,
    request: Request,
    dataset_id: str,
    filename: str,
    n_rows: int,
    n_cols: int,
) -> bool:
    """Audit log for dataset upload"""
    return create_audit_log(
        db=db,
        action="dataset.upload",
        request=request,
        entity_type="dataset",
        entity_id=dataset_id,
        meta={
            "filename": filename,
            "n_rows": n_rows,
            "n_cols": n_cols,
        },
    )


def audit_dataset_delete(
    db: Session,
    request: Request,
    dataset_id: str,
    filename: str,
) -> bool:
    """Audit log for dataset deletion"""
    return create_audit_log(
        db=db,
        action="dataset.delete",
        request=request,
        entity_type="dataset",
        entity_id=dataset_id,
        meta={"filename": filename},
    )


def audit_dataset_export(
    db: Session,
    request: Request,
    dataset_id: str,
    export_type: str,
) -> bool:
    """Audit log for dataset export"""
    return create_audit_log(
        db=db,
        action="dataset.export",
        request=request,
        entity_type="dataset",
        entity_id=dataset_id,
        meta={"export_type": export_type},
    )


def audit_transform_start(
    db: Session,
    request: Request,
    job_id: str,
    dataset_id: str,
    row_limit: Optional[int] = None,
) -> bool:
    """Audit log for transform job start"""
    return create_audit_log(
        db=db,
        action="transform.start",
        request=request,
        entity_type="transform_job",
        entity_id=job_id,
        meta={
            "dataset_id": dataset_id,
            "row_limit": row_limit,
        },
    )


def audit_transform_pause(
    db: Session,
    request: Request,
    job_id: str,
) -> bool:
    """Audit log for transform job pause"""
    return create_audit_log(
        db=db,
        action="transform.pause",
        request=request,
        entity_type="transform_job",
        entity_id=job_id,
    )


def audit_transform_resume(
    db: Session,
    request: Request,
    job_id: str,
) -> bool:
    """Audit log for transform job resume"""
    return create_audit_log(
        db=db,
        action="transform.resume",
        request=request,
        entity_type="transform_job",
        entity_id=job_id,
    )


def audit_transform_export(
    db: Session,
    request: Request,
    job_id: str,
    export_format: str,
    row_count: int,
) -> bool:
    """Audit log for transform results export"""
    return create_audit_log(
        db=db,
        action="transform.export",
        request=request,
        entity_type="transform_job",
        entity_id=job_id,
        meta={
            "format": export_format,
            "row_count": row_count,
        },
    )


def audit_smart_filter_generate(
    db: Session,
    request: Request,
    dataset_id: str,
    filter_count: int,
) -> bool:
    """Audit log for smart filter generation"""
    return create_audit_log(
        db=db,
        action="smart_filter.generate",
        request=request,
        entity_type="dataset",
        entity_id=dataset_id,
        meta={"filter_count": filter_count},
    )

