from celery import Celery
from celery.schedules import crontab

from app.core.config import settings

celery_app = Celery(
    "escalas",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=["app.workers.tasks"],
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="America/Sao_Paulo",
    enable_utc=True,
    task_track_started=True,
    worker_prefetch_multiplier=1,  # Um job de solver por vez
    # Tarefas periódicas (requer `celery beat`; ver docker-compose).
    beat_schedule={
        "expirar-trocas-vencidas": {
            "task": "expire_stale_exchanges",
            "schedule": crontab(hour=3, minute=0),  # diariamente às 03:00 (horário de SP)
        },
    },
)
