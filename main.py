"""CLI entry point.

Usage:
    python main.py <image_path> [output_dir] [options]
"""

import argparse
from pathlib import Path

from core.config import CropConfig, DetectionConfig
from core.line_detector import LineDetector
from core.page_processor import PageProcessor
from core.pipeline import Pipeline


def main():
    parser = argparse.ArgumentParser(description="Split a Mushaf page into line crops.")
    parser.add_argument("image_path", type=str)
    parser.add_argument("output_dir", type=str, nargs="?", default="output")
    parser.add_argument("--crop-x",          type=int,   default=45)
    parser.add_argument("--crop-y",          type=int,   default=60)
    parser.add_argument("--crop-w",          type=int,   default=45)
    parser.add_argument("--crop-h",          type=int,   default=60)
    parser.add_argument("--gap-threshold",   type=float, default=0.1)
    parser.add_argument("--min-line-height", type=int,   default=20)
    parser.add_argument("--padding",         type=int,   default=4)
    args = parser.parse_args()

    results_dir = Path(args.output_dir)
    results_dir.mkdir(parents=True, exist_ok=True)

    crop_cfg = CropConfig(x=args.crop_x, y=args.crop_y, w=args.crop_w, h=args.crop_h)
    det_cfg = DetectionConfig(
        gap_threshold=args.gap_threshold,
        min_line_height=args.min_line_height,
        padding=args.padding,
    )

    detector = LineDetector(crop=crop_cfg, detection=det_cfg)
    processor = PageProcessor(detector=detector, results_dir=results_dir)  # no classifier in CLI
    pipeline = Pipeline(processor=processor)

    image_path = Path(args.image_path)
    results = pipeline.run([(image_path.read_bytes(), image_path.name)])

    for r in results:
        if r["status"] == "success":
            for path in r["outputs"]:
                print(f"saved → {path}")
            print(f"\n✓ {r['lines']} line(s) saved to '{args.output_dir}/'")
        else:
            print(f"✗ {r['message']}")


if __name__ == "__main__":
    main()
