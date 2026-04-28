"""Pipeline: iterates over raw image bytes and delegates to PageProcessor."""

import io
import logging

from PIL import Image

from core.page_processor import PageProcessor

logger = logging.getLogger(__name__)


class Pipeline:
    def __init__(self, processor: PageProcessor):
        self.processor = processor

    def run(self, images_data: list[tuple[bytes, str]]) -> list[dict]:
        """Process a batch of (raw_bytes, filename) pairs."""
        results = []
        for page_index, (raw_bytes, filename) in enumerate(images_data, start=1):
            logger.info("Processing %s", filename)
            try:
                img = Image.open(io.BytesIO(raw_bytes))
            except Exception as e:
                logger.error("Failed to open %s: %s", filename, e)
                results.append(
                    {"filename": filename, "status": "error", "message": str(e)}
                )
                continue
            results.append(self.processor.process(img, filename, page_index=page_index))
        return results
