"""Aya separator preprocessing and line splitting helpers."""

from __future__ import annotations

from dataclasses import dataclass

import cv2
import numpy as np
from PIL import Image


@dataclass
class AyaSeparatorConfig:
    match_threshold: float = 0.45
    short_line_ratio: float = 0.9
    min_segment_width: int = 8


class AyaSeparatorProcessor:
    def __init__(self, template: Image.Image, config: AyaSeparatorConfig | None = None):
        self.config = config or AyaSeparatorConfig()
        self.template = self._prepare_template(template)

    def split_line(self, line_image: Image.Image) -> list[Image.Image]:
        maybe_trimmed = self._trim_if_short(line_image)
        boxes = self._detect_separator_boxes(maybe_trimmed)
        if not boxes:
            return [maybe_trimmed]
        return self._split_by_boxes(maybe_trimmed, boxes)

    def _prepare_template(self, template: Image.Image) -> np.ndarray:
        trimmed = self._trim_to_content(template)
        gray = np.array(trimmed.convert("L"), dtype=np.uint8)
        _, binary_inv = cv2.threshold(
            gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU
        )

        # Remove inner number by masking the central area.
        h, w = binary_inv.shape
        cx1, cx2 = int(w * 0.30), int(w * 0.70)
        cy1, cy2 = int(h * 0.20), int(h * 0.80)
        binary_inv[cy1:cy2, cx1:cx2] = 0

        kernel = np.ones((2, 2), dtype=np.uint8)
        cleaned = cv2.dilate(binary_inv, kernel, iterations=1)
        return cleaned

    def _trim_if_short(self, line_image: Image.Image) -> Image.Image:
        trimmed = self._trim_to_content(line_image)
        ratio = trimmed.width / max(1, line_image.width)
        if ratio < self.config.short_line_ratio:
            return trimmed
        return line_image

    def _trim_to_content(self, image: Image.Image) -> Image.Image:
        gray = np.array(image.convert("L"), dtype=np.uint8)
        _, binary_inv = cv2.threshold(
            gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU
        )
        non_zero = cv2.findNonZero(binary_inv)
        if non_zero is None:
            return image
        x, y, w, h = cv2.boundingRect(non_zero)
        return image.crop((x, y, x + w, y + h))

    def _detect_separator_boxes(self, line_image: Image.Image) -> list[tuple[int, int]]:
        line_gray = np.array(line_image.convert("L"), dtype=np.uint8)
        _, line_binary = cv2.threshold(
            line_gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU
        )
        template = self.template

        scale = line_binary.shape[0] / max(1, template.shape[0])
        resized_w = max(2, int(template.shape[1] * scale))
        resized_template = cv2.resize(
            template, (resized_w, line_binary.shape[0]), interpolation=cv2.INTER_AREA
        )
        if resized_template.shape[1] >= line_binary.shape[1]:
            return []

        match_map = cv2.matchTemplate(
            line_binary, resized_template, cv2.TM_CCOEFF_NORMED
        )
        scores = match_map[0]
        candidate_x = np.where(scores >= self.config.match_threshold)[0]
        if candidate_x.size == 0:
            return []

        # Keep strongest non-overlapping matches.
        by_score = sorted(candidate_x.tolist(), key=lambda x: float(scores[x]), reverse=True)
        min_gap = max(4, int(resized_template.shape[1] * 0.6))
        selected: list[int] = []
        for x in by_score:
            if all(abs(x - s) >= min_gap for s in selected):
                selected.append(x)
        selected.sort()
        return [(x, x + resized_template.shape[1]) for x in selected]

    def _split_by_boxes(
        self, line_image: Image.Image, boxes: list[tuple[int, int]]
    ) -> list[Image.Image]:
        width, height = line_image.size
        parts: list[Image.Image] = []
        start = 0
        for _, right in boxes:
            cut = min(width, right)
            if cut - start >= self.config.min_segment_width:
                parts.append(line_image.crop((start, 0, cut, height)))
            start = cut
        if width - start >= self.config.min_segment_width:
            parts.append(line_image.crop((start, 0, width, height)))
        return parts if parts else [line_image]
