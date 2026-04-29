"""Sura-name line classifier."""

import logging
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
        # Keep 'detection' as requested for the template preparation
        self._template_edge = self._prepare_template(template, detection)

    def _prepare_template(
        self, template: Image.Image, detection: DetectionConfig
    ) -> np.ndarray:
        """Crop the template with line detection, then keep the right 30% strip."""
        lines = crop_lines(template, **detection.as_dict())
        if not lines:
            # Fallback if detection fails on the specific template image
            prepped = template
        else:
            prepped = lines[0]
            
        gray = np.array(prepped.convert("L"), dtype=np.uint8)
        
        # Keep the right 30% (The 'Sura' keyword in Arabic)
        edge_w = max(1, int(gray.shape[1] * 0.30))
        return gray[:, -edge_w:]

    def classify_single(
        self,
        img: Image.Image,
        median_h: float,
        total_lines: int,
        idx: int = 0,
    ) -> bool:
        """
        Public method called by CoordinateExporter.
        Checks height first, then performs template matching.
        """
        # 1. Height-based check (Sura headers are usually significantly taller)
        if img.size[1] > median_h * self.config.height_factor:
            logger.info("  line %d: detected as SURA via height factor", idx)
            return True
            
        # 2. Template matching check
        return self._match(img, idx)

    def _match(self, img: Image.Image, idx: int) -> bool:
        """Perform template matching on the right side of the line image."""
        line_gray = np.array(img.convert("L"), dtype=np.uint8)
        edge = self._template_edge

        # Rescale template to match the current line height
        scale = line_gray.shape[0] / edge.shape[0]
        new_h = line_gray.shape[0]
        new_w = max(1, int(edge.shape[1] * scale))
        tmpl_resized = cv2.resize(edge, (new_w, new_h))

        # Search the RIGHT side of the line (Right-to-Left script)
        search_w = min(line_gray.shape[1], new_w * 2)
        search_region = line_gray[:, -search_w:]

        if (
            tmpl_resized.shape[0] > search_region.shape[0]
            or tmpl_resized.shape[1] > search_region.shape[1]
        ):
            return False

        result = cv2.matchTemplate(search_region, tmpl_resized, cv2.TM_CCOEFF_NORMED)
        _, max_val, _, _ = cv2.minMaxLoc(result)
        
        is_sura = max_val >= self.config.match_threshold
        if is_sura:
            logger.info("  line %d: score=%.4f → SURA", idx, max_val)
        
        return is_sura