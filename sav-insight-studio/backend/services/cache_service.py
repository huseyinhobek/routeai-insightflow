"""
Cache service for thread answers
Version-aware cache key generation
"""
from sqlalchemy.orm import Session
from sqlalchemy import and_
from typing import Optional
import hashlib
import json
import logging

from models import CacheAnswer, ThreadResult, Dataset
from database import DATABASE_AVAILABLE
from config import settings

logger = logging.getLogger(__name__)


class CacheService:
    """Service for caching thread answers"""
    
    def __init__(self):
        pass
    
    def generate_cache_key(
        self,
        dataset_id: str,
        dataset_version: int,
        audience_id: Optional[str],
        normalized_question: str,
        mode: str,
        router_version: Optional[str] = None,
        narration_policy_version: Optional[str] = None,
        embedding_model_id: Optional[str] = None
    ) -> str:
        """
        Generate cache key hash (model/policy version-aware)
        
        Includes:
        - dataset_id
        - dataset_version
        - audience_id (or None)
        - normalized_question
        - mode (structured/rag)
        - router_version (for router heuristics changes)
        - narration_policy_version (for quantifier policy changes)
        - embedding_model_id (for embedding model changes)
        """
        router_version = router_version or getattr(settings, 'ROUTER_VERSION', '1.0')
        narration_policy_version = narration_policy_version or getattr(settings, 'NARRATION_POLICY_VERSION', '1.0')
        embedding_model_id = embedding_model_id or getattr(settings, 'EMBEDDING_MODEL', 'text-embedding-3-small')
        
        # Build key components
        key_parts = [
            dataset_id,
            str(dataset_version),
            audience_id or '',
            normalized_question,
            mode,
            router_version,
            narration_policy_version,
            embedding_model_id
        ]
        
        # Create hash
        key_string = '|'.join(key_parts)
        key_hash = hashlib.sha256(key_string.encode('utf-8')).hexdigest()
        
        return key_hash
    
    def get_cached_answer(
        self,
        db: Session,
        dataset_id: str,
        dataset_version: int,
        audience_id: Optional[str],
        normalized_question: str,
        mode: str
    ) -> Optional[ThreadResult]:
        """
        Get cached answer if available
        
        Returns:
            ThreadResult if cache hit, None otherwise
        """
        if not DATABASE_AVAILABLE:
            return None
        
        try:
            # Generate cache key
            key_hash = self.generate_cache_key(
                dataset_id=dataset_id,
                dataset_version=dataset_version,
                audience_id=audience_id,
                normalized_question=normalized_question,
                mode=mode
            )
            
            # Look up cache entry
            cache_entry = db.query(CacheAnswer).filter(
                CacheAnswer.key_hash == key_hash
            ).first()
            
            if not cache_entry:
                return None
            
            # Get thread result
            thread_result = db.query(ThreadResult).filter(
                ThreadResult.id == cache_entry.thread_result_id
            ).first()
            
            return thread_result
            
        except Exception as e:
            logger.error(f"Error getting cached answer: {e}", exc_info=True)
            return None
    
    def save_cached_answer(
        self,
        db: Session,
        dataset_id: str,
        dataset_version: int,
        audience_id: Optional[str],
        normalized_question: str,
        mode: str,
        thread_result_id: int
    ) -> bool:
        """
        Save answer to cache
        
        Returns:
            True if successful, False otherwise
        """
        if not DATABASE_AVAILABLE:
            return False
        
        try:
            # Generate cache key
            key_hash = self.generate_cache_key(
                dataset_id=dataset_id,
                dataset_version=dataset_version,
                audience_id=audience_id,
                normalized_question=normalized_question,
                mode=mode
            )
            
            # Check if cache entry already exists
            existing = db.query(CacheAnswer).filter(
                CacheAnswer.key_hash == key_hash
            ).first()
            
            if existing:
                # Update existing entry
                existing.thread_result_id = thread_result_id
            else:
                # Create new cache entry
                cache_entry = CacheAnswer(
                    dataset_id=dataset_id,
                    dataset_version=dataset_version,
                    audience_id=audience_id,
                    normalized_question=normalized_question,
                    mode=mode,
                    key_hash=key_hash,
                    thread_result_id=thread_result_id
                )
                db.add(cache_entry)
            
            db.commit()
            return True
            
        except Exception as e:
            db.rollback()
            logger.error(f"Error saving cached answer: {e}", exc_info=True)
            return False


# Singleton instance
cache_service = CacheService()

