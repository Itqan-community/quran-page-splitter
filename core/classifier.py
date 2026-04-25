"""Sura-name line classifier."""

import logging
import statistics

import cv2
import numpy as np
from PIL import Image

from core.config import ClassifierConfig, DetectionConfig
from script.line_cutter import crop_lines

logger = logging.getLogger(__name__)


class SuraClassifier:
    def __init__(
        self,
        template: Image.Image,
        detection: DetectionConfig,
        config: ClassifierConfig | None = None,
    ):
        self.config = config or ClassifierConfig()
        self._template_edge = self._prepare_template(template, detection)

    def _prepare_template(
        self, template: Image.Image, detection: DetectionConfig
    ) -> np.ndarray:
        """Crop the template with line detection, then keep the left 15% strip."""
        lines = crop_lines(template, **detection.as_dict())
        if not lines:
            raise ValueError("Template image contains no detectable lines")
        prepped = lines[0]
        gray = np.array(prepped.convert("L"), dtype=np.uint8)
        edge_w = max(1, int(gray.shape[1] * 0.15))
        return gray[:, :edge_w]

    def classify(self, line_images: list[Image.Image]) -> list[bool]:
        """Return a parallel bool list: True = sura-name line."""
        if not line_images:
            return []

        heights = [img.height for img in line_images]
        median_h = statistics.median(heights)

        results: list[bool] = []
        for idx, (img, h) in enumerate(zip(line_images, heights), start=1):
            if len(line_images) >= 3 and h <= median_h * self.config.height_factor:
                results.append(False)
                continue
            results.append(self._match(img, idx))

        return results

    def classify_single(
        self,
        img: Image.Image,
        median_h: float,
        total_lines: int,
        idx: int = 0,
    ) -> bool:
        """Classify a single line given pre-computed median height.

        This allows inline classification during sequential processing
        without requiring all line images upfront.
        """
        if total_lines >= 3 and img.height <= median_h * self.config.height_factor:
            return False
        return self._match(img, idx)

    def _match(self, img: Image.Image, idx: int) -> bool:
        line_gray = np.array(img.convert("L"), dtype=np.uint8)
        edge = self._template_edge

        scale = line_gray.shape[0] / edge.shape[0]
        new_h = line_gray.shape[0]
        new_w = max(1, int(edge.shape[1] * scale))
        tmpl_resized = cv2.resize(edge, (new_w, new_h))

        search_w = min(line_gray.shape[1], new_w * 2)
        search_region = line_gray[:, :search_w]

        if (
            tmpl_resized.shape[0] > search_region.shape[0]
            or tmpl_resized.shape[1] > search_region.shape[1]
        ):
            logger.warning(
                "  line %d: template larger than search region, skipping", idx
            )
            return False

        result = cv2.matchTemplate(search_region, tmpl_resized, cv2.TM_CCOEFF_NORMED)
        _, max_val, _, _ = cv2.minMaxLoc(result)
        is_sura = max_val >= self.config.match_threshold
        logger.info(
            "  line %d: score=%.4f → %s", idx, max_val, "SURA" if is_sura else "normal"
        )
        return is_sura
