import uuid
from typing import Dict, Any, List
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.document import Document, DocumentStatus, DocumentPage, DocumentChunk, DocumentElement
from app.repositories.document_repository import DocumentRepository
from app.services.storage_service import get_storage_service
from app.services.pdf_processor import PDFProcessor
from app.services.chunker import ContextAwareChunker
from app.services.embedding_service import get_embedding_service
from app.services.vision_provider import get_vision_provider
from app.core.config import settings
from app.core.errors import NotFoundError, ValidationError, AppException
from app.core.logging import logger


class DocumentProcessingService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.doc_repo = DocumentRepository(db)
        self.storage = get_storage_service()
        self.chunker = ContextAwareChunker()
        self.vision_provider = get_vision_provider()

    async def process_document(self, document_id: uuid.UUID) -> Dict[str, Any]:
        """
        Orchestrate complete PDF processing pipeline for a given document:
        Extract Multimodal Pages -> Context Chunking & Table/Figure Extraction -> Batch Embedding Generation -> Persist -> Complete.
        Idempotent: Clears any existing pages, chunks, and elements before creating new ones.
        """
        doc = await self.doc_repo.get_by_id(document_id)
        if not doc:
            raise NotFoundError(message=f"Document with ID {document_id} not found.")

        doc.processing_status = DocumentStatus.PROCESSING
        doc.error_message = None
        await self.db.commit()

        try:
            logger.info(f"Starting Multimodal PDF processing pipeline for document_id={document_id} ({doc.original_filename})")

            file_bytes = await self.storage.download(doc.storage_key)
            processor = PDFProcessor(file_bytes)
            extracted_meta = processor.get_metadata()
            embedding_service = get_embedding_service()

            await self.doc_repo.clear_pages_and_chunks(document_id)

            total_pages_count = 0
            total_chunks_count = 0
            total_elements_count = 0
            batch_size = getattr(settings, "PROCESSING_BATCH_SIZE", 50)

            all_pages_text: List[tuple[int, str]] = []
            for page_batch in processor.iter_extracted_pages(batch_size=batch_size):
                page_entities: List[DocumentPage] = []
                element_entities: List[DocumentElement] = []
                multimodal_chunks: List[DocumentChunk] = []

                for page in page_batch:
                    raw_text_to_save = page.raw_text
                    if page.ocr_text:
                        raw_text_to_save += f"\n\n[OCR Text]\n{page.ocr_text}"

                    all_pages_text.append((page.page_number, raw_text_to_save))

                    page_entities.append(
                        DocumentPage(
                            document_id=document_id,
                            page_number=page.page_number,
                            raw_text=raw_text_to_save,
                            page_width=page.page_width,
                            page_height=page.page_height,
                        )
                    )

                    # Persist OCR Text element if present
                    if page.ocr_text:
                        element_entities.append(
                            DocumentElement(
                                document_id=document_id,
                                page_number=page.page_number,
                                element_type="ocr_text",
                                content=page.ocr_text,
                                ocr_confidence=page.ocr_confidence or 0.90,
                                metadata_json={"page_type": page.page_type}
                            )
                        )

                    # Extract & Persist Table Elements
                    for tab in page.tables:
                        element_entities.append(
                            DocumentElement(
                                document_id=document_id,
                                page_number=page.page_number,
                                element_type="table",
                                bbox_json={"x0": tab.bbox[0], "y0": tab.bbox[1], "x1": tab.bbox[2], "y1": tab.bbox[3]},
                                content=tab.markdown_content,
                                structured_data={"headers": tab.headers, "rows": tab.rows},
                                metadata_json={"table_number": tab.table_number}
                            )
                        )

                    # Extract & Persist Image Elements
                    for img in page.images:
                        img_key = f"documents/{document_id}/images/p{page.page_number}_img{img.image_index}.{img.ext}"
                        try:
                            await self.storage.upload(img.image_bytes, img_key, content_type=f"image/{img.ext}")
                        except Exception as storage_exc:
                            logger.warning(f"Failed to upload extracted image asset {img_key}: {storage_exc}")

                        visual_desc = await self.vision_provider.describe_image(img.image_bytes)

                        element_entities.append(
                            DocumentElement(
                                document_id=document_id,
                                page_number=page.page_number,
                                element_type="image",
                                bbox_json={"x0": img.bbox[0], "y0": img.bbox[1], "x1": img.bbox[2], "y1": img.bbox[3]},
                                content=visual_desc,
                                image_storage_key=img_key,
                                metadata_json={"image_index": img.image_index, "format": img.ext}
                            )
                        )

                await self.doc_repo.bulk_create_pages(page_entities)
                total_pages_count += len(page_entities)

                if element_entities:
                    await self.doc_repo.bulk_create_elements(element_entities)
                    total_elements_count += len(element_entities)

                # Context-aware chunking for standard text & multimodal elements
                batch_text_chunks = self.chunker.chunk_document(page_batch)

                # Convert Table and Image Elements into indexable DocumentChunks
                element_chunks: List[DocumentChunk] = []
                for elem in element_entities:
                    if elem.element_type == "table":
                        chunk_text = f"[Page {elem.page_number}, Table] Structured Data:\n{elem.content}"
                        element_chunks.append(
                            DocumentChunk(
                                document_id=document_id,
                                page_start=elem.page_number,
                                page_end=elem.page_number,
                                content=chunk_text,
                                token_count=len(chunk_text.split()),
                                metadata_json={"element_type": "table", "element_id": str(elem.id), "bbox": elem.bbox_json}
                            )
                        )
                    elif elem.element_type == "image":
                        chunk_text = f"[Page {elem.page_number}, Figure] Visual Summary:\n{elem.content}"
                        element_chunks.append(
                            DocumentChunk(
                                document_id=document_id,
                                page_start=elem.page_number,
                                page_end=elem.page_number,
                                content=chunk_text,
                                token_count=len(chunk_text.split()),
                                metadata_json={"element_type": "image", "element_id": str(elem.id), "bbox": elem.bbox_json, "image_storage_key": elem.image_storage_key}
                            )
                        )

                all_chunks_to_embed = batch_text_chunks + [
                    type('ChunkStruct', (), {'content': c.content, 'page_start': c.page_start, 'page_end': c.page_end, 'chapter_title': None, 'section_title': None, 'token_count': c.token_count, 'metadata_json': c.metadata_json})()
                    for c in element_chunks
                ]

                if all_chunks_to_embed:
                    chunk_contents = [c.content for c in all_chunks_to_embed]
                    chunk_embeddings = await embedding_service.generate_embeddings(chunk_contents)

                    chunk_entities = [
                        DocumentChunk(
                            document_id=document_id,
                            page_start=chunk.page_start,
                            page_end=chunk.page_end,
                            chapter_title=getattr(chunk, 'chapter_title', None),
                            section_title=getattr(chunk, 'section_title', None),
                            content=chunk.content,
                            token_count=chunk.token_count,
                            embedding=emb,
                            metadata_json=chunk.metadata_json,
                        )
                        for chunk, emb in zip(all_chunks_to_embed, chunk_embeddings)
                    ]
                    await self.doc_repo.bulk_create_chunks(chunk_entities)
                    total_chunks_count += len(chunk_entities)

                logger.info(
                    f"Processed multimodal batch for doc {document_id}: "
                    f"pages = {total_pages_count}/{extracted_meta.page_count}, chunks = {total_chunks_count}, elements = {total_elements_count}"
                )

            # Phase 10 Narrative Extraction Pass
            try:
                from app.services.narrative_extractor import NarrativeExtractor
                from app.models.entity_graph import Entity, EntityRelationship, NarrativeEvent

                extractor = NarrativeExtractor()
                extracted_entities, extracted_rels, extracted_events = extractor.extract_entities_and_relationships(all_pages_text)

                entity_orm_map: Dict[str, Entity] = {}
                for e_data in extracted_entities:
                    e_orm = Entity(
                        document_id=document_id,
                        name=e_data.canonical_name,
                        entity_type=e_data.entity_type,
                        description=e_data.description,
                        first_appeared_page=e_data.first_appeared_page,
                        attributes={
                            "aliases": e_data.aliases,
                            "importance": e_data.importance,
                            "mention_count": e_data.mention_count,
                            "last_appeared_page": e_data.last_appeared_page
                        }
                    )
                    self.db.add(e_orm)
                    entity_orm_map[e_data.canonical_name] = e_orm

                await self.db.flush()

                for r_data in extracted_rels:
                    src_orm = entity_orm_map.get(r_data.source_name)
                    tgt_orm = entity_orm_map.get(r_data.target_name)
                    if src_orm and tgt_orm:
                        r_orm = EntityRelationship(
                            document_id=document_id,
                            source_entity_id=src_orm.id,
                            target_entity_id=tgt_orm.id,
                            relationship_type=r_data.relationship_type,
                            description=r_data.description,
                            observed_page=r_data.observed_page,
                            valid_from_page=r_data.observed_page
                        )
                        self.db.add(r_orm)

                for ev_data in extracted_events:
                    ev_orm = NarrativeEvent(
                        document_id=document_id,
                        title=ev_data.title,
                        event_type=ev_data.event_type,
                        description=ev_data.description,
                        page_number=ev_data.page_number,
                        participants_json={"participants": ev_data.participants},
                        location_name=ev_data.location_name
                    )
                    self.db.add(ev_orm)

                await self.db.flush()
                logger.info(f"Extracted narrative intelligence for doc {document_id}: {len(extracted_entities)} entities, {len(extracted_rels)} relationships, {len(extracted_events)} events.")
            except Exception as narrative_exc:
                logger.warning(f"Narrative extraction failed for doc {document_id}: {narrative_exc}")

            doc.page_count = extracted_meta.page_count
            doc.processing_status = DocumentStatus.COMPLETED
            doc.error_message = None

            if doc.title == "Untitled Document" and extracted_meta.title:
                doc.title = extracted_meta.title.strip()

            await self.db.commit()
            logger.info(
                f"Successfully processed multimodal document_id={document_id}: "
                f"{total_pages_count} pages, {total_chunks_count} chunks, {total_elements_count} elements."
            )

            return {
                "document_id": str(document_id),
                "page_count": total_pages_count,
                "chunks_count": total_chunks_count,
                "elements_count": total_elements_count,
                "status": DocumentStatus.COMPLETED,
            }

        except Exception as e:
            logger.error(f"Multimodal processing failed for document_id={document_id}: {str(e)}", exc_info=True)
            user_safe_message = (
                str(e) if isinstance(e, ValidationError)
                else "Document processing failed due to an internal parsing error."
            )
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
