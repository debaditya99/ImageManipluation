```markdown
# ImageManipulation

A lightweight suite of standalone Python utilities for scraping, downloading, deduplicating, and organizing large media galleries.

---

## Features

* **Browser Extraction:** Console autoscrollers to capture virtualized DOM/lightbox gallery streams.
* **Batch Downloader:** Robust URL list downloader with stream verification, retry backoff, and extension detection.
* **Duplicate Cleaner:** Perceptual difference hashing (`dHash`) to detect and remove duplicate or lower-resolution copies.
* **Aspect Ratio Sorter:** Fast sorting into Portrait, Landscape, and Square folders based on dimensions.

---

## Installation

Ensure you have Python 3.9+ installed, then install the required dependencies:

```bash
pip install requests pillow imagehash

```

---

## Tools & Usage

### 1. Perceptual Duplicate Cleaner (`duplicate_cleaner.py`)

Scans an image directory, identifies identical images (including lower-resolution variants or renamed files), groups them, and keeps only the highest-resolution asset.

```bash
# Dry run (safe preview; generates report without deleting)
python duplicate_cleaner.py --path "./images"

# Execute deletion of lower-resolution copies
python duplicate_cleaner.py --path "./images" --delete

# Run with stricter similarity threshold (default is 4; lower is stricter)
python duplicate_cleaner.py --path "./images" --threshold 2 --delete

```

| Argument | Description | Default |
| --- | --- | --- |
| `-p, --path` | Target directory containing images (**required**) | — |
| `-t, --threshold` | Max Hamming distance for visual matching | `4` |
| `--delete` | Permanently deletes lower-quality duplicates | `False` |

---

### 2. Aspect Ratio Sorter (`sort_aspect_ratio.py`)

Analyzes dimensions of root-level images in a folder and moves or copies them into `Portrait/`, `Landscape/`, or `Square/` subdirectories.

```bash
# Standard move operation
python sort_aspect_ratio.py --path "./images"

# Copy mode (preserves files in source directory)
python sort_aspect_ratio.py --path "./images" --copy

# Custom square tolerance (e.g., 5% variance from 1:1)
python sort_aspect_ratio.py --path "./images" --tolerance 0.05

```

| Argument | Description | Default |
| --- | --- | --- |
| `-p, --path` | Target directory containing images (**required**) | — |
| `-t, --tolerance` | Square aspect ratio tolerance range (`1.0 ± tolerance`) | `0.02` |
| `--copy` | Copies files instead of moving them | `False` |

---

### 3. Batch URL Downloader (`download_urls.py`)

Downloads media from a newline-delimited file of image links. Includes header resolution, byte-integrity validation, resume checks, and rate-limit delays.

```bash
# Standard download
python download_urls.py --input "urls.txt" --output "./downloads"

# Add a 0.5-second cooldown per image to stay under strict rate limits
python download_urls.py -i "urls.txt" -o "./downloads" --delay 0.5

```

| Argument | Description | Default |
| --- | --- | --- |
| `-i, --input` | Path to text file with URLs (**required**) | — |
| `-o, --output` | Destination directory | `./downloaded_images` |
| `--delay` | Delay in seconds between requests | `0.1` |
| `--timeout` | Network timeout per request in seconds | `20` |

---

## Appendix: Extracting URLs via Browser Console

For web galleries using virtual DOM scrolling (elements removed when out of view), run these snippets directly inside DevTools (**F12 → Console**).

### A. Vertical Auto-Scroller (X / Twitter & Virtual Grids)

Scrolls the view automatically, extracts high-resolution asset tags, de-duplicates them, and saves an `image_urls.txt` file when reaching the bottom:

```javascript
(async () => {
  const links = new Set();
  let stagnantCount = 0, lastSize = 0;
  console.log("Starting scrape...");

  while (stagnantCount < 10) {
    document.querySelectorAll('img[src*="[pbs.twimg.com/media/](https://pbs.twimg.com/media/)"]').forEach(img => {
      const match = img.src.match(/media\/([^?]+)/);
      if (match) links.add(`[https://pbs.twimg.com/media/$](https://pbs.twimg.com/media/$){match[1]}?format=jpg&name=4096x4096`);
    });

    if (links.size === lastSize) stagnantCount++;
    else { stagnantCount = 0; lastSize = links.size; }

    window.scrollBy(0, window.innerHeight * 2);
    await new Promise(r => setTimeout(r, 1500));
  }

  const blob = new Blob([[...links].join("\n")], { type: "text/plain" });
  const a = document.createElement("a");
  a.href = URL.createObjectURL(blob);
  a.download = "image_urls.txt";
  a.click();
})();

```

### B. Gallery / Lightbox Traverser (Arrow Navigation)

Open the first image inside the gallery modal/lightbox and run this snippet to cycle through full-res slides and capture the active source URLs:

```javascript
(async () => {
  const links = new Set();
  let stagnantCount = 0, lastSize = 0;

  const pressRight = () => {
    const e = { key: "ArrowRight", code: "ArrowRight", keyCode: 39, bubbles: true };
    document.dispatchEvent(new KeyboardEvent("keydown", e));
    document.dispatchEvent(new KeyboardEvent("keyup", e));
  };

  while (stagnantCount < 15) {
    document.querySelectorAll('img').forEach(img => {
      const src = img.currentSrc || img.src;
      if (src && src.startsWith('http')) links.add(src);
    });

    if (links.size === lastSize) stagnantCount++;
    else { stagnantCount = 0; lastSize = links.size; }

    pressRight();
    await new Promise(r => setTimeout(r, 1000));
  }

  const blob = new Blob([[...links].join("\n")], { type: "text/plain" });
  const a = document.createElement("a");
  a.href = URL.createObjectURL(blob);
  a.download = "gallery_media_urls.txt";
  a.click();
})();

```

---

## License

MIT

```

```