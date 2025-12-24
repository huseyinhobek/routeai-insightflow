"""
SAV Insight Studio API
Comprehensive SPSS (.sav) file analysis platform with PostgreSQL storage
"""
from fastapi import FastAPI, UploadFile, File, HTTPException, Depends, BackgroundTasks, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from sqlalchemy.orm import Session
from typing import Optional, List, Any, Dict, Set
import pandas as pd
import pyreadstat
import os
import json
import uuid
import re
import logging
from datetime import datetime
from pathlib import Path
import numpy as np
import threading
from io import BytesIO
from dataclasses import asdict

# Local imports
from config import settings
from database import get_db, init_db, engine, Base, DATABASE_AVAILABLE
from models import Dataset, Variable, ExportHistory, AnalysisHistory, TransformJob, TransformResult, ExcludePattern, AuditLog, User, Organization
from services.quality_analyzer import QualityAnalyzer, QualityReport
from services.export_service import ExportService
from services.transform_service import transform_service, EXCLUDE_PATTERNS
from services.smart_filter_service import smart_filter_service
from dataclasses import asdict as dataclass_asdict

# Auth imports
from routers import auth_router, admin_router
from middleware.org_scope import OrgScopeMiddleware, get_org_id_from_request, apply_org_filter
from middleware.security import SecurityHeadersMiddleware
from auth.dependencies import get_current_user, get_current_user_optional, require_permission

# Create upload directory
UPLOAD_DIR = Path(settings.UPLOAD_DIR)
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

# Setup logger
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="SAV Insight Studio API",
    description="Comprehensive SPSS data analysis platform",
    version="2.0.0"
)

# Security middleware
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(OrgScopeMiddleware)

# CORS middleware - Use configured origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*", "X-CSRF-Token"],
    expose_headers=["*"],
)

# Include auth and admin routers
app.include_router(auth_router)
app.include_router(admin_router)

# Explicit OPTIONS handler for CORS preflight
@app.options("/{full_path:path}")
async def options_handler(full_path: str):
    return {"message": "OK"}

# Exception handler to ensure CORS headers are always sent on errors
@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc: HTTPException):
    from fastapi.responses import JSONResponse
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail},
        headers={
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "*",
            "Access-Control-Allow-Headers": "*",
        }
    )

# In-memory cache for dataframes (to avoid re-reading files)
# NOTE: This cache is cleared on restart. DataFrames are loaded on-demand from disk.
# For large datasets, consider implementing LRU cache with size limits.
_dataframe_cache = {}
_MAX_CACHE_SIZE = 5  # Maximum number of dataframes to keep in memory

# Prevent duplicate background runs inside a single backend process
_transform_bg_running: set[str] = set()
_transform_bg_lock = threading.Lock()


@app.on_event("startup")
async def startup_event():
    """Initialize database on startup"""
    try:
        Base.metadata.create_all(bind=engine)
        print("[OK] Database tables created successfully")
    except Exception as e:
        print(f"[UYARI] Database initialization warning: {e}")
        print("[UYARI] Running without database - data will be stored in memory only")


def detect_variable_type(series: pd.Series, value_labels: dict) -> str:
    """Detect variable type based on data characteristics"""
    if series.dtype == 'object':
        return 'text'
    elif pd.api.types.is_datetime64_any_dtype(series):
        return 'date'
    elif pd.api.types.is_numeric_dtype(series):
        if value_labels:
            unique_vals = series.dropna().unique()
            if len(unique_vals) <= 10:
                return 'single_choice'
            else:
                return 'scale'
        else:
            return 'numeric'
    return 'unknown'


def detect_measure_type(var_type: str, cardinality: int) -> str:
    """Detect measure type (nominal, ordinal, scale)"""
    if var_type in ['single_choice', 'multi_choice', 'text']:
        return 'nominal' if cardinality > 2 else 'ordinal'
    elif var_type == 'scale':
        return 'scale'
    elif var_type == 'numeric':
        return 'scale'
    return 'unknown'


def process_sav_file(file_path: Path, original_filename: str) -> dict:
    """Process SAV file and extract metadata with quality analysis"""
    df, meta = pyreadstat.read_sav(str(file_path))
    
    variables = []
    
    for col in df.columns:
        series = df[col]
        value_labels = meta.variable_value_labels.get(col, {}) if hasattr(meta, 'variable_value_labels') else {}
        variable_label = meta.column_names_to_labels.get(col, col) if hasattr(meta, 'column_names_to_labels') else col
        
        var_type = detect_variable_type(series, value_labels)
        cardinality = series.nunique()
        measure = detect_measure_type(var_type, cardinality)
        
        value_labels_list = [{"value": k, "label": v} for k, v in value_labels.items()]
        
        missing_values = None
        if hasattr(meta, 'missing_ranges') and col in meta.missing_ranges:
            missing_values = {"systemMissing": True, "userMissingValues": []}
        
        total = len(series)
        non_missing = series.notna().sum()
        response_rate = (non_missing / total * 100) if total > 0 else 0
        
        variables.append({
            "code": col,
            "label": variable_label,
            "type": var_type,
            "measure": measure,
            "valueLabels": value_labels_list,
            "missingValues": missing_values,
            "cardinality": int(cardinality),
            "responseCount": int(non_missing),
            "responseRate": round(response_rate, 2)
        })
    
    # Run quality analysis
    analyzer = QualityAnalyzer(df, meta, variables)
    quality_report = analyzer.analyze()
    quality_dict = asdict(quality_report)
    
    dataset_id = str(uuid.uuid4())
    
    result_info = {
        "id": dataset_id,
        "filename": file_path.name,
        "original_filename": original_filename,
        "file_path": str(file_path),
        "nRows": len(df),
        "nCols": len(df.columns),
        "createdAt": datetime.now().isoformat(),
        "variables": variables,
        "qualityReport": quality_dict,
        "overallCompletionRate": quality_dict["completeness_score"],
        "dataQualityScore": quality_dict["overall_score"],
        "digitalTwinReadiness": quality_dict["digital_twin_readiness"]
    }
    
    # Cache dataframe and info (with size limit)
    # Remove oldest entry if cache is full
    if len(_dataframe_cache) >= _MAX_CACHE_SIZE:
        oldest_key = next(iter(_dataframe_cache))
        del _dataframe_cache[oldest_key]
    
    _dataframe_cache[dataset_id] = {
        "df": df,
        "meta": meta,
        "info": result_info
    }
    
    return result_info


def save_to_database(db: Session, dataset_info: dict) -> Dataset:
    """Save dataset to database"""
    if db is None or not DATABASE_AVAILABLE:
        print("[UYARI] Veritabani mevcut degil, sadece in-memory saklama yapiliyor")
        return None
        
    try:
        # Convert numpy types to Python native types for database
        overall_completion_rate = dataset_info.get("overallCompletionRate")
        if overall_completion_rate is not None:
            overall_completion_rate = float(overall_completion_rate)
        
        data_quality_score = dataset_info.get("dataQualityScore")
        if data_quality_score is not None:
            data_quality_score = float(data_quality_score)
        
        dataset = Dataset(
            id=dataset_info["id"],
            filename=dataset_info["filename"],
            original_filename=dataset_info["original_filename"],
            file_path=dataset_info["file_path"],
            n_rows=dataset_info["nRows"],
            n_cols=dataset_info["nCols"],
            overall_completion_rate=overall_completion_rate,
            data_quality_score=data_quality_score,
            digital_twin_readiness=dataset_info.get("digitalTwinReadiness"),
            variables_meta=dataset_info["variables"],
            quality_report=dataset_info.get("qualityReport")
        )
        
        db.add(dataset)
        
        # Variables are stored in variables_meta JSON field, no need for separate Variable table
        # This avoids issues with numpy types and reduces database complexity
        # If you need to query variables separately, use JSON queries on variables_meta
        
        db.commit()
        db.refresh(dataset)
        return dataset
    except Exception as e:
        if db:
            db.rollback()
        print(f"[HATA] Veritabani kayit hatasi: {e}")
        import traceback
        traceback.print_exc()
        return None


def get_dataframe(dataset_id: str, db: Session = None) -> tuple:
    """Get dataframe from cache or re-read from file"""
    # Check cache first
    if dataset_id in _dataframe_cache:
        cached = _dataframe_cache[dataset_id]
        return cached["df"], cached["meta"]
    
    # Try to get from database and load from disk
    if db:
        dataset = db.query(Dataset).filter(Dataset.id == dataset_id).first()
        if dataset:
            file_path = Path(dataset.file_path)
            # Also check uploads directory if file_path doesn't exist
            if not file_path.exists():
                file_path = UPLOAD_DIR / file_path.name
            
            if file_path.exists():
                try:
                    df, meta = pyreadstat.read_sav(str(file_path))
                    # Cache with size limit (simple FIFO eviction)
                    if len(_dataframe_cache) >= _MAX_CACHE_SIZE:
                        # Remove oldest entry (simple FIFO)
                        oldest_key = next(iter(_dataframe_cache))
                        del _dataframe_cache[oldest_key]
                    
                    # Keep minimal info so list endpoints don't crash if they iterate cache
                    _dataframe_cache[dataset_id] = {
                        "df": df,
                        "meta": meta,
                        "info": {
                            "id": dataset.id,
                            "filename": dataset.filename,
                            "original_filename": dataset.original_filename,
                            "file_path": dataset.file_path,
                            "nRows": dataset.n_rows,
                            "nCols": dataset.n_cols,
                            "createdAt": dataset.created_at.isoformat() if dataset.created_at else None,
                            "dataQualityScore": dataset.data_quality_score,
                            "digitalTwinReadiness": dataset.digital_twin_readiness,
                            "overallCompletionRate": dataset.overall_completion_rate,
                        },
                    }
                    return df, meta
                except Exception as e:
                    print(f"Error loading dataset {dataset_id} from {file_path}: {e}")
                    return None, None
    
    # Try cache directory (for in-memory datasets)
    if dataset_id in _dataframe_cache:
        cached = _dataframe_cache[dataset_id]
        return cached["df"], cached["meta"]
    
    return None, None


def is_value_missing(val) -> bool:
    """Check if a single value is considered missing (implicit)"""
    if pd.isna(val):
        return True
    if isinstance(val, str):
        if val.strip() == '':
            return True
    return False


def get_explicit_missing_codes(var_info: dict, meta) -> set:
    """
    Extract explicit missing codes from SPSS metadata.
    Returns a set of values that should be treated as missing.
    """
    missing_codes = set()
    
    # Check missingValues from var_info
    if var_info and var_info.get("missingValues"):
        missing_vals = var_info["missingValues"]
        if isinstance(missing_vals, dict) and missing_vals.get("userMissingValues"):
            for val in missing_vals["userMissingValues"]:
                missing_codes.add(val)
    
    # Check SPSS meta missing_ranges
    var_name = var_info.get("code")
    if meta and hasattr(meta, 'missing_ranges') and var_name in meta.missing_ranges:
        ranges = meta.missing_ranges[var_name]
        # ranges is typically a dict with 'values' or ranges
        if isinstance(ranges, dict):
            if 'values' in ranges:
                for val in ranges['values']:
                    missing_codes.add(val)
    
    # Check value labels for common non-substantive answers
    non_substantive_keywords = [
        "don't know", "dont know", "prefer not to say", "refused", 
        "not applicable", "n/a", "no answer", "missing", "skip"
    ]
    
    if var_info and var_info.get("valueLabels"):
        for vl in var_info["valueLabels"]:
            label = vl.get("label", "").lower()
            for keyword in non_substantive_keywords:
                if keyword in label:
                    missing_codes.add(vl.get("value"))
                    break
    
    return missing_codes


def compute_variable_stats(df: pd.DataFrame, var_name: str, var_info: dict, meta) -> dict:
    """
    Compute comprehensive variable statistics with correct missing handling.
    
    Returns:
        {
            "totalN": int,
            "validN": int,
            "missingN": int,
            "missingPercentOfTotal": float,
            "frequencies": [
                {
                    "value": val,
                    "label": str,
                    "count": int,
                    "percentOfTotal": float,
                    "percentOfValid": float
                },
                ...
            ],
            "hasManyCategories": bool,
            "categoryCount": int
        }
    """
    series = df[var_name]
    total_n = len(df)
    
    # Get explicit missing codes
    explicit_missing = get_explicit_missing_codes(var_info, meta)
    
    # Identify missing values
    missing_mask = series.apply(is_value_missing)
    
    # Also mark explicit missing codes as missing
    if len(explicit_missing) > 0:
        explicit_mask = series.isin(explicit_missing)
        missing_mask = missing_mask | explicit_mask
    
    missing_n = int(missing_mask.sum())
    valid_n = total_n - missing_n
    missing_percent_of_total = round((missing_n / total_n * 100) if total_n > 0 else 0, 2)
    
    # Calculate frequencies for valid values only
    valid_series = series[~missing_mask]
    value_counts = valid_series.value_counts()
    
    frequencies = []
    for val, count in value_counts.items():
        label = str(val)
        
        # Try to find label from valueLabels
        if var_info.get("valueLabels"):
            label_match = next(
                (vl.get("label", str(vl.get("value"))) 
                 for vl in var_info.get("valueLabels", []) 
                 if vl.get("value") == val),
                str(val)
            )
            label = label_match
        
        percent_of_total = round((count / total_n * 100) if total_n > 0 else 0, 2)
        percent_of_valid = round((count / valid_n * 100) if valid_n > 0 else 0, 2)
        
        frequencies.append({
            "value": val if not pd.isna(val) else None,
            "label": label,
            "count": int(count),
            "percentOfTotal": percent_of_total,
            "percentOfValid": percent_of_valid
        })
    
    # Sort by count descending
    frequencies.sort(key=lambda x: x["count"], reverse=True)
    
    # Add missing row if there are any missing values
    if missing_n > 0:
        frequencies.append({
            "value": None,
            "label": "Missing / No answer",
            "count": missing_n,
            "percentOfTotal": missing_percent_of_total,
            "percentOfValid": 0.0  # Missing is not part of valid
        })
    
    category_count = len(value_counts)
    has_many_categories = category_count > 12
    
    return {
        "totalN": total_n,
        "validN": valid_n,
        "missingN": missing_n,
        "missingPercentOfTotal": missing_percent_of_total,
        "frequencies": frequencies,
        "hasManyCategories": has_many_categories,
        "categoryCount": category_count
    }


# Import audit service
from services.audit_service import (
    audit_dataset_upload, audit_dataset_delete, audit_dataset_export,
    audit_transform_start, audit_transform_pause, audit_transform_resume,
    audit_transform_export, audit_smart_filter_generate
)

# Import export policy
from services.export_policy import check_export_permission


# ==================== API ENDPOINTS ====================

@app.post("/api/datasets/upload")
async def upload_dataset(
    request: Request,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_optional),
):
    """Upload and process a SAV file"""
    # Validate filename
    if not file.filename:
        raise HTTPException(status_code=400, detail="Filename is required")
    
    if not file.filename.lower().endswith('.sav'):
        raise HTTPException(status_code=400, detail="Only .sav files are supported")
    
    file_path = UPLOAD_DIR / f"{uuid.uuid4()}.sav"
    
    try:
        # Read file content
        content = await file.read()
        
        # Validate file is not empty
        if len(content) == 0:
            raise HTTPException(status_code=400, detail="Uploaded file is empty")
        
        # Save file
        with open(file_path, "wb") as f:
            f.write(content)
        
        # Process SAV file
        try:
            dataset_info = process_sav_file(file_path, file.filename)
        except Exception as parse_error:
            import traceback
            error_trace = traceback.format_exc()
            print(f"[ERROR] Failed to parse SAV file: {str(parse_error)}")
            print(f"[ERROR] Traceback: {error_trace}")
            raise HTTPException(
                status_code=500, 
                detail=f"Failed to parse SAV file: {str(parse_error)}"
            )
        
        # Add org_id and created_by if user is authenticated
        if current_user:
            dataset_info["org_id"] = current_user.org_id
            dataset_info["created_by"] = current_user.id
        
        # Save to database
        saved_dataset = save_to_database(db, dataset_info)
        if not saved_dataset and db is not None and DATABASE_AVAILABLE:
            print(f"[UYARI] Dataset {dataset_info['id']} veritabanina kaydedilemedi, ancak dosya yuklendi")
        
        # Audit log
        audit_dataset_upload(
            db=db,
            request=request,
            dataset_id=dataset_info["id"],
            filename=dataset_info["original_filename"],
            n_rows=dataset_info["nRows"],
            n_cols=dataset_info["nCols"],
        )
        
        # Return response (without internal fields)
        return {
            "id": dataset_info["id"],
            "filename": dataset_info["original_filename"],
            "nRows": dataset_info["nRows"],
            "nCols": dataset_info["nCols"],
            "createdAt": dataset_info["createdAt"],
            "variables": dataset_info["variables"],
            "qualityReport": dataset_info["qualityReport"],
            "digitalTwinReadiness": dataset_info["digitalTwinReadiness"]
        }
    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        print(f"[ERROR] Upload error: {str(e)}")
        print(f"[ERROR] Traceback: {error_trace}")
        if file_path.exists():
            file_path.unlink()
        raise HTTPException(status_code=500, detail=f"Error processing file: {str(e)}")


@app.get("/api/datasets")
async def list_datasets(db: Session = Depends(get_db)):
    """List all previously uploaded datasets"""
    # First return from in-memory cache
    results = []
    
    for dataset_id, data in _dataframe_cache.items():
        info = data.get("info")
        if not isinstance(info, dict):
            continue
        results.append({
            "id": dataset_id,
            "filename": info.get("original_filename", info.get("filename")),
            "nRows": info.get("nRows"),
            "nCols": info.get("nCols"),
            "createdAt": info.get("createdAt"),
            "dataQualityScore": info.get("dataQualityScore"),
            "digitalTwinReadiness": info.get("digitalTwinReadiness"),
            "overallCompletionRate": info.get("overallCompletionRate")
        })
    
    # Then try database
    if db is not None and DATABASE_AVAILABLE:
        try:
            datasets = db.query(Dataset).order_by(Dataset.created_at.desc()).all()
            existing_ids = {r["id"] for r in results}
            
            for d in datasets:
                if d.id not in existing_ids:
                    results.append({
                        "id": d.id,
                        "filename": d.original_filename,
                        "nRows": d.n_rows,
                        "nCols": d.n_cols,
                        "createdAt": d.created_at.isoformat() if d.created_at else None,
                        "dataQualityScore": d.data_quality_score,
                        "digitalTwinReadiness": d.digital_twin_readiness,
                        "overallCompletionRate": d.overall_completion_rate
                    })
        except Exception as e:
            print(f"Database query error: {e}")
    
    # Sort by createdAt descending
    results.sort(key=lambda x: x.get("createdAt") or "", reverse=True)
    return results


@app.get("/api/datasets/{dataset_id}")
async def get_dataset(dataset_id: str, db: Session = Depends(get_db)):
    """Get dataset metadata"""
    # Try cache first - but only if we have complete info
    if dataset_id in _dataframe_cache and "info" in _dataframe_cache[dataset_id]:
        info = _dataframe_cache[dataset_id]["info"]
        # Check if cache has all required fields
        if "variables" in info and info.get("variables"):
            return {
                "id": info.get("id", dataset_id),
                "filename": info.get("original_filename", info.get("filename")),
                "nRows": info.get("nRows", 0),
                "nCols": info.get("nCols", 0),
                "createdAt": info.get("createdAt"),
                "variables": info["variables"],
                "qualityReport": info.get("qualityReport"),
                "digitalTwinReadiness": info.get("digitalTwinReadiness")
            }
    
    # Try database - load metadata from DB
    if db is not None and DATABASE_AVAILABLE:
        dataset = db.query(Dataset).filter(Dataset.id == dataset_id).first()
        
        if dataset:
            # Try to load dataframe if not in cache (for future use)
            try:
                df, meta = get_dataframe(dataset_id, db)
            except Exception as e:
                logger.warning(f"Failed to load dataframe for {dataset_id}: {e}")
            
            return {
                "id": dataset.id,
                "filename": dataset.original_filename,
                "nRows": dataset.n_rows,
                "nCols": dataset.n_cols,
                "createdAt": dataset.created_at.isoformat() if dataset.created_at else None,
                "variables": dataset.variables_meta or [],
                "qualityReport": dataset.quality_report,
                "digitalTwinReadiness": dataset.digital_twin_readiness
            }
    
    raise HTTPException(status_code=404, detail="Dataset not found")


@app.get("/api/datasets/{dataset_id}/quality")
async def get_quality_report(dataset_id: str, db: Session = Depends(get_db)):
    """Get detailed quality report for a dataset"""
    # Try cache first
    if dataset_id in _dataframe_cache and "info" in _dataframe_cache[dataset_id]:
        return _dataframe_cache[dataset_id]["info"].get("qualityReport", {})
    
    # Try database
    if db is not None and DATABASE_AVAILABLE:
        dataset = db.query(Dataset).filter(Dataset.id == dataset_id).first()
        if dataset:
            return dataset.quality_report or {}
    
    raise HTTPException(status_code=404, detail="Dataset not found")


@app.get("/api/datasets/{dataset_id}/variables/{var_name}")
async def get_variable_detail(dataset_id: str, var_name: str, db: Session = Depends(get_db)):
    """Get detailed information about a specific variable with correct missing handling"""
    try:
        df, meta = get_dataframe(dataset_id, db)
        
        if df is None:
            raise HTTPException(status_code=404, detail="Dataset not found or file missing")
        
        if var_name not in df.columns:
            raise HTTPException(status_code=404, detail="Variable not found")
        
        # Get variable info from cache or database
        var_info = None
        
        # Try cache first
        if dataset_id in _dataframe_cache and "info" in _dataframe_cache[dataset_id]:
            variables = _dataframe_cache[dataset_id]["info"].get("variables", [])
            var_info = next((v for v in variables if v.get("code") == var_name), None)
        
        # Try database if not found in cache
        if not var_info and db is not None and DATABASE_AVAILABLE:
            dataset = db.query(Dataset).filter(Dataset.id == dataset_id).first()
            if dataset and dataset.variables_meta:
                var_info = next((v for v in dataset.variables_meta if v.get("code") == var_name), None)
        
        # If still not found, create basic info from dataframe
        if not var_info:
            series = df[var_name]
            var_info = {
                "code": var_name,
                "label": var_name,
                "type": "unknown",
                "measure": "unknown",
                "valueLabels": [],
                "missingValues": None,
                "cardinality": int(series.nunique()),
                "responseCount": int(series.notna().sum()),
                "responseRate": round((series.notna().sum() / len(series) * 100) if len(series) > 0 else 0, 2)
            }
        
        series = df[var_name]
        var_type = var_info.get("type", "unknown")
        
        # Compute comprehensive statistics with correct missing handling
        var_stats = compute_variable_stats(df, var_name, var_info, meta)
        
        # Calculate numeric statistics if applicable
        stats = None
        if var_type in ["numeric", "scale"]:
            # Get explicit missing codes
            explicit_missing = get_explicit_missing_codes(var_info, meta)
            
            # Filter out missing values
            missing_mask = series.apply(is_value_missing)
            if len(explicit_missing) > 0:
                explicit_mask = series.isin(explicit_missing)
                missing_mask = missing_mask | explicit_mask
            
            valid_series = series[~missing_mask]
            numeric_series = pd.to_numeric(valid_series, errors='coerce').dropna()
            
            if len(numeric_series) > 0:
                stats = {
                    "min": float(numeric_series.min()),
                    "max": float(numeric_series.max()),
                    "mean": float(numeric_series.mean()),
                    "median": float(numeric_series.median()),
                    "std": float(numeric_series.std())
                }
        
        return {
            **var_info,
            "totalN": var_stats["totalN"],
            "validN": var_stats["validN"],
            "missingN": var_stats["missingN"],
            "missingPercentOfTotal": var_stats["missingPercentOfTotal"],
            "frequencies": var_stats["frequencies"],
            "hasManyCategories": var_stats["hasManyCategories"],
            "categoryCount": var_stats["categoryCount"],
            "stats": stats
        }
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error in get_variable_detail: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@app.get("/api/datasets/{dataset_id}/export/{export_type}")
async def export_dataset(
    request: Request,
    dataset_id: str,
    export_type: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_optional),
):
    """Export dataset in various formats"""
    # Get dataset info from cache or database
    dataset_info = None
    
    if dataset_id in _dataframe_cache and "info" in _dataframe_cache[dataset_id]:
        dataset_info = _dataframe_cache[dataset_id]["info"]
    elif db is not None and DATABASE_AVAILABLE:
        dataset = db.query(Dataset).filter(Dataset.id == dataset_id).first()
        if dataset:
            dataset_info = {
                "id": dataset.id,
                "filename": dataset.filename,
                "original_filename": dataset.original_filename,
                "nRows": dataset.n_rows,
                "nCols": dataset.n_cols,
                "createdAt": dataset.created_at.isoformat() if dataset.created_at else None,
                "variables": dataset.variables_meta or [],
                "qualityReport": dataset.quality_report or {}
            }
    
    if not dataset_info:
        raise HTTPException(status_code=404, detail="Dataset not found")
    
    # Check export permission
    check_export_permission(db=db, user=current_user, export_type="dataset")
    
    df, meta = get_dataframe(dataset_id, db)
    
    if df is None:
        raise HTTPException(status_code=404, detail="Dataset file not found")
    
    # Audit log for export
    audit_dataset_export(db=db, request=request, dataset_id=dataset_id, export_type=export_type)
    
    if export_type == "summary":
        # Generate comprehensive summary Excel
        original_filename = dataset_info.get("original_filename", dataset_info.get("filename", "export"))
        
        output = ExportService.generate_summary_excel(
            dataset_info=dataset_info,
            df=df,
            quality_report=dataset_info.get("qualityReport", {}),
            variables_info=dataset_info.get("variables", [])
        )
        
        filename = f"{original_filename.replace('.sav', '')}_ozet.xlsx"
        
        return StreamingResponse(
            output,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'}
        )
    
    elif export_type == "excel":
        # Generate data Excel (raw + labeled)
        original_filename = dataset_info.get("original_filename", dataset_info.get("filename", "export"))
        
        output = ExportService.generate_data_excel(df, dataset_info.get("variables", []))
        
        filename = f"{original_filename.replace('.sav', '')}_veri.xlsx"
        
        return StreamingResponse(
            output,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'}
        )
    
    elif export_type == "json":
        # Generate JSON export
        json_data = ExportService.generate_json_export(
            dataset_info=dataset_info,
            quality_report=dataset_info.get("qualityReport", {})
        )
        
        return JSONResponse(content=json_data)
    
    elif export_type == "report":
        # Generate quality report as JSON
        return JSONResponse(content=dataset_info.get("qualityReport", {}))
    
    else:
        raise HTTPException(status_code=400, detail=f"Unsupported export type: {export_type}")


@app.delete("/api/datasets/{dataset_id}")
async def delete_dataset(
    request: Request,
    dataset_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_optional),
):
    """Delete a dataset"""
    deleted = False
    deleted_filename = None
    
    # If DB is available, also delete transform jobs/results for this dataset to avoid DB bloat
    if db is not None and DATABASE_AVAILABLE:
        try:
            # If any transform job is currently running in this process, request stop and wait briefly
            jobs = db.query(TransformJob).filter(TransformJob.dataset_id == dataset_id).all()
            running_job_ids = [j.id for j in jobs if j.status == "running"]
            if running_job_ids:
                for jid in running_job_ids:
                    # Best-effort stop (thread worker checks these flags)
                    try:
                        transform_service._job_stop_flags[jid] = True  # type: ignore[attr-defined]
                        transform_service._job_pause_flags[jid] = False  # type: ignore[attr-defined]
                    except Exception:
                        pass
                
                # Wait up to ~10s for background thread(s) to exit to avoid FK / partial writes
                import asyncio as _asyncio
                loop = _asyncio.get_running_loop()
                deadline = loop.time() + 10.0
                while loop.time() < deadline:
                    with _transform_bg_lock:
                        still_running = any(jid in _transform_bg_running for jid in running_job_ids)
                    if not still_running:
                        break
                    await _asyncio.sleep(0.2)
                
                with _transform_bg_lock:
                    still_running = any(jid in _transform_bg_running for jid in running_job_ids)
                if still_running:
                    raise HTTPException(
                        status_code=409,
                        detail="Dataset silinemedi: dönüşüm işi halen çalışıyor. Önce dönüşümü durdurun ve tekrar deneyin."
                    )
            
            # Delete transform jobs (results/exclude_patterns cascade from FK/relationship)
            for j in jobs:
                try:
                    db.delete(j)
                except Exception:
                    pass
            db.commit()
        except HTTPException:
            raise
        except Exception as e:
            try:
                db.rollback()
            except Exception:
                pass
            raise HTTPException(status_code=500, detail=f"Failed to delete transform jobs for dataset: {e}")
    
    # Try cache first
    if dataset_id in _dataframe_cache:
        info = _dataframe_cache[dataset_id].get("info", {})
        file_path = info.get("file_path")
        deleted_filename = info.get("original_filename", info.get("filename"))
        if file_path and os.path.exists(file_path):
            os.remove(file_path)
        del _dataframe_cache[dataset_id]
        deleted = True
    
    # Try database
    if db is not None and DATABASE_AVAILABLE:
        dataset = db.query(Dataset).filter(Dataset.id == dataset_id).first()
        if dataset:
            deleted_filename = dataset.original_filename
            if os.path.exists(dataset.file_path):
                os.remove(dataset.file_path)
            db.delete(dataset)
            db.commit()
            deleted = True
    
    if not deleted:
        raise HTTPException(status_code=404, detail="Dataset not found")
    
    # Audit log
    audit_dataset_delete(
        db=db,
        request=request,
        dataset_id=dataset_id,
        filename=deleted_filename or "unknown",
    )
    
    return {"message": "Dataset deleted successfully"}


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "ok", "service": "sav-insight-api", "version": "2.0.0"}


@app.get("/api/config")
async def get_config():
    """Get application configuration status"""
    return {
        "gemini_api_configured": bool(settings.GEMINI_API_KEY),
        "openai_api_configured": bool(settings.OPENAI_API_KEY),
        "smart_filters_configured": bool(settings.OPENAI_API_KEY),
        "database_url_configured": bool(settings.DATABASE_URL),
        "upload_dir": str(UPLOAD_DIR),
        "version": "2.0.0"
    }


@app.post("/api/smart-filters/generate")
@app.post("/smart-filters/generate")  # nginx compatibility (sav-api rewrite)
async def generate_smart_filters(
    http_request: Request,
    request: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_optional),
):
    """
    Generate smart filter suggestions from variable metadata (NO respondent-level data sent to model).
    Then enrich with dataset-derived option counts where possible.
    """
    dataset_id = request.get("datasetId") or request.get("dataset_id")
    max_filters = request.get("maxFilters", 8)

    if not dataset_id:
        raise HTTPException(status_code=400, detail="datasetId is required")

    # Validate OpenAI key (we run this server-side to avoid exposing keys in browser)
    if not settings.OPENAI_API_KEY:
        raise HTTPException(status_code=503, detail="OpenAI API key not configured")

    df, meta = get_dataframe(dataset_id, db)
    if df is None:
        raise HTTPException(status_code=404, detail="Dataset not found")

    # Get variable metadata
    variables = []
    cache_entry = _dataframe_cache.get(dataset_id)
    if cache_entry and isinstance(cache_entry.get("info"), dict):
        variables = cache_entry["info"].get("variables") or []
    if (not variables) and db is not None and DATABASE_AVAILABLE:
        dataset = db.query(Dataset).filter(Dataset.id == dataset_id).first()
        if dataset:
            variables = dataset.variables_meta or []

    if not variables:
        raise HTTPException(status_code=404, detail="Variable metadata not found")

    # Ask the model to propose filters
    try:
        ai_result = await smart_filter_service.suggest_filters(variables=variables, max_filters=int(max_filters))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Smart filter generation failed: {e}")

    # Validate + de-hallucinate using BOTH metadata codes AND actual dataset columns
    valid_codes = {v.get("code") for v in variables if v.get("code")}
    
    # Also get actual column names from the dataframe for extra validation
    actual_columns = set(df.columns.tolist()) if df is not None else set()
    
    # Combine both - a valid code must exist in either metadata OR actual columns
    # But prefer codes that exist in actual columns (for CSV export compatibility)
    all_valid = valid_codes | actual_columns
    
    print(f"[SMART FILTER] Valid metadata codes: {len(valid_codes)}, Actual columns: {len(actual_columns)}")
    
    clean_filters = []
    for f in (ai_result.get("filters") or []):
        if not isinstance(f, dict):
            continue
        src = f.get("sourceVars") or []
        if not isinstance(src, list) or not src:
            continue
        
        # Check if all source vars exist in actual dataset columns
        valid_src = [s for s in src if s in actual_columns]
        if not valid_src:
            # Fallback: check if they exist in metadata codes (might work with mapping)
            valid_src = [s for s in src if s in valid_codes]
        
        if not valid_src:
            print(f"[SMART FILTER] Skipping filter '{f.get('title')}' - sourceVars {src} not found in dataset")
            continue
        
        # Update sourceVars to only include valid ones
        f["sourceVars"] = valid_src
        clean_filters.append(f)
    
    print(f"[SMART FILTER] AI returned {len(ai_result.get('filters', []))} filters, {len(clean_filters)} passed validation")

    # Enrich options based on data (best-effort)
    var_by_code = {v.get("code"): v for v in variables if v.get("code")}

    def choose_best_var(codes: List[str], kind: str) -> Optional[str]:
        """
        For non-multi_select filters we want EXACTLY one sourceVar.
        If the model returned multiple, choose the best candidate by metadata heuristics.
        """
        best = None
        best_score = -1e9
        for c in codes:
            info = var_by_code.get(c) or {}
            vtype = (info.get("type") or "").lower()
            rr = float(info.get("responseRate") or 0)
            card = float(info.get("cardinality") or 0)
            has_labels = bool(info.get("valueLabels"))

            score = rr

            if kind in ("categorical", "ordinal"):
                # Prefer labeled categorical-ish vars with moderate cardinality
                if vtype in ("single_choice", "multi_choice"):
                    score += 10
                if has_labels:
                    score += 5
                if 2 <= card <= 20:
                    score += 10
                elif card > 50:
                    score -= 50
            elif kind == "numeric_range":
                if vtype in ("numeric", "scale"):
                    score += 10
                if card > 10:
                    score += 5
            elif kind == "date_range":
                if vtype == "date":
                    score += 10

            if score > best_score:
                best_score = score
                best = c
        return best

    # Normalize sourceVars: for most filter types, force a single variable
    normalized_filters: List[Dict[str, Any]] = []
    for f in clean_filters:
        ftype = f.get("filterType")
        src = f.get("sourceVars") or []
        if ftype in ("categorical", "ordinal", "numeric_range", "date_range"):
            if isinstance(src, list) and len(src) != 1:
                best = choose_best_var([s for s in src if isinstance(s, str)], ftype)
                if not best:
                    continue
                f["sourceVars"] = [best]
        elif ftype == "multi_select":
            # keep list, but cap to avoid huge payloads
            if isinstance(src, list) and len(src) > 50:
                f["sourceVars"] = src[:50]
        normalized_filters.append(f)

    clean_filters = normalized_filters

    def map_label(code: str, raw_val: Any) -> str:
        info = var_by_code.get(code) or {}
        for vl in (info.get("valueLabels") or []):
            try:
                if isinstance(vl, dict) and vl.get("value") == raw_val:
                    return vl.get("label") or str(raw_val)
            except Exception:
                pass
        return str(raw_val)

    total_n = len(df)

    for f in clean_filters:
        f.setdefault("options", [])
        f.setdefault("recommendedDefault", None)
        ftype = f.get("filterType")
        src = f.get("sourceVars") or []

        # numeric/date range: use first var
        if ftype in ("numeric_range", "date_range") and len(src) >= 1:
            code = src[0]
            if code in df.columns:
                s = df[code]
                # drop missing
                s2 = s.dropna()
                try:
                    if len(s2) > 0:
                        vmin = s2.min()
                        vmax = s2.max()
                        f["recommendedDefault"] = {"min": vmin.item() if hasattr(vmin, "item") else vmin,
                                                   "max": vmax.item() if hasattr(vmax, "item") else vmax}
                except Exception:
                    pass

        # categorical/ordinal: counts for single var
        if ftype in ("categorical", "ordinal") and len(src) == 1:
            code = src[0]
            if code in df.columns:
                s = df[code]
                # value counts on non-missing
                vc = s.dropna().value_counts().head(50)
                opts = []
                for raw_val, cnt in vc.items():
                    try:
                        key = raw_val.item() if hasattr(raw_val, "item") else raw_val
                    except Exception:
                        key = raw_val
                    label = map_label(code, raw_val)
                    pct = round((int(cnt) / total_n * 100) if total_n else 0, 2)
                    opts.append({"key": key, "label": label, "count": int(cnt), "percent": pct})
                f["options"] = opts

        # multi_select: interpret sourceVars as multi-response columns; count "selected"
        if ftype == "multi_select" and len(src) >= 2:
            opts = []
            for code in src[:50]:
                if code not in df.columns:
                    continue
                s = df[code]
                # Selected heuristic: non-missing AND not 0
                try:
                    selected = s.dropna()
                    cnt = int((selected != 0).sum())
                except Exception:
                    cnt = int(s.notna().sum())
                label = (var_by_code.get(code) or {}).get("label") or code
                pct = round((cnt / total_n * 100) if total_n else 0, 2)
                opts.append({"key": code, "label": label, "count": cnt, "percent": pct})
            f["options"] = opts

    # Audit log
    final_filters = clean_filters[: int(max_filters) if str(max_filters).isdigit() else 8]
    audit_smart_filter_generate(
        db=db,
        request=http_request,
        dataset_id=dataset_id,
        filter_count=len(final_filters),
    )

    return {"filters": final_filters}


@app.get("/api/smart-filters/{dataset_id}")
@app.get("/smart-filters/{dataset_id}")  # nginx compatibility
async def get_smart_filters(
    dataset_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_optional),
):
    """
    Get saved smart filters for a dataset from database.
    """
    if not dataset_id:
        raise HTTPException(status_code=400, detail="dataset_id is required")
    
    if db is None or not DATABASE_AVAILABLE:
        raise HTTPException(status_code=503, detail="Database not available")
    
    dataset = db.query(Dataset).filter(Dataset.id == dataset_id).first()
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")
    
    # Check organization access if user is authenticated
    if current_user:
        if dataset.org_id and current_user.org_id != dataset.org_id:
            raise HTTPException(status_code=403, detail="Access denied to this dataset")
    
    # Return saved filters or empty array
    saved_filters = dataset.smart_filters or []
    return {"filters": saved_filters}


@app.put("/api/smart-filters/{dataset_id}")
@app.post("/api/smart-filters/{dataset_id}")  # Support POST for compatibility
@app.put("/smart-filters/{dataset_id}")  # nginx compatibility
@app.post("/smart-filters/{dataset_id}")  # nginx compatibility
async def save_smart_filters(
    dataset_id: str,
    request: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_optional),
):
    """
    Save smart filters for a dataset to database.
    """
    if not dataset_id:
        raise HTTPException(status_code=400, detail="dataset_id is required")
    
    if db is None or not DATABASE_AVAILABLE:
        raise HTTPException(status_code=503, detail="Database not available")
    
    dataset = db.query(Dataset).filter(Dataset.id == dataset_id).first()
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")
    
    # Check organization access if user is authenticated
    if current_user:
        if dataset.org_id and current_user.org_id != dataset.org_id:
            raise HTTPException(status_code=403, detail="Access denied to this dataset")
    
    # Get filters from request body
    filters = request.get("filters", [])
    if not isinstance(filters, list):
        raise HTTPException(status_code=400, detail="filters must be an array")
    
    # Save to database
    try:
        dataset.smart_filters = filters
        dataset.updated_at = datetime.utcnow()
        db.commit()
        return {"success": True, "message": f"Saved {len(filters)} smart filter(s)", "count": len(filters)}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to save smart filters: {str(e)}")


@app.get("/api/system/cache-stats")
async def get_cache_stats():
    """Get cache statistics and memory usage"""
    import sys
    
    cache_size = len(_dataframe_cache)
    cache_keys = list(_dataframe_cache.keys())
    
    # Estimate memory usage (rough calculation)
    total_memory_mb = 0
    for dataset_id, data in _dataframe_cache.items():
        if "df" in data:
            df = data["df"]
            # Rough estimate: number of cells * 8 bytes (for numeric data)
            memory_bytes = df.memory_usage(deep=True).sum()
            total_memory_mb += memory_bytes / (1024 * 1024)
    
    return {
        "cached_datasets": cache_size,
        "max_cache_size": _MAX_CACHE_SIZE,
        "estimated_memory_mb": round(total_memory_mb, 2),
        "cache_keys": cache_keys
    }


@app.post("/api/system/clear-cache")
async def clear_cache():
    """Clear the in-memory dataframe cache"""
    cleared_count = len(_dataframe_cache)
    _dataframe_cache.clear()
    return {
        "message": f"Cache cleared successfully",
        "cleared_datasets": cleared_count
    }


@app.post("/api/system/sync-uploads-to-db")
async def sync_uploads_to_db(db: Session = Depends(get_db)):
    """Sync existing uploaded files to database"""
    if db is None or not DATABASE_AVAILABLE:
        raise HTTPException(status_code=503, detail="Database not available")
    
    uploaded_files = list(UPLOAD_DIR.glob("*.sav"))
    synced = []
    errors = []
    
    for file_path in uploaded_files:
        try:
            # Check if already in database
            file_name = file_path.name
            existing = db.query(Dataset).filter(Dataset.filename == file_name).first()
            if existing:
                synced.append({"file": file_name, "status": "already_exists", "id": existing.id})
                continue
            
            # Process and save
            dataset_info = process_sav_file(file_path, file_name)
            saved = save_to_database(db, dataset_info)
            
            if saved:
                synced.append({"file": file_name, "status": "synced", "id": dataset_info["id"]})
            else:
                errors.append({"file": file_name, "error": "Failed to save to database"})
        except Exception as e:
            errors.append({"file": file_path.name, "error": str(e)})
    
    return {
        "message": f"Synced {len(synced)} files, {len(errors)} errors",
        "synced": synced,
        "errors": errors,
        "total_files": len(uploaded_files)
    }


# ==================== TWIN TRANSFORMER ENDPOINTS ====================

# Background runner helpers (module-level)
import threading
import asyncio as _asyncio

def _run_transform_job_in_thread(job_id: str, dataset_id: str):
    """
    Runs the async transform job inside a *new* event loop on a background thread.
    This avoids the issue where asyncio.create_task() scheduled inside a FastAPI
    endpoint never runs because the request completes and uvicorn idles.
    """
    with _transform_bg_lock:
        if job_id in _transform_bg_running:
            print(f"[BG] Job {job_id} already running, skipping duplicate start")
            return
        _transform_bg_running.add(job_id)

    def _worker():
        from database import SessionLocal
        db_session = SessionLocal()
        try:
            print(f"[BG] Starting transform job {job_id} for dataset {dataset_id}")
            df_bg, meta_bg = get_dataframe(dataset_id, db_session)
            if df_bg is None:
                print(f"[BG] Dataset {dataset_id} not found")
                return

            variables_bg = []
            cache_entry_bg = _dataframe_cache.get(dataset_id)
            if cache_entry_bg and isinstance(cache_entry_bg.get("info"), dict):
                variables_bg = cache_entry_bg["info"].get("variables") or []
            if (not variables_bg) and db_session is not None and DATABASE_AVAILABLE:
                dataset = db_session.query(Dataset).filter(Dataset.id == dataset_id).first()
                if dataset:
                    variables_bg = dataset.variables_meta or []

            # Create a new event loop for this thread and run the async job
            loop = _asyncio.new_event_loop()
            _asyncio.set_event_loop(loop)
            try:
                loop.run_until_complete(transform_service.run_job(db_session, job_id, df_bg, variables_bg))
            finally:
                loop.close()
            print(f"[BG] Transform job {job_id} finished")
        except Exception as e:
            print(f"[BG] Transform job error: {e}")
            import traceback
            traceback.print_exc()
        finally:
            db_session.close()
            with _transform_bg_lock:
                _transform_bg_running.discard(job_id)

    t = threading.Thread(target=_worker, daemon=True)
    t.start()

@app.get("/api/datasets/{dataset_id}/rows")
async def get_dataset_rows(
    dataset_id: str,
    offset: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """Get dataset rows with pagination"""
    df, meta = get_dataframe(dataset_id, db)
    
    if df is None:
        raise HTTPException(status_code=404, detail="Dataset not found")
    
    total_rows = len(df)
    end_idx = min(offset + limit, total_rows)
    
    rows = []
    for idx in range(offset, end_idx):
        row_data = df.iloc[idx].to_dict()
        # Convert numpy types to Python types
        cleaned_row = {}
        for k, v in row_data.items():
            if pd.isna(v):
                cleaned_row[k] = None
            elif hasattr(v, 'item'):
                cleaned_row[k] = v.item()
            else:
                cleaned_row[k] = v
        rows.append({"index": idx, "data": cleaned_row})
    
    return {
        "total": total_rows,
        "offset": offset,
        "limit": limit,
        "rows": rows
    }


@app.post("/api/transform/analyze-columns")
@app.post("/transform/analyze-columns")  # nginx compatibility (sav-api rewrite)
async def analyze_columns_for_transform(
    request: dict,
    db: Session = Depends(get_db)
):
    """Analyze columns for transformation - detect admin columns and exclude candidates"""
    dataset_id = request.get("datasetId") or request.get("dataset_id")
    force_refresh = request.get("forceRefresh", False)
    
    if not dataset_id:
        raise HTTPException(status_code=400, detail="datasetId is required")
    
    # Check if we have a cached analysis in the database (from existing job)
    if not force_refresh and db is not None and DATABASE_AVAILABLE:
        existing_job = db.query(TransformJob).filter(
            TransformJob.dataset_id == dataset_id
        ).order_by(TransformJob.created_at.desc()).first()
        
        if existing_job and existing_job.column_analysis:
            logger.info(f"Returning cached column analysis for dataset {dataset_id}")
            return existing_job.column_analysis
    
    df, meta = get_dataframe(dataset_id, db)
    
    if df is None:
        raise HTTPException(status_code=404, detail="Dataset not found")
    
    # Get variables info
    variables = []
    cache_entry = _dataframe_cache.get(dataset_id)
    if cache_entry and isinstance(cache_entry.get("info"), dict):
        variables = cache_entry["info"].get("variables") or []
    # Fallback to DB if cache doesn't have variables (common after restart)
    if (not variables) and db is not None and DATABASE_AVAILABLE:
        dataset = db.query(Dataset).filter(Dataset.id == dataset_id).first()
        if dataset:
            variables = dataset.variables_meta or []
    
    if not variables:
        raise HTTPException(status_code=404, detail="Variable metadata not found")
    
    result = transform_service.analyze_columns(df, variables)
    
    analysis_result = {
        "datasetId": dataset_id,
        "adminColumns": result.admin_columns,
        "excludeCandidates": result.exclude_candidates,
        "excludedByDefaultColumns": result.excluded_by_default_columns,
        "transformableColumns": result.transformable_columns,
        "totalColumns": result.total_columns,
        "totalRows": result.total_rows,
        "suggestedIdColumn": result.suggested_id_column
    }
    
    # Save analysis to the most recent job if it exists
    if db is not None and DATABASE_AVAILABLE:
        existing_job = db.query(TransformJob).filter(
            TransformJob.dataset_id == dataset_id
        ).order_by(TransformJob.created_at.desc()).first()
        
        if existing_job:
            existing_job.column_analysis = analysis_result
            db.commit()
            logger.info(f"Saved column analysis to job {existing_job.id}")
    
    return analysis_result


@app.post("/api/transform/start")
@app.post("/transform/start")  # nginx compatibility (sav-api rewrite)
async def start_transform_job(
    http_request: Request,
    request: dict,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_optional),
):
    """Start a new transformation job"""
    if db is None or not DATABASE_AVAILABLE:
        raise HTTPException(status_code=503, detail="Database not available")
    
    dataset_id = request.get("datasetId") or request.get("dataset_id")
    chunk_size = request.get("chunkSize", 30)
    row_concurrency = request.get("rowConcurrency", 5)
    exclude_config = request.get("excludeOptionsConfig", {})
    exclude_pattern_variables = request.get("excludePatternVariables", {})
    admin_columns = request.get("adminColumns", [])
    excluded_variables = request.get("excludedVariables", [])
    respondent_id_column = request.get("respondentIdColumn") or request.get("respondent_id_column")
    row_limit = request.get("rowLimit")  # None = process all rows
    auto_start = request.get("autoStart", True)  # Whether to auto-start the job (default: True for backward compatibility)
    
    if not dataset_id:
        raise HTTPException(status_code=400, detail="datasetId is required")
    
    # Validate OpenAI API key
    if not settings.OPENAI_API_KEY:
        raise HTTPException(status_code=503, detail="OpenAI API key not configured")
    
    df, meta = get_dataframe(dataset_id, db)
    
    if df is None:
        raise HTTPException(status_code=404, detail="Dataset not found")

    def _calc_effective_total_rows(df_len: int, row_limit_val) -> int:
        if row_limit_val is None:
            return df_len
        try:
            return min(int(row_limit_val), df_len)
        except Exception:
            return df_len
    
    # Get variables info
    variables = []
    cache_entry = _dataframe_cache.get(dataset_id)
    if cache_entry and isinstance(cache_entry.get("info"), dict):
        variables = cache_entry["info"].get("variables") or []
    if (not variables) and db is not None:
        dataset = db.query(Dataset).filter(Dataset.id == dataset_id).first()
        if dataset:
            variables = dataset.variables_meta or []
    
    # Normalize + persist column-level excludes inside exclude_config (single source of truth in DB)
    if isinstance(excluded_variables, list) and excluded_variables:
        exclude_config = dict(exclude_config or {})
        exclude_config["excludedVariables"] = excluded_variables

    if isinstance(exclude_pattern_variables, dict) and exclude_pattern_variables:
        exclude_config = dict(exclude_config or {})
        exclude_config["excludePatternVariables"] = exclude_pattern_variables

    # Persist which column should be used as respondentId in transform results
    if respondent_id_column:
        exclude_config = dict(exclude_config or {})
        exclude_config["respondentIdColumn"] = respondent_id_column

    # Check for existing job (including completed - user might want to restart with new settings)
    existing_job = db.query(TransformJob).filter(
        TransformJob.dataset_id == dataset_id,
        TransformJob.status.in_(["idle", "running", "paused", "completed"])
    ).order_by(TransformJob.created_at.desc()).first()  # Get most recent job
    
    if existing_job:
        # If job is completed, check if user wants to restart with new settings
        if existing_job.status == "completed":
            # Check if row_limit changed (user wants to continue processing more rows)
            new_row_limit = row_limit if row_limit else None
            
            # Check if any settings changed (not just row_limit)
            settings_changed = (
                new_row_limit != existing_job.row_limit or
                chunk_size != existing_job.chunk_size or
                row_concurrency != existing_job.row_concurrency or
                exclude_config != existing_job.exclude_options_config or
                admin_columns != existing_job.admin_columns
            )
            
            if settings_changed:
                # Update job settings
                try:
                    existing_job.chunk_size = chunk_size
                    existing_job.row_concurrency = row_concurrency
                    existing_job.exclude_options_config = exclude_config
                    existing_job.admin_columns = admin_columns
                    if new_row_limit is not None:
                        existing_job.row_limit = new_row_limit
                    
                    # Only start job if autoStart=True AND row_limit allows more processing
                    should_start = (
                        auto_start and 
                        new_row_limit is not None and 
                        new_row_limit > (existing_job.processed_rows or 0)
                    )
                    
                    if should_start:
                        existing_job.status = "running"
                        existing_job.last_error = None
                        db.commit()
                        logger.info(f"Starting job {existing_job.id} with row_limit: {new_row_limit}, autoStart: {auto_start}")
                        
                        # Start job in background
                        _run_transform_job_in_thread(existing_job.id, dataset_id)
                        
                        return {
                            "jobId": existing_job.id,
                            "status": "running",
                            "message": "Job started",
                            "isExisting": True
                        }
                    else:
                        # Just update settings, don't start
                        db.commit()
                        db.refresh(existing_job)
                        logger.info(f"Updated settings for job {existing_job.id}, autoStart: {auto_start}, admin_columns: {len(admin_columns) if admin_columns else 0}")
                        
                        return {
                            "jobId": existing_job.id,
                            "status": existing_job.status,
                            "message": "Job settings updated",
                            "isExisting": True
                        }
                except Exception as e:
                    logger.error(f"Failed to update job: {e}", exc_info=True)
                    db.rollback()
                    raise HTTPException(status_code=500, detail=f"Failed to update job: {str(e)}")
            else:
                # No changes, return existing completed job
                return {
                    "jobId": existing_job.id,
                    "status": existing_job.status,
                    "message": "Existing completed job found",
                    "isExisting": True
                }
        # Continue with existing job logic for non-completed jobs
        # If paused, require explicit /resume
        if existing_job.status == "paused":
            # Update config even if paused, so user's new settings (rowLimit, excludes, etc.) are not ignored.
            new_row_limit = row_limit if row_limit else None
            effective_total = new_row_limit if new_row_limit else len(df)

            # If user reduces the limit below already processed rows, require reset (otherwise progress becomes nonsensical).
            try:
                if existing_job.processed_rows and int(existing_job.processed_rows) > effective_total:
                    raise HTTPException(
                        status_code=409,
                        detail="Seçilen satır limiti, mevcut işte zaten işlenen satır sayısından küçük. Yeni limitin uygulanması için önce Sıfırla yapın."
                    )
            except HTTPException:
                raise
            except Exception:
                # If conversion fails, just proceed to update config
                pass

            try:
                existing_job.chunk_size = chunk_size
                existing_job.row_concurrency = row_concurrency
                existing_job.exclude_options_config = exclude_config
                existing_job.admin_columns = admin_columns
                existing_job.row_limit = new_row_limit
                db.commit()
            except Exception as e:
                db.rollback()
                raise HTTPException(status_code=500, detail=f"Failed to update paused job config: {e}")

            return {
                "jobId": existing_job.id,
                "status": existing_job.status,
                "message": "Existing paused job found (updated config; use Resume)",
                "isExisting": True
            }

        # IMPORTANT: After backend restarts, DB may say "running" but there is no in-memory worker.
        # Treat "start" as "enqueue/restart" for idle OR running jobs.
        if existing_job.status in ["idle", "running"]:
            # Set row_limit
            new_row_limit = row_limit if row_limit else None
            
            try:
                # Update job config with latest settings before starting
                existing_job.chunk_size = chunk_size
                existing_job.row_concurrency = row_concurrency
                existing_job.exclude_options_config = exclude_config
                existing_job.admin_columns = admin_columns
                existing_job.row_limit = new_row_limit
                existing_job.status = "running"
                existing_job.started_at = datetime.utcnow()
                existing_job.last_error = None
                db.commit()
            except Exception as e:
                db.rollback()
                raise HTTPException(status_code=500, detail=f"Failed to restart existing job: {e}")

            # Start job in background thread
            _run_transform_job_in_thread(existing_job.id, dataset_id)

            return {
                "jobId": existing_job.id,
                "status": "running",
                "message": "Existing job enqueued",
                "isExisting": True
            }

        return {
            "jobId": existing_job.id,
            "status": existing_job.status,
            "message": "Existing job found",
            "isExisting": True
        }
    
    # Create new job
    # Get or create column analysis for caching
    column_analysis_data = None
    try:
        # Try to get from existing job first
        any_job = db.query(TransformJob).filter(
            TransformJob.dataset_id == dataset_id
        ).order_by(TransformJob.created_at.desc()).first()
        
        if any_job and any_job.column_analysis:
            column_analysis_data = any_job.column_analysis
        else:
            # Perform fresh analysis and cache it
            result = transform_service.analyze_columns(df, variables)
            column_analysis_data = {
                "datasetId": dataset_id,
                "adminColumns": result.admin_columns,
                "excludeCandidates": result.exclude_candidates,
                "excludedByDefaultColumns": result.excluded_by_default_columns,
                "transformableColumns": result.transformable_columns,
                "totalColumns": result.total_columns,
                "totalRows": result.total_rows,
                "suggestedIdColumn": result.suggested_id_column
            }
    except Exception as e:
        logger.warning(f"Failed to get/create column analysis: {e}")
    
    # Create job with total rows from dataset and optional row_limit
    job = transform_service.create_job(
        db=db,
        dataset_id=dataset_id,
        total_rows=len(df),  # Total rows in dataset
        row_limit=row_limit if row_limit else None,  # Max rows to process
        chunk_size=chunk_size,
        row_concurrency=row_concurrency,
        exclude_config=exclude_config,
        admin_columns=admin_columns,
        column_analysis=column_analysis_data,
        respondent_id_column=respondent_id_column
    )

    # Mark as running immediately so UI doesn't get stuck at "idle" even briefly
    try:
        job.status = "running"
        job.started_at = datetime.utcnow()
        job.last_error = None
        db.commit()
        db.refresh(job)
    except Exception:
        db.rollback()
    
    # Start job in background thread
    _run_transform_job_in_thread(job.id, dataset_id)
    
    # Audit log
    audit_transform_start(
        db=db,
        request=http_request,
        job_id=job.id,
        dataset_id=dataset_id,
        row_limit=row_limit,
    )
    
    return {
        "jobId": job.id,
        "status": job.status,
        "message": "Job started",
        "isExisting": False
    }


@app.post("/api/transform/pause/{job_id}")
@app.post("/transform/pause/{job_id}")  # nginx compatibility (sav-api rewrite)
async def pause_transform_job(
    request: Request,
    job_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_optional),
):
    """Pause a running transformation job"""
    if db is None or not DATABASE_AVAILABLE:
        raise HTTPException(status_code=503, detail="Database not available")
    
    success = transform_service.pause_job(db, job_id)
    
    if not success:
        raise HTTPException(status_code=400, detail="Cannot pause job - job not running")
    
    # Audit log
    audit_transform_pause(db=db, request=request, job_id=job_id)
    
    return {"jobId": job_id, "status": "paused", "message": "Job paused"}


class ResumeJobRequest(BaseModel):
    """Optional settings to update on resume"""
    rowConcurrency: Optional[int] = None
    chunkSize: Optional[int] = None
    rowLimit: Optional[int] = None
    excludeOptions: Optional[dict] = None
    adminColumns: Optional[list] = None


@app.post("/api/transform/resume/{job_id}")
@app.post("/transform/resume/{job_id}")  # nginx compatibility (sav-api rewrite)
async def resume_transform_job(
    request: Request,
    job_id: str,
    body: Optional[ResumeJobRequest] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_optional),
):
    """Resume a paused transformation job with optional new settings"""
    if db is None or not DATABASE_AVAILABLE:
        raise HTTPException(status_code=503, detail="Database not available")
    
    job = transform_service.get_job(db, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    # Get dataframe and variables
    df, meta = get_dataframe(job.dataset_id, db)
    if df is None:
        raise HTTPException(status_code=404, detail="Dataset not found")
    
    variables = []
    cache_entry = _dataframe_cache.get(job.dataset_id)
    if cache_entry and isinstance(cache_entry.get("info"), dict):
        variables = cache_entry["info"].get("variables") or []
    if (not variables) and db is not None:
        dataset = db.query(Dataset).filter(Dataset.id == job.dataset_id).first()
        if dataset:
            variables = dataset.variables_meta or []
    
    # Update job settings if provided in request body
    if body:
        try:
            if body.rowConcurrency is not None:
                job.row_concurrency = body.rowConcurrency
                logger.info(f"Resume job {job_id}: Updated row_concurrency to {body.rowConcurrency}")
            if body.chunkSize is not None:
                job.chunk_size = body.chunkSize
            if body.rowLimit is not None:
                # Check if new limit is less than processed rows
                if job.processed_rows and job.processed_rows > body.rowLimit:
                    raise HTTPException(
                        status_code=409,
                        detail=f"Row limit ({body.rowLimit}) cannot be less than already processed rows ({job.processed_rows}). Reset the job first."
                    )
                job.row_limit = body.rowLimit
            if body.excludeOptions is not None:
                job.exclude_options_config = body.excludeOptions
            if body.adminColumns is not None:
                job.admin_columns = body.adminColumns
            db.commit()
        except HTTPException:
            raise
        except Exception as e:
            db.rollback()
            logger.error(f"Failed to update job settings on resume: {e}")
    
    # Mark job as running and run via the same background-thread runner used by /start
    try:
        job.status = "running"
        job.last_error = None
        job.started_at = job.started_at or datetime.utcnow()
        db.commit()
        db.refresh(job)
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to resume job: {e}")

    _run_transform_job_in_thread(job.id, job.dataset_id)
    
    # Audit log
    audit_transform_resume(db=db, request=request, job_id=job_id)
    
    return {
        "jobId": job_id,
        "status": "running",
        "message": "Job resumed",
        "rowConcurrency": job.row_concurrency,
        "rowLimit": job.row_limit
    }


@app.post("/api/transform/stop/{job_id}")
@app.post("/transform/stop/{job_id}")  # nginx compatibility (sav-api rewrite)
async def stop_transform_job(job_id: str, db: Session = Depends(get_db)):
    """Stop a transformation job (pause)"""
    if db is None or not DATABASE_AVAILABLE:
        raise HTTPException(status_code=503, detail="Database not available")
    
    success = transform_service.stop_job(db, job_id)
    
    if not success:
        raise HTTPException(status_code=404, detail="Job not found")
    
    return {"jobId": job_id, "status": "paused", "message": "Job stopped"}


@app.post("/api/transform/cancel/{job_id}")
@app.post("/transform/cancel/{job_id}")  # nginx compatibility (sav-api rewrite)
async def cancel_transform_job(job_id: str, db: Session = Depends(get_db)):
    """
    Cancel a transformation job.
    Stops execution, removes waiting/pending results, but KEEPS completed results.
    Sets row_limit to current progress so user can resume with new settings.
    """
    if db is None or not DATABASE_AVAILABLE:
        raise HTTPException(status_code=503, detail="Database not available")
    
    result = transform_service.cancel_job(db, job_id)
    
    if not result.get("success"):
        raise HTTPException(status_code=404, detail=result.get("error", "Job not found"))
    
    return {
        "jobId": job_id,
        "status": "cancelled",
        "message": f"Job cancelled. Kept {result['completedKept']} completed results, removed {result['waitingRemoved']} waiting.",
        "completedKept": result["completedKept"],
        "waitingRemoved": result["waitingRemoved"],
        "newRowLimit": result["newRowLimit"]
    }


@app.delete("/api/transform/reset/{job_id}")
@app.delete("/transform/reset/{job_id}")  # nginx compatibility (sav-api rewrite)
async def reset_transform_job(
    job_id: str,
    request: dict,
    db: Session = Depends(get_db)
):
    """Reset a transformation job - requires confirmation text 'DELETE'"""
    if db is None or not DATABASE_AVAILABLE:
        raise HTTPException(status_code=503, detail="Database not available")
    
    confirm_text = request.get("confirmText", "")
    
    success = transform_service.reset_job(db, job_id, confirm_text)
    
    if not success:
        raise HTTPException(
            status_code=400, 
            detail="Cannot reset job - either job not found or confirmation text incorrect (must be 'DELETE')"
        )
    
    return {"jobId": job_id, "status": "idle", "message": "Job reset successfully"}


@app.get("/api/transform/status/{job_id}")
@app.get("/transform/status/{job_id}")  # nginx compatibility (sav-api rewrite)
async def get_transform_job_status(job_id: str, db: Session = Depends(get_db)):
    """Get the status and progress of a transformation job"""
    if db is None or not DATABASE_AVAILABLE:
        raise HTTPException(status_code=503, detail="Database not available")
    
    job = transform_service.get_job(db, job_id)
    
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    progress = transform_service.get_job_progress(job)
    
    return dataclass_asdict(progress)


@app.get("/api/transform/jobs/{dataset_id}")
@app.get("/transform/jobs/{dataset_id}")  # nginx compatibility (sav-api rewrite)
async def get_transform_jobs_for_dataset(dataset_id: str, db: Session = Depends(get_db)):
    """Get all transform jobs for a dataset"""
    if db is None or not DATABASE_AVAILABLE:
        raise HTTPException(status_code=503, detail="Database not available")
    
    jobs = db.query(TransformJob).filter(
        TransformJob.dataset_id == dataset_id
    ).order_by(TransformJob.created_at.desc()).all()
    
    return [{
        "jobId": job.id,
        "status": job.status,
        "totalRows": job.total_rows,
        "processedRows": job.processed_rows,
        "failedRows": job.failed_rows,
        "createdAt": job.created_at.isoformat() if job.created_at else None,
        "updatedAt": job.updated_at.isoformat() if job.updated_at else None
    } for job in jobs]


@app.get("/api/transform/results/{job_id}")
@app.get("/transform/results/{job_id}")  # nginx compatibility (sav-api rewrite)
async def get_transform_results(
    job_id: str,
    offset: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db)
):
    """Get transformation results with pagination"""
    if db is None or not DATABASE_AVAILABLE:
        raise HTTPException(status_code=503, detail="Database not available")
    
    job = transform_service.get_job(db, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    results = transform_service.get_results(db, job_id, offset, limit)
    
    total = db.query(TransformResult).filter(TransformResult.job_id == job_id).count()
    
    return {
        "jobId": job_id,
        "total": total,
        "offset": offset,
        "limit": limit,
        "results": [{
            "rowIndex": r.row_index,
            "respondentId": r.respondent_id,
            "status": r.status,
            "sentences": r.sentences or [],
            "excluded": r.excluded or {},
            "errorMessage": r.error_message,
            "retryCount": r.retry_count,
            "processedAt": r.processed_at.isoformat() if r.processed_at else None
        } for r in results]
    }


@app.get("/api/transform/results-range/{job_id}")
@app.get("/transform/results-range/{job_id}")  # nginx compatibility (sav-api rewrite)
async def get_transform_results_range(
    job_id: str,
    startRow: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db)
):
    """
    Get transform results for a specific row-index range [startRow, startRow+limit).
    Intended for the row table UI so "row 1..50" can show results as they arrive.
    """
    if db is None or not DATABASE_AVAILABLE:
        raise HTTPException(status_code=503, detail="Database not available")
    
    job = transform_service.get_job(db, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    if limit <= 0:
        return {"jobId": job_id, "startRow": startRow, "limit": limit, "results": []}
    
    start_row = max(0, int(startRow))
    end_row = start_row + int(limit)
    
    results = db.query(TransformResult).filter(
        TransformResult.job_id == job_id,
        TransformResult.row_index >= start_row,
        TransformResult.row_index < end_row
    ).order_by(TransformResult.row_index).all()
    
    return {
        "jobId": job_id,
        "startRow": start_row,
        "limit": int(limit),
        "results": [{
            "rowIndex": r.row_index,
            "respondentId": r.respondent_id,
            "status": r.status,
            "sentences": r.sentences or [],
            "excluded": r.excluded or {},
            "errorMessage": r.error_message,
            "retryCount": r.retry_count,
            "processedAt": r.processed_at.isoformat() if r.processed_at else None
        } for r in results]
    }


@app.get("/api/transform/result/{job_id}/{row_index}")
@app.get("/transform/result/{job_id}/{row_index}")  # nginx compatibility (sav-api rewrite)
async def get_transform_result_by_row(
    job_id: str,
    row_index: int,
    db: Session = Depends(get_db)
):
    """Get a single transformation result by row index"""
    if db is None or not DATABASE_AVAILABLE:
        raise HTTPException(status_code=503, detail="Database not available")
    
    result = transform_service.get_result_by_row(db, job_id, row_index)
    
    if not result:
        raise HTTPException(status_code=404, detail="Result not found")
    
    return {
        "rowIndex": result.row_index,
        "respondentId": result.respondent_id,
        "status": result.status,
        "sentences": result.sentences or [],
        "excluded": result.excluded or {},
        "rawTrace": result.raw_trace or {},
        "errorMessage": result.error_message,
        "retryCount": result.retry_count,
        "processedAt": result.processed_at.isoformat() if result.processed_at else None
    }


@app.post("/api/transform/retry-row/{job_id}/{row_index}")
@app.post("/transform/retry-row/{job_id}/{row_index}")  # nginx compatibility (sav-api rewrite)
async def retry_single_row(
    job_id: str,
    row_index: int,
    db: Session = Depends(get_db)
):
    """Retry transformation for a single row"""
    if db is None or not DATABASE_AVAILABLE:
        raise HTTPException(status_code=503, detail="Database not available")
    
    job = transform_service.get_job(db, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    df, meta = get_dataframe(job.dataset_id, db)
    if df is None:
        raise HTTPException(status_code=404, detail="Dataset not found")
    
    if row_index < 0 or row_index >= len(df):
        raise HTTPException(status_code=400, detail="Invalid row index")
    
    # Get variables
    variables = []
    cache_entry = _dataframe_cache.get(job.dataset_id)
    if cache_entry and isinstance(cache_entry.get("info"), dict):
        variables = cache_entry["info"].get("variables") or []
    if (not variables) and db is not None:
        dataset = db.query(Dataset).filter(Dataset.id == job.dataset_id).first()
        if dataset:
            variables = dataset.variables_meta or []
    
    # Delete existing result
    existing_result = db.query(TransformResult).filter(
        TransformResult.job_id == job_id,
        TransformResult.row_index == row_index
    ).first()
    
    if existing_result:
        db.delete(existing_result)
        db.commit()
    
    # Get row data
    row_data = df.iloc[row_index]
    
    # Get exclude config
    exclude_config = job.exclude_options_config or {}
    exclude_pattern_variables = exclude_config.get("excludePatternVariables", {})
    excluded_variables = set(exclude_config.get("excludedVariables", []) or [])
    admin_columns = set(job.admin_columns or [])
    
    # Build exclude values mapping (same logic as in run_job)
    def build_exclude_values_by_variable():
        mapping: Dict[str, Set[Any]] = {}
        enabled_patterns = {k for k, v in exclude_config.items() if isinstance(v, bool) and v}
        
        for var in variables:
            code = var.get("code")
            if not code:
                continue
            value_labels = var.get("valueLabels", []) or []
            excluded_vals: Set[Any] = set()
            
            for pattern_key in enabled_patterns:
                if pattern_key not in EXCLUDE_PATTERNS:
                    continue
                selected_vars = set(exclude_pattern_variables.get(pattern_key, []) or [])
                if code not in selected_vars:
                    continue
                
                # Get pattern info
                pattern_info = EXCLUDE_PATTERNS.get(pattern_key)
                if not pattern_info:
                    continue
                for vl in value_labels:
                    v = vl.get("value")
                    lab = (vl.get("label") or "").lower()
                    if any(re.search(rx, lab, re.IGNORECASE) for rx in pattern_info["patterns"]):
                        excluded_vals.add(v)
                for v in pattern_info.get("values", []):
                    excluded_vals.add(v)
            
            if excluded_vals:
                mapping[code] = excluded_vals
        
        return mapping
    
    exclude_values_by_variable = build_exclude_values_by_variable()
    
    # Process row
    try:
        result = await transform_service.process_row(
            db, job, row_index, row_data,
            variables,
            exclude_values_by_variable,
            admin_columns,
            excluded_variables
        )
        
        db.add(result)
        db.commit()
        
        return {
            "jobId": job_id,
            "rowIndex": row_index,
            "status": result.status,
            "message": "Row retried successfully"
        }
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to retry row: {str(e)}")


class SmartFilterExport(BaseModel):
    id: str
    title: str
    source_vars: List[str]
    source: str = "manual"

class ExportRequestBody(BaseModel):
    smart_filters: List[SmartFilterExport] = []


@app.post("/api/transform/export/{job_id}")
@app.post("/transform/export/{job_id}")  # nginx compatibility (sav-api rewrite)
async def export_transform_results(
    job_id: str,
    request: Request,
    format: str = "json",
    product_id: str = "",
    product_name: str = "",
    data_source: str = "",
    review_rating: float = 5.0,
    review_title: str = "",  # Manual review title (same for all rows)
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_optional),
):
    """Export transformation results"""
    if db is None or not DATABASE_AVAILABLE:
        raise HTTPException(status_code=503, detail="Database not available")
    
    # Check export permission
    check_export_permission(db=db, user=current_user, export_type="transform")
    
    job = transform_service.get_job(db, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    # Count results for audit
    result_count = db.query(TransformResult).filter(
        TransformResult.job_id == job_id,
        TransformResult.status == "completed"
    ).count()
    
    # Audit log
    audit_transform_export(
        db=db,
        request=request,
        job_id=job_id,
        export_format=format,
        row_count=result_count,
    )
    
    # Parse request body for smart filters
    smart_filters = []
    try:
        body = await request.json()
        print(f"[CSV EXPORT] Request body: {body}")
        if body and "smart_filters" in body:
            smart_filters = body["smart_filters"]
            print(f"[CSV EXPORT] Found {len(smart_filters)} smart filters to export")
    except Exception as e:
        print(f"[CSV EXPORT] No body or invalid JSON in export request: {e}")
    
    # Get all results
    results = db.query(TransformResult).filter(
        TransformResult.job_id == job_id,
        TransformResult.status == "completed"
    ).order_by(TransformResult.row_index).all()
    
    if format == "json":
        export_data = {
            "jobId": job_id,
            "datasetId": job.dataset_id,
            "exportedAt": datetime.now().isoformat(),
            "totalResults": len(results),
            "results": [{
                "rowIndex": r.row_index,
                "respondentId": r.respondent_id,
                "sentences": r.sentences or [],
                "excluded": r.excluded or {}
            } for r in results]
        }
        return JSONResponse(content=export_data)
    
    elif format == "csv":
        # Get dataset info
        dataset = db.query(Dataset).filter(Dataset.id == job.dataset_id).first()
        
        # Load original dataset data for smart filter values
        dataset_rows_data = {}
        var_labels = {}
        if dataset and smart_filters:
            print(f"[CSV EXPORT] Loading dataset {dataset.id} for {len(smart_filters)} smart filters")
            try:
                # Try different path patterns
                file_path = None
                possible_paths = [
                    os.path.join(UPLOAD_DIR, dataset.filename),  # Direct in uploads
                    os.path.join(UPLOAD_DIR, dataset.id, dataset.filename),  # In subfolder
                    dataset.file_path if dataset.file_path else None,  # From database field
                ]
                for path in possible_paths:
                    if path and os.path.exists(path):
                        file_path = path
                        break
                
                print(f"[CSV EXPORT] Dataset file path: {file_path}, exists: {file_path and os.path.exists(file_path)}")
                if file_path and os.path.exists(file_path):
                    # Use pyreadstat to read the data
                    df, meta = pyreadstat.read_sav(file_path)
                    
                    # Build label lookup for each variable from metadata
                    for col in df.columns:
                        if col in meta.variable_value_labels:
                            var_labels[col] = {str(k): str(v) for k, v in meta.variable_value_labels[col].items()}
                    
                    # Read all rows as dict
                    for row_idx in range(len(df)):
                        row_dict = df.iloc[row_idx].to_dict()
                        dataset_rows_data[row_idx] = row_dict
                    
                    print(f"[CSV EXPORT] Loaded {len(dataset_rows_data)} rows, {len(var_labels)} variables with labels")
            except Exception as e:
                print(f"[CSV EXPORT] Error loading dataset for smart filters: {e}")
                import traceback
                print(traceback.format_exc())
        
        # Helper to get smart filter column name
        def get_sf_column_name(title: str) -> str:
            import re
            clean = re.sub(r'[^a-z0-9]+', '_', title.lower())
            return clean.strip('_') + '_sf'
        
        # Helper to truncate long labels (max 30 chars for concise output)
        def truncate_label(label: str, max_length: int = 30) -> str:
            if len(label) <= max_length:
                return label
            # Try to cut at a sensible point (word boundary)
            truncated = label[:max_length].rsplit(' ', 1)[0]
            if len(truncated) < max_length * 0.5:  # If too short after word break
                truncated = label[:max_length]
            return truncated.rstrip() + "..."
        
        # Helper to get smart filter value for a row
        def get_sf_value(row_data: dict, source_vars: List[str], var_labels: dict) -> str:
            values = []
            for var in source_vars:
                if var in row_data:
                    raw_val = row_data[var]
                    # Try to get label if exists
                    if var in var_labels and str(raw_val) in var_labels[var]:
                        label = var_labels[var][str(raw_val)]
                        # Truncate long labels
                        values.append(truncate_label(label, 50))
                    elif raw_val is not None:
                        values.append(str(raw_val))
            return "; ".join(values) if values else ""
        
        # Create CSV with review format
        rows = []
        current_date = datetime.now().strftime("%m-%d-%Y")  # American format
        
        for idx, r in enumerate(results, start=1):
            # Combine all sentences into review_content
            all_sentences = []
            for sentence_data in (r.sentences or []):
                sentence = sentence_data.get("sentence", "")
                if sentence:
                    all_sentences.append(sentence)
            
            review_content = " ".join(all_sentences)
            
            # Use manual review_title if provided, otherwise auto-generate
            final_review_title = review_title
            if not final_review_title and all_sentences:
                final_review_title = all_sentences[0][:50] + ("..." if len(all_sentences[0]) > 50 else "")
            
            row_data = {
                "product_id": product_id or "PROD-001",
                "product_name": product_name or "Product",
                "data_source": data_source or (dataset.filename if dataset else "survey_data.sav"),
                "review_date": current_date,
                "review_rating": review_rating,
                "review_content": review_content,
                "review_title": final_review_title,
                "reviewer_id": r.respondent_id or str(r.row_index + 1),
                "reviewer_name": f"Anonymous{idx}"
            }
            
            # Add smart filter columns
            original_row = dataset_rows_data.get(r.row_index, {})
            if idx == 1 and smart_filters:  # Log first row only
                print(f"[CSV EXPORT] First row smart filter processing: {len(smart_filters)} filters, row_index={r.row_index}")
                print(f"[CSV EXPORT] Original row keys: {list(original_row.keys())[:10]}...")
            for sf in smart_filters:
                col_name = get_sf_column_name(sf.get("title", "filter"))
                source_vars = sf.get("source_vars", [])
                sf_value = get_sf_value(original_row, source_vars, var_labels)
                if idx == 1:  # Log first row only
                    print(f"[CSV EXPORT] SF '{col_name}': source_vars={source_vars}, value='{sf_value}'")
                row_data[col_name] = sf_value
            
            rows.append(row_data)
        
        if not rows:
            empty_row = {
                "product_id": product_id or "",
                "product_name": product_name or "",
                "data_source": data_source or "",
                "review_date": current_date,
                "review_rating": review_rating,
                "review_content": "",
                "review_title": "",
                "reviewer_id": "",
                "reviewer_name": ""
            }
            # Add empty smart filter columns
            for sf in smart_filters:
                col_name = get_sf_column_name(sf.get("title", "filter"))
                empty_row[col_name] = ""
            rows = [empty_row]
        
        df = pd.DataFrame(rows)
        output = BytesIO()
        df.to_csv(output, index=False, encoding='utf-8-sig')
        output.seek(0)
        
        filename = f"{product_name.replace(' ', '_') if product_name else 'reviews'}_{job_id[:8]}.csv"
        
        return StreamingResponse(
            output,
            media_type="text/csv",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'}
        )
    
    else:
        raise HTTPException(status_code=400, detail=f"Unsupported format: {format}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
