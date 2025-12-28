"""
Ingestion service for populating respondents and responses tables
"""
from sqlalchemy.orm import Session
from sqlalchemy import and_
from typing import List, Dict, Any, Optional
import pandas as pd
import uuid
from datetime import datetime
import logging

from models import Dataset, Variable, ValueLabel, Respondent, Response
from database import DATABASE_AVAILABLE

logger = logging.getLogger(__name__)


class IngestionService:
    """Service for populating respondents and responses from dataset files"""
    
    def __init__(self):
        pass
    
    @staticmethod
    def normalize_value_code(value: Any) -> str:
        """
        Normalize value_code to consistent string format for matching.
        
        Strategy:
        - If numeric and whole number -> use int format as string ("1")
        - If numeric and decimal -> use float format as string ("1.5")
        - If not numeric -> use as-is string
        
        This ensures ValueLabel.value_code and Response.value_code can be matched
        consistently using Float cast comparison in SQL queries.
        
        Args:
            value: Any value (int, float, string, etc.)
            
        Returns:
            Normalized string representation
        """
        if value is None:
            return ""
        
        try:
            # Try to parse as float
            float_val = float(value)
            if float_val == int(float_val):
                # Whole number: use int format ("1")
                return str(int(float_val))
            else:
                # Decimal: use float format ("1.5")
                return str(float_val)
        except (ValueError, TypeError):
            # Not numeric, use as-is string
            return str(value)
    
    def populate_respondents_and_responses(
        self,
        db: Session,
        dataset_id: str,
        df: pd.DataFrame,
        variables: List[Dict[str, Any]],
        meta: Any
    ) -> Dict[str, int]:
        """
        Populate respondents and responses tables from dataframe
        
        Args:
            db: Database session
            dataset_id: Dataset ID
            df: DataFrame with survey data
            variables: List of variable metadata dicts
            meta: Metadata object (pyreadstat or ExcelCsvMeta)
            
        Returns:
            Dict with counts: {'respondents': int, 'responses': int}
        """
        if not DATABASE_AVAILABLE or db is None:
            logger.warning("Database not available, skipping respondent/response population")
            return {'respondents': 0, 'responses': 0}
        
        try:
            # Get or create Variable records
            variable_map = {}  # {var_code: Variable}
            
            # Build variable map from existing variables or create them
            for var_meta in variables:
                var_code = var_meta.get('code')
                if not var_code:
                    continue
                
                # Check if variable exists
                variable = db.query(Variable).filter(
                    and_(Variable.dataset_id == dataset_id, Variable.code == var_code)
                ).first()
                
                if not variable:
                    # Create new variable
                    # Convert numpy types to Python native types to avoid SQL schema errors
                    cardinality = var_meta.get('cardinality')
                    if cardinality is not None:
                        cardinality = int(cardinality) if not isinstance(cardinality, (str, type(None))) else cardinality
                    
                    response_count = var_meta.get('responseCount')
                    if response_count is not None:
                        response_count = int(response_count) if not isinstance(response_count, (str, type(None))) else response_count
                    
                    response_rate = var_meta.get('responseRate')
                    if response_rate is not None:
                        response_rate = float(response_rate) if not isinstance(response_rate, (str, type(None))) else response_rate
                    
                    # Determine is_demographic using heuristics
                    is_demographic = var_meta.get('is_demographic', False)
                    
                    # If not explicitly set, use heuristics
                    if not is_demographic:
                        label_lower = (var_meta.get('label') or '').lower()
                        code_lower = var_code.lower()
                        section_path = (var_meta.get('section_path') or '').lower()
                        
                        # Demographic keywords
                        demog_keywords = [
                            'demographic', 'demographics', 'demografi',
                            'age', 'yaş', 'age_band', 'age_group',
                            'gender', 'sex', 'cinsiyet',
                            'income', 'gelir', 'income_band', 'income_group',
                            'region', 'region', 'bölge', 'geography', 'location',
                            'education', 'education_level', 'eğitim',
                            'generation', 'generational', 'cohort', 'kuşak',
                            'generation', 'gen', 'generation'
                        ]
                        
                        # Check if label, code, or section_path contains demographic keywords
                        combined_text = f"{label_lower} {code_lower} {section_path}"
                        if any(keyword in combined_text for keyword in demog_keywords):
                            is_demographic = True
                    
                    variable = Variable(
                        dataset_id=dataset_id,
                        code=var_code,
                        label=var_meta.get('label') or var_code,
                        question_text=var_meta.get('label') or var_code,  # Use label as question_text for now
                        var_type=var_meta.get('type') or 'unknown',
                        measure=var_meta.get('measure') or 'unknown',
                        cardinality=cardinality,
                        response_count=response_count,
                        response_rate=response_rate,
                        is_demographic=is_demographic,
                        value_labels=var_meta.get('valueLabels'),
                        missing_values=var_meta.get('missingValues'),
                    )
                    db.add(variable)
                    db.flush()  # Get variable.id
                
                variable_map[var_code] = variable
                
                # Populate ValueLabel records
                value_labels_list = var_meta.get('valueLabels', [])
                if value_labels_list:
                    for idx, vl in enumerate(value_labels_list):
                        value_code = str(vl.get('value', ''))
                        value_label = vl.get('label', '')
                        
                        if not value_code:
                            continue
                        
                        # Normalize value_code using shared helper
                        value_code = self.normalize_value_code(value_code)
                        
                        # Check if value label exists
                        existing_vl = db.query(ValueLabel).filter(
                            and_(
                                ValueLabel.variable_id == variable.id,
                                ValueLabel.value_code == value_code
                            )
                        ).first()
                        
                        if not existing_vl:
                            value_label_obj = ValueLabel(
                                variable_id=variable.id,
                                value_code=value_code,
                                value_label=value_label,
                                order_index=idx,
                                is_missing_label=False,  # Will be determined from missing_values
                                is_other='other' in value_label.lower() if value_label else False
                            )
                            db.add(value_label_obj)
            
            db.commit()
            
            # Get respondent_id column (if available)
            respondent_id_col = None
            for var_code, variable in variable_map.items():
                if 'id' in var_code.lower() or 'respondent' in var_code.lower():
                    respondent_id_col = var_code
                    break
            
            # Populate Respondents
            respondent_map = {}  # {row_index: Respondent}
            respondents_created = 0
            
            for idx, row in df.iterrows():
                respondent_key = None
                if respondent_id_col and respondent_id_col in row:
                    val = row[respondent_id_col]
                    if pd.notna(val):
                        respondent_key = str(val)
                
                if not respondent_key:
                    respondent_key = f"row_{idx}"
                
                # Check if respondent exists
                respondent = db.query(Respondent).filter(
                    and_(
                        Respondent.dataset_id == dataset_id,
                        Respondent.respondent_key == respondent_key
                    )
                ).first()
                
                if not respondent:
                    respondent = Respondent(
                        dataset_id=dataset_id,
                        respondent_key=respondent_key,
                        weight=None,  # Will be populated if weight column exists
                        meta_json={'row_index': int(idx)}
                    )
                    db.add(respondent)
                    db.flush()
                    respondents_created += 1
                
                respondent_map[idx] = respondent
            
            db.commit()
            
            # Populate Responses (batch insert for performance)
            responses_created = 0
            response_batch = []
            
            for var_code, variable in variable_map.items():
                if var_code not in df.columns:
                    continue
                
                series = df[var_code]
                
                for idx, value in series.items():
                    if idx not in respondent_map:
                        continue
                    
                    respondent = respondent_map[idx]
                    
                    # Handle missing values
                    is_missing = pd.isna(value)
                    missing_type = "system" if is_missing else "none"
                    
                    # Convert value to normalized string for value_code
                    if is_missing:
                        value_code = None
                        numeric_value = None
                        verbatim_text = None
                    elif pd.api.types.is_numeric_dtype(series):
                        numeric_value = float(value) if pd.notna(value) else None
                        # Use normalize_value_code helper for consistent format
                        value_code = self.normalize_value_code(value) if pd.notna(value) else None
                        verbatim_text = None
                    else:
                        # Use normalize_value_code helper for consistency (handles edge cases)
                        value_code = self.normalize_value_code(value) if value is not None else None
                        numeric_value = None
                        verbatim_text = str(value) if value is not None else None
                    
                    # For multi-select, we'll create multiple response rows
                    # This handles both comma-separated and list formats
                    if value_code and ',' in value_code:
                        # Multi-select: create multiple responses
                        codes = [c.strip() for c in value_code.split(',')]
                        for code in codes:
                            if code:
                                response_batch.append(Response(
                                    respondent_id=respondent.id,
                                    variable_id=variable.id,
                                    value_code=code,
                                    numeric_value=None,
                                    verbatim_text=None,
                                    is_missing=False,
                                    missing_type="none"
                                ))
                    else:
                        # Single response
                        if value_code is not None or is_missing:
                            response_batch.append(Response(
                                respondent_id=respondent.id,
                                variable_id=variable.id,
                                value_code=value_code if value_code else '',
                                numeric_value=numeric_value,
                                verbatim_text=verbatim_text,
                                is_missing=is_missing,
                                missing_type=missing_type
                            ))
                    
                    # Batch insert every 1000 rows
                    if len(response_batch) >= 1000:
                        db.bulk_save_objects(response_batch)
                        db.commit()
                        responses_created += len(response_batch)
                        response_batch = []
            
            # Insert remaining responses
            if response_batch:
                db.bulk_save_objects(response_batch)
                db.commit()
                responses_created += len(response_batch)
            
            logger.info(f"Populated {respondents_created} respondents and {responses_created} responses for dataset {dataset_id}")
            
            return {
                'respondents': respondents_created,
                'responses': responses_created
            }
            
        except Exception as e:
            db.rollback()
            logger.error(f"Error populating respondents/responses: {e}", exc_info=True)
            raise


# Singleton instance
ingestion_service = IngestionService()

