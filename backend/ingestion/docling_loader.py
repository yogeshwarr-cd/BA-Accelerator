"""
=== FILE: backend/ingestion/docling_loader.py ===

Async Docling-based document loader.
Supports local file ingestion, remote URL ingestion (via httpx + tempfile),
and a plain-text fallback for .txt files when Docling fails.
"""

from __future__ import annotations

import asyncio
import os
import tempfile
from pathlib import Path
from typing import Any

import httpx

from designlab_core.utilities.logger import get_logger, log_error, log_info, log_warning

logger = get_logger("ingestion.docling_loader")

# ── Docling import (lazy) ──────────────────────────────────────────────────────

try:
    from docling.document_converter import DocumentConverter
    from docling.exceptions import ConversionError  # graceful if missing
    _DOCLING_AVAILABLE = True
except ImportError:
    _DOCLING_AVAILABLE = False
    log_warning(
        "Docling is not installed. File/URL extraction will use text fallback only.",
    )


# ── Helpers ───────────────────────────────────────────────────────────────────

def _get_converter() -> "DocumentConverter":
    """Return a lazily-instantiated DocumentConverter (cached per process)."""
    if not _DOCLING_AVAILABLE:
        raise RuntimeError(
            "docling package is not installed. Run: pip install docling"
        )
    # Re-use a module-level singleton to avoid reloading models on every call.
    if _get_converter._instance is None:
        log_info("Initialising Docling DocumentConverter (models may download on first run).")
        _get_converter._instance = DocumentConverter()
    return _get_converter._instance


_get_converter._instance = None  # type: ignore[attr-defined]


def _run_docling_sync(source: str) -> dict[str, Any]:
    """
    Synchronous Docling conversion. Returns {"text": str, "metadata": dict}.
    Runs in a thread via asyncio.to_thread to avoid blocking the event loop.
    """
    converter = _get_converter()
    try:
        result = converter.convert(source)
    except Exception as exc:
        # Attempt to catch DocumentConversionError or any Docling-internal error
        raise RuntimeError(f"Docling conversion failed for '{source}': {exc}") from exc

    markdown: str = result.document.export_to_markdown()

    # Build metadata from Docling result where available
    meta: dict[str, Any] = {}
    try:
        meta["page_count"] = len(result.document.pages) if hasattr(result.document, "pages") else None
        meta["title"] = result.document.title if hasattr(result.document, "title") else None
        meta["docling_version"] = result.document.version if hasattr(result.document, "version") else None
    except Exception:
        pass  # metadata extraction is best-effort

    return {"text": markdown, "metadata": meta}


# ── Public async functions ─────────────────────────────────────────────────────

async def load_from_file(file_path: str) -> dict[str, Any]:
    """
    Load and extract text from a local file using Docling.

    Args:
        file_path: Absolute or relative path to the document.

    Returns:
        {"text": str, "metadata": dict}

    Raises:
        FileNotFoundError: If the file does not exist.
        RuntimeError: If Docling extraction fails with no fallback possible.
    """
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")

    log_info("load_from_file called", context={"path": file_path})

    # ── Plain-text fast-path ──────────────────────────────────────────────────
    if path.suffix.lower() == ".txt":
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
            log_info("Plain-text fast-path used for .txt file.")
            return {
                "text": text,
                "metadata": {"source": "txt_read", "file_name": path.name},
            }
        except Exception as exc:
            log_warning(f"Plain-text read failed, falling back to Docling: {exc}")

    # ── Docling extraction ────────────────────────────────────────────────────
    try:
        result = await asyncio.to_thread(_run_docling_sync, str(path))
        result["metadata"]["file_name"] = path.name
        result["metadata"]["file_path"] = str(path)
        result["metadata"]["extraction_method"] = "docling"
        log_info("Docling extraction succeeded.", context={"file": path.name})
        return result
    except RuntimeError as exc:
        # Last-resort: attempt raw text read
        log_error("Docling extraction failed — attempting raw text fallback.", exc=exc)
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
            return {
                "text": text,
                "metadata": {
                    "file_name": path.name,
                    "file_path": str(path),
                    "extraction_method": "text_fallback",
                },
            }
        except Exception as fallback_exc:
            raise RuntimeError(
                f"All extraction methods failed for '{file_path}': {fallback_exc}"
            ) from exc


async def load_from_url(url: str) -> dict[str, Any]:
    """
    Download a remote document, save to a temp file, extract via Docling, then clean up.

    Args:
        url: HTTP/HTTPS URL pointing to the document.

    Returns:
        {"text": str, "metadata": dict}

    Raises:
        RuntimeError: On download failure or extraction failure.
    """
    log_info("load_from_url called", context={"url": url})

    tmp_path: str | None = None
    try:
        async with httpx.AsyncClient(follow_redirects=True, timeout=60.0) as client:
            response = await client.get(url)
            response.raise_for_status()

        content_type = response.headers.get("content-type", "")
        # Derive a safe extension from the content-type or URL
        suffix = _infer_suffix(url, content_type)

        with tempfile.NamedTemporaryFile(
            delete=False, suffix=suffix, prefix="ingestion_url_"
        ) as tmp:
            tmp.write(response.content)
            tmp_path = tmp.name

        log_info("URL document downloaded to temp file.", context={"tmp": tmp_path})

        result = await load_from_file(tmp_path)
        result["metadata"]["source_url"] = url
        result["metadata"]["content_type"] = content_type
        return result

    except httpx.HTTPStatusError as exc:
        raise RuntimeError(
            f"HTTP error downloading '{url}': {exc.response.status_code}"
        ) from exc
    except httpx.RequestError as exc:
        raise RuntimeError(f"Network error downloading '{url}': {exc}") from exc
    finally:
        # Always clean up the temporary file
        if tmp_path and os.path.exists(tmp_path):
            try:
                os.unlink(tmp_path)
                log_info("Temporary download file cleaned up.", context={"tmp": tmp_path})
            except OSError:
                pass


def _infer_suffix(url: str, content_type: str) -> str:
    """Attempt to infer a file extension from the URL path or Content-Type."""
    from urllib.parse import urlparse
    parsed = urlparse(url)
    path_suffix = Path(parsed.path).suffix
    if path_suffix and len(path_suffix) <= 5:
        return path_suffix

    # Map common MIME types
    mime_map = {
        "application/pdf": ".pdf",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document": ".docx",
        "application/vnd.openxmlformats-officedocument.presentationml.presentation": ".pptx",
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": ".xlsx",
        "text/html": ".html",
        "text/plain": ".txt",
        "image/png": ".png",
        "image/jpeg": ".jpg",
    }
    for mime, ext in mime_map.items():
        if mime in content_type:
            return ext
    return ".bin"


async def load(ingestion_input: Any) -> dict[str, Any]:
    """
    Route-aware load: dispatches to load_from_file or load_from_url
    based on the IngestionInput fields.

    Args:
        ingestion_input: IngestionInput instance.

    Returns:
        {"text": str, "metadata": dict}
    """
    if ingestion_input.file_path:
        return await load_from_file(ingestion_input.file_path)
    if ingestion_input.url:
        return await load_from_url(ingestion_input.url)
    raise ValueError(
        "load() requires either file_path or url on the IngestionInput."
    )


# ─── INTEGRATION NOTE ─────────────────────────────────────────────────────────
# Produces : {"text": str, "metadata": dict}
# Consumed : ingestion/__init__.py  run_ingestion() for file/url source types
