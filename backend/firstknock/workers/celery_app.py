from celery import Celery
from firstknock.config import settings

app = Celery(
    "firstknock",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
    include=["firstknock.pipeline.enrichment.tasks"],
)

app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    worker_prefetch_multiplier=1,
)
