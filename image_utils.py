"""Shared image utilities used by both the server pipeline and the CLI."""

import numpy as np
from PIL import Image


def make_transparent(image: Image.Image, threshold: int = 200) -> Image.Image:
    """Convert white (or near-white) background pixels to transparent.

    Uses NumPy vectorised operations instead of pixel-by-pixel Python loops
    for significantly better performance on large images.

    Args:
        image: Input PIL image (any mode).
        threshold: Pixels with R, G, and B all above this value are
            treated as background and made fully transparent.

    Returns:
        An RGBA image with the background removed.
    """
    rgba = image.convert("RGBA")
    data = np.array(rgba)

    # Mask: pixels where R, G, and B are all above the threshold
    is_white = np.all(data[:, :, :3] > threshold, axis=2)
    data[is_white, 3] = 0

    return Image.fromarray(data, "RGBA")
