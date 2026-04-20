import numpy as np
from PIL import Image


def get_line_boxes(
    image: Image.Image,
    gap_threshold: float = 0.03,
    min_line_height: int = 20,
    padding: int = 8,
) -> list[dict]:
    # Flatten transparency onto white before converting to grayscale
    base = Image.new("RGBA", image.size, (255, 255, 255, 255))
    base.paste(image.convert("RGBA"), mask=image.convert("RGBA").split()[3])
    img = np.array(base.convert("L"), dtype=np.float32)
    h, w = img.shape

    # Auto-detect: dark bg (mean < 128) → gaps are low-sum rows
    #              light bg (mean > 128) → invert so gaps become low-sum rows
    if img.mean() > 128:
        img = 255.0 - img  # now dark text becomes bright, white gaps become dark

    row_sums = img.sum(axis=1)
    gap_limit = row_sums.max() * gap_threshold
    is_gap = row_sums < gap_limit

    # Find contiguous text bands
    in_text = False
    bands = []
    start = 0
    for y, gap in enumerate(is_gap):
        if not gap and not in_text:
            start = y
            in_text = True
        elif gap and in_text:
            bands.append((start, y))
            in_text = False
    if in_text:
        bands.append((start, len(is_gap)))

    boxes = []
    for y1, y2 in bands:
        if (y2 - y1) < min_line_height:
            continue
        boxes.append({
            "left":   0,
            "top":    max(0, y1 - padding),
            "right":  w,
            "bottom": min(h, y2 + padding),
        })

    return boxes


def crop_lines(image: Image.Image, **kwargs) -> list[Image.Image]:
    boxes = get_line_boxes(image, **kwargs)
    return [image.crop((b["left"], b["top"], b["right"], b["bottom"])) for b in boxes]