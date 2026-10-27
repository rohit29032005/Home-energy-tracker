"""Overlay professionally typeset forms of the two existing REFIT equations.

The source PDF remains the page-layout authority.  The overlay covers only the
raw formula text and the raw LaTeX-style interval condition on page 2.
"""

from __future__ import annotations

import io
import sys
from pathlib import Path

from pypdf import PdfReader, PdfWriter
from reportlab.lib.colors import white
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen.canvas import Canvas


ARIAL = r"C:\Windows\Fonts\arial.ttf"
ARIAL_ITALIC = r"C:\Windows\Fonts\ariali.ttf"


def register_fonts() -> None:
    pdfmetrics.registerFont(TTFont("EquationRoman", ARIAL))
    pdfmetrics.registerFont(TTFont("EquationItalic", ARIAL_ITALIC))


def draw_text(canvas: Canvas, x: float, y: float, text: str, size: float, *, italic: bool = False) -> float:
    font = "EquationItalic" if italic else "EquationRoman"
    canvas.setFont(font, size)
    canvas.setFillColorRGB(0, 0, 0)
    canvas.drawString(x, y, text)
    return x + pdfmetrics.stringWidth(text, font, size)


def draw_subscript(canvas: Canvas, x: float, y: float, base: str, sub: str, *, base_size: float, sub_size: float) -> float:
    x = draw_text(canvas, x, y, base, base_size, italic=True)
    draw_text(canvas, x, y - 2.5, sub, sub_size)
    return x + pdfmetrics.stringWidth(sub, "EquationRoman", sub_size)


def draw_energy_equation(canvas: Canvas, x: float, y: float) -> None:
    cursor = draw_subscript(canvas, x, y, "E", "kWh", base_size=9.5, sub_size=5.9)
    cursor = draw_text(canvas, cursor + 1.8, y, " = ", 9.5)
    cursor = draw_subscript(canvas, cursor, y, "P", "start,W", base_size=9.5, sub_size=5.9)
    cursor = draw_text(canvas, cursor + 1.2, y, " × ", 9.5)
    cursor = draw_subscript(canvas, cursor, y, "Δt", "s", base_size=9.5, sub_size=5.9)
    draw_text(canvas, cursor + 1.2, y, " / 3,600,000", 9.5)


def draw_condition(canvas: Canvas, x: float, y: float) -> None:
    cursor = draw_text(canvas, x, y, "0 < ", 10.0)
    cursor = draw_subscript(canvas, cursor, y, "Δt", "s", base_size=10.0, sub_size=6.0)
    draw_text(canvas, cursor + 0.8, y, " ≤ 16 s.", 10.0)


def overlay_page(width: float, height: float):
    stream = io.BytesIO()
    canvas = Canvas(stream, pagesize=(width, height))
    # These rectangles cover only the source formula tokens identified by PDF text coordinates.
    canvas.setFillColor(white)
    canvas.rect(305.5, 79.2, 175.0, 14.4, fill=1, stroke=0)
    canvas.rect(397.2, 69.0, 97.0, 13.0, fill=1, stroke=0)
    draw_energy_equation(canvas, 332.0, 82.1)
    draw_condition(canvas, 398.2, 70.4)
    canvas.save()
    stream.seek(0)
    return PdfReader(stream).pages[0]


def main() -> None:
    if len(sys.argv) != 3:
        raise SystemExit("Usage: overlay_equations.py INPUT.pdf OUTPUT.pdf")
    source = Path(sys.argv[1])
    destination = Path(sys.argv[2])
    destination.parent.mkdir(parents=True, exist_ok=True)
    register_fonts()
    reader = PdfReader(source)
    if len(reader.pages) != 6:
        raise ValueError(f"Expected six source pages; found {len(reader.pages)}")
    writer = PdfWriter()
    for index, page in enumerate(reader.pages):
        if index == 1:
            width = float(page.mediabox.width)
            height = float(page.mediabox.height)
            page.merge_page(overlay_page(width, height))
        writer.add_page(page)
    if reader.metadata:
        metadata = {key: value for key, value in reader.metadata.items() if isinstance(value, str)}
        writer.add_metadata(metadata)
    with destination.open("wb") as handle:
        writer.write(handle)


if __name__ == "__main__":
    main()
