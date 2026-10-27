"""Compare source and final rendered PDFs for confinement of visual changes."""

from __future__ import annotations

import sys
from pathlib import Path

from PIL import Image, ImageChops


def main() -> None:
    if len(sys.argv) != 3:
        raise SystemExit("Usage: compare_equation_pdf_pages.py SOURCE_PNG_DIR FINAL_PNG_DIR")
    source_dir = Path(sys.argv[1])
    final_dir = Path(sys.argv[2])
    source_pages = sorted(source_dir.glob("page-*.png"))
    final_pages = sorted(final_dir.glob("page-*.png"))
    if len(source_pages) != len(final_pages):
        raise SystemExit(f"Page-count mismatch: {len(source_pages)} vs {len(final_pages)}")
    for source, final in zip(source_pages, final_pages):
        with Image.open(source).convert("RGB") as a, Image.open(final).convert("RGB") as b:
            bbox = ImageChops.difference(a, b).getbbox()
        print(f"{source.name}: {'identical' if bbox is None else 'changed bbox=' + str(bbox)}")


if __name__ == "__main__":
    main()
