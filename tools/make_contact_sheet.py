from math import ceil
from pathlib import Path
import sys

from PIL import Image, ImageOps


if len(sys.argv) != 3:
    raise SystemExit("Usage: make_contact_sheet.py INPUT_DIR OUTPUT_PNG")

source = Path(sys.argv[1])
target = Path(sys.argv[2])
images = [Image.open(path).convert("RGB") for path in sorted(source.glob("*.png"))]
if not images:
    raise SystemExit("No PNGs found")
thumb_width = 500
thumbs = []
for image in images:
    ratio = thumb_width / image.width
    thumb = image.resize((thumb_width, round(image.height * ratio)))
    thumbs.append(ImageOps.expand(thumb, border=3, fill="#888888"))
cell_width = thumb_width + 6
cell_height = max(image.height for image in thumbs)
columns = 2
rows = ceil(len(thumbs) / columns)
sheet = Image.new("RGB", (cell_width * columns, cell_height * rows), "#f4f4f4")
for index, image in enumerate(thumbs):
    x = (index % columns) * cell_width
    y = (index // columns) * cell_height
    sheet.paste(image, (x, y))
target.parent.mkdir(parents=True, exist_ok=True)
sheet.save(target)
