import io
import logging
import sys
from app.core.config import settings


def _make_utf8_stream(stream):
    """
    Wrap a stream to use UTF-8 encoding with 'replace' error handling.
    This prevents UnicodeEncodeError on Windows (default cp1252) when
    logging content that contains emoji or other non-ASCII characters
    (e.g., from LLM responses like qwen3 that include emoji in their output).
    """
    try:
        # Re-wrap the underlying buffer with explicit UTF-8 + replace
        return io.TextIOWrapper(
            stream.buffer,
            encoding="utf-8",
            errors="replace",
            line_buffering=True,
        )
    except AttributeError:
        # stream doesn't have a .buffer (e.g. already wrapped, or StringIO in tests)
        return stream


def setup_logging():
    """Configure structured logging format for application with UTF-8 safety on Windows."""
    log_level = logging.DEBUG if settings.DEBUG else logging.INFO

    # Ensure stdout uses UTF-8 to safely handle emoji / non-ASCII from LLM responses
    utf8_stdout = _make_utf8_stream(sys.stdout)

    logging.basicConfig(
        level=log_level,
        format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        handlers=[
            logging.StreamHandler(utf8_stdout)
        ]
    )

    # Suppress verbose loggers
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.engine").setLevel(
        logging.WARNING if not settings.DEBUG else logging.INFO
    )


logger = logging.getLogger("pdfchatter")

