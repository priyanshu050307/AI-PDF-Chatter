import uuid
from typing import List
from fastapi import APIRouter, Depends, UploadFile, File, Response, BackgroundTasks, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_async_db, AsyncSessionLocal
from app.api.deps import get_current_user
from app.models.user import User
from app.models.document import DocumentStatus
from app.schemas.document import DocumentResponse
from app.schemas.common import StatusResponse
from app.schemas.retrieval import RetrievalDebugRequest, RetrievalDebugResponse
from app.services.document_service import DocumentService
from app.services.processing_service import DocumentProcessingService
from app.services.retrieval.retrieval_pipeline import HybridRetrievalPipeline
from app.core.errors import ValidationError, NotFoundError
from app.core.logging import logger

router = APIRouter()


async def run_background_document_processing(document_id: uuid.UUID):
    """Execute document processing asynchronously in background with a dedicated database session."""
    try:
        async with AsyncSessionLocal() as session:
            proc_service = DocumentProcessingService(session)
            await proc_service.process_document(document_id)
    except Exception as exc:
        logger.error(f"Background processing error for document_id={document_id}: {str(exc)}", exc_info=True)


@router.post("/upload", response_model=DocumentResponse, status_code=status.HTTP_201_CREATED)
async def upload_document(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db)
):
    """Upload a PDF file to current user's document library and schedule background processing."""
    from app.core.config import settings

    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise ValidationError(message="Only PDF files (.pdf extension) are supported.")

    file_bytes = await file.read()

    # File size validation
    if len(file_bytes) > settings.MAX_UPLOAD_SIZE_BYTES:
        raise ValidationError(message=f"File size exceeds maximum allowed limit of {settings.MAX_UPLOAD_SIZE_BYTES / (1024*1024):.0f} MB.")

    # Magic Header (%PDF-) & MIME validation
    if not file_bytes.startswith(b"%PDF-"):
        raise ValidationError(message="Invalid PDF file. Header signature %PDF- missing or file is corrupted.")

    service = DocumentService(db)
    doc_res = await service.upload_document(current_user, file_bytes, file.filename, run_inline_processing=False)

    # Schedule non-blocking background processing
    try:
        from app.workers.tasks import process_document_task
        process_document_task.delay(str(doc_res.id))
    except Exception as exc:
        logger.info(f"Celery task dispatch unavailable ({str(exc)}). Enqueuing FastAPI BackgroundTask for doc_id={doc_res.id}.")
        background_tasks.add_task(run_background_document_processing, doc_res.id)

    return doc_res


@router.get("", response_model=List[DocumentResponse])
async def list_documents(
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db)
):
    """List all documents owned by authenticated user."""
    service = DocumentService(db)
    return await service.list_user_documents(current_user, skip=skip, limit=limit)


@router.get("/{document_id}", response_model=DocumentResponse)
async def get_document(
    document_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db)
):
    """Get metadata for a specific document."""
    service = DocumentService(db)
    return await service.get_user_document(current_user, document_id)


@router.get("/{document_id}/file")
async def stream_document_file(
    document_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db)
):
    """Securely stream PDF binary bytes for reading in reader."""
    service = DocumentService(db)
    file_bytes, filename = await service.stream_user_document_file(current_user, document_id)

    return Response(
        content=file_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'inline; filename="{filename}"',
            "Cache-Control": "private, max-age=3600",
        }
    )


@router.post("/{document_id}/process", response_model=DocumentResponse)
async def trigger_document_processing(
    document_id: uuid.UUID,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db)
):
    """Manually re-trigger processing for a user's document."""
    service = DocumentService(db)
    doc_res = await service.get_user_document(current_user, document_id)

    try:
        from app.workers.tasks import process_document_task
        process_document_task.delay(str(document_id))
    except Exception as exc:
        logger.info(f"Celery task dispatch unavailable ({str(exc)}). Enqueuing FastAPI BackgroundTask for doc_id={document_id}.")
        background_tasks.add_task(run_background_document_processing, document_id)

    return await service.get_user_document(current_user, document_id)


@router.delete("/{document_id}", response_model=StatusResponse)
async def delete_document(
    document_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db)
):
    """Delete a document and all related vector chunks."""
    service = DocumentService(db)
    await service.delete_user_document(current_user, document_id)
    return StatusResponse(status="success", message="Document deleted successfully.")


@router.post("/{document_id}/retrieval/debug", response_model=RetrievalDebugResponse)
async def debug_retrieval(
    document_id: uuid.UUID,
    req: RetrievalDebugRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db)
):
    """Development/debug inspection endpoint showing dense, lexical, fused, and reranked candidate scores."""
    doc_service = DocumentService(db)
    await doc_service.get_user_document(current_user, document_id)

    pipeline = HybridRetrievalPipeline(db)
    return await pipeline.debug_pipeline(
        document_id=document_id,
        query=req.query,
        top_k=req.top_k or 5,
        selected_text=req.selected_text
    )


@router.get("/{document_id}/elements")
async def list_document_elements(
    document_id: uuid.UUID,
    element_type: str = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db)
):
    """Get all extracted multimodal elements (tables, figures, OCR regions) for document."""
    doc_service = DocumentService(db)
    await doc_service.get_user_document(current_user, document_id)

    elements = await doc_service.repo.get_elements_for_document(document_id, element_type=element_type)
    return [
        {
            "id": str(elem.id),
            "document_id": str(elem.document_id),
            "page_number": elem.page_number,
            "element_type": elem.element_type,
            "bbox_json": elem.bbox_json,
            "content": elem.content,
            "structured_data": elem.structured_data,
            "image_storage_key": elem.image_storage_key,
            "ocr_confidence": elem.ocr_confidence,
            "created_at": elem.created_at.isoformat()
        }
        for elem in elements
    ]


@router.get("/{document_id}/elements/{element_id}/image")
async def stream_element_image(
    document_id: uuid.UUID,
    element_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db)
):
    """Stream extracted figure/image asset."""
    doc_service = DocumentService(db)
    await doc_service.get_user_document(current_user, document_id)

    elements = await doc_service.repo.get_elements_for_document(document_id)
    target_elem = next((e for e in elements if e.id == element_id), None)
    if not target_elem or not target_elem.image_storage_key:
        raise NotFoundError(message="Extracted image asset not found.")

    storage = doc_service.storage
    img_bytes = await storage.download(target_elem.image_storage_key)

    return Response(
        content=img_bytes,
        media_type="image/png",
        headers={"Cache-Control": "private, max-age=86400"}
    )

