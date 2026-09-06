"""
Duplicate Image Cleaner
Scans a target directory for duplicate or lower-resolution images using
perceptual difference hashing (dHash) and optional filename token matching.
"""

import argparse
import re
import sys
from pathlib import Path
from PIL import Image
import imagehash

SUPPORTED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}


def clean_name_token(filename: str) -> str:
    """Strips file extensions and common numeric index prefixes (e.g., '0042_')."""
    base = Path(filename).stem
    return re.sub(r"^\d+[\s_-]*", "", base).strip().lower()


def scan_images(directory: Path):
    """Scans directory and extracts visual hashes, dimensions, and metadata."""
    image_entries = []
    filepaths = sorted(
        [p for p in directory.iterdir() if p.is_file() and p.suffix.lower() in SUPPORTED_EXTENSIONS]
    )
    total = len(filepaths)

    print(f"Scanning {total} images in: {directory}")

    for idx, fpath in enumerate(filepaths, 1):
        try:
            with Image.open(fpath) as img:
                w, h = img.size
                total_pixels = w * h
                p_hash = imagehash.dhash(img)

            image_entries.append({
                "filename": fpath.name,
                "filepath": fpath,
                "dimensions": (w, h),
                "pixels": total_pixels,
                "size_bytes": fpath.stat().st_size,
                "clean_stem": clean_name_token(fpath.name),
                "hash": p_hash,
            })
        except Exception as err:
            print(f"[{idx}/{total}] Skipping unreadable file {fpath.name}: {err}")

    return image_entries


def are_duplicates(a: dict, b: dict, threshold: int) -> bool:
    """Evaluates whether two files are duplicates via visual hash distance or matching names."""
    # Check 1: Perceptual difference hash
    if (a["hash"] - b["hash"]) <= threshold:
        return True

    # Check 2: Filename stem equality or substring relation
    name_a, name_b = a["clean_stem"], b["clean_stem"]
    if name_a and name_b and (name_a == name_b or name_a in name_b or name_b in name_a):
        return True

    return False


def group_duplicates(entries: list, threshold: int) -> list:
    """Clusters matching images into connected groups to avoid redundant deletions."""
    visited = set()
    clusters = []

    for i, a in enumerate(entries):
        if i in visited:
            continue

        current_cluster = [a]
        visited.add(i)

        for j in range(i + 1, len(entries)):
            if j not in visited and are_duplicates(a, entries[j], threshold):
                current_cluster.append(entries[j])
                visited.add(j)

        if len(current_cluster) > 1:
            clusters.append(current_cluster)

    return clusters


def parse_args():
    parser = argparse.ArgumentParser(
        description="Find and remove lower-resolution duplicate images using perceptual hashing."
    )
    parser.add_argument(
        "-p", "--path",
        type=Path,
        required=True,
        help="Path to the directory containing images to analyze.",
    )
    parser.add_argument(
        "-t", "--threshold",
        type=int,
        default=4,
        help="Max Hamming distance for visual similarity (0 = exact, 4 = typical default).",
    )
    parser.add_argument(
        "--delete",
        action="store_true",
        help="Permanently delete duplicate files. If omitted, runs in DRY-RUN preview mode.",
    )
    return parser.parse_args()


def main():
    args = parse_args()
    target_dir = args.path.resolve()
    dry_run = not args.delete

    if not target_dir.exists() or not target_dir.is_dir():
        print(f"Error: Directory not found: {target_dir}", file=sys.stderr)
        sys.exit(1)

    output_report = target_dir / "duplicates_report.txt"

    if dry_run:
        print("Running in DRY-RUN mode. Use --delete to remove duplicate files permanently.\n")

    items = scan_images(target_dir)
    print(f"Loaded {len(items)} valid images. Identifying duplicates...\n")

    duplicate_groups = group_duplicates(items, args.threshold)
    files_to_delete = []

    report_lines = [
        "Duplicate Image Scan & Deletion Report",
        f"Directory: {target_dir}",
        f"Mode: {'DRY RUN (Preview Only)' if dry_run else 'LIVE DELETION'}",
        f"Duplicate Groups Identified: {len(duplicate_groups)}",
        "=" * 70,
    ]

    for group_idx, group in enumerate(duplicate_groups, 1):
        # Retain highest resolution, falling back to file size
        sorted_group = sorted(
            group,
            key=lambda x: (x["pixels"], x["size_bytes"]),
            reverse=True,
        )

        keeper = sorted_group[0]
        discards = sorted_group[1:]

        report_lines.append(f"• GROUP {group_idx}:")
        report_lines.append(
            f"  [KEEP]   {keeper['filename']} ({keeper['dimensions'][0]}x{keeper['dimensions'][1]})"
        )

        for d in discards:
            report_lines.append(
                f"  [DELETE] {d['filename']} ({d['dimensions'][0]}x{d['dimensions'][1]})"
            )
            files_to_delete.append(d)

        report_lines.append("-" * 70)

    deleted_count = 0
    if files_to_delete:
        print(f"Found {len(files_to_delete)} duplicate file(s) marked for deletion.")
        for d in files_to_delete:
            if not dry_run:
                try:
                    d["filepath"].unlink()
                    deleted_count += 1
                except OSError as e:
                    print(f"Error deleting {d['filename']}: {e}", file=sys.stderr)
            else:
                deleted_count += 1

        action_word = "Simulated deletion of" if dry_run else "Successfully deleted"
        summary = f"\n{action_word} {deleted_count} duplicate files."
    else:
        summary = "\nNo duplicate files found."

    report_lines.append(summary)
    report_text = "\n".join(report_lines)

    print(report_text)

    with open(output_report, "w", encoding="utf-8") as f:
        f.write(report_text)

    print(f"\nReport saved to: {output_report}")


if __name__ == "__main__":
    main()