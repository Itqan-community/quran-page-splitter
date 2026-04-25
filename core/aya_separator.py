"""Aya separator preprocessing and line splitting helpers."""

from __future__ import annotations

from dataclasses import dataclass

import cv2
import numpy as np
from PIL import Image


@dataclass
class AyaSeparatorConfig:
    match_threshold: float = 0.55
    short_line_ratio: float = 0.99
    min_segment_width: int = 8


@dataclass
class SegmentResult:
    """A segment produced by splitting a line at aya separators."""

    image: Image.Image
    x_start: int  # left edge in the *original* (untrimmed) line image
    x_end: int  # right edge in the *original* (untrimmed) line image
    has_separator: bool  # True if this segment contains an aya separator


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

    def split_line_with_coords(
        self, line_image: Image.Image
    ) -> list[SegmentResult]:
        """Split a line and return segments with coordinate info.

        Each SegmentResult has x_start/x_end relative to the *original*
        (untrimmed) line image, and a has_separator flag indicating whether
        the segment contains an aya separator ornament.
        """
        maybe_trimmed, trim_x = self._trim_if_short_with_offset(line_image)
        boxes = self._detect_separator_boxes(maybe_trimmed)

        if not boxes:
            return [
                SegmentResult(
                    image=maybe_trimmed,
                    x_start=trim_x,
                    x_end=trim_x + maybe_trimmed.width,
                    has_separator=False,
                )
            ]

        return self._split_by_boxes_with_coords(maybe_trimmed, boxes, trim_x)

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

    def _trim_if_short_with_offset(
        self, line_image: Image.Image
    ) -> tuple[Image.Image, int]:
        """Trim short lines and return (trimmed_image, x_offset_in_original)."""
        trimmed, x_offset = self._trim_to_content_with_offset(line_image)
        ratio = trimmed.width / max(1, line_image.width)
        if ratio < self.config.short_line_ratio:
            return trimmed, x_offset
        return line_image, 0

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

    def _trim_to_content_with_offset(
        self, image: Image.Image
    ) -> tuple[Image.Image, int]:
        """Trim to content and return (trimmed_image, x_offset)."""
        gray = np.array(image.convert("L"), dtype=np.uint8)
        _, binary_inv = cv2.threshold(
            gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU
        )
        non_zero = cv2.findNonZero(binary_inv)
        if non_zero is None:
            return image, 0
        x, y, w, h = cv2.boundingRect(non_zero)
        return image.crop((x, y, x + w, y + h)), x

    def _detect_separator_boxes(self, line_image: Image.Image) -> list[tuple[int, int]]:
        line_gray = np.array(line_image.convert("L"), dtype=np.uint8)
        _, line_binary = cv2.threshold(
            line_gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU
        )
        template = self.template

        # Template must fit inside the line in both dimensions.
        if (
            template.shape[0] > line_binary.shape[0]
            or template.shape[1] >= line_binary.shape[1]
        ):
            return []

        match_map = cv2.matchTemplate(line_binary, template, cv2.TM_CCOEFF_NORMED)
        # Best score at each x-column regardless of y-position,
        # since the separator can appear at any vertical offset.
        scores = match_map.max(axis=0)
        candidate_x = np.where(scores >= self.config.match_threshold)[0]
        if candidate_x.size == 0:
            return []

        # Keep strongest non-overlapping matches.
        by_score = sorted(
            candidate_x.tolist(), key=lambda x: float(scores[x]), reverse=True
        )
        min_gap = max(4, int(template.shape[1] * 0.6))
        selected: list[int] = []
        for x in by_score:
            if all(abs(x - s) >= min_gap for s in selected):
                selected.append(x)
        selected.sort()
        return [(x, x + template.shape[1]) for x in selected]

    def _split_by_boxes(
        self, line_image: Image.Image, boxes: list[tuple[int, int]]
    ) -> list[Image.Image]:
        """Split line at separator boxes, producing segments in RTL order.

        Cuts at the LEFT edge of each separator so the separator circle
        is included with the aya text to its right (the aya it terminates).
        """
        width, height = line_image.size
        min_w = self.config.min_segment_width
        parts: list[Image.Image] = []
        end = width
        for left, _ in reversed(boxes):  # right-to-left
            cut = max(0, left)
            if end - cut >= min_w:
                parts.append(line_image.crop((cut, 0, end, height)))
            end = cut
        # Leftmost remaining text
        if end >= min_w:
            parts.append(line_image.crop((0, 0, end, height)))
        return parts if parts else [line_image]

    def _split_by_boxes_with_coords(
        self,
        line_image: Image.Image,
        boxes: list[tuple[int, int]],
        trim_x: int,
    ) -> list[SegmentResult]:
        """Split at separator boxes and return SegmentResults in RTL order.

        Coordinates are translated back to the original (untrimmed) line
        image space by adding ``trim_x``.
        """
        width, height = line_image.size
        min_w = self.config.min_segment_width
        results: list[SegmentResult] = []
        end = width

        for left, _ in reversed(boxes):  # right-to-left
            cut = max(0, left)
            if end - cut >= min_w:
                results.append(
                    SegmentResult(
                        image=line_image.crop((cut, 0, end, height)),
                        x_start=trim_x + cut,
                        x_end=trim_x + end,
                        has_separator=True,
                    )
                )
            end = cut

        # Leftmost remaining text — no separator
        if end >= min_w:
            results.append(
                SegmentResult(
                    image=line_image.crop((0, 0, end, height)),
                    x_start=trim_x,
                    x_end=trim_x + end,
                    has_separator=False,
                )
            )

        if not results:
            return [
                SegmentResult(
                    image=line_image,
                    x_start=trim_x,
                    x_end=trim_x + width,
                    has_separator=False,
                )
            ]
        return results

