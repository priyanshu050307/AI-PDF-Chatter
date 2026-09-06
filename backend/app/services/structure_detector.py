import re
from typing import List, Optional, Tuple
from app.services.pdf_processor import ExtractedPage, ExtractedTextBlock


class StructureDetector:
    """
    Deterministic structure detector for PDF documents.
    Analyzes font sizes, text styles, and structural regex patterns to identify chapter/section titles.
    """

    CHAPTER_PATTERNS = [
        re.compile(r"^(?:CHAPTER|Chapter)\s+([0-9IVXLCDM]+[:.]?\s*.*)", re.IGNORECASE),
        re.compile(r"^Part\s+([0-9IVXLCDM]+[:.]?\s*.*)", re.IGNORECASE),
    ]

    SECTION_PATTERNS = [
        re.compile(r"^(\d+\.\d+(?:\.\d+)?)\s+(.+)"),
        re.compile(r"^(?:SECTION|Section)\s+(\d+.*)", re.IGNORECASE),
    ]

    def __init__(self, pages: List[ExtractedPage]):
        self.pages = pages
        self.avg_font_size = self._calculate_average_font_size()

    def _calculate_average_font_size(self) -> float:
        """Calculate median/average body text font size across document."""
        font_sizes = []
        for page in self.pages:
            for block in page.text_blocks:
                if len(block.text) > 10:  # Body text candidate
                    font_sizes.append(block.font_size)

        if not font_sizes:
            return 10.0
        return sum(font_sizes) / len(font_sizes)

    def detect_heading(self, line: str, block: Optional[ExtractedTextBlock] = None) -> Tuple[Optional[str], Optional[str]]:
        """
        Analyze a line/block of text to test if it forms a Chapter or Section heading.
        Returns tuple of (chapter_title, section_title).
        """
        clean_line = line.strip()
        if not clean_line or len(clean_line) > 120:
            return None, None

        # Check Chapter Patterns
        for pat in self.CHAPTER_PATTERNS:
            if pat.match(clean_line):
                return clean_line, None

        # Check Section Patterns
        for pat in self.SECTION_PATTERNS:
            if pat.match(clean_line):
                return None, clean_line

        # Font-size based heuristic (e.g. font size >= 1.35x average body font size)
        if block and block.font_size >= self.avg_font_size * 1.35:
            if block.font_size >= self.avg_font_size * 1.6:
                return clean_line, None  # Major Chapter/Title heading
            return None, clean_line  # Sub-heading / Section

        return None, None
