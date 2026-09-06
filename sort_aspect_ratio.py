"""
Aspect Ratio Image Sorter
Organizes images in a directory into Portrait, Landscape, and Square subfolders
based on their dimensions and configurable square tolerance.
"""

import argparse
import shutil
import sys
from pathlib import Path
from PIL import Image

SUPPORTED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}


def parse_args():
    parser = argparse.ArgumentParser(
        description="Sort images into Portrait, Landscape, and Square subdirectories."
    )
    parser.add_argument(
        "-p", "--path",
        type=Path,
        required=True,
        help="Path to the directory containing images to sort.",
    )
    parser.add_argument(
        "-t", "--tolerance",
        type=float,
        default=0.02,
        help="Square detection aspect ratio tolerance (default: 0.02, i.e., 0.98-1.02 is square).",
    )
    parser.add_argument(
        "--copy",
        action="store_true",
        help="Copy files instead of moving them.",
    )
    return parser.parse_args()


def main():
    args = parse_args()
    target_dir = args.path.resolve()

    if not target_dir.exists() or not target_dir.is_dir():
        print(f"Error: Directory not found: {target_dir}", file=sys.stderr)
        sys.exit(1)

    portrait_dir = target_dir / "Portrait"
    landscape_dir = target_dir / "Landscape"
    square_dir = target_dir / "Square"

    for folder in [portrait_dir, landscape_dir, square_dir]:
        folder.mkdir(parents=True, exist_ok=True)

    # Collect only root-level images in the target directory
    image_files = sorted([
        p for p in target_dir.iterdir()
        if p.is_file() and p.suffix.lower() in SUPPORTED_EXTENSIONS
    ])

    total = len(image_files)
    counts = {"portrait": 0, "landscape": 0, "square": 0, "failed": 0}
    action_verb = "Copied" if args.copy else "Moved"

    print(f"Sorting {total} images in: {target_dir}\n")

    for idx, fpath in enumerate(image_files, 1):
        try:
            with Image.open(fpath) as img:
                w, h = img.size

            ratio = w / h

            if abs(ratio - 1.0) <= args.tolerance:
                dest_dir = square_dir
                cat = "square"
            elif w > h:
                dest_dir = landscape_dir
                cat = "landscape"
            else:
                dest_dir = portrait_dir
                cat = "portrait"

            dest_path = dest_dir / fpath.name

            if args.copy:
                shutil.copy2(fpath, dest_path)
            else:
                shutil.move(fpath, dest_path)

            counts[cat] += 1
            print(f"[{idx}/{total}] {action_verb} to {cat.capitalize()}: {fpath.name} ({w}x{h})")

        except Exception as e:
            print(f"[{idx}/{total}] Error processing {fpath.name}: {e}", file=sys.stderr)
            counts["failed"] += 1

    print("\n" + "=" * 50)
    print("Summary:")
    print(f"• Portrait:  {counts['portrait']}")
    print(f"• Landscape: {counts['landscape']}")
    print(f"• Square:    {counts['square']}")
    if counts["failed"]:
        print(f"• Failed:    {counts['failed']}")
    print("=" * 50)


if __name__ == "__main__":
    main()