"""
SQLAlchemy database models
"""
from sqlalchemy import Column, Integer, String, Float, DateTime, Text, JSON, Boolean, ForeignKey, Enum, Index
from sqlalchemy.orm import relationship
from datetime import datetime
import enum
from database import Base


class QualityStatus(enum.Enum):
    """Data quality status for digital twin readiness"""
    GREEN = "green"      # Ready for digital twin
    YELLOW = "yellow"    # Needs attention
    RED = "red"          # Not suitable without major fixes


class UserRole(enum.Enum):
    """User roles for RBAC"""
    SUPER_ADMIN = "super_admin"    # Full access to all orgs
    ORG_ADMIN = "org_admin"        # Org-level admin
    TRANSFORMER = "transformer"    # Can upload, transform, export
    REVIEWER = "reviewer"          # Can view, approve, optionally export
    VIEWER = "viewer"              # Read-only access


class UserStatus(enum.Enum):
    """User account status"""
    ACTIVE = "active"
    PENDING = "pending"
    DISABLED = "disabled"


# =============================================================================
# SECURITY / AUTH MODELS
# =============================================================================

class Organization(Base):
    """Multi-tenant organization"""
    __tablename__ = "organizations"
    
    id = Column(String(36), primary_key=True)
    name = Column(String(255), nullable=False)
    slug = Column(String(100), unique=True, nullable=False)
    
    # Organization settings
    settings = Column(JSON, default=dict)  # {export_allowed, retention_days, reviewer_can_export, etc.}
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    users = relationship("User", back_populates="organization", cascade="all, delete-orphan")
    datasets = relationship("Dataset", back_populates="organization", cascade="all, delete-orphan")
    audit_logs = relationship("AuditLog", back_populates="organization", cascade="all, delete-orphan")


class User(Base):
    """Application user"""
    __tablename__ = "users"
    
    id = Column(String(36), primary_key=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    name = Column(String(255))
    password_hash = Column(String(255), nullable=True)  # SHA256 hash of password
    
    # Organization membership
    org_id = Column(String(36), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=True)
    
    # Role and status
    role = Column(String(50), default="viewer")  # super_admin, org_admin, transformer, reviewer, viewer
    status = Column(String(20), default="pending")  # active, pending, disabled
    
    # Password management
    must_change_password = Column(Boolean, default=False)  # Force password change on first login
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_login_at = Column(DateTime)
    
    # Relationships
    organization = relationship("Organization", back_populates="users")
    sessions = relationship("Session", back_populates="user", cascade="all, delete-orphan")
    audit_logs = relationship("AuditLog", back_populates="user", cascade="all, delete-orphan")
    
    # Indexes
    __table_args__ = (
        Index('ix_users_org_id', 'org_id'),
    )


class Session(Base):
    """User session for JWT token tracking"""
    __tablename__ = "sessions"
    
    id = Column(String(36), primary_key=True)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    
    # Token tracking
    token_hash = Column(String(255), nullable=False)  # SHA256 hash of JWT
    
    # Session metadata
    expires_at = Column(DateTime, nullable=False)
    ip_address = Column(String(45))  # IPv6 compatible
    user_agent = Column(Text)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    last_used_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    user = relationship("User", back_populates="sessions")
    
    # Indexes
    __table_args__ = (
        Index('ix_sessions_user_id', 'user_id'),
        Index('ix_sessions_token_hash', 'token_hash'),
        Index('ix_sessions_expires_at', 'expires_at'),
    )


class MagicLink(Base):
    """Magic link for passwordless authentication"""
    __tablename__ = "magic_links"
    
    id = Column(String(36), primary_key=True)
    email = Column(String(255), nullable=False, index=True)
    
    # Token (hashed)
    token_hash = Column(String(255), nullable=False)
    
    # Expiration and usage
    expires_at = Column(DateTime, nullable=False)
    used = Column(Boolean, default=False)
    used_at = Column(DateTime)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Indexes
    __table_args__ = (
        Index('ix_magic_links_token_hash', 'token_hash'),
        Index('ix_magic_links_expires_at', 'expires_at'),
    )


class AuditLog(Base):
    """Audit log for security and compliance"""
    __tablename__ = "audit_logs"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # Organization and user context
    org_id = Column(String(36), ForeignKey("organizations.id", ondelete="SET NULL"), nullable=True)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    
    # Action details
    action = Column(String(100), nullable=False)  # e.g., "user.login", "dataset.upload", "transform.export"
    entity_type = Column(String(50))  # e.g., "dataset", "transform_job", "user"
    entity_id = Column(String(36))
    
    # Request context
    ip_address = Column(String(45))
    user_agent = Column(Text)
    
    # Additional metadata
    meta_json = Column(JSON)  # Flexible storage for action-specific data
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    
    # Relationships
    organization = relationship("Organization", back_populates="audit_logs")
    user = relationship("User", back_populates="audit_logs")
    
    # Indexes
    __table_args__ = (
        Index('ix_audit_logs_org_id', 'org_id'),
        Index('ix_audit_logs_user_id', 'user_id'),
        Index('ix_audit_logs_action', 'action'),
        Index('ix_audit_logs_entity', 'entity_type', 'entity_id'),
    )


# =============================================================================
# DATA MODELS
# =============================================================================

class Dataset(Base):
    """Stores uploaded SAV dataset metadata"""
    __tablename__ = "datasets"
    
    id = Column(String(36), primary_key=True)
    filename = Column(String(255), nullable=False)
    original_filename = Column(String(255), nullable=False)
    file_path = Column(String(500), nullable=False)
    
    # Multi-tenant isolation
    org_id = Column(String(36), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=True)
    created_by = Column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    
    # Basic stats
    n_rows = Column(Integer, nullable=False)
    n_cols = Column(Integer, nullable=False)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Quality metrics
    overall_completion_rate = Column(Float)
    data_quality_score = Column(Float)  # 0-100
    digital_twin_readiness = Column(String(20))  # green/yellow/red
    
    # Analysis results (JSON)
    variables_meta = Column(JSON)  # Full variable metadata
    quality_report = Column(JSON)  # Detailed quality analysis
    transformation_analysis = Column(JSON)  # Transformation recommendations
    smart_filters = Column(JSON)  # Saved smart filters for this dataset
    
    # Relationships
    organization = relationship("Organization", back_populates="datasets")
    variables = relationship("Variable", back_populates="dataset", cascade="all, delete-orphan")
    exports = relationship("ExportHistory", back_populates="dataset", cascade="all, delete-orphan")
    
    # Indexes for tenant isolation
    __table_args__ = (
        Index('ix_datasets_org_id', 'org_id'),
        Index('ix_datasets_created_by', 'created_by'),
    )


class Variable(Base):
    """Stores individual variable metadata"""
    __tablename__ = "variables"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    dataset_id = Column(String(36), ForeignKey("datasets.id", ondelete="CASCADE"), nullable=False)
    
    code = Column(String(100), nullable=False)
    label = Column(Text)
    var_type = Column(String(50))  # single_choice, multi_choice, numeric, text, date, scale
    measure = Column(String(50))   # nominal, ordinal, scale
    
    # Statistics
    cardinality = Column(Integer)
    response_count = Column(Integer)
    response_rate = Column(Float)
    missing_count = Column(Integer)
    
    # Value labels (JSON)
    value_labels = Column(JSON)
    missing_values = Column(JSON)
    
    # Quality flags
    has_issues = Column(Boolean, default=False)
    issue_details = Column(JSON)
    
    # Relationships
    dataset = relationship("Dataset", back_populates="variables")


class ExportHistory(Base):
    """Tracks export history"""
    __tablename__ = "export_history"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    dataset_id = Column(String(36), ForeignKey("datasets.id", ondelete="CASCADE"), nullable=False)
    
    # Multi-tenant isolation
    org_id = Column(String(36), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=True)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    
    export_type = Column(String(50), nullable=False)  # excel, json, report, summary
    file_path = Column(String(500))
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    dataset = relationship("Dataset", back_populates="exports")
    
    # Indexes
    __table_args__ = (
        Index('ix_export_history_org_id', 'org_id'),
    )


class AnalysisHistory(Base):
    """Stores analysis snapshots for comparison"""
    __tablename__ = "analysis_history"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    dataset_id = Column(String(36), ForeignKey("datasets.id", ondelete="CASCADE"), nullable=False)
    
    analysis_type = Column(String(50), nullable=False)  # quality, transformation, summary
    results = Column(JSON)
    created_at = Column(DateTime, default=datetime.utcnow)


class TransformJobStatus(enum.Enum):
    """Status for transform jobs"""
    IDLE = "idle"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"


class TransformJob(Base):
    """Stores twin transformation job state and progress"""
    __tablename__ = "transform_jobs"
    
    id = Column(String(36), primary_key=True)
    dataset_id = Column(String(36), nullable=False)  # No foreign key - dataset may be in-memory cache
    
    # Multi-tenant isolation
    org_id = Column(String(36), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=True)
    created_by = Column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    
    # Job status
    status = Column(String(20), default="idle")  # idle, running, paused, completed, failed
    
    # Configuration
    chunk_size = Column(Integer, default=30)  # Number of columns per chunk
    row_concurrency = Column(Integer, default=5)  # Parallel row processing
    row_limit = Column(Integer, nullable=True)  # Max rows to process (None = all rows)
    
    # Progress tracking
    total_rows = Column(Integer, default=0)  # Total rows in dataset
    current_row_index = Column(Integer, default=0)
    processed_rows = Column(Integer, default=0)
    failed_rows = Column(Integer, default=0)
    
    # Statistics
    stats = Column(JSON)  # {totalColumns, processedColumns, emptySkipped, excludedSkipped, errors, retries}
    
    # Exclude configuration
    exclude_options_config = Column(JSON)  # {patternKey: boolean, perVariable: {varName: [values]}}
    admin_columns = Column(JSON)  # List of admin column names to exclude
    respondent_id_column = Column(String(100))  # Column to use as respondent ID
    
    # Column analysis (cached)
    column_analysis = Column(JSON)  # Cached column analysis result
    
    # Error tracking
    last_error = Column(Text)
    error_count = Column(Integer, default=0)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    started_at = Column(DateTime)
    completed_at = Column(DateTime)
    
    # Checkpoint system
    last_checkpoint = Column(Integer, default=0)  # Last row index saved as checkpoint
    checkpoint_timestamp = Column(DateTime)  # When checkpoint was saved
    
    # Relationships
    results = relationship("TransformResult", back_populates="job", cascade="all, delete-orphan")
    exclude_patterns = relationship("ExcludePattern", back_populates="job", cascade="all, delete-orphan")
    
    # Indexes for tenant isolation
    __table_args__ = (
        Index('ix_transform_jobs_org_id', 'org_id'),
        Index('ix_transform_jobs_dataset_id', 'dataset_id'),
    )


class TransformResult(Base):
    """Stores transformation results per respondent row"""
    __tablename__ = "transform_results"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    job_id = Column(String(36), ForeignKey("transform_jobs.id", ondelete="CASCADE"), nullable=False)
    
    # Row identification
    row_index = Column(Integer, nullable=False)
    respondent_id = Column(String(100))  # If available in data
    
    # Transformation output
    sentences = Column(JSON)  # [{sentence: str, sources: [str], confidence: str, notes: str}]
    
    # Excluded information
    excluded = Column(JSON)  # {emptyVars: [str], excludedByOption: [str], adminVars: [str]}
    
    # Trace for debugging
    raw_trace = Column(JSON)  # {perChunk: [{chunkIndex, sentVars, modelRequestId, parsedOk, errors}]}
    
    # Status
    status = Column(String(20), default="pending")  # pending, processing, completed, failed
    error_message = Column(Text)
    retry_count = Column(Integer, default=0)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    processed_at = Column(DateTime)
    
    # Relationships
    job = relationship("TransformJob", back_populates="results")


class ExcludePattern(Base):
    """Stores exclude patterns detected and configured for a transform job"""
    __tablename__ = "exclude_patterns"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    job_id = Column(String(36), ForeignKey("transform_jobs.id", ondelete="CASCADE"), nullable=False)
    
    # Pattern identification
    pattern_key = Column(String(100), nullable=False)  # e.g., "none_of_above", "prefer_not_to_say"
    pattern_label = Column(String(255))  # Human readable label
    
    # Detection
    detected_values = Column(JSON)  # [{value: any, label: str, count: int, variables: [str]}]
    detected_count = Column(Integer, default=0)
    
    # User configuration
    is_excluded = Column(Boolean, default=True)  # User's choice to exclude or include
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    job = relationship("TransformJob", back_populates="exclude_patterns")
