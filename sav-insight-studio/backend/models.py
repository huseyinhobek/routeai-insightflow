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
    
    # Versioning
    version = Column(Integer, default=1)  # Increment on upload/merge for cache invalidation
    
    # Relationships
    organization = relationship("Organization", back_populates="datasets")
    variables = relationship("Variable", back_populates="dataset", cascade="all, delete-orphan")
    exports = relationship("ExportHistory", back_populates="dataset", cascade="all, delete-orphan")
    respondents = relationship("Respondent", back_populates="dataset", cascade="all, delete-orphan")
    audiences = relationship("Audience", back_populates="dataset", cascade="all, delete-orphan")
    threads = relationship("Thread", back_populates="dataset", cascade="all, delete-orphan")
    
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
    question_text = Column(Text)  # Full question text
    section_path = Column(String(500))  # Section/path in questionnaire
    var_type = Column(String(50))  # single_choice, multi_choice, numeric, text, date, scale
    measure = Column(String(50))   # nominal, ordinal, scale
    
    # Demographics flag
    is_demographic = Column(Boolean, default=False)  # True for demographic variables
    
    # Statistics
    cardinality = Column(Integer)
    response_count = Column(Integer)
    response_rate = Column(Float)
    missing_count = Column(Integer)
    stats_json = Column(JSON)  # Additional statistics in JSON format
    
    # Value labels (JSON) - for backward compatibility, but ValueLabel table is primary
    value_labels = Column(JSON)
    missing_values = Column(JSON)
    
    # Quality flags
    has_issues = Column(Boolean, default=False)
    issue_details = Column(JSON)
    
    # Relationships
    dataset = relationship("Dataset", back_populates="variables")
    value_labels_list = relationship("ValueLabel", back_populates="variable", cascade="all, delete-orphan")
    responses = relationship("Response", back_populates="variable", cascade="all, delete-orphan")
    utterances = relationship("Utterance", back_populates="variable", cascade="all, delete-orphan")
    
    # Unique constraint
    __table_args__ = (
        Index('ix_variables_dataset_code', 'dataset_id', 'code', unique=True),
        Index('ix_variables_dataset_id', 'dataset_id'),
        Index('ix_variables_code', 'code'),
    )


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


# =============================================================================
# RESEARCH WORKFLOW MODELS
# =============================================================================

class ValueLabel(Base):
    """Stores value labels for variables"""
    __tablename__ = "value_labels"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    variable_id = Column(Integer, ForeignKey("variables.id", ondelete="CASCADE"), nullable=False)
    
    value_code = Column(Text, nullable=False)  # TEXT to support both int and string
    value_label = Column(Text, nullable=False)
    order_index = Column(Integer)  # Order in which values should be displayed
    
    # Flags
    is_missing_label = Column(Boolean, default=False)  # True if this is a missing value label
    is_other = Column(Boolean, default=False)  # True if this is "Other (specify)" type
    
    # Relationships
    variable = relationship("Variable", back_populates="value_labels_list")
    
    # Indexes
    __table_args__ = (
        Index('ix_value_labels_variable_id', 'variable_id'),
        Index('ix_value_labels_variable_code', 'variable_id', 'value_code'),
    )


class Respondent(Base):
    """Stores respondent/participant records"""
    __tablename__ = "respondents"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    dataset_id = Column(String(36), ForeignKey("datasets.id", ondelete="CASCADE"), nullable=False)
    
    respondent_key = Column(String(255))  # Original respondent ID/key from dataset
    weight = Column(Float)  # Weight if dataset has weights
    meta_json = Column(JSON)  # Additional metadata
    
    # Relationships
    dataset = relationship("Dataset", back_populates="respondents")
    responses = relationship("Response", back_populates="respondent", cascade="all, delete-orphan")
    utterances = relationship("Utterance", back_populates="respondent", cascade="all, delete-orphan")
    audience_members = relationship("AudienceMember", back_populates="respondent", cascade="all, delete-orphan")
    
    # Indexes
    __table_args__ = (
        Index('ix_respondents_dataset_id', 'dataset_id'),
        Index('ix_respondents_key', 'dataset_id', 'respondent_key'),
    )


class MissingType(enum.Enum):
    """Missing value type"""
    NONE = "none"
    SYSTEM = "system"
    USER = "user"


class Response(Base):
    """Stores individual responses/answers"""
    __tablename__ = "responses"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    respondent_id = Column(Integer, ForeignKey("respondents.id", ondelete="CASCADE"), nullable=False)
    variable_id = Column(Integer, ForeignKey("variables.id", ondelete="CASCADE"), nullable=False)
    
    value_code = Column(Text, nullable=False)  # TEXT to support both int and string codes
    numeric_value = Column(Float)  # Numeric value if applicable
    verbatim_text = Column(Text)  # Open-text response if applicable
    is_missing = Column(Boolean, default=False)
    missing_type = Column(String(20))  # "system", "user", "none"
    
    # Relationships
    respondent = relationship("Respondent", back_populates="responses")
    variable = relationship("Variable", back_populates="responses")
    # utterances relationship disabled until response_id column is added to Utterance table
    # utterances = relationship("Utterance", back_populates="response", cascade="all, delete-orphan")
    
    # Indexes for performance
    __table_args__ = (
        Index('ix_responses_respondent_variable', 'respondent_id', 'variable_id'),
        Index('ix_responses_variable_value', 'variable_id', 'value_code'),
        Index('ix_responses_respondent_id', 'respondent_id'),
        Index('ix_responses_variable_id', 'variable_id'),
    )


class Utterance(Base):
    """Stores deterministic template-based sentences for RAG"""
    __tablename__ = "utterances"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    respondent_id = Column(Integer, ForeignKey("respondents.id", ondelete="CASCADE"), nullable=False)
    variable_id = Column(Integer, ForeignKey("variables.id", ondelete="CASCADE"), nullable=False)
    # Optional direct link to the originating response row for stronger uniqueness guarantees
    # NOTE: response_id column not yet in database - will be added via migration later
    # response_id = Column(Integer, ForeignKey("responses.id", ondelete="CASCADE"), nullable=True)
    value_code = Column(Text)
    
    utterance_text = Column(Text)  # Canonical or original sentence
    display_text = Column(Text)  # Human-friendly format (for UI)
    # Always "Q: {question_text} | A: {value_label or numeric_value or verbatim} | var: {var_code} | U: {display_text}"
    text_for_embedding = Column(Text)
    language = Column(String(10), default="en")  # en, es, tr, etc.
    provenance_json = Column(JSON)  # {respondent_id, variable_id, value_code, question_text, ...}
    
    # Relationships
    respondent = relationship("Respondent", back_populates="utterances")
    variable = relationship("Variable", back_populates="utterances")
    # response relationship disabled until response_id column is added to database
    # response = relationship("Response", back_populates="utterances")
    
    # Indexes / constraints
    __table_args__ = (
        Index('ix_utterances_respondent_id', 'respondent_id'),
        Index('ix_utterances_variable_id', 'variable_id'),
        Index('ix_utterances_respondent_variable', 'respondent_id', 'variable_id'),
        # response_id unique index disabled until column is added
        # Index('ix_utterances_response_id_unique', 'response_id', unique=True),
    )


class ObjectType(enum.Enum):
    """Object type for embeddings"""
    VARIABLE = "variable"
    UTTERANCE = "utterance"


class Embedding(Base):
    """Stores vector embeddings for variables and utterances"""
    __tablename__ = "embeddings"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    object_type = Column(String(20), nullable=False)  # 'variable' or 'utterance'
    object_id = Column(Integer, nullable=False)  # ID of variable or utterance
    dataset_id = Column(String(36), ForeignKey("datasets.id", ondelete="CASCADE"), nullable=False)
    
    vector = Column(Text)  # Vector stored as text (pgvector type in PostgreSQL)
    text_for_embedding = Column(Text)  # Text that was embedded
    meta_json = Column(JSON)  # Additional metadata
    
    # Relationships - Note: polymorphic relationships are complex, will handle in service layer
    # Instead of complex relationships, use object_type and object_id for lookups
    
    # Indexes - pgvector HNSW index will be created separately
    __table_args__ = (
        Index('ix_embeddings_object', 'object_type', 'object_id'),
        Index('ix_embeddings_dataset_id', 'dataset_id'),
        Index('ix_embeddings_dataset_type', 'dataset_id', 'object_type'),
    )


class Audience(Base):
    """Stores audience/segment definitions"""
    __tablename__ = "audiences"
    
    id = Column(String(36), primary_key=True)
    dataset_id = Column(String(36), ForeignKey("datasets.id", ondelete="CASCADE"), nullable=False)
    
    name = Column(String(255), nullable=False)
    description = Column(Text)
    filter_json = Column(JSON, nullable=False)  # Filter definition
    
    size_n = Column(Integer)  # Number of respondents in audience
    active_membership_version = Column(Integer, default=1)  # Active membership version for atomic swap
    
    share_token = Column(String(100), unique=True)  # Token for sharing
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    dataset = relationship("Dataset", back_populates="audiences")
    members = relationship("AudienceMember", back_populates="audience", cascade="all, delete-orphan")
    threads = relationship("Thread", back_populates="audience", cascade="all, delete-orphan")
    
    # Indexes
    __table_args__ = (
        Index('ix_audiences_dataset_id', 'dataset_id'),
    )


class AudienceMember(Base):
    """Materialized membership table with versioning for atomic swaps"""
    __tablename__ = "audience_members"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    audience_id = Column(String(36), ForeignKey("audiences.id", ondelete="CASCADE"), nullable=False)
    version = Column(Integer, nullable=False)  # Membership version
    respondent_id = Column(Integer, ForeignKey("respondents.id", ondelete="CASCADE"), nullable=False)
    
    # Relationships
    audience = relationship("Audience", back_populates="members")
    respondent = relationship("Respondent", back_populates="audience_members")
    
    # Unique constraint and indexes
    __table_args__ = (
        Index('ix_audience_members_audience_version', 'audience_id', 'version'),
        Index('ix_audience_members_audience_id', 'audience_id'),
        Index('ix_audience_members_respondent_id', 'respondent_id'),
        Index('ix_audience_members_unique', 'audience_id', 'version', 'respondent_id', unique=True),
    )


class ThreadStatus(enum.Enum):
    """Thread status"""
    PROCESSING = "processing"
    READY = "ready"
    ERROR = "error"


class Thread(Base):
    """Stores persistent Q&A sessions"""
    __tablename__ = "threads"
    
    id = Column(String(36), primary_key=True)
    dataset_id = Column(String(36), ForeignKey("datasets.id", ondelete="CASCADE"), nullable=False)
    audience_id = Column(String(36), ForeignKey("audiences.id", ondelete="SET NULL"), nullable=True)
    
    title = Column(String(255))
    status = Column(String(20), default="ready")  # processing, ready, error
    share_token = Column(String(100), unique=True)
    last_error = Column(Text)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    dataset = relationship("Dataset", back_populates="threads")
    audience = relationship("Audience", back_populates="threads")
    questions = relationship("ThreadQuestion", back_populates="thread", cascade="all, delete-orphan")
    
    # Indexes
    __table_args__ = (
        Index('ix_threads_dataset_id', 'dataset_id'),
        Index('ix_threads_audience_id', 'audience_id'),
    )


class QuestionMode(enum.Enum):
    """Question routing mode"""
    STRUCTURED = "structured"
    RAG = "rag"


class ThreadQuestion(Base):
    """Stores questions within a thread"""
    __tablename__ = "thread_questions"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    thread_id = Column(String(36), ForeignKey("threads.id", ondelete="CASCADE"), nullable=False)
    
    question_text = Column(Text, nullable=False)
    normalized_question = Column(Text, nullable=False)  # Normalized version for caching
    mode = Column(String(20))  # structured or rag
    mapped_variable_ids = Column(JSON)  # List of variable IDs if structured mode
    negation_flags_json = Column(JSON)  # Negation AST structure
    status = Column(String(20), default="processing")  # processing, ready, error
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    thread = relationship("Thread", back_populates="questions")
    result = relationship("ThreadResult", back_populates="question", uselist=False, cascade="all, delete-orphan")
    
    # Indexes
    __table_args__ = (
        Index('ix_thread_questions_thread_id', 'thread_id'),
    )


class ThreadResult(Base):
    """Stores results/answers for thread questions"""
    __tablename__ = "thread_results"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    thread_question_id = Column(Integer, ForeignKey("thread_questions.id", ondelete="CASCADE"), nullable=False)
    
    dataset_version = Column(Integer)  # Dataset version when result was created
    evidence_json = Column(JSON)  # Structured evidence data
    chart_json = Column(JSON)  # Chart data
    narrative_text = Column(Text)  # LLM-generated narrative
    citations_json = Column(JSON)  # Citations for RAG mode
    mapping_debug_json = Column(JSON)  # Mapping rationale, candidate list, scores
    model_info_json = Column(JSON)  # Model information
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    question = relationship("ThreadQuestion", back_populates="result")
    
    # Indexes
    __table_args__ = (
        Index('ix_thread_results_question_id', 'thread_question_id'),
    )


class CacheAnswer(Base):
    """Cache for thread answers to avoid recomputation"""
    __tablename__ = "cache_answers"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    dataset_id = Column(String(36), ForeignKey("datasets.id", ondelete="CASCADE"), nullable=False)
    dataset_version = Column(Integer, nullable=False)
    audience_id = Column(String(36), ForeignKey("audiences.id", ondelete="CASCADE"), nullable=True)
    
    normalized_question = Column(Text, nullable=False)
    mode = Column(String(20), nullable=False)
    key_hash = Column(String(64), nullable=False, unique=True)  # Hash of cache key
    
    thread_result_id = Column(Integer, ForeignKey("thread_results.id", ondelete="CASCADE"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Indexes
    __table_args__ = (
        Index('ix_cache_answers_key_hash', 'key_hash'),
        Index('ix_cache_answers_dataset', 'dataset_id', 'dataset_version', 'audience_id'),
    )
