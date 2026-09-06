import re
import uuid
from typing import List, Optional, Set, Any
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.document import DocumentChunk
from app.schemas.retrieval import RetrievalResult
from app.core.logging import logger

# Regex to capture technical tokens (e.g., CVE-2026-1234, AES-256, OAuth 2.0, SHA-256, JWT)
TECHNICAL_TOKEN_PATTERN = re.compile(
    r'\b(?:CVE-\d{4}-\d+|[A-Z0-9]+-[A-Z0-9]+|OAuth\s*\d(?:\.\d)?|SHA-\d+|AES-\d+|JWT|RSA-\d+|SQLi?)\b',
    re.IGNORECASE
)


class LexicalRetriever:
    """
    PostgreSQL Full-Text Lexical Search Retriever (BM25-style keyword search).
    Preserves exact technical identifiers and provides an in-memory term frequency
    fallback for SQLite test environments.
    """

    def __init__(self, db: AsyncSession):
        self.db = db

    def normalize_query(self, query: str) -> tuple[str, Set[str]]:
        """
        Extract technical tokens to preserve them, then normalize whitespace.
        Returns (clean_query, technical_tokens).
        """
        if not query:
            return "", set()

        tech_tokens = set(TECHNICAL_TOKEN_PATTERN.findall(query))
        clean = re.sub(r'[^\w\s\-\.]', ' ', query)
        clean = re.sub(r'\s+', ' ', clean).strip()
        return clean, tech_tokens

    async def retrieve(
        self,
        document_id: uuid.UUID,
        query: Any,
        top_k: int = 10,
        selected_text: Optional[str] = None
    ) -> List[RetrievalResult]:
        if isinstance(query, list):
            query = ""
        full_raw_query = f"{selected_text or ''} {query or ''}".strip()
        if not full_raw_query:
            return []

        clean_query, tech_tokens = self.normalize_query(full_raw_query)

        # Check database dialect
        bind = self.db.get_bind()
        is_postgres = bind.dialect.name == "postgresql"

        results: List[RetrievalResult] = []

        if is_postgres:
            try:
                # Execute PostgreSQL native tsvector full text search with ts_rank_cd
                raw_sql = text("""
                    SELECT id, document_id, content, page_start, page_end, chapter_title, section_title, token_count,
                           ts_rank_cd(to_tsvector('english', content), plainto_tsquery('english', :query_text)) AS rank_score
                    FROM document_chunks
                    WHERE document_id = :doc_id
                      AND to_tsvector('english', content) @@ plainto_tsquery('english', :query_text)
                    ORDER BY rank_score DESC
                    LIMIT :top_k
                """)
                res = await self.db.execute(raw_sql, {"query_text": clean_query, "doc_id": document_id, "top_k": top_k})
                rows = res.fetchall()

                for row in rows:
                    results.append(
                        RetrievalResult(
                            chunk_id=str(row.id),
                            document_id=str(row.document_id),
                            content=row.content,
                            page_start=row.page_start,
                            page_end=row.page_end,
                            chapter_title=row.chapter_title,
                            section_title=row.section_title,
                            token_count=row.token_count or 0,
                            lexical_score=round(float(row.rank_score), 4),
                        )
                    )
                return results
            except Exception as exc:
                logger.warning(f"PostgreSQL tsvector query failed, using Python lexical fallback: {exc}")

        # In-memory keyword match & Term-Frequency fallback for SQLite test execution
        res = await self.db.execute(
            select(DocumentChunk).where(DocumentChunk.document_id == document_id)
        )
        chunks = list(res.scalars().all())
        if not chunks:
            return []

        # Extract terms (words with length >= 3)
        terms = [t.lower() for t in clean_query.split() if len(t) >= 2]
        if not terms and not tech_tokens:
            return []

        scored_list: List[RetrievalResult] = []
        for chunk in chunks:
            content_lower = chunk.content.lower()
            score = 0.0

            # Boost exact technical token matches
            for token in tech_tokens:
                if token.lower() in content_lower:
                    score += 3.0

            # Count term frequencies
            for term in terms:
                count = content_lower.count(term)
                if count > 0:
                    score += (1.0 + float(count) * 0.2)

            if score > 0.0:
                scored_list.append(
                    RetrievalResult(
                        chunk_id=str(chunk.id),
                        document_id=str(chunk.document_id),
                        content=chunk.content,
                        page_start=chunk.page_start,
                        page_end=chunk.page_end,
                        chapter_title=chunk.chapter_title,
                        section_title=chunk.section_title,
                        token_count=chunk.token_count or 0,
                        lexical_score=round(score, 4),
                    )
                )

        scored_list.sort(key=lambda x: x.lexical_score or 0.0, reverse=True)
        return scored_list[:top_k]
