"""
Embedding service for creating and retrieving vector embeddings
Uses OpenAI text-embedding models and pgvector for storage/retrieval
"""
from sqlalchemy.orm import Session
from sqlalchemy import text, and_
from typing import List, Dict, Any, Optional, Tuple
import logging
import json
import numpy as np

from models import Variable, Utterance, Embedding, Dataset
from database import DATABASE_AVAILABLE
from config import settings

logger = logging.getLogger(__name__)


class EmbeddingService:
    """Service for generating and retrieving embeddings"""
    
    def __init__(self):
        self.model = getattr(settings, "EMBEDDING_MODEL", "text-embedding-3-small")
        self.client = None
    
    def _ensure_client(self):
        """Initialize OpenAI client"""
        if self.client is None:
            try:
                from openai import OpenAI
                if not settings.OPENAI_API_KEY:
                    raise ValueError("OPENAI_API_KEY is not configured")
                self.client = OpenAI(api_key=settings.OPENAI_API_KEY)
            except ImportError:
                raise ImportError("openai package is required for embedding generation")
    
    def generate_embedding(self, text: str) -> Optional[List[float]]:
        """
        Generate embedding for a text using OpenAI API
        
        Returns:
            List of floats (embedding vector) or None if error
        """
        if not text or not text.strip():
            return None
        
        try:
            self._ensure_client()
            
            response = self.client.embeddings.create(
                model=self.model,
                input=text.strip()
            )
            
            return response.data[0].embedding
            
        except Exception as e:
            logger.error(f"Error generating embedding: {e}", exc_info=True)
            return None
    
    def vector_to_text(self, vector: List[float]) -> str:
        """
        Convert embedding vector to text format for pgvector storage
        pgvector expects format: '[0.1,0.2,0.3,...]'
        """
        if not vector:
            return '[]'
        return '[' + ','.join(str(float(v)) for v in vector) + ']'
    
    def generate_variable_embedding_text(self, variable: Variable) -> str:
        """
        Generate text to embed for a variable
        Format: var_code + question_text + var_label + section_path + value_labels_summary
        """
        parts = []
        
        if variable.code:
            parts.append(variable.code)
        
        if variable.question_text:
            parts.append(variable.question_text)
        elif variable.label:
            parts.append(variable.label)
        
        if variable.section_path:
            parts.append(variable.section_path)
        
        # Add value labels summary (first 20 labels)
        if variable.value_labels and isinstance(variable.value_labels, list):
            labels = []
            for vl in variable.value_labels[:20]:
                if isinstance(vl, dict):
                    label = vl.get('label', '')
                    if label:
                        labels.append(label)
                else:
                    labels.append(str(vl))
            
            if labels:
                parts.append("Values: " + ", ".join(labels))
        
        return " | ".join(parts)
    
    def create_variable_embedding(
        self,
        db: Session,
        variable: Variable
    ) -> Optional[Embedding]:
        """
        Create embedding for a variable
        
        Returns:
            Embedding object or None if error
        """
        if not DATABASE_AVAILABLE:
            return None
        
        try:
            # Check if embedding already exists
            existing = db.query(Embedding).filter(
                and_(
                    Embedding.object_type == 'variable',
                    Embedding.object_id == variable.id,
                    Embedding.dataset_id == variable.dataset_id
                )
            ).first()
            
            if existing:
                return existing
            
            # Generate embedding text
            embedding_text = self.generate_variable_embedding_text(variable)
            
            # Generate embedding vector
            vector = self.generate_embedding(embedding_text)
            if not vector:
                logger.warning(f"Failed to generate embedding for variable {variable.id}")
                return None
            
            # Convert to text format for storage
            vector_text = self.vector_to_text(vector)
            
            # Create embedding record
            embedding = Embedding(
                object_type='variable',
                object_id=variable.id,
                dataset_id=variable.dataset_id,
                vector=vector_text,
                text_for_embedding=embedding_text,
                meta_json={
                    'variable_code': variable.code,
                    'var_type': variable.var_type
                }
            )
            
            db.add(embedding)
            db.commit()
            db.refresh(embedding)
            
            return embedding
            
        except Exception as e:
            db.rollback()
            logger.error(f"Error creating variable embedding: {e}", exc_info=True)
            return None
    
    def create_utterance_embedding(
        self,
        db: Session,
        utterance: Utterance
    ) -> Optional[Embedding]:
        """
        Create embedding for an utterance
        
        Returns:
            Embedding object or None if error
        """
        if not DATABASE_AVAILABLE:
            return None
        
        try:
            # Resolve variable and dataset first (needed both for canonical text reconstruction
            # and for Embedding.dataset_id)
            variable = db.query(Variable).filter(Variable.id == utterance.variable_id).first()
            if not variable:
                logger.warning(f"Variable {utterance.variable_id} not found for utterance {utterance.id}")
                return None
            dataset_id = variable.dataset_id

            # Check if embedding already exists
            existing = db.query(Embedding).filter(
                and_(
                    Embedding.object_type == 'utterance',
                    Embedding.object_id == utterance.id,
                    Embedding.dataset_id == dataset_id,
                )
            ).first()
            if existing:
                return existing

            # Always prefer the canonical survey-aware format.
            # If text_for_embedding is missing, try to reconstruct it deterministically.
            if not utterance.text_for_embedding:
                answer_text = ""

                # If we have a linked response, use it (best source of truth)
                response = None
                if utterance.response_id:
                    from models import Response as ResponseModel  # local import to avoid cycles
                    response = db.query(ResponseModel).filter(ResponseModel.id == utterance.response_id).first()

                if response:
                    # Try to find value label
                    from models import ValueLabel as ValueLabelModel  # local import to avoid cycles
                    value_label_obj = None
                    if response.value_code is not None:
                        value_label_obj = db.query(ValueLabelModel).filter(
                            and_(
                                ValueLabelModel.variable_id == variable.id,
                                ValueLabelModel.value_code == str(response.value_code),
                            )
                        ).first()
                    if value_label_obj and value_label_obj.value_label:
                        answer_text = value_label_obj.value_label
                    elif response.verbatim_text:
                        answer_text = str(response.verbatim_text)
                    elif response.numeric_value is not None:
                        answer_text = str(response.numeric_value)
                    elif response.value_code is not None:
                        answer_text = str(response.value_code)
                else:
                    # Fallback to provenance/value_code when response is not linked
                    prov = utterance.provenance_json or {}
                    answer_text = prov.get("value_label") or prov.get("value_code") or ""

                canonical_text = (
                    f"Q: {variable.question_text or variable.label or variable.code} | "
                    f"A: {answer_text} | var: {variable.code} | "
                    f"U: {utterance.display_text or utterance.utterance_text or ''}"
                )
                utterance.text_for_embedding = canonical_text

            embedding_text = utterance.text_for_embedding
            if not embedding_text or not embedding_text.strip():
                # If we still don't have a safe canonical text, skip embedding to avoid polluting the index
                logger.warning(f"Skipping embedding for utterance {utterance.id}: no canonical text_for_embedding")
                return None

            # Generate embedding vector
            vector = self.generate_embedding(embedding_text)
            if not vector:
                logger.warning(f"Failed to generate embedding for utterance {utterance.id}")
                return None
            
            # Convert to text format for storage
            vector_text = self.vector_to_text(vector)

            # Create embedding record
            embedding = Embedding(
                object_type='utterance',
                object_id=utterance.id,
                dataset_id=dataset_id,
                vector=vector_text,
                text_for_embedding=embedding_text,
                meta_json={
                    'variable_id': utterance.variable_id,
                    'variable_code': utterance.variable.code,
                    'respondent_id': utterance.respondent_id
                }
            )
            
            db.add(embedding)
            db.commit()
            db.refresh(embedding)
            
            return embedding
            
        except Exception as e:
            db.rollback()
            logger.error(f"Error creating utterance embedding: {e}", exc_info=True)
            return None
    
    def get_variable_embeddings(
        self,
        db: Session,
        dataset_id: str,
        query_vector: List[float],
        top_k: int = 20
    ) -> List[Dict[str, Any]]:
        """
        Retrieve top-K variable embeddings by similarity
        
        Args:
            db: Database session
            dataset_id: Dataset ID
            query_vector: Query embedding vector
            top_k: Number of results to return
            
        Returns:
            List of dicts with keys: variable_id, var_code, score, distance
        """
        if not DATABASE_AVAILABLE:
            return []
        
        try:
            query_vector_text = self.vector_to_text(query_vector)
            
            # Use pgvector cosine distance operator (<=>)
            # Note: Use CAST instead of :: syntax for SQLAlchemy parameter binding
            sql = text("""
                SELECT 
                    e.object_id as variable_id,
                    e.meta_json->>'variable_code' as var_code,
                    (CAST(e.vector AS vector) <=> CAST(:query_vec AS vector)) as distance
                FROM embeddings e
                WHERE e.dataset_id = CAST(:dataset_id AS VARCHAR)
                  AND e.object_type = 'variable'
                ORDER BY distance ASC
                LIMIT CAST(:top_k AS INTEGER)
            """)
            
            result = db.execute(
                sql,
                {
                    'dataset_id': dataset_id,
                    'query_vec': query_vector_text,
                    'top_k': top_k
                }
            )
            
            variables = []
            for row in result:
                try:
                    variables.append({
                        'variable_id': row.variable_id,
                        'var_code': row.var_code,
                        'distance': float(row.distance),
                        'score': 1.0 - float(row.distance)  # Convert distance to similarity (cosine similarity = 1 - distance)
                    })
                except Exception as row_error:
                    logger.warning(f"Error processing embedding row: {row_error}")
                    continue
            
            return variables
            
        except Exception as e:
            logger.error(f"Error retrieving variable embeddings: {e}", exc_info=True)
            # Rollback to clear any failed transaction state
            try:
                db.rollback()
            except:
                pass
            # Fallback: if pgvector query fails, return empty list
            return []
    
    def get_utterance_embeddings(
        self,
        db: Session,
        dataset_id: str,
        query_vector: List[float],
        top_k: int = 50,
        audience_id: Optional[str] = None,
        variable_id: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Retrieve top-K utterance embeddings by similarity with optional filters
        
        Args:
            db: Database session
            dataset_id: Dataset ID
            query_vector: Query embedding vector
            top_k: Number of results to return
            audience_id: Optional audience ID to filter by membership
            variable_id: Optional variable ID to filter utterances
            
        Returns:
            List of dicts with keys: utterance_id, respondent_id, variable_id, var_code, distance, score
        """
        if not DATABASE_AVAILABLE:
            return []
        
        try:
            query_vector_text = self.vector_to_text(query_vector)
            
            # Build SQL query with optional filters
            # Note: We need to use CAST instead of :: syntax for SQLAlchemy parameter binding
            if audience_id:
                # Join with audience_members for active version
                sql = text("""
                    SELECT 
                        u.id as utterance_id,
                        u.respondent_id,
                        u.variable_id,
                        e.meta_json->>'variable_code' as var_code,
                        u.display_text,
                        u.provenance_json,
                        (CAST(e.vector AS vector) <=> CAST(:query_vec AS vector)) as distance
                    FROM embeddings e
                    JOIN utterances u ON e.object_id = u.id
                    JOIN audience_members am ON u.respondent_id = am.respondent_id
                    JOIN audiences a ON am.audience_id = a.id
                    WHERE e.dataset_id = CAST(:dataset_id AS VARCHAR)
                      AND e.object_type = 'utterance'
                      AND a.id = CAST(:audience_id AS VARCHAR)
                      AND am.version = a.active_membership_version
                      AND (CAST(:variable_id AS INTEGER) IS NULL OR u.variable_id = CAST(:variable_id AS INTEGER))
                    ORDER BY distance ASC
                    LIMIT CAST(:top_k AS INTEGER)
                """)
                
                params = {
                    'dataset_id': dataset_id,
                    'query_vec': query_vector_text,
                    'audience_id': audience_id,
                    'variable_id': variable_id,
                    'top_k': top_k
                }
            else:
                # No audience filter
                sql = text("""
                    SELECT 
                        u.id as utterance_id,
                        u.respondent_id,
                        u.variable_id,
                        e.meta_json->>'variable_code' as var_code,
                        u.display_text,
                        u.provenance_json,
                        (CAST(e.vector AS vector) <=> CAST(:query_vec AS vector)) as distance
                    FROM embeddings e
                    JOIN utterances u ON e.object_id = u.id
                    WHERE e.dataset_id = CAST(:dataset_id AS VARCHAR)
                      AND e.object_type = 'utterance'
                      AND (CAST(:variable_id AS INTEGER) IS NULL OR u.variable_id = CAST(:variable_id AS INTEGER))
                    ORDER BY distance ASC
                    LIMIT CAST(:top_k AS INTEGER)
                """)
                
                params = {
                    'dataset_id': dataset_id,
                    'query_vec': query_vector_text,
                    'variable_id': variable_id,
                    'top_k': top_k
                }
            
            result = db.execute(sql, params)
            
            utterances = []
            for row in result:
                utterances.append({
                    'utterance_id': row.utterance_id,
                    'respondent_id': row.respondent_id,
                    'variable_id': row.variable_id,
                    'var_code': row.var_code,
                    'display_text': row.display_text,
                    'provenance': row.provenance_json,
                    'distance': float(row.distance),
                    'score': 1.0 - float(row.distance)  # Convert distance to similarity
                })
            
            return utterances
            
        except Exception as e:
            logger.error(f"Error retrieving utterance embeddings: {e}", exc_info=True)
            # Fallback: if pgvector query fails, return empty list
            return []
    
    def generate_embeddings_for_variables(
        self,
        db: Session,
        dataset_id: str,
        limit: Optional[int] = None
    ) -> Dict[str, int]:
        """
        Generate embeddings for all variables in a dataset
        
        Returns:
            Dict with counts: {'embeddings': int, 'errors': int}
        """
        if not DATABASE_AVAILABLE:
            return {'embeddings': 0, 'errors': 0}
        
        embeddings_created = 0
        errors = 0
        
        try:
            query = db.query(Variable).filter(Variable.dataset_id == dataset_id)
            if limit:
                query = query.limit(limit)
            
            variables = query.all()
            
            for variable in variables:
                embedding = self.create_variable_embedding(db, variable)
                if embedding:
                    embeddings_created += 1
                else:
                    errors += 1
            
            logger.info(f"Generated {embeddings_created} variable embeddings for dataset {dataset_id}, errors: {errors}")
            
            return {'embeddings': embeddings_created, 'errors': errors}
            
        except Exception as e:
            logger.error(f"Error generating variable embeddings: {e}", exc_info=True)
            raise
    
    def generate_embeddings_for_utterances(
        self,
        db: Session,
        dataset_id: str,
        limit: Optional[int] = None
    ) -> Dict[str, int]:
        """
        Generate embeddings for all utterances in a dataset
        
        Returns:
            Dict with counts: {'embeddings': int, 'errors': int}
        """
        if not DATABASE_AVAILABLE:
            return {'embeddings': 0, 'errors': 0}
        
        embeddings_created = 0
        errors = 0
        
        try:
            query = db.query(Utterance).join(Variable).filter(
                Variable.dataset_id == dataset_id
            )
            if limit:
                query = query.limit(limit)
            
            utterances = query.all()
            
            for utterance in utterances:
                embedding = self.create_utterance_embedding(db, utterance)
                if embedding:
                    embeddings_created += 1
                else:
                    errors += 1
            
            logger.info(f"Generated {embeddings_created} utterance embeddings for dataset {dataset_id}, errors: {errors}")
            
            return {'embeddings': embeddings_created, 'errors': errors}
            
        except Exception as e:
            logger.error(f"Error generating utterance embeddings: {e}", exc_info=True)
            raise


# Singleton instance
embedding_service = EmbeddingService()

