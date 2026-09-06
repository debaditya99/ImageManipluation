"""
Batch Image List Downloader
Reads a newline-delimited text file of media URLs and downloads them
concurrently or sequentially with user-agent spoofing and extension resolution.
"""

import argparse
import os
import sys
import time
from pathlib import Path
from urllib.parse import urlparse
import requests

DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    )
}

# Mapping common Content-Type headers to extensions
MIME_EXTENSION_MAP = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
    "image/gif": ".gif",
}


def parse_args():
    parser = argparse.ArgumentParser(
        description="Download a list of image URLs from a text file."
    )
    parser.add_argument(
        "-i", "--input",
        type=Path,
        required=True,
        help="Path to the text file containing image URLs (one per line).",
    )
    parser.add_argument(
        "-o", "--output",
        type=Path,
        default=Path("./downloaded_images"),
        help="Directory to save downloaded files (default: ./downloaded_images).",
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=0.1,
        help="Delay in seconds between requests to avoid rate limits (default: 0.1).",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=20,
        help="Request timeout in seconds (default: 20).",
    )
    return parser.parse_args()


def get_extension(response: requests.Response, url_path: str) -> str:
    """Infers extension from headers or falls back to path or .jpg."""
    content_type = response.headers.get("Content-Type", "").split(";")[0].strip().lower()
    if content_type in MIME_EXTENSION_MAP:
        return MIME_EXTENSION_MAP[content_type]

    suffix = Path(url_path).suffix.lower()
    if suffix in [".jpg", ".jpeg", ".png", ".webp", ".gif"]:
        return suffix

    return ".jpg"


def main():
    args = parse_args()
    input_file = args.input.resolve()
    output_dir = args.output.resolve()

    if not input_file.exists() or not input_file.is_file():
        print(f"Error: Input file not found: {input_file}", file=sys.stderr)
        sys.exit(1)

    output_dir.mkdir(parents=True, exist_ok=True)

    with open(input_file, "r", encoding="utf-8") as f:
        urls = [line.strip() for line in f if line.strip() and not line.startswith("#")]

    total = len(urls)
    print(f"Loaded {total} URLs from: {input_file.name}")
    print(f"Saving assets to: {output_dir}\n")

    session = requests.Session()
    session.headers.update(DEFAULT_HEADERS)

    success_count = 0
    fail_count = 0

    for idx, url in enumerate(urls, 1):
        if args.delay > 0 and idx > 1:
            time.sleep(args.delay)

        raw_name = Path(urlparse(url).path).stem or f"media_{idx}"
        # Sanitize filename characters
        safe_name = "".join(c for c in raw_name if c.isalnum() or c in ("-", "_")).strip()

        # Temporary generic path to check existence before network call
        prefix = f"{idx:04d}_{safe_name}"

        # If a file starting with this index exists, skip
        existing = list(output_dir.glob(f"{prefix}.*"))
        if existing and existing[0].stat().st_size > 0:
            print(f"[{idx}/{total}] Already exists, skipping: {existing[0].name}")
            success_count += 1
            continue

        try:
            res = session.get(url, stream=True, timeout=args.timeout)
            res.raise_for_status()

            ext = get_extension(res, urlparse(url).path)
            final_filename = f"{prefix}{ext}"
            filepath = output_dir / final_filename

            with open(filepath, "wb") as out:
                for chunk in res.iter_content(chunk_size=16384):
                    if chunk:
                        out.write(chunk)

            print(f"[{idx}/{total}] Downloaded: {final_filename}")
            success_count += 1

        except requests.exceptions.HTTPError as e:
            print(f"[{idx}/{total}] HTTP Error ({res.status_code}) on {url}", file=sys.stderr)
            fail_count += 1
        except Exception as e:
            print(f"[{idx}/{total}] Failed: {url} ({e})", file=sys.stderr)
            fail_count += 1

    print("\n" + "=" * 50)
    print("Download Summary:")
    print(f"• Successfully fetched: {success_count}")
    print(f"• Failed:                {fail_count}")
    print(f"• Total processed:       {total}")
    print("=" * 50)


if __name__ == "__main__":
    main()