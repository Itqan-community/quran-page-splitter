"""Line detection logic wrapped in a class."""

import logging
from PIL import Image

from core.config import CropConfig, DetectionConfig, ProcessingConfig
from script.line_cutter import crop_lines

logger = logging.getLogger(__name__)


class LineDetector:
    def __init__(
        self,
        crop: CropConfig,
        detection: DetectionConfig,
        processing: ProcessingConfig | None = None,
    ):
        self.crop = crop
        self.detection = detection
        self.processing = processing or ProcessingConfig()

    def _crop(self, img: Image.Image, page_index: int) -> Image.Image:
        x, y, w, h = self.crop.as_tuple()
        img_w, img_h = img.size
        should_swap = (
            self.processing.alternate_horizontal_margin and page_index % 2 == 0
        )
        crop_x = (img_w - (x + w)) if should_swap else x
        left   = max(0, crop_x)
        top    = max(0, y)
        right  = min(img_w, left + w)
        bottom = min(img_h, top + h)
        if right <= left or bottom <= top:
            raise ValueError("Crop rectangle is outside image bounds")
        return img.crop((left, top, right, bottom))

    def detect(self, img: Image.Image, page_index: int = 0) -> list[Image.Image]:
        """Crop the image then return detected line images."""
        cropped = self._crop(img, page_index)
        lines = crop_lines(cropped, **self.detection.as_dict())
        logger.info("Detected %d lines", len(lines))
        return lines
