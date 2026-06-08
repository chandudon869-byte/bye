from celery import Celery
from ..config import settings

celery_app = Celery(
    "nepse_worker",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
    include=["app.workers.tasks"]
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="Asia/Kathmandu",
    enable_utc=False,
    task_track_started=True,
    task_time_limit=30 * 60,  # 30 minutes
    task_soft_time_limit=25 * 60,
    
    # Beat schedule - runs every 6 hours
    beat_schedule={
        "scrape-all-sources": {
            "task": "app.workers.tasks.scrape_all_sources",
            "schedule": settings.SCRAPE_INTERVAL_SECONDS,  # 21600 seconds = 6 hours
            "options": {"queue": "scraping"}
        },
        "update-ai-scores": {
            "task": "app.workers.tasks.update_ai_scores",
            "schedule": 43200,  # 12 hours
            "options": {"queue": "scoring"}
        },
        "cleanup-old-logs": {
            "task": "app.workers.tasks.cleanup_logs",
            "schedule": 86400,  # 24 hours
        }
    }
)