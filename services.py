"""Image processing orchestration for the line-cutter pipeline.

This module owns the processing logic: cropping, line detection, and export.
The HTTP layer (server.py) and CLI (main.py) both delegate here.

To change the export format (e.g. from PNG images to JSON coordinates),
modify or replace ``export_lines``.
"""

import io
import logging
from pathlib import Path
from typing import Optional

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


def export_lines(
    line_images: list[Image.Image],
    stem: str,
    results_dir: Path,
) -> list[str]:
    """Save detected lines as transparent PNGs.

    To switch to a different export format (e.g. JSON coordinates),
    modify this function or create an alternative and update
    ``process_page`` to call it.

    Returns a list of saved file paths (as strings).
    """
    saved: list[str] = []
    for idx, line_img in enumerate(line_images, start=1):
        out_path = results_dir / f"{stem}-{idx}.png"
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
) -> dict:
    """Process a single page image: crop → detect lines → export.

    Args:
        img: The opened page image.
        filename: Original filename (used for logging and output naming).
        crop_rect: ``(crop_x, crop_y, crop_w, crop_h)`` rectangle.
        line_params: Keyword arguments forwarded to ``detect_lines``
            (gap_threshold, min_line_height, padding).
        results_dir: Directory to write exported files into.

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

    # --- Export ---
    stem = Path(filename).stem
    saved_paths = export_lines(line_images, stem, results_dir)

    logger.info("Finished %s: %d lines", filename, len(line_images))
    return {"filename": filename, "status": "success", "lines": len(line_images), "outputs": saved_paths}


def process_all_pages(
    images_data: list[tuple[bytes, str]],
    crop_rect: tuple[int, int, int, int],
    line_params: dict,
    results_dir: Path,
) -> list[dict]:
    """Process multiple page images and collect results.

    Args:
        images_data: List of ``(raw_bytes, filename)`` tuples.
        crop_rect: ``(crop_x, crop_y, crop_w, crop_h)`` rectangle.
        line_params: Forwarded to ``detect_lines``.
        results_dir: Output directory.

    Returns:
        A list of per-page result dicts (see ``process_page``).
    """
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

        results.append(process_page(img, filename, crop_rect, line_params, results_dir))

    return results
