import asyncio
from docling.document_converter import DocumentConverter
from backend.shared.logger import get_logger

logger = get_logger(__name__)

class DoclingLoader:
    """
    Wrapper around the Docling library for loading and converting document files/URLs
    into unified Markdown/Text representations.
    """
    def __init__(self):
        # We lazy initialize DocumentConverter to speed up import time and avoid pre-downloading models on start
        self._converter = None

    @property
    def converter(self) -> DocumentConverter:
        if self._converter is None:
            logger.info("Initializing Docling DocumentConverter. This may download parsing models on first call.")
            self._converter = DocumentConverter()
        return self._converter

    async def load(self, target: str) -> str:
        """
        Ingests document from local path or remote URL.
        Runs CPU-bound Docling conversion in a separate executor thread.
        """
        logger.info(f"Converting document via Docling: {target}")
        
        try:
            def convert_sync():
                result = self.converter.convert(target)
                # Export the document layout as markdown format to retain headers/tables
                return result.document.export_to_markdown()

            markdown_content = await asyncio.to_thread(convert_sync)
            logger.info("Docling conversion completed successfully.")
            return markdown_content
        except Exception as e:
            logger.error(f"Docling failed parsing target {target}: {str(e)}")
            # Failover: read local text files directly if target matches local file system
            try:
                import os
                if os.path.exists(target):
                    logger.info(f"Fallback direct read for local file: {target}")
                    with open(target, "r", encoding="utf-8") as f:
                        return f.read()
            except Exception:
                pass
            raise RuntimeError(f"Docling parsing failed: {str(e)}")

# INTEGRATION NOTE
# Docling processes PDF, DOCX, PPTX, images, and HTML URLs.
# In execution environments, ensure permissions allow Docling to cache download models locally.
