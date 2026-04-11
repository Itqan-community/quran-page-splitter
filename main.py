"""
Usage:
    python run.py <image_path> [output_dir]

Example:
    python run.py receipt.jpg output/
"""

import sys
from pathlib import Path
from PIL import Image
from line_cutter import crop_lines


def main():
    if len(sys.argv) < 2:
        print("Usage: python run.py <image_path> [output_dir]")
        sys.exit(1)

    image_path = Path(sys.argv[1])
    output_dir = Path(sys.argv[2]) if len(sys.argv) > 2 else Path("output")
    output_dir.mkdir(parents=True, exist_ok=True)

    image = Image.open(image_path).convert("RGB")
    crops = crop_lines(image)

    if not crops:
        print("No text lines detected.")
        return

    for i, crop in enumerate(crops, start=1):
        out_path = output_dir / f"line_{i:03}.png"
        crop.save(out_path)
        print(f"[{i:03}] saved → {out_path}")

    print(f"\n✓ Saved {len(crops)} line(s) to '{output_dir}/'")


if __name__ == "__main__":
    main()