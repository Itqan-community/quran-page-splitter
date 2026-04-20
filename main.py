"""
Usage:
    python run.py <image_path> [output_dir] [options]

Example:
    python run.py page.png output/ --margin-x 50 --padding 10
"""

import argparse
from pathlib import Path
from PIL import Image
from services import crop_to_region
from image_utils import make_transparent
from script.line_cutter import crop_lines


def main():
    parser = argparse.ArgumentParser(description="Split a Mushaf page into line crops.")
    parser.add_argument("image_path",        type=str)
    parser.add_argument("output_dir",        type=str,   nargs="?", default="output")
    parser.add_argument("--crop-x",        type=int,   default=45)
    parser.add_argument("--crop-y",        type=int,   default=60)
    parser.add_argument("--crop-w",        type=int,   default=45)
    parser.add_argument("--crop-h",        type=int,   default=60)
    parser.add_argument("--gap-threshold",   type=float, default=0.1)
    parser.add_argument("--min-line-height", type=int,   default=20)
    parser.add_argument("--padding",         type=int,   default=4)
    args = parser.parse_args()

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    image = Image.open(args.image_path)
    crops = crop_lines(
        crop_to_region(
            image,
            crop_x=args.crop_x,
            crop_y=args.crop_y,
            crop_w=args.crop_w,
            crop_h=args.crop_h,
        ),
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