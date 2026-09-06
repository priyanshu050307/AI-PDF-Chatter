import io
import uuid
import fitz  # PyMuPDF
from typing import List, Tuple
from pypdf import PdfReader
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.user import User
from app.models.document import Document, DocumentStatus
from app.schemas.document import DocumentResponse
from app.schemas.reading_progress import ReadingProgressResponse
from app.repositories.document_repository import DocumentRepository
from app.services.storage_service import get_storage_service
from app.services.processing_service import DocumentProcessingService
from app.core.errors import ValidationError, NotFoundError, ForbiddenError, AppException
from app.core.logging import logger

MAX_FILE_SIZE_BYTES = 50 * 1024 * 1024  # 50 MB


class DocumentService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.doc_repo = DocumentRepository(db)
        self.storage = get_storage_service()

    def _validate_pdf_bytes(self, file_bytes: bytes, filename: str) -> int:
        """Validate PDF magic header, size limit, and extract page count using PyMuPDF."""
        if len(file_bytes) == 0:
            raise ValidationError(message="Uploaded file is empty.")

        max_size = getattr(settings, "MAX_UPLOAD_SIZE_BYTES", 524_288_000)
        if len(file_bytes) > max_size:
            max_mb = max_size // (1024 * 1024)
            raise ValidationError(message=f"File size exceeds maximum limit of {max_mb} MB.")

        # Magic bytes check for PDF (%PDF)
        if not file_bytes.startswith(b"%PDF"):
            raise ValidationError(message="Only PDF files (.pdf extension) are supported.")

        try:
            doc = fitz.open(stream=file_bytes, filetype="pdf")
            page_count = len(doc)
            doc.close()
            if page_count == 0:
                raise ValidationError(message="PDF contains no pages.")
            return page_count
        except Exception as e:
            raise ValidationError(message=f"Could not parse PDF document structure: {str(e)}")

    async def upload_document(self, user: User, file_bytes: bytes, filename: str, run_inline_processing: bool = False) -> DocumentResponse:
        """Process PDF upload, store file in object storage, and dispatch background processing task."""
        # 1. Server-side PDF validation & page count extraction
        page_count = self._validate_pdf_bytes(file_bytes, filename)

        # 2. Derive title from filename
        title = filename.rsplit(".", 1)[0].replace("_", " ").strip()
        if not title:
            title = "Untitled Document"

        # 3. Store file binary using storage abstraction
        doc_id = uuid.uuid4()
        storage_key = f"users/{user.id}/documents/{doc_id}.pdf"
        await self.storage.upload(file_bytes=file_bytes, key=storage_key, content_type="application/pdf")

        # 4. Save DB record with status PENDING
        doc = Document(
            id=doc_id,
            user_id=user.id,
            title=title,
            original_filename=filename,
            storage_key=storage_key,
            file_size_bytes=len(file_bytes),
            page_count=page_count,
            processing_status=DocumentStatus.PENDING,
        )
        created_doc = await self.doc_repo.create(doc)
        await self.db.commit()

        # 5. Optionally execute processing inline if requested (e.g. unit tests)
        if run_inline_processing:
            try:
                proc_service = DocumentProcessingService(self.db)
                await proc_service.process_document(doc_id)
            except Exception as proc_exc:
                logger.error(f"Inline document processing error for {doc_id}: {str(proc_exc)}")

        fresh_doc = await self.doc_repo.get_by_id_and_user_id(doc_id, user.id)
        return DocumentResponse.model_validate(fresh_doc or created_doc)

    async def list_user_documents(self, user: User, skip: int = 0, limit: int = 100) -> List[DocumentResponse]:
        """Fetch all documents belonging to authenticated user."""
        docs = await self.doc_repo.get_by_user_id_with_progress(user.id, skip=skip, limit=limit)
        response_list = []
        for doc in docs:
            doc_res = DocumentResponse.model_validate(doc)
            if doc.reading_progresses:
                progress = doc.reading_progresses[0]
                doc_res.progress = ReadingProgressResponse.model_validate(progress)
            response_list.append(doc_res)
        return response_list

    async def get_user_document(self, user: User, document_id: uuid.UUID) -> DocumentResponse:
        """Retrieve metadata for a specific document with strict user ownership enforcement."""
        doc = await self.doc_repo.get_by_id_and_user_id(document_id, user.id)
        if not doc:
            raise NotFoundError(message="Document not found.")

        doc_res = DocumentResponse.model_validate(doc)
        if doc.reading_progresses:
            doc_res.progress = ReadingProgressResponse.model_validate(doc.reading_progresses[0])
        return doc_res

    async def stream_user_document_file(self, user: User, document_id: uuid.UUID) -> Tuple[bytes, str]:
        """Fetch raw PDF binary bytes for reading, strictly enforcing user ownership."""
        doc = await self.doc_repo.get_by_id_and_user_id(document_id, user.id)
        if not doc:
            raise NotFoundError(message="Document not found.")

        try:
            file_bytes = await self.storage.download(doc.storage_key)
            return file_bytes, doc.original_filename
        except Exception as e:
            raise NotFoundError(message=f"Stored file payload unavailable: {str(e)}")

    async def delete_user_document(self, user: User, document_id: uuid.UUID) -> bool:
        """Delete document from database and underlying object storage."""
        doc = await self.doc_repo.get_by_id_and_user_id(document_id, user.id)
        if not doc:
            raise NotFoundError(message="Document not found.")

        # Delete from object storage
        await self.storage.delete(doc.storage_key)

        # Delete database entity
        deleted = await self.doc_repo.delete_by_id_and_user_id(document_id, user.id)
        await self.db.commit()
        return deleted
