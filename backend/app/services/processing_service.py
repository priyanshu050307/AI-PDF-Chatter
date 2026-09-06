import uuid
from typing import Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.document import Document, DocumentStatus, DocumentPage, DocumentChunk
from app.repositories.document_repository import DocumentRepository
from app.services.storage_service import get_storage_service
from app.services.pdf_processor import PDFProcessor
from app.services.chunker import ContextAwareChunker
from app.services.embedding_service import get_embedding_service
from app.core.config import settings
from app.core.errors import NotFoundError, ValidationError, AppException
from app.core.logging import logger


class DocumentProcessingService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.doc_repo = DocumentRepository(db)
        self.storage = get_storage_service()
        self.chunker = ContextAwareChunker()

    async def process_document(self, document_id: uuid.UUID) -> Dict[str, Any]:
        """
        Orchestrate complete PDF processing pipeline for a given document:
        Extract Pages -> Context Chunking -> Batch Embedding Generation -> Persist -> Complete.
        Idempotent: Clears any existing pages and chunks before creating new ones.
        """
        doc = await self.doc_repo.get_by_id(document_id)
        if not doc:
            raise NotFoundError(message=f"Document with ID {document_id} not found.")

        # Update status to PROCESSING
        doc.processing_status = DocumentStatus.PROCESSING
        doc.error_message = None
        await self.db.commit()

        try:
            logger.info(f"Starting PDF processing pipeline for document_id={document_id} ({doc.original_filename})")

            # 1. Download PDF binary from object storage
            file_bytes = await self.storage.download(doc.storage_key)

            # 2. Initialize PDF Processor and services
            processor = PDFProcessor(file_bytes)
            extracted_meta = processor.get_metadata()
            embedding_service = get_embedding_service()

            # 3. Transactional Delete-and-Rebuild for Idempotency
            await self.doc_repo.clear_pages_and_chunks(document_id)

            total_pages_count = 0
            total_chunks_count = 0
            batch_size = getattr(settings, "PROCESSING_BATCH_SIZE", 50)

            # 4. Incremental Page Batch Processing
            for page_batch in processor.iter_extracted_pages(batch_size=batch_size):
                # Build DocumentPage ORM entities for batch
                page_entities = [
                    DocumentPage(
                        document_id=document_id,
                        page_number=page.page_number,
                        raw_text=page.raw_text,
                        page_width=page.page_width,
                        page_height=page.page_height,
                    )
                    for page in page_batch
                ]
                await self.doc_repo.bulk_create_pages(page_entities)
                total_pages_count += len(page_entities)

                # Structure detection & context-aware chunking for current batch
                batch_chunks = self.chunker.chunk_document(page_batch)

                if batch_chunks:
                    chunk_contents = [c.content for c in batch_chunks]
                    chunk_embeddings = await embedding_service.generate_embeddings(chunk_contents)

                    chunk_entities = [
                        DocumentChunk(
                            document_id=document_id,
                            page_start=chunk.page_start,
                            page_end=chunk.page_end,
                            chapter_title=chunk.chapter_title,
                            section_title=chunk.section_title,
                            content=chunk.content,
                            token_count=chunk.token_count,
                            embedding=emb,
                            metadata_json=chunk.metadata_json,
                        )
                        for chunk, emb in zip(batch_chunks, chunk_embeddings)
                    ]
                    await self.doc_repo.bulk_create_chunks(chunk_entities)
                    total_chunks_count += len(chunk_entities)

                logger.info(f"Processed batch for document {document_id}: total pages so far = {total_pages_count}/{extracted_meta.page_count}, chunks = {total_chunks_count}")

            # 5. Update Document status to COMPLETED
            doc.page_count = extracted_meta.page_count
            doc.processing_status = DocumentStatus.COMPLETED
            doc.error_message = None

            if doc.title == "Untitled Document" and extracted_meta.title:
                doc.title = extracted_meta.title.strip()

            await self.db.commit()
            logger.info(
                f"Successfully processed document_id={document_id}: "
                f"{total_pages_count} pages, {total_chunks_count} chunks created with embeddings."
            )

            return {
                "document_id": str(document_id),
                "page_count": total_pages_count,
                "chunks_count": total_chunks_count,
                "status": DocumentStatus.COMPLETED,
            }

        except Exception as e:
            logger.error(f"Processing failed for document_id={document_id}: {str(e)}", exc_info=True)
            user_safe_message = (
                str(e) if isinstance(e, ValidationError)
                else "Document processing failed due to an internal parsing error."
            )
            # Rollback aborted transaction before saving status update
            await self.db.rollback()
            try:
                failed_doc = await self.doc_repo.get_by_id(document_id)
                if failed_doc:
                    failed_doc.processing_status = DocumentStatus.FAILED
                    failed_doc.error_message = user_safe_message
                    await self.db.commit()
            except Exception as rollback_exc:
                logger.error(f"Failed to set document FAILED status for {document_id}: {str(rollback_exc)}")

            return {
                "document_id": str(document_id),
                "status": DocumentStatus.FAILED,
                "error": user_safe_message,
            }
