"""
Celery application for background task processing
"""
from celery import Celery
from config import settings

# Create Celery app instance
celery_app = Celery(
    "sav_insight_studio",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND
)

# Celery configuration
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=30 * 60,  # 30 minutes
    task_soft_time_limit=25 * 60,  # 25 minutes
    worker_prefetch_multiplier=1,
    worker_max_tasks_per_child=50,  # Restart worker after 50 tasks
)

# Import tasks (this will register them with celery_app)
try:
    from tasks import research_tasks  # noqa: F401
except ImportError:
    # If tasks module is not available, continue without it
    pass

if __name__ == "__main__":
    celery_app.start()

