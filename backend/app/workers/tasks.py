import uuid
import asyncio
from typing import Dict, Any
from celery.exceptions import MaxRetriesExceededError

from app.workers.celery_app import celery_app
from app.core.database import AsyncSessionLocal
from app.services.processing_service import DocumentProcessingService
from app.core.errors import ValidationError, NotFoundError
from app.core.logging import logger


async def _run_process_document(document_id_str: str) -> Dict[str, Any]:
    """Helper to run async document processing inside dedicated AsyncSession context."""
    doc_uuid = uuid.UUID(document_id_str)
    async with AsyncSessionLocal() as session:
        service = DocumentProcessingService(session)
        return await service.process_document(doc_uuid)


@celery_app.task(name="tasks.ping_worker_task")
def ping_worker_task() -> str:
    """Infrastructure health check task for background workers."""
    logger.info("Executing worker ping health check task...")
    return "PONG"


@celery_app.task(
    name="tasks.process_document_task",
    bind=True,
    max_retries=3,
    default_retry_delay=10,
    acks_late=True,
)
def process_document_task(self, document_id: str) -> Dict[str, Any]:
    """
    Celery background task for PDF document extraction, structure detection, and chunking.
    Handles bounded retries for transient infrastructure failures.
    Non-retryable parsing/validation errors mark the document FAILED and exit safely.
    """
    logger.info(f"Celery task process_document_task started for document_id={document_id} (Attempt {self.request.retries + 1})")

    try:
        import concurrent.futures
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
            result = pool.submit(asyncio.run, _run_process_document(document_id)).result()
        return result
    except (ValidationError, NotFoundError) as val_err:
        # Non-retryable input validation error
        logger.warning(f"Non-retryable error for document_id={document_id}: {str(val_err)}")
        return {"document_id": document_id, "status": "FAILED", "error": str(val_err)}
    except Exception as exc:
        logger.error(f"Transient or system error processing document_id={document_id}: {str(exc)}", exc_info=True)
        try:
            raise self.retry(exc=exc)
        except MaxRetriesExceededError:
            logger.error(f"Max retries exceeded for document_id={document_id}.")
            return {"document_id": document_id, "status": "FAILED", "error": "Max retries exceeded."}
