"""Single-page processing: detect → classify → export."""

import logging
from pathlib import Path

from PIL import Image

from image_utils import make_transparent
from core.line_detector import LineDetector
from core.classifier import SuraClassifier

logger = logging.getLogger(__name__)


class PageProcessor:
    def __init__(
        self,
        detector: LineDetector,
        results_dir: Path,
        classifier: SuraClassifier | None = None,
    ):
        self.detector = detector
        self.classifier = classifier
        self.results_dir = results_dir

    def process(self, img: Image.Image, filename: str) -> dict:
        """Detect → classify → export. Returns a result dict."""
        # Detect
        try:
            line_images = self.detector.detect(img)
        except Exception as e:
            logger.error("Detection failed for %s: %s", filename, e)
            return {"filename": filename, "status": "error", "message": str(e)}

        if not line_images:
            return {"filename": filename, "status": "no_lines", "message": "No text lines detected", "outputs": []}

        # Classify
        labels: list[bool] | None = None
        if self.classifier is not None:
            try:
                labels = self.classifier.classify(line_images)
            except Exception as e:
                logger.warning("Classification failed for %s, skipping: %s", filename, e)

        # Export
        saved = self._export(line_images, Path(filename).stem, labels)
        logger.info("Finished %s: %d lines", filename, len(line_images))
        return {"filename": filename, "status": "success", "lines": len(line_images), "outputs": saved}

    def _export(
        self,
        line_images: list[Image.Image],
        stem: str,
        labels: list[bool] | None,
    ) -> list[str]:
        if labels is None:
            labels = [False] * len(line_images)

        saved: list[str] = []
        text_idx = sura_idx = 0
        for line_img, is_sura in zip(line_images, labels, strict=True):
            if is_sura:
                sura_idx += 1
                name = f"{stem}-sura_name-{sura_idx}.png"
            else:
                text_idx += 1
                name = f"{stem}-{text_idx}.png"
            out_path = self.results_dir / name
            make_transparent(line_img).save(out_path)
            saved.append(str(out_path))
            logger.info("Saved %s", out_path)
        return saved
