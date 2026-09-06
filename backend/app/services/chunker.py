import tiktoken
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
from app.services.pdf_processor import ExtractedPage
from app.services.structure_detector import StructureDetector


@dataclass
class GeneratedChunk:
    page_start: int
    page_end: int
    chapter_title: Optional[str]
    section_title: Optional[str]
    content: str
    token_count: int
    metadata_json: Dict[str, Any] = field(default_factory=dict)


class ContextAwareChunker:
    """
    Structure and page-aware text chunker.
    Groups paragraphs and headings into coherent semantic units while preserving exact page boundaries (page_start, page_end).
    """

    def __init__(
        self,
        target_tokens: int = 500,
        min_tokens: int = 50,
        max_tokens: int = 1000,
        overlap_tokens: int = 100,
    ):
        self.target_tokens = target_tokens
        self.min_tokens = min_tokens
        self.max_tokens = max_tokens
        self.overlap_tokens = overlap_tokens

        try:
            self.tokenizer = tiktoken.get_encoding("cl100k_base")
        except Exception:
            self.tokenizer = None

    def count_tokens(self, text: str) -> int:
        """Calculate token count using tiktoken or fallback approximation."""
        if not text:
            return 0
        if self.tokenizer:
            return len(self.tokenizer.encode(text))
        return max(1, len(text) // 4)

    def chunk_document(self, pages: List[ExtractedPage]) -> List[GeneratedChunk]:
        """
        Process extracted pages into structured chunks.
        """
        if not pages:
            return []

        detector = StructureDetector(pages)
        chunks: List[GeneratedChunk] = []

        current_chapter: Optional[str] = None
        current_section: Optional[str] = None

        current_chunk_paragraphs: List[str] = []
        current_chunk_tokens = 0
        current_page_start: Optional[int] = None
        current_page_end: Optional[int] = None

        for page in pages:
            page_num = page.page_number
            raw_text = page.raw_text

            if not raw_text.strip():
                continue

            # Split page raw text into paragraphs
            paragraphs = [p.strip() for p in raw_text.split("\n\n") if p.strip()]

            for para in paragraphs:
                # Test for Chapter or Section heading updates
                chap, sec = detector.detect_heading(para)
                if chap:
                    current_chapter = chap
                if sec:
                    current_section = sec

                para_tokens = self.count_tokens(para)

                # Initialize new chunk page range if empty
                if current_page_start is None:
                    current_page_start = page_num
                current_page_end = page_num

                # If single paragraph exceeds max_tokens, force split it
                if para_tokens > self.max_tokens:
                    # Flush current accumulated chunk if any
                    if current_chunk_paragraphs:
                        chunk_text = "\n\n".join(current_chunk_paragraphs)
                        chunks.append(
                            GeneratedChunk(
                                page_start=current_page_start,
                                page_end=current_page_end,
                                chapter_title=current_chapter,
                                section_title=current_section,
                                content=chunk_text,
                                token_count=self.count_tokens(chunk_text),
                                metadata_json={"paragraph_count": len(current_chunk_paragraphs)},
                            )
                        )
                        current_chunk_paragraphs = []
                        current_chunk_tokens = 0
                        current_page_start = page_num

                    # Split large paragraph by sentences / lines
                    sub_lines = para.split("\n")
                    sub_buf = []
                    sub_tokens = 0
                    for line in sub_lines:
                        l_tokens = self.count_tokens(line)
                        if sub_tokens + l_tokens > self.target_tokens and sub_buf:
                            c_text = " ".join(sub_buf)
                            chunks.append(
                                GeneratedChunk(
                                    page_start=page_num,
                                    page_end=page_num,
                                    chapter_title=current_chapter,
                                    section_title=current_section,
                                    content=c_text,
                                    token_count=self.count_tokens(c_text),
                                    metadata_json={"split_large_para": True},
                                )
                            )
                            sub_buf = [line]
                            sub_tokens = l_tokens
                        else:
                            sub_buf.append(line)
                            sub_tokens += l_tokens

                    if sub_buf:
                        c_text = " ".join(sub_buf)
                        chunks.append(
                            GeneratedChunk(
                                page_start=page_num,
                                page_end=page_num,
                                chapter_title=current_chapter,
                                section_title=current_section,
                                content=c_text,
                                token_count=self.count_tokens(c_text),
                                metadata_json={"split_large_para": True},
                            )
                        )
                    current_page_start = None
                    current_page_end = None
                    continue

                # Check if adding this paragraph exceeds target/max chunk limits
                if current_chunk_tokens + para_tokens > self.target_tokens and current_chunk_tokens >= self.min_tokens:
                    chunk_text = "\n\n".join(current_chunk_paragraphs)
                    chunks.append(
                        GeneratedChunk(
                            page_start=current_page_start,
                            page_end=current_page_end,
                            chapter_title=current_chapter,
                            section_title=current_section,
                            content=chunk_text,
                            token_count=self.count_tokens(chunk_text),
                            metadata_json={"paragraph_count": len(current_chunk_paragraphs)},
                        )
                    )

                    # Compute overlap from end of previous chunk if overlap enabled
                    overlap_paras = []
                    overlap_count = 0
                    for prev_p in reversed(current_chunk_paragraphs):
                        p_t = self.count_tokens(prev_p)
                        if overlap_count + p_t <= self.overlap_tokens:
                            overlap_paras.insert(0, prev_p)
                            overlap_count += p_t
                        else:
                            break

                    current_chunk_paragraphs = overlap_paras + [para]
                    current_chunk_tokens = overlap_count + para_tokens
                    current_page_start = current_page_end
                    current_page_end = page_num
                else:
                    current_chunk_paragraphs.append(para)
                    current_chunk_tokens += para_tokens

        # Flush remaining trailing chunk if any
        if current_chunk_paragraphs and current_page_start is not None:
            chunk_text = "\n\n".join(current_chunk_paragraphs)
            chunks.append(
                GeneratedChunk(
                    page_start=current_page_start,
                    page_end=current_page_end or current_page_start,
                    chapter_title=current_chapter,
                    section_title=current_section,
                    content=chunk_text,
                    token_count=self.count_tokens(chunk_text),
                    metadata_json={"paragraph_count": len(current_chunk_paragraphs)},
                )
            )

        return chunks
