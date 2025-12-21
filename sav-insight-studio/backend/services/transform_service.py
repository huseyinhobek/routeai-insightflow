"""
Transform Service for Twin Transformer
Handles job queue, chunking, concurrency, and progress tracking
"""
import asyncio
import uuid
import re
from datetime import datetime
from typing import List, Dict, Any, Optional, Set
from dataclasses import dataclass, asdict
from sqlalchemy.orm import Session
import pandas as pd
import logging

from models import TransformJob, TransformResult, ExcludePattern
from services.openai_service import openai_service

logger = logging.getLogger(__name__)


# Patterns for detecting admin/metadata columns
ADMIN_COLUMN_PATTERNS = [
    r'^respondent[_\s]?id$',
    r'^resp[_\s]?id$',
    r'^record[_\s]?id$',
    r'^case[_\s]?id$',
    r'^interview[_\s]?id$',
    r'^participant[_\s]?id$',
    r'^id$',
    r'^uuid$',
    r'^timestamp$',
    r'^date[_\s]?collected$',
    r'^start[_\s]?time$',
    r'^end[_\s]?time$',
    r'^duration$',
    r'^ip[_\s]?address$',
    r'^user[_\s]?agent$',
    r'^device[_\s]?type$',
    r'^browser$',
    r'^language$',
    r'^country$',
    r'^region$',
    r'^city$',
    # Common SPSS / survey metadata fields
    r'^casenumber$',
    r'^case[_\s]?number$',
    r'^record$',
    r'^weight.*$',
    r'^base.*$',
    r'^sample.*$',
    r'^quota.*$',
    r'^panel.*$',
    r'^lang.*$',
]

# Suffix patterns commonly used for "All/None of the above" in multi grids
NONE_ALL_SUFFIXES = [
    "_99", "_999", "_98", "_998"
]

NONE_ALL_KEYWORDS = [
    "none of the above",
    "none of these",
    "yukarıdakilerin hiçbiri",
    "yukarıdakilerden hiçbiri",
    "hiçbiri",
    "hepsi",
    "yukarıdakilerin hepsi",
    "yukarıdakilerden hepsi",
    "all of the above",
    "all of these",
]

# Not applicable patterns - these should be filtered per-participant, not excluded globally
NOT_APPLICABLE_PATTERNS = [
    r"not\s*applicable",
    r"n\s*/\s*a",
    r"uygulanamaz",
    r"geçerli\s*değil",
    r"does\s*not\s*apply",
]

# Patterns for detecting exclude candidates in value labels
EXCLUDE_PATTERNS = {
    "none_of_above": {
        "label": "None of the above / Yukarıdakilerin hiçbiri",
        "patterns": [
            r"none\s*of\s*(the\s*)?(above|these)",
            r"hiçbiri",
            r"yukarıdakilerin\s*hiçbiri",
            r"hepsi\s*değil",
        ],
        "values": [99, 999, -99, -999, 98, 998]
    },
    "prefer_not_to_say": {
        "label": "Prefer not to say / Söylemek istemiyorum",
        "patterns": [
            r"prefer\s*not\s*to\s*(say|answer)",
            r"söylemek\s*istemiyorum",
            r"cevap\s*vermek\s*istemiyorum",
            r"belirtmek\s*istemiyorum",
        ],
        "values": [97, 997, -97, 99, 999, -99, -999],  # Added 99/999
        "default_enabled": True  # Enable by default for all variables
    },
    "dont_know": {
        "label": "Don't know / Bilmiyorum",
        "patterns": [
            r"don'?t\s*know",
            r"do\s*not\s*know",
            r"bilmiyorum",
            r"fikrim\s*yok",
            r"emin\s*değilim",
        ],
        "values": [96, 996, -96, 88, 888, 98, 998],  # Added 98/998
        "default_enabled": True  # Enable by default for all variables
    },
    "not_applicable": {
        "label": "Not applicable / Uygulanabilir değil",
        "patterns": [
            r"not\s*applicable",
            r"n/?a",
            r"uygulanabilir\s*değil",
            r"geçerli\s*değil",
        ],
        "values": [95, 995, -95]
    },
    "refused": {
        "label": "Refused / Reddetti",
        "patterns": [
            r"refused?",
            r"reddett?i",
            r"yanıt\s*vermedi",
        ],
        "values": [94, 994, -94]
    },
    "other_specify": {
        "label": "Other (specify) / Diğer (belirtiniz)",
        "patterns": [
            r"other\s*\(?specify\)?",
            r"diğer\s*\(?belirt",
            r"başka\s*\(?belirt",
        ],
        "values": []  # Usually open-ended, don't exclude by default
    }
}


@dataclass
class ColumnAnalysisResult:
    """Result of analyzing columns for transformation"""
    admin_columns: List[Dict[str, Any]]
    exclude_candidates: List[Dict[str, Any]]
    excluded_by_default_columns: List[Dict[str, Any]]  # [{code,label,type,reason}]
    transformable_columns: List[Dict[str, Any]]
    total_columns: int
    total_rows: int
    suggested_id_column: Optional[str] = None  # Auto-detected ID column


@dataclass
class JobProgress:
    """Current job progress"""
    job_id: str
    status: str
    total_rows: int  # Total rows in dataset
    row_limit: Optional[int]  # Max rows to process
    processed_rows: int
    failed_rows: int
    current_row_index: int
    percent_complete: float
    stats: Dict[str, Any]
    last_error: Optional[str]
    started_at: Optional[str]
    updated_at: str
    row_concurrency: Optional[int] = None
    chunk_size: Optional[int] = None
    exclude_options_config: Optional[Dict[str, Any]] = None  # Saved exclude settings
    admin_columns: Optional[List[str]] = None  # Saved admin columns
    column_analysis: Optional[Dict[str, Any]] = None  # Cached column analysis
    respondent_id_column: Optional[str] = None  # Respondent ID column


class TransformService:
    """Service for managing transform jobs"""
    
    def __init__(self):
        self._running_jobs: Dict[str, asyncio.Task] = {}
        self._job_stop_flags: Dict[str, bool] = {}
        self._job_pause_flags: Dict[str, bool] = {}
    
    def detect_admin_columns(self, variables: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Detect admin/metadata columns that should be excluded by default"""
        admin_cols = []
        
        for var in variables:
            code = var.get("code", "").lower()
            label = var.get("label", "").lower()
            
            is_admin = False
            for pattern in ADMIN_COLUMN_PATTERNS:
                if re.match(pattern, code, re.IGNORECASE) or re.match(pattern, label, re.IGNORECASE):
                    is_admin = True
                    break
            
            if is_admin:
                admin_cols.append({
                    "code": var.get("code"),
                    "label": var.get("label"),
                    "type": var.get("type"),
                    "reason": "Admin/metadata column"
                })
        
        return admin_cols

    def detect_id_column(self, df: pd.DataFrame, variables: List[Dict[str, Any]]) -> Optional[str]:
        """
        Detect the best ID column candidate from the dataset.
        Returns the column code with highest confidence score.
        """
        if df is None or len(df) == 0:
            return None
        
        candidates: List[Dict[str, Any]] = []
        
        # Check first 5 rows for ID patterns
        sample_rows = min(5, len(df))
        
        for var in variables:
            code = var.get("code")
            if not code or code not in df.columns:
                continue
            
            label = (var.get("label") or "").lower()
            code_l = code.lower()
            
            score = 0.0
            reasons = []
            
            # Pattern matching (high weight)
            id_patterns = [
                r'^id$',
                r'^respondent[_\s]?id$',
                r'^resp[_\s]?id$',
                r'^record[_\s]?id$',
                r'^case[_\s]?id$',
                r'^case[_\s]?number$',
                r'^participant[_\s]?id$',
                r'^interview[_\s]?id$',
            ]
            
            for pattern in id_patterns:
                if re.match(pattern, code_l, re.IGNORECASE) or re.match(pattern, label, re.IGNORECASE):
                    score += 50.0
                    reasons.append("ID pattern match")
                    break
            
            # Check uniqueness (high weight)
            series = df[code]
            unique_count = series.nunique()
            total_count = len(series)
            uniqueness_ratio = unique_count / total_count if total_count > 0 else 0
            
            if uniqueness_ratio > 0.95:  # Very unique
                score += 30.0
                reasons.append(f"High uniqueness ({uniqueness_ratio:.1%})")
            elif uniqueness_ratio > 0.8:
                score += 15.0
                reasons.append(f"Moderate uniqueness ({uniqueness_ratio:.1%})")
            
            # Check if values look like IDs (numeric, sequential, etc.)
            non_null = series.dropna()
            if len(non_null) > 0:
                # Check if mostly numeric
                numeric_count = 0
                for val in non_null.head(100):  # Sample first 100
                    try:
                        float(val)
                        numeric_count += 1
                    except (ValueError, TypeError):
                        pass
                
                if numeric_count / min(100, len(non_null)) > 0.8:
                    score += 10.0
                    reasons.append("Numeric values")
                
                # Check if sequential (IDs often are)
                if len(non_null) > 1:
                    try:
                        numeric_vals = pd.to_numeric(non_null.head(100), errors='coerce').dropna()
                        if len(numeric_vals) > 1:
                            sorted_vals = sorted(numeric_vals)
                            diffs = [sorted_vals[i+1] - sorted_vals[i] for i in range(len(sorted_vals)-1)]
                            if all(d == 1 for d in diffs[:10]):  # First 10 are sequential
                                score += 10.0
                                reasons.append("Sequential values")
                    except:
                        pass
            
            # Check sample rows for ID-like patterns
            sample_values = series.head(sample_rows).dropna()
            if len(sample_values) > 0:
                # Check if all sample values are non-empty and look like IDs
                all_valid = True
                for val in sample_values:
                    val_str = str(val).strip()
                    if not val_str or val_str.lower() in ['nan', 'none', 'null', '']:
                        all_valid = False
                        break
                
                if all_valid:
                    score += 5.0
                    reasons.append("All sample rows have valid values")
            
            if score > 0:
                candidates.append({
                    "code": code,
                    "label": var.get("label", code),
                    "score": score,
                    "reasons": reasons
                })
        
        if not candidates:
            return None
        
        # Sort by score descending
        candidates.sort(key=lambda x: x["score"], reverse=True)
        best = candidates[0]
        
        # Only return if score is above threshold
        if best["score"] >= 30.0:
            return best["code"]
        
        return None

    def detect_none_all_of_above_columns(self, variables: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Detect columns that represent 'None/All of the above' options.
        These are typically separate checkbox columns like QV6_99 etc.
        We exclude these columns by default (user can include).
        """
        excluded_cols: List[Dict[str, Any]] = []
        for var in variables:
            code = (var.get("code") or "").strip()
            label = (var.get("label") or "").strip()
            code_l = code.lower()
            label_l = label.lower()

            # Heuristic 1: suffix pattern
            has_suffix = any(code_l.endswith(suf) for suf in NONE_ALL_SUFFIXES)

            # Heuristic 2: label/value labels contains keywords
            has_keyword = any(k in label_l for k in NONE_ALL_KEYWORDS)
            if not has_keyword:
                for vl in (var.get("valueLabels") or []):
                    vl_label = (vl.get("label") or "").lower()
                    if any(k in vl_label for k in NONE_ALL_KEYWORDS):
                        has_keyword = True
                        break

            if has_suffix and has_keyword:
                excluded_cols.append({
                    "code": code,
                    "label": label,
                    "type": var.get("type"),
                    "reason": "None/All of the above (otomatik hariç)"
                })
        return excluded_cols
    
    def detect_exclude_candidates(
        self, 
        variables: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Detect potential exclude candidates in value labels"""
        candidates = {}
        
        for pattern_key, pattern_info in EXCLUDE_PATTERNS.items():
            candidates[pattern_key] = {
                "patternKey": pattern_key,
                "label": pattern_info["label"],
                "detectedValues": [],
                "affectedVariables": [],
                "defaultExclude": pattern_key != "other_specify"
            }
        
        for var in variables:
            value_labels = var.get("valueLabels", [])
            
            for vl in value_labels:
                value = vl.get("value")
                label = vl.get("label", "").lower()
                
                for pattern_key, pattern_info in EXCLUDE_PATTERNS.items():
                    matched = False
                    
                    # Check label patterns
                    for regex in pattern_info["patterns"]:
                        if re.search(regex, label, re.IGNORECASE):
                            matched = True
                            break
                    
                    # Check value patterns
                    if not matched and value in pattern_info["values"]:
                        matched = True
                    
                    if matched:
                        # Add to candidates
                        existing_values = [v["value"] for v in candidates[pattern_key]["detectedValues"]]
                        if value not in existing_values:
                            candidates[pattern_key]["detectedValues"].append({
                                "value": value,
                                "label": vl.get("label", str(value))
                            })
                        
                        if var.get("code") not in candidates[pattern_key]["affectedVariables"]:
                            candidates[pattern_key]["affectedVariables"].append(var.get("code"))
        
        # Filter out empty candidates
        return [c for c in candidates.values() if len(c["detectedValues"]) > 0]
    
    def analyze_columns(
        self,
        df: pd.DataFrame,
        variables: List[Dict[str, Any]]
    ) -> ColumnAnalysisResult:
        """Analyze columns for transformation readiness"""
        admin_columns = self.detect_admin_columns(variables)
        admin_codes = {c["code"] for c in admin_columns}

        none_all_columns = self.detect_none_all_of_above_columns(variables)
        none_all_codes = {c["code"] for c in none_all_columns}
        
        exclude_candidates = self.detect_exclude_candidates(variables)
        
        # Detect ID column
        suggested_id_column = self.detect_id_column(df, variables)
        
        transformable = []
        for var in variables:
            if (var.get("code") not in admin_codes) and (var.get("code") not in none_all_codes):
                transformable.append({
                    "code": var.get("code"),
                    "label": var.get("label"),
                    "type": var.get("type"),
                    "responseRate": var.get("responseRate", 0),
                    "valueLabels": var.get("valueLabels", [])
                })
        
        return ColumnAnalysisResult(
            admin_columns=admin_columns,
            exclude_candidates=exclude_candidates,
            excluded_by_default_columns=none_all_columns,
            transformable_columns=transformable,
            total_columns=len(variables),
            total_rows=len(df),
            suggested_id_column=suggested_id_column
        )
    
    def create_job(
        self,
        db: Session,
        dataset_id: str,
        total_rows: int,
        row_limit: int = None,
        chunk_size: int = 30,
        row_concurrency: int = 5,
        exclude_config: Dict[str, bool] = None,
        admin_columns: List[str] = None,
        column_analysis: Dict[str, Any] = None,
        respondent_id_column: str = None
    ) -> TransformJob:
        """Create a new transform job"""
        job = TransformJob(
            id=str(uuid.uuid4()),
            dataset_id=dataset_id,
            status="idle",
            chunk_size=chunk_size,
            row_concurrency=row_concurrency,
            total_rows=total_rows,  # Total rows in dataset
            row_limit=row_limit,  # Max rows to process
            current_row_index=0,
            processed_rows=0,
            failed_rows=0,
            stats={
                "totalColumns": 0,
                "processedColumns": 0,
                "emptySkipped": 0,
                "excludedSkipped": 0,
                "errors": 0,
                "retries": 0
            },
            exclude_options_config=exclude_config or {},
            admin_columns=admin_columns or [],
            column_analysis=column_analysis,
            respondent_id_column=respondent_id_column
        )
        
        db.add(job)
        db.commit()
        db.refresh(job)
        
        return job
    
    def get_job(self, db: Session, job_id: str) -> Optional[TransformJob]:
        """Get a job by ID"""
        return db.query(TransformJob).filter(TransformJob.id == job_id).first()
    
    def get_job_progress(self, job: TransformJob) -> JobProgress:
        """Get current job progress"""
        # Calculate effective total for progress calculation
        effective_total = job.row_limit if job.row_limit else job.total_rows
        percent = 0.0
        if effective_total > 0:
            percent = (job.processed_rows / effective_total) * 100
        
        return JobProgress(
            job_id=job.id,
            status=job.status,
            total_rows=job.total_rows,  # Total rows in dataset
            row_limit=job.row_limit,  # Max rows to process
            processed_rows=job.processed_rows,
            failed_rows=job.failed_rows,
            current_row_index=job.current_row_index,
            percent_complete=round(percent, 2),
            stats=job.stats or {},
            last_error=job.last_error,
            started_at=job.started_at.isoformat() if job.started_at else None,
            updated_at=job.updated_at.isoformat() if job.updated_at else datetime.utcnow().isoformat(),
            row_concurrency=job.row_concurrency,
            chunk_size=job.chunk_size,
            exclude_options_config=job.exclude_options_config,
            admin_columns=job.admin_columns,
            column_analysis=job.column_analysis,
            respondent_id_column=job.respondent_id_column
        )
    
    def _prepare_variable_input(
        self,
        var_info: Dict[str, Any],
        row_data: Any,
        excluded_values: Set[Any]
    ) -> Optional[Dict[str, Any]]:
        """Prepare a single variable for transformation"""
        code = var_info.get("code")
        value = row_data
        
        # Skip empty values
        if pd.isna(value) or value == "" or value is None:
            return None
        
        # Get value labels for checking "not applicable"
        value_labels = var_info.get("valueLabels", [])
        
        # Check if variable name indicates an exclude option (e.g., _99, _999, _98, etc.)
        def is_exclude_variable_by_name(var_code: str) -> bool:
            """Check if variable name ends with common exclude codes"""
            if not var_code:
                return False
            # Common suffixes for exclude options
            exclude_suffixes = ['_99', '_999', '_98', '_998', '_97', '_997', '_96', '_996', '_88', '_888']
            for suffix in exclude_suffixes:
                if var_code.endswith(suffix):
                    return True
            return False
        
        # Check if this variable should be excluded based on its name
        if is_exclude_variable_by_name(code):
            # This is an exclude option variable (like K2_R2_99)
            # If value is 0 or "No" or similar, skip it (participant didn't select this option)
            # If value is 1 or "Yes" or similar, also skip it (participant selected "prefer not to say")
            # Either way, we don't want to include these meta-variables in the transformation
            return None
        
        # Check if this specific value should be excluded (not applicable, prefer not to say, don't know)
        def should_exclude_value(val):
            """Check if a value should be excluded for this participant"""
            # First check common numeric codes (99, 999, 98, 998, 97, 997, 96, 996, 88, 888)
            common_exclude_codes = [99, 999, -99, -999, 98, 998, -98, -998, 97, 997, -97, -997, 96, 996, -96, -996, 88, 888, -88, -888]
            if val in common_exclude_codes:
                return True
            
            # Then check label patterns
            for vl in value_labels:
                if vl.get("value") == val:
                    label = (vl.get("label") or "").lower()
                    
                    # Check not applicable patterns
                    for pattern in NOT_APPLICABLE_PATTERNS:
                        if re.search(pattern, label, re.IGNORECASE):
                            return True
                    
                    # Check prefer not to say patterns
                    for pattern in EXCLUDE_PATTERNS.get("prefer_not_to_say", {}).get("patterns", []):
                        if re.search(pattern, label, re.IGNORECASE):
                            return True
                    
                    # Check don't know patterns
                    for pattern in EXCLUDE_PATTERNS.get("dont_know", {}).get("patterns", []):
                        if re.search(pattern, label, re.IGNORECASE):
                            return True
            
            return False
        
        # Skip / filter excluded values (per-variable) AND auto-excluded values
        if isinstance(value, (list, tuple)):
            filtered = [v for v in value if v not in excluded_values and not should_exclude_value(v)]
            if not filtered:
                return None
            value = filtered
        else:
            if value in excluded_values or should_exclude_value(value):
                return None
        
        # Get label for the value
        label = str(value)
        labels = []
        
        for vl in value_labels:
            if vl.get("value") == value:
                label = vl.get("label", str(value))
                break
        
        # For multi-choice, handle multiple values
        var_type = var_info.get("type", "unknown")
        if var_type == "multi_choice" and isinstance(value, (list, tuple)):
            labels = []
            for v in value:
                for vl in value_labels:
                    if vl.get("value") == v:
                        labels.append(vl.get("label", str(v)))
                        break
        
        # Build all possible options for context
        all_options = []
        for vl in value_labels:
            all_options.append(vl.get("label", str(vl.get("value"))))
        
        return {
            "name": code,
            "question": var_info.get("label", code),
            "var_type": var_type,
            "all_options": all_options,  # All possible answers for context
            "answer": {
                "raw": value,
                "label": label,
                "labels": labels if labels else [label]
            }
        }
    
    async def process_row(
        self,
        db: Session,
        job: TransformJob,
        row_index: int,
        row_data: pd.Series,
        variables: List[Dict[str, Any]],
        exclude_values_by_variable: Dict[str, Set[Any]],
        admin_columns: Set[str],
        excluded_variables: Set[str]
    ) -> TransformResult:
        """Process a single row - skip if already completed"""
        print(f"[PROCESS] Starting row {row_index}")
        
        # Check if this row was already processed successfully
        existing_result = db.query(TransformResult).filter(
            TransformResult.job_id == job.id,
            TransformResult.row_index == row_index,
            TransformResult.status == "completed"
        ).first()
        
        if existing_result:
            print(f"[PROCESS] Row {row_index} already completed, skipping")
            return existing_result
        
        result = TransformResult(
            job_id=job.id,
            row_index=row_index,
            status="processing"
        )
        
        # Prepare variables for this row
        prepared_vars = []
        empty_vars = []
        excluded_vars = []
        excluded_by_user_vars = []
        admin_vars = []
        
        for var_info in variables:
            code = var_info.get("code")
            
            if code in admin_columns:
                admin_vars.append(code)
                continue

            if code in excluded_variables:
                excluded_by_user_vars.append(code)
                continue
            
            value = row_data.get(code)
            
            if pd.isna(value) or value == "" or value is None:
                empty_vars.append(code)
                continue
            
            excluded_vals = exclude_values_by_variable.get(code, set())
            # If multi-select style value is a list/tuple, treat as excluded only if all selected values are excluded
            try:
                if isinstance(value, (list, tuple)):
                    filtered_vals = [v for v in value if v not in excluded_vals]
                    if not filtered_vals:
                        excluded_vars.append(code)
                        continue
                    value = filtered_vals
                else:
                    if value in excluded_vals:
                        excluded_vars.append(code)
                        continue
            except TypeError:
                # Defensive: if value is unhashable or weird type, skip this early exclude check
                pass
            
            var_input = self._prepare_variable_input(var_info, value, excluded_vals)
            if var_input:
                prepared_vars.append(var_input)
        
        result.excluded = {
            "emptyVars": empty_vars,
            "excludedByOption": excluded_vars,
            "adminVars": admin_vars,
            "excludedVariables": excluded_by_user_vars
        }
        
        # Check for respondent ID
        respondent_id = None
        # Prefer explicit configured respondentIdColumn (if provided)
        try:
            configured_id_col = (job.exclude_options_config or {}).get("respondentIdColumn")
        except Exception:
            configured_id_col = None

        if configured_id_col:
            val = row_data.get(configured_id_col)
            if val is not None and not pd.isna(val) and str(val).strip() != "":
                respondent_id = str(val)
        else:
            # Fallback: heuristic among admin columns containing "id"
            for admin_col in admin_columns:
                if "id" in admin_col.lower():
                    val = row_data.get(admin_col)
                    if val is not None and not pd.isna(val) and str(val).strip() != "":
                        respondent_id = str(val)
                        break
        
        result.respondent_id = respondent_id
        
        if not prepared_vars:
            result.status = "completed"
            result.sentences = []
            result.raw_trace = {"perChunk": [], "note": "No variables to process"}
            result.processed_at = datetime.utcnow()
            return result
        
        try:
            # Call OpenAI service
            transform_result = await openai_service.transform_row(
                job_id=job.id,
                dataset_id=job.dataset_id,
                row_index=row_index,
                respondent_id=respondent_id,
                variables=prepared_vars,
                chunk_size=job.chunk_size
            )
            
            result.sentences = transform_result["sentences"]
            result.raw_trace = transform_result["rawTrace"]
            result.status = "completed" if transform_result["success"] else "failed"
            result.retry_count = transform_result["totalRetries"]
            result.processed_at = datetime.utcnow()
            
        except Exception as e:
            logger.error(f"Error processing row {row_index}: {e}")
            result.status = "failed"
            result.error_message = str(e)
            result.processed_at = datetime.utcnow()
        
        return result
    
    async def run_job(
        self,
        db: Session,
        job_id: str,
        df: pd.DataFrame,
        variables: List[Dict[str, Any]]
    ):
        """Run the transform job"""
        print(f"[BG] run_job() called for {job_id}")
        # Clear any leftover flags from previous runs (e.g., after reset)
        self._job_stop_flags[job_id] = False
        self._job_pause_flags[job_id] = False

        job = self.get_job(db, job_id)
        if not job:
            print(f"[BG] Job {job_id} not found in DB")
            raise ValueError(f"Job {job_id} not found")
        print(f"[BG] Job {job_id} loaded, status={job.status}, total_rows={job.total_rows}")
        
        # Prepare excludes
        exclude_config = job.exclude_options_config or {}

        # Pattern toggles (global on/off), but applied per-variable via excludePatternVariables
        exclude_pattern_variables: Dict[str, List[str]] = exclude_config.get("excludePatternVariables", {}) or {}

        # Column-level excludes (user-controlled)
        excluded_variables = set(exclude_config.get("excludedVariables", []) or [])

        def build_exclude_values_by_variable() -> Dict[str, Set[Any]]:
            """
            Build mapping: variable_code -> set(excluded_raw_values)
            Only for variables that user selected for a given pattern AND pattern is enabled.
            If a column is in multiple patterns, only the first pattern is used (duplicate detection).
            """
            mapping: Dict[str, Set[Any]] = {}

            # enabled patterns
            enabled_patterns = {k for k, v in (exclude_config or {}).items() if isinstance(v, bool) and v}

            # Detect duplicates: column -> first_pattern
            column_to_patterns: Dict[str, List[str]] = {}
            for pattern_key in enabled_patterns:
                if pattern_key not in EXCLUDE_PATTERNS:
                    continue
                selected_vars = set(exclude_pattern_variables.get(pattern_key, []) or [])
                for code in selected_vars:
                    if code not in column_to_patterns:
                        column_to_patterns[code] = []
                    column_to_patterns[code].append(pattern_key)
            
            # For duplicates, use first pattern only
            duplicates: Dict[str, str] = {}
            for code, patterns in column_to_patterns.items():
                if len(patterns) > 1:
                    duplicates[code] = patterns[0]  # First pattern wins
                    logger.warning(f"Column {code} is in multiple exclude patterns: {patterns}. Using first pattern: {patterns[0]}")

            for var in variables:
                code = var.get("code")
                if not code:
                    continue
                value_labels = var.get("valueLabels", []) or []

                excluded_vals: Set[Any] = set()
                # Only process patterns that are enabled and not superseded by a duplicate
                patterns_to_check = enabled_patterns
                if code in duplicates:
                    # Only check the first pattern for this column
                    patterns_to_check = {duplicates[code]}
                
                for pattern_key in patterns_to_check:
                    if pattern_key not in EXCLUDE_PATTERNS:
                        continue
                    selected_vars = set(exclude_pattern_variables.get(pattern_key, []) or [])
                    if code not in selected_vars:
                        continue

                    pattern_info = EXCLUDE_PATTERNS[pattern_key]

                    # Match via valueLabels label regex
                    for vl in value_labels:
                        v = vl.get("value")
                        lab = (vl.get("label") or "").lower()
                        if any(re.search(rx, lab, re.IGNORECASE) for rx in pattern_info["patterns"]):
                            excluded_vals.add(v)

                    # Also include known numeric codes for this pattern (99/999/etc)
                    for v in pattern_info.get("values", []):
                        excluded_vals.add(v)

                if excluded_vals:
                    mapping[code] = excluded_vals

            return mapping

        exclude_values_by_variable = build_exclude_values_by_variable()
        # NOTE:
        # We previously used a global `exclude_values` set, but that caused cross-variable false positives
        # (e.g., "99" meaning different things in different questions). We now use per-variable excludes
        # via `exclude_values_by_variable` built above, so no global scan is needed.
        
        admin_columns = set(job.admin_columns or [])
        
        # Update job status
        job.status = "running"
        job.started_at = datetime.utcnow()
        db.commit()
        print(f"[BG] Job {job_id} marked running, starting processing")
        
        try:
            start_row = job.current_row_index or 0
            # Calculate effective total rows: use row_limit if set, otherwise all rows
            dataset_total_rows = len(df)
            if job.row_limit and job.row_limit > 0:
                effective_total_rows = min(job.row_limit, dataset_total_rows)
            else:
                effective_total_rows = dataset_total_rows
            
            print(f"[BG] Job {job_id}: start_row={start_row}, effective_total_rows={effective_total_rows}, dataset_total={dataset_total_rows}, row_limit={job.row_limit}, row_concurrency={job.row_concurrency}")
            
            # Process rows with concurrency
            semaphore = asyncio.Semaphore(job.row_concurrency)
            
            async def process_with_semaphore(row_idx: int, row_data: pd.Series):
                async with semaphore:
                    # Check stop/pause flags
                    if self._job_stop_flags.get(job_id):
                        return None
                    
                    while self._job_pause_flags.get(job_id):
                        await asyncio.sleep(0.5)
                        if self._job_stop_flags.get(job_id):
                            return None
                    
                    return await self.process_row(
                        db, job, row_idx, row_data, 
                        variables,
                        exclude_values_by_variable,
                        admin_columns,
                        excluded_variables
                    )
            
            print(f"[BG] Job {job_id}: entering main loop")
            checkpoint_interval = 10  # Save checkpoint every 10 rows
            
            for batch_start in range(start_row, effective_total_rows, job.row_concurrency):
                # Check stop flag
                if self._job_stop_flags.get(job_id):
                    print(f"[BG] Job {job_id}: stop flag set, breaking")
                    job.status = "paused"
                    db.commit()
                    break
                
                batch_end = min(batch_start + job.row_concurrency, effective_total_rows)
                tasks = []
                
                print(f"[BG] Job {job_id}: processing batch {batch_start}-{batch_end}")
                for row_idx in range(batch_start, batch_end):
                    # Ensure we don't read beyond the effective total row limit
                    if row_idx >= effective_total_rows:
                        continue
                    
                    # Check if already completed (skip if so)
                    existing = db.query(TransformResult).filter(
                        TransformResult.job_id == job.id,
                        TransformResult.row_index == row_idx,
                        TransformResult.status == "completed"
                    ).first()
                    if existing:
                        print(f"[BG] Row {row_idx} already completed, skipping")
                        job.processed_rows += 1
                        job.current_row_index = row_idx + 1
                        continue
                    
                    row_data = df.iloc[row_idx]
                    tasks.append(process_with_semaphore(row_idx, row_data))
                
                results = await asyncio.gather(*tasks, return_exceptions=True)
                print(f"[BG] Job {job_id}: batch done, {len(results)} results")
                
                # Save results
                for result in results:
                    if result is None:
                        continue
                    if isinstance(result, Exception):
                        logger.error(f"Task exception: {result}")
                        job.failed_rows += 1
                        job.stats["errors"] = job.stats.get("errors", 0) + 1
                        continue
                    
                    db.add(result)
                    job.processed_rows += 1
                    job.current_row_index = result.row_index + 1
                    
                    if result.status == "failed":
                        job.failed_rows += 1
                        job.last_error = result.error_message
                        job.stats["errors"] = job.stats.get("errors", 0) + 1
                    
                    job.stats["retries"] = job.stats.get("retries", 0) + result.retry_count
                    
                    # Save checkpoint every N rows
                    if job.processed_rows % checkpoint_interval == 0:
                        job.last_checkpoint = result.row_index
                        job.checkpoint_timestamp = datetime.utcnow()
                
                job.updated_at = datetime.utcnow()
                db.commit()
            
            # Check final status
            if not self._job_stop_flags.get(job_id):
                job.status = "completed"
                job.completed_at = datetime.utcnow()
                db.commit()
                
        except Exception as e:
            logger.error(f"Job {job_id} failed: {e}")
            job.status = "failed"
            job.last_error = str(e)
            db.commit()
        finally:
            # Cleanup flags
            self._job_stop_flags.pop(job_id, None)
            self._job_pause_flags.pop(job_id, None)
            self._running_jobs.pop(job_id, None)
    
    def start_job(
        self,
        db: Session,
        job_id: str,
        df: pd.DataFrame,
        variables: List[Dict[str, Any]]
    ) -> bool:
        """Start a job asynchronously"""
        if job_id in self._running_jobs:
            return False
        
        job = self.get_job(db, job_id)
        if not job or job.status == "running":
            return False
        
        # Create task
        self._job_stop_flags[job_id] = False
        self._job_pause_flags[job_id] = False
        
        task = asyncio.create_task(self.run_job(db, job_id, df, variables))
        self._running_jobs[job_id] = task
        
        return True
    
    def pause_job(self, db: Session, job_id: str) -> bool:
        """Pause a running job"""
        job = self.get_job(db, job_id)
        if not job or job.status != "running":
            return False
        
        self._job_pause_flags[job_id] = True
        job.status = "paused"
        db.commit()
        
        return True
    
    def resume_job(
        self,
        db: Session,
        job_id: str,
        df: pd.DataFrame,
        variables: List[Dict[str, Any]]
    ) -> bool:
        """Resume a paused job"""
        job = self.get_job(db, job_id)
        if not job or job.status not in ["paused", "idle"]:
            return False
        
        self._job_pause_flags[job_id] = False
        
        if job_id not in self._running_jobs:
            return self.start_job(db, job_id, df, variables)
        
        return True
    
    def stop_job(self, db: Session, job_id: str) -> bool:
        """Stop a running or paused job"""
        job = self.get_job(db, job_id)
        if not job:
            return False
        
        self._job_stop_flags[job_id] = True
        self._job_pause_flags[job_id] = False
        
        job.status = "paused"
        db.commit()
        
        return True
    
    def reset_job(self, db: Session, job_id: str, confirm_text: str) -> bool:
        """Reset a job - requires confirmation"""
        if confirm_text != "DELETE":
            return False
        
        job = self.get_job(db, job_id)
        if not job:
            return False
        
        # Stop if running (and clear in-memory flags/tasks)
        self._job_stop_flags[job_id] = True
        self._job_pause_flags[job_id] = False
        task = self._running_jobs.pop(job_id, None)
        if task:
            try:
                task.cancel()
            except Exception:
                pass
        
        # Delete results
        db.query(TransformResult).filter(TransformResult.job_id == job_id).delete()
        
        # Reset job state
        job.status = "idle"
        job.current_row_index = 0
        job.processed_rows = 0
        job.failed_rows = 0
        job.last_error = None
        job.error_count = 0
        job.stats = {
            "totalColumns": 0,
            "processedColumns": 0,
            "emptySkipped": 0,
            "excludedSkipped": 0,
            "errors": 0,
            "retries": 0
        }
        job.started_at = None
        job.completed_at = None
        
        db.commit()

        # Ensure future starts are not blocked by stale stop/pause flags
        self._job_stop_flags.pop(job_id, None)
        self._job_pause_flags.pop(job_id, None)
        
        return True
    
    def get_results(
        self,
        db: Session,
        job_id: str,
        offset: int = 0,
        limit: int = 50
    ) -> List[TransformResult]:
        """Get transformation results with pagination"""
        return db.query(TransformResult)\
            .filter(TransformResult.job_id == job_id)\
            .order_by(TransformResult.row_index)\
            .offset(offset)\
            .limit(limit)\
            .all()
    
    def get_result_by_row(
        self,
        db: Session,
        job_id: str,
        row_index: int
    ) -> Optional[TransformResult]:
        """Get a single result by row index"""
        return db.query(TransformResult)\
            .filter(TransformResult.job_id == job_id, TransformResult.row_index == row_index)\
            .first()


# Singleton instance
transform_service = TransformService()

