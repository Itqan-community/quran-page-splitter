"""
Usage:
    python run.py <image_path> [output_dir] [options]

Example:
    python run.py page.png output/ --margin-x 50 --padding 10
"""

import argparse
from pathlib import Path
from PIL import Image
from script.line_cutter import crop_lines


def make_transparent(crop: Image.Image, threshold: int = 200) -> Image.Image:
    rgba = crop.convert("RGBA")
    data = rgba.load()
    width, height = rgba.size
    for y in range(height):
        for x in range(width):
            r, g, b, a = data[x, y]
            if r > threshold and g > threshold and b > threshold:
                data[x, y] = (r, g, b, 0)
    return rgba


def main():
    parser = argparse.ArgumentParser(description="Split a Mushaf page into line crops.")
    parser.add_argument("image_path",        type=str)
    parser.add_argument("output_dir",        type=str,   nargs="?", default="output")
    parser.add_argument("--margin-x",        type=int,   default=45)
    parser.add_argument("--margin-y",        type=int,   default=60)
    parser.add_argument("--gap-threshold",   type=float, default=0.1)
    parser.add_argument("--min-line-height", type=int,   default=20)
    parser.add_argument("--padding",         type=int,   default=4)
    args = parser.parse_args()

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    image = Image.open(args.image_path)
    crops = crop_lines(
        image,
        margin_x=args.margin_x,
        margin_y=args.margin_y,
        gap_threshold=args.gap_threshold,
        min_line_height=args.min_line_height,
        padding=args.padding,
    )

    if not crops:
        print("No text lines detected.")
        return

    for i, crop in enumerate(crops, start=1):
        out_path = output_dir / f"line_{i:03}.png"
        make_transparent(crop).save(out_path)
        print(f"[{i:03}] saved → {out_path}")

    print(f"\n✓ Saved {len(crops)} line(s) to '{output_dir}/'")


if __name__ == "__main__":
    main()