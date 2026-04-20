"""Line detection logic wrapped in a class."""

import logging
from PIL import Image

from core.config import CropConfig, DetectionConfig
from script.line_cutter import crop_lines

logger = logging.getLogger(__name__)


class LineDetector:
    def __init__(self, crop: CropConfig, detection: DetectionConfig):
        self.crop = crop
        self.detection = detection

    def _crop(self, img: Image.Image) -> Image.Image:
        x, y, w, h = self.crop.as_tuple()
        img_w, img_h = img.size
        left   = max(0, x)
        top    = max(0, y)
        right  = min(img_w, left + w)
        bottom = min(img_h, top + h)
        if right <= left or bottom <= top:
            raise ValueError("Crop rectangle is outside image bounds")
        return img.crop((left, top, right, bottom))

    def detect(self, img: Image.Image) -> list[Image.Image]:
        """Crop the image then return detected line images."""
        cropped = self._crop(img)
        lines = crop_lines(cropped, **self.detection.as_dict())
        logger.info("Detected %d lines", len(lines))
        return lines
