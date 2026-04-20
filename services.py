"""Image processing orchestration for the line-cutter pipeline.

This module owns the processing logic: cropping, line detection, and export.
The HTTP layer (server.py) and CLI (main.py) both delegate here.

To change the export format (e.g. from PNG images to JSON coordinates),
modify or replace ``export_lines``.
"""

import io
import logging
import statistics
from pathlib import Path
from typing import Optional

import cv2
import numpy as np

from PIL import Image

from image_utils import make_transparent
from script.line_cutter import crop_lines

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Border asset helpers
# ---------------------------------------------------------------------------

def save_upload(
    data: bytes,
    original_name: Optional[str],
    default_name: str,
    results_dir: Path,
) -> Path:
    """Write raw bytes to *results_dir* using the upload's basename.

    Returns the resolved path of the saved file.
    """
    base = Path(original_name or default_name).name
    if not base or base in (".", ".."):
        base = default_name
    path = results_dir / base
    path.write_bytes(data)
    return path


def save_border_assets(
    sura_data: bytes,
    sura_name: Optional[str],
    aya_data: bytes,
    aya_name: Optional[str],
    results_dir: Path,
) -> tuple[Path, Path]:
    """Persist the sura-name and aya-separator images into *results_dir*."""
    sura_path = save_upload(sura_data, sura_name, "sura_name.png", results_dir)
    logger.info("Saved sura_name.png")
    aya_path = save_upload(aya_data, aya_name, "aya_separator.png", results_dir)
    logger.info("Saved aya_separator.png")
    return sura_path, aya_path


# ---------------------------------------------------------------------------
# Single-image processing
# ---------------------------------------------------------------------------

def crop_to_region(
    img: Image.Image,
    crop_x: int,
    crop_y: int,
    crop_w: int,
    crop_h: int,
) -> Image.Image:
    """Crop *img* to the given rectangle, clamped to image bounds.

    Raises ``ValueError`` if the resulting region is empty.
    """
    img_w, img_h = img.size
    left = max(0, crop_x)
    top = max(0, crop_y)
    right = min(img_w, left + crop_w)
    bottom = min(img_h, top + crop_h)
    if right <= left or bottom <= top:
        raise ValueError("Crop rectangle is outside image bounds")
    return img.crop((left, top, right, bottom))


def detect_lines(
    cropped: Image.Image,
    *,
    gap_threshold: float = 0.1,
    min_line_height: int = 20,
    padding: int = 4,
) -> list[Image.Image]:
    """Run line detection on a cropped page image."""
    return crop_lines(
        cropped,
        gap_threshold=gap_threshold,
        min_line_height=min_line_height,
        padding=padding,
    )


# ---------------------------------------------------------------------------
# Sura name classification
# ---------------------------------------------------------------------------

def classify_lines(
    line_images: list[Image.Image],
    sura_template: Image.Image,
    height_factor: float = 1.5,
    match_threshold: float = 0.5,
) -> list[bool]:
    """Classify each line as sura-name border (True) or normal text (False).

    Two-stage approach:
    1. **Height filter** — lines significantly taller than the median are
       candidates.  When there are fewer than 3 lines the height filter
       is skipped and every line is treated as a candidate.
    2. **Template matching** — the left edge of *sura_template* is matched
       against candidates using ``cv2.matchTemplate``.

    Args:
        line_images: Detected line images for one page.
        sura_template: Reference sura-name border image (from the user).
        height_factor: A line must be at least this many times the median
            height to be considered a candidate.
        match_threshold: Minimum ``TM_CCOEFF_NORMED`` score to confirm a
            sura-name match.

    Returns:
        A list of booleans parallel to *line_images*.
    """
    if not line_images:
        return []

    heights = [img.height for img in line_images]
    median_h = statistics.median(heights)
    logger.info(
        "classify_lines: %d lines, heights=%s, median=%d",
        len(line_images), heights, median_h,
    )

    # Prepare template: keep leftmost 15% as the decoration strip
    tmpl_gray = np.array(sura_template.convert("L"), dtype=np.uint8)
    edge_w = max(1, int(tmpl_gray.shape[1] * 0.15))
    template_edge = tmpl_gray[:, :edge_w]
    logger.info(
        "classify_lines: sura template %s, edge strip %s",
        tmpl_gray.shape, template_edge.shape,
    )

    results: list[bool] = []
    for idx, (img, h) in enumerate(zip(line_images, heights), start=1):
        # Stage 1: height filter (skip when too few lines to compare)
        if len(line_images) >= 3 and h <= median_h * height_factor:
            logger.debug(
                "  line %d (h=%d): skipped by height filter (threshold=%d)",
                idx, h, int(median_h * height_factor),
            )
            results.append(False)
            continue

        logger.info(
            "  line %d (h=%d): candidate (>%d), running template match…",
            idx, h, int(median_h * height_factor),
        )

        # Stage 2: template matching on the left edge
        line_gray = np.array(img.convert("L"), dtype=np.uint8)

        # Resize template edge to match the candidate's height so scale
        # differences between the reference crop and the detected line
        # don't cause a mismatch.
        scale = line_gray.shape[0] / template_edge.shape[0]
        new_h = line_gray.shape[0]
        new_w = max(1, int(template_edge.shape[1] * scale))
        tmpl_resized = cv2.resize(template_edge, (new_w, new_h))

        # The search region: left portion of the line (2× template width
        # so matchTemplate has room to slide).
        search_w = min(line_gray.shape[1], new_w * 2)
        search_region = line_gray[:, :search_w]

        logger.info(
            "  line %d: line_gray=%s, tmpl_resized=%s, search_region=%s",
            idx, line_gray.shape, tmpl_resized.shape, search_region.shape,
        )

        # Template must be smaller than or equal to the search region.
        if (
            tmpl_resized.shape[0] > search_region.shape[0]
            or tmpl_resized.shape[1] > search_region.shape[1]
        ):
            logger.warning(
                "  line %d: template larger than search region, skipping", idx
            )
            results.append(False)
            continue

        match_result = cv2.matchTemplate(
            search_region, tmpl_resized, cv2.TM_CCOEFF_NORMED
        )
        _, max_val, _, _ = cv2.minMaxLoc(match_result)
        is_sura = max_val >= match_threshold

        logger.info(
            "  line %d: match_score=%.4f, threshold=%.2f → %s",
            idx, max_val, match_threshold,
            "SURA NAME" if is_sura else "normal",
        )
        results.append(is_sura)

    return results


# ---------------------------------------------------------------------------
# Export
# ---------------------------------------------------------------------------

def export_lines(
    line_images: list[Image.Image],
    stem: str,
    results_dir: Path,
    line_labels: list[bool] | None = None,
) -> list[str]:
    """Save detected lines as transparent PNGs.

    To switch to a different export format (e.g. JSON coordinates),
    modify this function or create an alternative and update
    ``process_page`` to call it.

    Args:
        line_images: Line crops to save.
        stem: Base name for output files (typically the page filename stem).
        results_dir: Target directory.
        line_labels: Optional parallel list of booleans from
            ``classify_lines``.  ``True`` → sura-name line,
            ``False`` → normal text line.

    Returns a list of saved file paths (as strings).
    """
    if line_labels is None:
        line_labels = [False] * len(line_images)

    saved: list[str] = []
    text_idx = 0
    sura_idx = 0
    for line_img, is_sura in zip(line_images, line_labels):
        if is_sura:
            sura_idx += 1
            out_name = f"{stem}-sura_name-{sura_idx}.png"
        else:
            text_idx += 1
            out_name = f"{stem}-{text_idx}.png"
        out_path = results_dir / out_name
        make_transparent(line_img).save(out_path)
        saved.append(str(out_path))
        logger.info("Saved %s", out_path)
    return saved


# ---------------------------------------------------------------------------
# Page-level orchestration
# ---------------------------------------------------------------------------

def process_page(
    img: Image.Image,
    filename: str,
    crop_rect: tuple[int, int, int, int],
    line_params: dict,
    results_dir: Path,
    sura_template: Image.Image | None = None,
) -> dict:
    """Process a single page image: crop → detect → classify → export.

    Args:
        img: The opened page image.
        filename: Original filename (used for logging and output naming).
        crop_rect: ``(crop_x, crop_y, crop_w, crop_h)`` rectangle.
        line_params: Keyword arguments forwarded to ``detect_lines``
            (gap_threshold, min_line_height, padding).
        results_dir: Directory to write exported files into.
        sura_template: Optional reference image of the sura-name border.
            When provided, detected lines are classified and sura-name
            lines are exported with a distinct filename.

    Returns:
        A result dict with keys: filename, status, and either
        lines/outputs or message.
    """
    crop_x, crop_y, crop_w, crop_h = crop_rect

    # --- Crop ---
    try:
        cropped = crop_to_region(img, crop_x, crop_y, crop_w, crop_h)
    except (ValueError, Exception) as e:
        logger.error("Crop failed for %s: %s", filename, e)
        return {"filename": filename, "status": "error", "message": f"Crop failed: {e}"}

    # --- Detect ---
    try:
        line_images = detect_lines(cropped, **line_params)
    except Exception as e:
        logger.error("Line detection failed for %s: %s", filename, e)
        return {"filename": filename, "status": "error", "message": f"Line detection failed: {e}"}

    if not line_images:
        logger.warning("No lines detected in %s", filename)
        return {"filename": filename, "status": "no_lines", "message": "No text lines detected", "outputs": []}

    # --- Classify ---
    line_labels = None
    if sura_template is not None:
        try:
            line_labels = classify_lines(line_images, sura_template)
        except Exception as e:
            logger.warning("Classification failed for %s, skipping: %s", filename, e)

    # --- Export ---
    stem = Path(filename).stem
    saved_paths = export_lines(line_images, stem, results_dir, line_labels)

    logger.info("Finished %s: %d lines", filename, len(line_images))
    return {"filename": filename, "status": "success", "lines": len(line_images), "outputs": saved_paths}


def process_all_pages(
    images_data: list[tuple[bytes, str]],
    crop_rect: tuple[int, int, int, int],
    line_params: dict,
    results_dir: Path,
    sura_template_path: Path | None = None,
) -> list[dict]:
    """Process multiple page images and collect results.

    Args:
        images_data: List of ``(raw_bytes, filename)`` tuples.
        crop_rect: ``(crop_x, crop_y, crop_w, crop_h)`` rectangle.
        line_params: Forwarded to ``detect_lines``.
        results_dir: Output directory.
        sura_template_path: Path to the sura-name border reference
            image.  Loaded once and reused for every page.

    Returns:
        A list of per-page result dicts (see ``process_page``).
    """
    # Load sura template once for the entire batch
    sura_template: Image.Image | None = None
    if sura_template_path is not None:
        try:
            sura_template = Image.open(sura_template_path)
            logger.info("Loaded sura template from %s", sura_template_path)
        except Exception as e:
            logger.warning("Could not load sura template: %s", e)

    results: list[dict] = []

    for raw_bytes, filename in images_data:
        logger.info("Processing %s", filename)
        try:
            img = Image.open(io.BytesIO(raw_bytes))
        except Exception as e:
            logger.error("Failed to open %s: %s", filename, e)
            results.append({
                "filename": filename,
                "status": "error",
                "message": f"Failed to open image: {e}",
            })
            continue

        results.append(
            process_page(img, filename, crop_rect, line_params, results_dir, sura_template)
        )

    return results
