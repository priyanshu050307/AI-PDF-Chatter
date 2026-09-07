import re
from typing import List, Optional, Dict, Any, Tuple
from dataclasses import dataclass, field
import fitz  # PyMuPDF
from app.core.errors import ValidationError
from app.services.ocr_provider import get_ocr_provider


@dataclass
class ExtractedTextBlock:
    text: str
    font_size: float
    is_bold: bool
    bbox: tuple  # (x0, y0, x1, y1)


@dataclass
class ExtractedTable:
    table_number: int
    headers: List[str]
    rows: List[List[str]]
    markdown_content: str
    bbox: tuple  # (x0, y0, x1, y1)


@dataclass
class ExtractedImage:
    image_index: int
    bbox: tuple  # (x0, y0, x1, y1)
    image_bytes: bytes
    ext: str = "png"


@dataclass
class ExtractedPage:
    page_number: int  # 1-indexed
    raw_text: str
    page_width: float
    page_height: float
    text_blocks: List[ExtractedTextBlock]
    page_type: str = "text-native"  # "text-native", "scanned", "mixed", "image-heavy"
    tables: List[ExtractedTable] = field(default_factory=list)
    images: List[ExtractedImage] = field(default_factory=list)
    ocr_text: Optional[str] = None
    ocr_confidence: Optional[float] = None


@dataclass
class ExtractedDocumentMetadata:
    title: Optional[str]
    author: Optional[str]
    subject: Optional[str]
    creator: Optional[str]
    producer: Optional[str]
    page_count: int


class PDFProcessor:
    """High-performance PDF parser using PyMuPDF (fitz) with Multimodal PDF Intelligence."""

    def __init__(self, file_bytes: bytes):
        if not file_bytes:
            raise ValidationError(message="Cannot process empty PDF bytes payload.")
        self.file_bytes = file_bytes
        self.ocr_provider = get_ocr_provider()

    def _normalize_text(self, text: str) -> str:
        """Clean null characters, excessive trailing whitespace, and excessive blank lines."""
        if not text:
            return ""
        cleaned = text.replace("\x00", "")
        cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
        lines = [line.rstrip() for line in cleaned.splitlines()]
        return "\n".join(lines).strip()

    def _detect_page_type(self, raw_text: str, image_count: int, drawing_count: int) -> str:
        text_len = len(raw_text.strip())
        if text_len < 50 and (image_count > 0 or drawing_count > 0):
            return "scanned"
        elif text_len < 150 and image_count > 0:
            return "mixed"
        elif image_count >= 3:
            return "image-heavy"
        return "text-native"

    def _extract_tables_from_page(self, page: fitz.Page) -> List[ExtractedTable]:
        extracted_tables: List[ExtractedTable] = []
        try:
            tabs = page.find_tables()
            for idx, tab in enumerate(tabs or []):
                table_data = tab.extract()
                if not table_data or len(table_data) < 1:
                    continue

                headers = [str(cell or "").strip() for cell in table_data[0]]
                rows = []
                for row in table_data[1:]:
                    rows.append([str(cell or "").strip() for cell in row])

                # Build clean markdown table string
                md_lines = []
                if headers:
                    md_lines.append("| " + " | ".join(headers) + " |")
                    md_lines.append("| " + " | ".join(["---"] * len(headers)) + " |")
                for row in rows:
                    md_lines.append("| " + " | ".join(row) + " |")
                markdown_str = "\n".join(md_lines)

                bbox = tuple(tab.bbox) if hasattr(tab, "bbox") else (0.0, 0.0, 0.0, 0.0)
                extracted_tables.append(
                    ExtractedTable(
                        table_number=idx + 1,
                        headers=headers,
                        rows=rows,
                        markdown_content=markdown_str,
                        bbox=bbox
                    )
                )
        except Exception:
            pass
        return extracted_tables

    def _extract_images_from_page(self, page: fitz.Page, doc: fitz.Document) -> List[ExtractedImage]:
        extracted_images: List[ExtractedImage] = []
        try:
            image_list = page.get_images(full=True)
            for idx, img_info in enumerate(image_list):
                xref = img_info[0]
                base_image = doc.extract_image(xref)
                if not base_image or "image" not in base_image:
                    continue
                img_bytes = base_image["image"]
                img_ext = base_image.get("ext", "png")

                # Bounding box estimation via image rects
                rects = page.get_image_rects(xref)
                bbox = tuple(rects[0]) if rects else (0.0, 0.0, 0.0, 0.0)

                extracted_images.append(
                    ExtractedImage(
                        image_index=idx + 1,
                        bbox=bbox,
                        image_bytes=img_bytes,
                        ext=img_ext
                    )
                )
        except Exception:
            pass
        return extracted_images

    def process(self) -> Tuple[ExtractedDocumentMetadata, List[ExtractedPage]]:
        """Open PDF stream, validate encryption, extract metadata and multimodal page data."""
        try:
            doc = fitz.open(stream=self.file_bytes, filetype="pdf")
        except Exception as e:
            raise ValidationError(message=f"Failed to open PDF document: {str(e)}")

        if doc.is_encrypted and not doc.authenticate(""):
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

        extracted_pages: List[ExtractedPage] = []

        for page_idx in range(page_count):
            page = doc.load_page(page_idx)
            page_number = page_idx + 1
            rect = page.rect
            width = float(rect.width)
            height = float(rect.height)

            raw_text = self._normalize_text(page.get_text("text"))

            page_dict = page.get_text("dict", flags=fitz.TEXT_PRESERVE_WHITESPACE)
            text_blocks: List[ExtractedTextBlock] = []
            image_blocks_count = 0
            drawing_blocks_count = 0

            for block in page_dict.get("blocks", []) or []:
                b_type = block.get("type", 0)
                if b_type == 0:  # Text block
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
                elif b_type == 1:
                    image_blocks_count += 1
                else:
                    drawing_blocks_count += 1

            page_type = self._detect_page_type(raw_text, image_blocks_count, drawing_blocks_count)
            tables = self._extract_tables_from_page(page)
            images = self._extract_images_from_page(page, doc)

            ocr_text = None
            ocr_conf = None
            if page_type in ["scanned", "mixed"]:
                pix = page.get_pixmap(dpi=150)
                page_img_bytes = pix.tobytes("png")
                ocr_text, ocr_conf = self.ocr_provider.extract_text(page_img_bytes)

            extracted_pages.append(
                ExtractedPage(
                    page_number=page_number,
                    raw_text=raw_text,
                    page_width=width,
                    page_height=height,
                    text_blocks=text_blocks,
                    page_type=page_type,
                    tables=tables,
                    images=images,
                    ocr_text=ocr_text,
                    ocr_confidence=ocr_conf
                )
            )

        doc.close()
        return doc_metadata, extracted_pages

    def get_metadata(self) -> ExtractedDocumentMetadata:
        try:
            doc = fitz.open(stream=self.file_bytes, filetype="pdf")
        except Exception as e:
            raise ValidationError(message=f"Failed to open PDF document: {str(e)}")

        if doc.is_encrypted and not doc.authenticate(""):
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
        """Yield extracted multimodal pages in bounded memory batches."""
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
            image_blocks_count = 0
            drawing_blocks_count = 0

            for block in page_dict.get("blocks", []) or []:
                b_type = block.get("type", 0)
                if b_type == 0:
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
                elif b_type == 1:
                    image_blocks_count += 1
                else:
                    drawing_blocks_count += 1

            page_type = self._detect_page_type(raw_text, image_blocks_count, drawing_blocks_count)
            tables = self._extract_tables_from_page(page)
            images = self._extract_images_from_page(page, doc)

            ocr_text = None
            ocr_conf = None
            if page_type in ["scanned", "mixed"]:
                pix = page.get_pixmap(dpi=150)
                page_img_bytes = pix.tobytes("png")
                ocr_text, ocr_conf = self.ocr_provider.extract_text(page_img_bytes)

            batch.append(
                ExtractedPage(
                    page_number=page_number,
                    raw_text=raw_text,
                    page_width=float(rect.width),
                    page_height=float(rect.height),
                    text_blocks=text_blocks,
                    page_type=page_type,
                    tables=tables,
                    images=images,
                    ocr_text=ocr_text,
                    ocr_confidence=ocr_conf
                )
            )

            if len(batch) >= batch_size:
                yield batch
                batch = []

        if batch:
            yield batch

        doc.close()
