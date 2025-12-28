"""
Celery background tasks for research workflow
"""
from celery import Task
from database import SessionLocal
import logging

from services.utterance_service import utterance_service
from services.embedding_service import embedding_service

logger = logging.getLogger(__name__)

# Import celery_app to define tasks
try:
    from celery_app import celery_app
except ImportError:
    # Fallback if celery_app is not available (for testing)
    celery_app = None


class DatabaseTask(Task):
    """Base task class that provides database session"""
    _db = None
    
    def get_db(self):
        """Get or create database session"""
        if self._db is None:
            self._db = SessionLocal()
        return self._db
    
    def after_return(self, *args, **kwargs):
        """Clean up database session after task completes"""
        if self._db is not None:
            self._db.close()
            self._db = None


if celery_app:
    @celery_app.task(bind=True, base=DatabaseTask, name="tasks.generate_utterances_for_dataset")
    def generate_utterances_for_dataset(self, dataset_id: str):
        """
        Generate utterances for all responses in a dataset (deterministic template-based)
        
        This is an idempotent operation; re-running will not create duplicates.
        """
        db = self.get_db()
        try:
            result = utterance_service.generate_utterances_for_dataset(
                db=db,
                dataset_id=dataset_id
            )
            logger.info(f"Task generate_utterances_for_dataset completed for dataset {dataset_id}: {result}")
            return result
        except Exception as e:
            logger.error(f"Task generate_utterances_for_dataset failed for dataset {dataset_id}: {e}", exc_info=True)
            raise
        finally:
            db.close()
    
    @celery_app.task(bind=True, base=DatabaseTask, name="tasks.generate_embeddings_for_variables")
    def generate_embeddings_for_variables(self, dataset_id: str):
        """
        Generate embeddings for all variables in a dataset
        
        This is an idempotent operation; existing embeddings will be skipped.
        """
        db = self.get_db()
        try:
            result = embedding_service.generate_embeddings_for_variables(
                db=db,
                dataset_id=dataset_id
            )
            logger.info(f"Task generate_embeddings_for_variables completed for dataset {dataset_id}: {result}")
            return result
        except Exception as e:
            logger.error(f"Task generate_embeddings_for_variables failed for dataset {dataset_id}: {e}", exc_info=True)
            raise
        finally:
            db.close()
    
    @celery_app.task(bind=True, base=DatabaseTask, name="tasks.generate_embeddings_for_utterances")
    def generate_embeddings_for_utterances(self, dataset_id: str):
        """
        Generate embeddings for all utterances in a dataset
        
        This is an idempotent operation; existing embeddings will be skipped.
        """
        db = self.get_db()
        try:
            result = embedding_service.generate_embeddings_for_utterances(
                db=db,
                dataset_id=dataset_id
            )
            logger.info(f"Task generate_embeddings_for_utterances completed for dataset {dataset_id}: {result}")
            return result
        except Exception as e:
            logger.error(f"Task generate_embeddings_for_utterances failed for dataset {dataset_id}: {e}", exc_info=True)
            raise
        finally:
            db.close()
else:
    # Fallback functions if Celery is not configured
    def generate_utterances_for_dataset(dataset_id: str):
        logger.warning("Celery not configured, generate_utterances_for_dataset task not available")
        return {"error": "Celery not configured"}
    
    def generate_embeddings_for_variables(dataset_id: str):
        logger.warning("Celery not configured, generate_embeddings_for_variables task not available")
        return {"error": "Celery not configured"}
    
    def generate_embeddings_for_utterances(dataset_id: str):
        logger.warning("Celery not configured, generate_embeddings_for_utterances task not available")
        return {"error": "Celery not configured"}

