import asyncio
import structlog
from firstknock.workers.celery_app import app
from firstknock.pipeline.embedding.writer import embed_and_write

logger = structlog.get_logger()


@app.task(bind=True, max_retries=2, default_retry_delay=15, name="embedding.generate")
def run_embedding_task(self, user_id: str, resume_id: str, extracted_json: dict) -> None:
    from firstknock.pipeline.persistence.db import engine
    engine.sync_engine.pool.dispose()
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        result = loop.run_until_complete(embed_and_write(user_id, resume_id, extracted_json))
        pending = asyncio.all_tasks(loop)
        if pending:
            loop.run_until_complete(asyncio.gather(*pending, return_exceptions=True))
        logger.info("embedding_complete", person_id=user_id, **result)
    except Exception as exc:
        logger.warning("embedding_task_failed", person_id=user_id, error=str(exc))
        raise self.retry(exc=exc)
    finally:
        loop.close()
        asyncio.set_event_loop(None)


def dispatch_embedding(user_id: str, resume_id: str, extracted_json: dict) -> None:
    run_embedding_task.delay(user_id, resume_id, extracted_json)
    logger.info("embedding_dispatched", person_id=user_id, resume_id=resume_id)
