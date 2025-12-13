"""
SAV Insight Studio API
Comprehensive SPSS (.sav) file analysis platform with PostgreSQL storage
"""
from fastapi import FastAPI, UploadFile, File, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from sqlalchemy.orm import Session
from typing import Optional, List
import pandas as pd
import pyreadstat
import os
import json
import uuid
from datetime import datetime
from pathlib import Path
import numpy as np
from io import BytesIO
from dataclasses import asdict

# Local imports
from config import settings
from database import get_db, init_db, engine, Base, DATABASE_AVAILABLE
from models import Dataset, Variable, ExportHistory, AnalysisHistory
from services.quality_analyzer import QualityAnalyzer, QualityReport
from services.export_service import ExportService

# Create upload directory
UPLOAD_DIR = Path(settings.UPLOAD_DIR)
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

# Create FastAPI app
app = FastAPI(
    title="SAV Insight Studio API",
    description="Comprehensive SPSS data analysis platform",
    version="2.0.0"
)

# CORS middleware - Allow all origins for development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify exact origins like ["http://localhost:3000", "http://localhost:3001"]
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
)

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
_dataframe_cache = {}


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
    
    # Cache dataframe and info
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
        dataset = Dataset(
            id=dataset_info["id"],
            filename=dataset_info["filename"],
            original_filename=dataset_info["original_filename"],
            file_path=dataset_info["file_path"],
            n_rows=dataset_info["nRows"],
            n_cols=dataset_info["nCols"],
            overall_completion_rate=dataset_info.get("overallCompletionRate"),
            data_quality_score=dataset_info.get("dataQualityScore"),
            digital_twin_readiness=dataset_info.get("digitalTwinReadiness"),
            variables_meta=dataset_info["variables"],
            quality_report=dataset_info.get("qualityReport")
        )
        
        db.add(dataset)
        
        # Add variables
        for var_info in dataset_info["variables"]:
            variable = Variable(
                dataset_id=dataset_info["id"],
                code=var_info["code"],
                label=var_info.get("label"),
                var_type=var_info.get("type"),
                measure=var_info.get("measure"),
                cardinality=var_info.get("cardinality"),
                response_count=var_info.get("responseCount"),
                response_rate=var_info.get("responseRate"),
                value_labels=var_info.get("valueLabels"),
                missing_values=var_info.get("missingValues")
            )
            db.add(variable)
        
        db.commit()
        db.refresh(dataset)
        return dataset
    except Exception as e:
        if db:
            db.rollback()
        print(f"Database save error: {e}")
        return None


def get_dataframe(dataset_id: str, db: Session = None) -> tuple:
    """Get dataframe from cache or re-read from file"""
    if dataset_id in _dataframe_cache:
        cached = _dataframe_cache[dataset_id]
        return cached["df"], cached["meta"]
    
    # Try to get from database
    if db:
        dataset = db.query(Dataset).filter(Dataset.id == dataset_id).first()
        if dataset and os.path.exists(dataset.file_path):
            df, meta = pyreadstat.read_sav(dataset.file_path)
            _dataframe_cache[dataset_id] = {"df": df, "meta": meta}
            return df, meta
    
    return None, None


# ==================== API ENDPOINTS ====================

@app.post("/api/datasets/upload")
async def upload_dataset(file: UploadFile = File(...), db: Session = Depends(get_db)):
    """Upload and process a SAV file"""
    if not file.filename.lower().endswith('.sav'):
        raise HTTPException(status_code=400, detail="Only .sav files are supported")
    
    file_path = UPLOAD_DIR / f"{uuid.uuid4()}.sav"
    
    try:
        content = await file.read()
        with open(file_path, "wb") as f:
            f.write(content)
        
        dataset_info = process_sav_file(file_path, file.filename)
        
        # Save to database
        save_to_database(db, dataset_info)
        
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
    except Exception as e:
        if file_path.exists():
            file_path.unlink()
        raise HTTPException(status_code=500, detail=f"Error processing file: {str(e)}")


@app.get("/api/datasets")
async def list_datasets(db: Session = Depends(get_db)):
    """List all previously uploaded datasets"""
    # First return from in-memory cache
    results = []
    
    for dataset_id, data in _dataframe_cache.items():
        if "info" in data:
            info = data["info"]
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
    # Try cache first
    if dataset_id in _dataframe_cache and "info" in _dataframe_cache[dataset_id]:
        info = _dataframe_cache[dataset_id]["info"]
        return {
            "id": info["id"],
            "filename": info.get("original_filename", info.get("filename")),
            "nRows": info["nRows"],
            "nCols": info["nCols"],
            "createdAt": info["createdAt"],
            "variables": info["variables"],
            "qualityReport": info.get("qualityReport"),
            "digitalTwinReadiness": info.get("digitalTwinReadiness")
        }
    
    # Try database
    if db is not None and DATABASE_AVAILABLE:
        dataset = db.query(Dataset).filter(Dataset.id == dataset_id).first()
        
        if dataset:
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
    """Get detailed information about a specific variable"""
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
        
        # Calculate frequencies
        frequencies = []
        var_type = var_info.get("type", "unknown")
        if var_type in ["single_choice", "multi_choice", "scale"]:
            value_counts = series.value_counts()
            total = len(series.dropna())
            
            for val, count in value_counts.items():
                label = str(val)
                # Try to find label from valueLabels
                if var_info.get("valueLabels"):
                    label_match = next(
                        (vl.get("label", str(vl.get("value"))) for vl in var_info.get("valueLabels", []) 
                         if vl.get("value") == val),
                        str(val)
                    )
                    label = label_match
                
                frequencies.append({
                    "value": val if not pd.isna(val) else None,
                    "label": label,
                    "count": int(count),
                    "percent": round((count / total * 100) if total > 0 else 0, 2)
                })
        
        # Calculate statistics
        stats = None
        if var_type in ["numeric", "scale"]:
            numeric_series = pd.to_numeric(series, errors='coerce').dropna()
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
            "frequencies": frequencies,
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
async def export_dataset(dataset_id: str, export_type: str, db: Session = Depends(get_db)):
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
    
    df, meta = get_dataframe(dataset_id, db)
    
    if df is None:
        raise HTTPException(status_code=404, detail="Dataset file not found")
    
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
async def delete_dataset(dataset_id: str, db: Session = Depends(get_db)):
    """Delete a dataset"""
    deleted = False
    
    # Try cache first
    if dataset_id in _dataframe_cache:
        info = _dataframe_cache[dataset_id].get("info", {})
        file_path = info.get("file_path")
        if file_path and os.path.exists(file_path):
            os.remove(file_path)
        del _dataframe_cache[dataset_id]
        deleted = True
    
    # Try database
    if db is not None and DATABASE_AVAILABLE:
        dataset = db.query(Dataset).filter(Dataset.id == dataset_id).first()
        if dataset:
            if os.path.exists(dataset.file_path):
                os.remove(dataset.file_path)
            db.delete(dataset)
            db.commit()
            deleted = True
    
    if not deleted:
        raise HTTPException(status_code=404, detail="Dataset not found")
    
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
        "database_url_configured": bool(settings.DATABASE_URL),
        "upload_dir": str(UPLOAD_DIR),
        "version": "2.0.0"
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
