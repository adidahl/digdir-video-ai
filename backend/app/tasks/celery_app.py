"""Celery application configuration."""
from celery import Celery
from app.config import get_settings

settings = get_settings()

celery_app = Celery(
    "video_rag",
    broker=settings.redis_url,
    backend=settings.redis_url,
    include=["app.tasks.video_tasks"]
)

# Celery configuration
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=3600 * 4,  # 4 hours max
    task_soft_time_limit=3600 * 3,  # 3 hours soft limit
    worker_prefetch_multiplier=1,
    worker_max_tasks_per_child=10,
)

