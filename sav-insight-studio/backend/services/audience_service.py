"""
Audience service for managing audience membership with atomic swap pattern
"""
from sqlalchemy.orm import Session
from sqlalchemy import and_, text
from typing import Dict, Any, List
import pandas as pd
import logging

from models import Audience, AudienceMember, Respondent, Dataset, Variable, Response
from database import DATABASE_AVAILABLE
from pathlib import Path
from datetime import datetime

logger = logging.getLogger(__name__)


class AudienceService:
    """Service for managing audience membership"""
    
    def __init__(self):
        pass
    
    def _filter_respondents_by_filter_json(
        self,
        db: Session,
        dataset_id: str,
        filter_json: Dict[str, Any]
    ) -> List[int]:
        """
        Filter respondents based on filter_json
        Returns list of respondent IDs that match the filter
        
        TODO: Implement full filter_json parsing logic
        For now, basic implementation
        """
        # This is a simplified implementation
        # In production, filter_json should support complex conditions
        
        # Get all respondents for dataset
        respondents = db.query(Respondent).filter(
            Respondent.dataset_id == dataset_id
        ).all()
        
        if not filter_json:
            return [r.id for r in respondents]
        
        # Basic filter implementation
        # filter_json structure: {"variable_code": {"operator": "in", "values": [...]}}
        matching_respondent_ids = []
        
        for respondent in respondents:
            matches = True
            
            for var_code, filter_condition in filter_json.items():
                if not isinstance(filter_condition, dict):
                    continue
                
                operator = filter_condition.get("operator", "in")
                values = filter_condition.get("values", [])
                
                # Get variable
                variable = db.query(Variable).filter(
                    and_(
                        Variable.dataset_id == dataset_id,
                        Variable.code == var_code
                    )
                ).first()
                
                if not variable:
                    matches = False
                    break
                
                # Get response for this respondent and variable
                response = db.query(Response).filter(
                    and_(
                        Response.respondent_id == respondent.id,
                        Response.variable_id == variable.id
                    )
                ).first()
                
                if not response:
                    matches = False
                    break
                
                # Check if response value matches filter
                if operator == "in":
                    if str(response.value_code) not in [str(v) for v in values]:
                        matches = False
                        break
                elif operator == "not_in":
                    if str(response.value_code) in [str(v) for v in values]:
                        matches = False
                        break
                elif operator == "eq":
                    if str(response.value_code) != str(values[0] if values else None):
                        matches = False
                        break
                # Add more operators as needed
            
            if matches:
                matching_respondent_ids.append(respondent.id)
        
        return matching_respondent_ids
    
    def refresh_audience_membership(
        self,
        db: Session,
        audience_id: str
    ) -> Dict[str, Any]:
        """
        Refresh audience membership using atomic swap pattern
        
        Returns:
            Dict with status and size_n
        """
        if not DATABASE_AVAILABLE:
            raise ValueError("Database not available")
        
        try:
            # Get audience
            audience = db.query(Audience).filter(Audience.id == audience_id).first()
            if not audience:
                raise ValueError(f"Audience {audience_id} not found")
            
            # Get dataset
            dataset = db.query(Dataset).filter(Dataset.id == audience.dataset_id).first()
            if not dataset:
                raise ValueError(f"Dataset {audience.dataset_id} not found")
            
            # Get matching respondent IDs
            matching_respondent_ids = self._filter_respondents_by_filter_json(
                db=db,
                dataset_id=audience.dataset_id,
                filter_json=audience.filter_json
            )
            
            # Calculate new version
            new_version = audience.active_membership_version + 1
            
            # Insert new membership records (batch insert)
            # Use bulk_insert_mappings for better performance
            membership_records = []
            for respondent_id in matching_respondent_ids:
                membership_records.append(AudienceMember(
                    audience_id=audience_id,
                    version=new_version,
                    respondent_id=respondent_id
                ))
            
            # Batch insert
            if membership_records:
                # Split into batches of 1000
                batch_size = 1000
                for i in range(0, len(membership_records), batch_size):
                    batch = membership_records[i:i + batch_size]
                    db.bulk_save_objects(batch)
                    db.commit()
            
            # Atomic update: Set active_membership_version (single row update)
            audience.active_membership_version = new_version
            audience.size_n = len(matching_respondent_ids)
            audience.updated_at = datetime.utcnow()
            db.commit()
            
            logger.info(f"Refreshed audience {audience_id} membership: version {new_version}, size {len(matching_respondent_ids)}")
            
            # TODO: Async cleanup of old versions (background task)
            
            return {
                'status': 'success',
                'version': new_version,
                'size_n': len(matching_respondent_ids)
            }
            
        except Exception as e:
            db.rollback()
            logger.error(f"Error refreshing audience membership: {e}", exc_info=True)
            raise


# Singleton instance
audience_service = AudienceService()

