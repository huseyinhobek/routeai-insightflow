"""
Utterance generation service
Creates deterministic template-based sentences for RAG retrieval
"""
from sqlalchemy.orm import Session
from typing import List, Dict, Any, Optional
import logging

from models import Variable, ValueLabel, Respondent, Response, Utterance, TransformResult, TransformJob
from database import DATABASE_AVAILABLE

logger = logging.getLogger(__name__)


class UtteranceService:
    """Service for generating deterministic utterances from survey responses"""
    
    def __init__(self):
        pass
    
    def generate_utterance_text(
        self,
        variable: Variable,
        value_code: str,
        value_label: Optional[str] = None,
        numeric_value: Optional[float] = None,
        verbatim_text: Optional[str] = None,
        var_type: Optional[str] = None
    ) -> Dict[str, str]:
        """
        Generate utterance text using deterministic templates
        
        Returns:
            Dict with keys: 'utterance_text', 'display_text', 'text_for_embedding'
        """
        var_type = var_type or variable.var_type or 'unknown'
        question_short = variable.question_text or variable.label or variable.code
        
        # Generate utterance based on type
        if var_type in ['single_choice', 'multi_choice']:
            if value_label:
                # Template: "{question_short}: {value_label}."
                utterance_text = f"{question_short}: {value_label}."
                display_text = utterance_text
            else:
                utterance_text = f"{question_short}: {value_code}."
                display_text = utterance_text
                
        elif var_type == 'numeric':
            if numeric_value is not None:
                utterance_text = f"{question_short}: {numeric_value}."
                display_text = utterance_text
            else:
                utterance_text = f"{question_short}: {value_code}."
                display_text = utterance_text
                
        elif var_type == 'text' and verbatim_text:
            utterance_text = f"{question_short}: {verbatim_text}."
            display_text = utterance_text
        else:
            # Fallback
            if value_label:
                utterance_text = f"{question_short}: {value_label}."
            else:
                utterance_text = f"{question_short}: {value_code}."
            display_text = utterance_text
        
        # Generate canonical text_for_embedding format
        # Format: "Q: {question_text} | A: {value_label} | var: {var_code} | U: {display_text}"
        answer_text = value_label or str(value_code) or str(numeric_value) or verbatim_text or ""
        text_for_embedding = f"Q: {variable.question_text or variable.label or variable.code} | A: {answer_text} | var: {variable.code} | U: {display_text}"
        
        return {
            'utterance_text': utterance_text,
            'display_text': display_text,
            'text_for_embedding': text_for_embedding
        }
    
    def generate_utterances_for_response(
        self,
        db: Session,
        response: Response,
        variable: Variable,
        value_label_obj: Optional[ValueLabel] = None
    ) -> Optional[Utterance]:
        """
        Generate utterance for a single response
        
        Returns:
            Utterance object or None if generation should be skipped
        """
        if not DATABASE_AVAILABLE:
            return None
        
        # Skip missing responses (unless we want to include them with special handling)
        if response.is_missing:
            return None
        
        # Get value label if available
        value_label = None
        if value_label_obj:
            value_label = value_label_obj.value_label
        elif response.value_code:
            # Try to find value label from database
            vl = db.query(ValueLabel).filter(
                ValueLabel.variable_id == variable.id,
                ValueLabel.value_code == response.value_code
            ).first()
            if vl:
                value_label = vl.value_label
        
        # Generate utterance text
        utterance_data = self.generate_utterance_text(
            variable=variable,
            value_code=response.value_code or '',
            value_label=value_label,
            numeric_value=response.numeric_value,
            verbatim_text=response.verbatim_text,
            var_type=variable.var_type
        )
        
        # Create provenance JSON
        provenance_json = {
            'respondent_id': response.respondent_id,
            'variable_id': variable.id,
            'variable_code': variable.code,
            'value_code': response.value_code,
            'question_text': variable.question_text or variable.label
        }
        
        # Create utterance
        utterance = Utterance(
            respondent_id=response.respondent_id,
            variable_id=variable.id,
            # response_id=response.id,  # Disabled until response_id column is added to database
            value_code=response.value_code,
            utterance_text=utterance_data['utterance_text'],
            display_text=utterance_data['display_text'],
            text_for_embedding=utterance_data['text_for_embedding'],
            language="en",  # Default, can be detected from dataset metadata
            provenance_json=provenance_json
        )
        
        return utterance
    
    def generate_utterances_from_transform_results(
        self,
        db: Session,
        dataset_id: str,
        job_id: Optional[str] = None
    ) -> Dict[str, int]:
        """
        Generate utterances from existing TransformResult sentences (hybrid strategy)
        
        This reuses sentences from TransformResult but ensures canonical text_for_embedding format
        """
        if not DATABASE_AVAILABLE:
            return {'utterances': 0, 'skipped': 0}
        
        utterances_created = 0
        skipped = 0
        
        try:
            # Get transform results
            query = db.query(TransformResult).join(TransformJob).filter(
                TransformJob.dataset_id == dataset_id
            )
            if job_id:
                query = query.filter(TransformJob.id == job_id)
            
            transform_results = query.all()
            
            for result in transform_results:
                if not result.sentences or not isinstance(result.sentences, list):
                    skipped += 1
                    continue
                
                # Get respondent - use row_index to match with respondent_key ("row_0", "row_1", etc.)
                # This handles cases where TransformResult.respondent_id might be in a different format
                respondent = None
                if result.row_index is not None:
                    expected_key = f"row_{result.row_index}"
                    respondent = db.query(Respondent).filter(
                        Respondent.dataset_id == dataset_id,
                        Respondent.respondent_key == expected_key
                    ).first()
                
                # Fallback: try using respondent_id if row_index matching failed
                if not respondent and result.respondent_id:
                    respondent = db.query(Respondent).filter(
                        Respondent.dataset_id == dataset_id,
                        Respondent.respondent_key == str(result.respondent_id)
                    ).first()
                
                if not respondent:
                    skipped += 1
                    continue
                
                # Process each sentence from TransformResult
                for sentence_data in result.sentences:
                    if not isinstance(sentence_data, dict):
                        continue
                    
                    sentence_text = sentence_data.get('sentence', '')
                    sources = sentence_data.get('sources', [])
                    
                    if not sentence_text or not sources:
                        continue
                    
                    # Try to match sources to variables
                    for source_var_code in sources:
                        variable = db.query(Variable).filter(
                            Variable.dataset_id == dataset_id,
                            Variable.code == source_var_code
                        ).first()
                        
                        if not variable:
                            continue
                        
                        # Get response for this variable and respondent
                        response = db.query(Response).filter(
                            Response.respondent_id == respondent.id,
                            Response.variable_id == variable.id
                        ).first()
                        
                        if not response:
                            continue
                        
                        # Check if utterance already exists
                        existing = db.query(Utterance).filter(
                            Utterance.respondent_id == respondent.id,
                            Utterance.variable_id == variable.id,
                            Utterance.value_code == (response.value_code or '')
                        ).first()
                        
                        if existing:
                            # Update text_for_embedding to canonical format
                            value_label = None
                            vl = db.query(ValueLabel).filter(
                                ValueLabel.variable_id == variable.id,
                                ValueLabel.value_code == response.value_code
                            ).first()
                            if vl:
                                value_label = vl.value_label
                            
                            answer_text = value_label or str(response.value_code) or ""
                            existing.text_for_embedding = f"Q: {variable.question_text or variable.label or variable.code} | A: {answer_text} | var: {variable.code} | U: {existing.display_text or sentence_text}"
                            continue
                        
                        # Get value label
                        value_label = None
                        if response.value_code:
                            vl = db.query(ValueLabel).filter(
                                ValueLabel.variable_id == variable.id,
                                ValueLabel.value_code == response.value_code
                            ).first()
                            if vl:
                                value_label = vl.value_label
                        
                        # Create utterance with canonical format
                        answer_text = value_label or str(response.value_code) or ""
                        text_for_embedding = f"Q: {variable.question_text or variable.label or variable.code} | A: {answer_text} | var: {variable.code} | U: {sentence_text}"
                        
                        provenance_json = {
                            'respondent_id': respondent.id,
                            'variable_id': variable.id,
                            'variable_code': variable.code,
                            'value_code': response.value_code,
                            'question_text': variable.question_text or variable.label
                        }
                        
                        utterance = Utterance(
                            respondent_id=respondent.id,
                            variable_id=variable.id,
                            # response_id=response.id,  # Disabled until response_id column is added to database
                            value_code=response.value_code,
                            utterance_text=sentence_text,  # Use TransformResult sentence as canonical
                            display_text=sentence_text,
                            text_for_embedding=text_for_embedding,  # Always canonical format
                            language="en",
                            provenance_json=provenance_json
                        )
                        
                        db.add(utterance)
                        utterances_created += 1
            
            db.commit()
            logger.info(f"Generated {utterances_created} utterances from TransformResults, skipped {skipped}")
            
            return {'utterances': utterances_created, 'skipped': skipped}
            
        except Exception as e:
            db.rollback()
            logger.error(f"Error generating utterances from TransformResults: {e}", exc_info=True)
            raise
    
    def generate_utterances_for_dataset(
        self,
        db: Session,
        dataset_id: str,
        limit: Optional[int] = None
    ) -> Dict[str, int]:
        """
        Generate utterances for all responses in a dataset (deterministic template-based)
        
        Args:
            db: Database session
            dataset_id: Dataset ID
            limit: Optional limit on number of responses to process
            
        Returns:
            Dict with counts: {'utterances': int, 'skipped': int}
        """
        if not DATABASE_AVAILABLE:
            return {'utterances': 0, 'skipped': 0}
        
        utterances_created = 0
        skipped = 0
        
        try:
            # Get all variables for this dataset
            variables = db.query(Variable).filter(Variable.dataset_id == dataset_id).all()
            variable_map = {v.id: v for v in variables}
            
            # Get all responses
            query = db.query(Response).join(Respondent).filter(
                Respondent.dataset_id == dataset_id
            )
            
            if limit:
                query = query.limit(limit)
            
            responses = query.all()
            
            # Pre-fetch value labels
            variable_ids = list(variable_map.keys())
            value_labels = db.query(ValueLabel).filter(
                ValueLabel.variable_id.in_(variable_ids)
            ).all()
            vl_map = {}  # {(variable_id, value_code): ValueLabel}
            for vl in value_labels:
                vl_map[(vl.variable_id, vl.value_code)] = vl
            
            # Generate utterances
            utterance_batch = []
            for response in responses:
                variable = variable_map.get(response.variable_id)
                if not variable:
                    skipped += 1
                    continue
                
                # Check if utterance already exists (prefer matching by response_id)
                existing = None
                if response.id is not None:
                    existing = db.query(Utterance).filter(
                        Utterance.response_id == response.id
                    ).first()
                if not existing:
                    existing = db.query(Utterance).filter(
                        Utterance.respondent_id == response.respondent_id,
                        Utterance.variable_id == response.variable_id,
                        Utterance.value_code == (response.value_code or '')
                    ).first()
                
                if existing:
                    skipped += 1
                    continue
                
                value_label_obj = vl_map.get((response.variable_id, response.value_code))
                utterance = self.generate_utterances_for_response(
                    db=db,
                    response=response,
                    variable=variable,
                    value_label_obj=value_label_obj
                )
                
                if utterance:
                    utterance_batch.append(utterance)
                    
                    # Batch insert every 1000 utterances
                    if len(utterance_batch) >= 1000:
                        db.bulk_save_objects(utterance_batch)
                        db.commit()
                        utterances_created += len(utterance_batch)
                        utterance_batch = []
            
            # Insert remaining utterances
            if utterance_batch:
                db.bulk_save_objects(utterance_batch)
                db.commit()
                utterances_created += len(utterance_batch)
            
            logger.info(f"Generated {utterances_created} utterances for dataset {dataset_id}, skipped {skipped}")
            
            return {'utterances': utterances_created, 'skipped': skipped}
            
        except Exception as e:
            db.rollback()
            logger.error(f"Error generating utterances: {e}", exc_info=True)
            raise


# Singleton instance
utterance_service = UtteranceService()

