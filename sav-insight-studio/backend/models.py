"""
SQLAlchemy database models
"""
from sqlalchemy import Column, Integer, String, Float, DateTime, Text, JSON, Boolean, ForeignKey, Enum
from sqlalchemy.orm import relationship
from datetime import datetime
import enum
from database import Base


class QualityStatus(enum.Enum):
    """Data quality status for digital twin readiness"""
    GREEN = "green"      # Ready for digital twin
    YELLOW = "yellow"    # Needs attention
    RED = "red"          # Not suitable without major fixes


class Dataset(Base):
    """Stores uploaded SAV dataset metadata"""
    __tablename__ = "datasets"
    
    id = Column(String(36), primary_key=True)
    filename = Column(String(255), nullable=False)
    original_filename = Column(String(255), nullable=False)
    file_path = Column(String(500), nullable=False)
    
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
    
    # Relationships
    variables = relationship("Variable", back_populates="dataset", cascade="all, delete-orphan")
    exports = relationship("ExportHistory", back_populates="dataset", cascade="all, delete-orphan")


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
    
    export_type = Column(String(50), nullable=False)  # excel, json, report, summary
    file_path = Column(String(500))
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    dataset = relationship("Dataset", back_populates="exports")


class AnalysisHistory(Base):
    """Stores analysis snapshots for comparison"""
    __tablename__ = "analysis_history"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    dataset_id = Column(String(36), ForeignKey("datasets.id", ondelete="CASCADE"), nullable=False)
    
    analysis_type = Column(String(50), nullable=False)  # quality, transformation, summary
    results = Column(JSON)
    created_at = Column(DateTime, default=datetime.utcnow)

