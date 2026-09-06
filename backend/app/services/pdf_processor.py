import re
from typing import List, Optional, Dict, Any
from dataclasses import dataclass
import fitz  # PyMuPDF
from app.core.errors import ValidationError


@dataclass
class ExtractedTextBlock:
    text: str
    font_size: float
    is_bold: bool
    bbox: tuple  # (x0, y0, x1, y1)


@dataclass
class ExtractedPage:
    page_number: int  # 1-indexed
    raw_text: str
    page_width: float
    page_height: float
    text_blocks: List[ExtractedTextBlock]


@dataclass
class ExtractedDocumentMetadata:
    title: Optional[str]
    author: Optional[str]
    subject: Optional[str]
    creator: Optional[str]
    producer: Optional[str]
    page_count: int


class PDFProcessor:
    """High-performance PDF parser using PyMuPDF (fitz)."""

    def __init__(self, file_bytes: bytes):
        if not file_bytes:
            raise ValidationError(message="Cannot process empty PDF bytes payload.")
        self.file_bytes = file_bytes

    def _normalize_text(self, text: str) -> str:
        """Clean null characters, excessive trailing whitespace, and excessive blank lines."""
        if not text:
            return ""
        # Remove null bytes
        cleaned = text.replace("\x00", "")
        # Replace multiple consecutive newlines (>2) with double newline
        cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
        # Strip leading/trailing whitespaces per line while preserving indentation
        lines = [line.rstrip() for line in cleaned.splitlines()]
        return "\n".join(lines).strip()

    def process(self) -> tuple[ExtractedDocumentMetadata, List[ExtractedPage]]:
        """Open PDF stream, validate encryption, extract metadata and page layout data."""
        try:
            doc = fitz.open(stream=self.file_bytes, filetype="pdf")
        except Exception as e:
            raise ValidationError(message=f"Failed to open PDF document: {str(e)}")

        if doc.is_encrypted:
            # Attempt to authenticate with empty password
            if not doc.authenticate(""):
                doc.close()
                raise ValidationError(message="PDF is encrypted and password-protected.")

        page_count = len(doc)
        if page_count == 0:
            doc.close()
            raise ValidationError(message="PDF contains 0 pages.")

        # Extract Document Metadata
        meta = doc.metadata or {}
        doc_metadata = ExtractedDocumentMetadata(
            title=meta.get("title") or None,
            author=meta.get("author") or None,
            subject=meta.get("subject") or None,
            creator=meta.get("creator") or None,
            producer=meta.get("producer") or None,
            page_count=page_count,
        )

        extracted_pages: List[ExtractedPage] = []

        for page_idx in range(page_count):
            page = doc.load_page(page_idx)
            page_number = page_idx + 1  # 1-indexed for user readability
            rect = page.rect
            width = float(rect.width)
            height = float(rect.height)

            raw_text = self._normalize_text(page.get_text("text"))

            # Extract detailed block structures for font & layout structure detection
            page_dict = page.get_text("dict", flags=fitz.TEXT_PRESERVE_WHITESPACE)
            text_blocks: List[ExtractedTextBlock] = []

            for block in page_dict.get("blocks", []) or []:
                if block and block.get("type") == 0:  # Text block
                    for line in block.get("lines", []) or []:
                        for span in line.get("spans", []) or []:
                            raw_span_text = span.get("text")
                            span_text = raw_span_text.strip() if raw_span_text else ""
                            if span_text:
                                font_flags = span.get("flags") or 0
                                font_name = span.get("font") or ""
                                font_size = span.get("size") or 10.0
                                bbox = span.get("bbox") or (0, 0, 0, 0)
                                is_bold = bool(font_flags & 2) or "bold" in str(font_name).lower()
                                text_blocks.append(
                                    ExtractedTextBlock(
                                        text=span_text,
                                        font_size=float(font_size),
                                        is_bold=is_bold,
                                        bbox=tuple(bbox)
                                    )
                                )

            extracted_pages.append(
                ExtractedPage(
                    page_number=page_number,
                    raw_text=raw_text,
                    page_width=width,
                    page_height=height,
                    text_blocks=text_blocks,
                )
            )

        doc.close()
        return doc_metadata, extracted_pages

    def get_metadata(self) -> ExtractedDocumentMetadata:
        """Extract basic document metadata without building page structures in memory."""
        try:
            doc = fitz.open(stream=self.file_bytes, filetype="pdf")
        except Exception as e:
            raise ValidationError(message=f"Failed to open PDF document: {str(e)}")

        if doc.is_encrypted:
            if not doc.authenticate(""):
                doc.close()
                raise ValidationError(message="PDF is encrypted and password-protected.")

        page_count = len(doc)
        if page_count == 0:
            doc.close()
            raise ValidationError(message="PDF contains 0 pages.")

        meta = doc.metadata or {}
        doc_metadata = ExtractedDocumentMetadata(
            title=meta.get("title") or None,
            author=meta.get("author") or None,
            subject=meta.get("subject") or None,
            creator=meta.get("creator") or None,
            producer=meta.get("producer") or None,
            page_count=page_count,
        )
        doc.close()
        return doc_metadata

    def iter_extracted_pages(self, batch_size: int = 50):
        """Yield extracted pages in bounded memory batches for high-scalability ingestion."""
        try:
            doc = fitz.open(stream=self.file_bytes, filetype="pdf")
        except Exception as e:
            raise ValidationError(message=f"Failed to open PDF document stream: {str(e)}")

        if doc.is_encrypted and not doc.authenticate(""):
            doc.close()
            raise ValidationError(message="PDF is encrypted and password-protected.")

        page_count = len(doc)
        batch: List[ExtractedPage] = []

        for page_idx in range(page_count):
            page = doc.load_page(page_idx)
            page_number = page_idx + 1
            rect = page.rect
            raw_text = self._normalize_text(page.get_text("text"))

            page_dict = page.get_text("dict", flags=fitz.TEXT_PRESERVE_WHITESPACE)
            text_blocks: List[ExtractedTextBlock] = []

            for block in page_dict.get("blocks", []) or []:
                if block and block.get("type") == 0:  # Text block
                    for line in block.get("lines", []) or []:
                        for span in line.get("spans", []) or []:
                            raw_span_text = span.get("text")
                            span_text = raw_span_text.strip() if raw_span_text else ""
                            if span_text:
                                font_flags = span.get("flags") or 0
                                font_name = span.get("font") or ""
                                font_size = span.get("size") or 10.0
                                bbox = span.get("bbox") or (0, 0, 0, 0)
                                is_bold = bool(font_flags & 2) or "bold" in str(font_name).lower()
                                text_blocks.append(
                                    ExtractedTextBlock(
                                        text=span_text,
                                        font_size=float(font_size),
                                        is_bold=is_bold,
                                        bbox=tuple(bbox)
                                    )
                                )

            batch.append(
                ExtractedPage(
                    page_number=page_number,
                    raw_text=raw_text,
                    page_width=float(rect.width),
                    page_height=float(rect.height),
                    text_blocks=text_blocks,
                )
            )

            if len(batch) >= batch_size:
                yield batch
                batch = []

        if batch:
            yield batch

        doc.close()
