"""Read-only DOCX template distillation for the research-paper formatting task."""

from __future__ import annotations

import argparse
import hashlib
import json
import zipfile
from pathlib import Path

from docx import Document
from docx.oxml.ns import qn


def pt(value):
    return "unset" if value is None else f"{value.pt:.1f} pt"


def inches(value):
    return "unset" if value is None else f"{value.inches:.2f} in"


def color(value):
    return "auto" if value is None else str(value)


def paragraph_snapshot(paragraph, index):
    fmt = paragraph.paragraph_format
    runs = []
    for run in paragraph.runs:
        if not run.text:
            continue
        font = run.font
        runs.append(
            {
                "text": run.text[:160],
                "font": font.name,
                "size": pt(font.size),
                "bold": font.bold,
                "italic": font.italic,
                "underline": font.underline,
                "color": color(font.color.rgb),
            }
        )
    return {
        "index": index,
        "style": paragraph.style.name,
        "text": paragraph.text[:240],
        "alignment": str(paragraph.alignment),
        "space_before": pt(fmt.space_before),
        "space_after": pt(fmt.space_after),
        "line_spacing": str(fmt.line_spacing),
        "left_indent": inches(fmt.left_indent),
        "first_line_indent": inches(fmt.first_line_indent),
        "keep_with_next": fmt.keep_with_next,
        "page_break_before": fmt.page_break_before,
        "runs": runs,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("reference", type=Path)
    parser.add_argument("--artifact", type=Path, required=True)
    parser.add_argument("--json", type=Path, required=True)
    args = parser.parse_args()

    raw = args.reference.read_bytes()
    sha = hashlib.sha256(raw).hexdigest()
    doc = Document(args.reference)

    styles = {}
    for style in doc.styles:
        if style.type != 1:  # paragraph styles only
            continue
        font = style.font
        fmt = style.paragraph_format
        styles[style.name] = {
            "font": font.name,
            "size": pt(font.size),
            "bold": font.bold,
            "italic": font.italic,
            "caps": font.all_caps,
            "color": color(font.color.rgb),
            "alignment": str(fmt.alignment),
            "space_before": pt(fmt.space_before),
            "space_after": pt(fmt.space_after),
            "line_spacing": str(fmt.line_spacing),
            "left_indent": inches(fmt.left_indent),
            "first_line_indent": inches(fmt.first_line_indent),
        }

    sections = []
    for section in doc.sections:
        sections.append(
            {
                "page_width": inches(section.page_width),
                "page_height": inches(section.page_height),
                "left_margin": inches(section.left_margin),
                "right_margin": inches(section.right_margin),
                "top_margin": inches(section.top_margin),
                "bottom_margin": inches(section.bottom_margin),
                "header_distance": inches(section.header_distance),
                "footer_distance": inches(section.footer_distance),
                "first_page_header": [p.text for p in section.first_page_header.paragraphs],
                "header": [p.text for p in section.header.paragraphs],
                "footer": [p.text for p in section.footer.paragraphs],
                "different_first_page": section.different_first_page_header_footer,
            }
        )

    tables = []
    for table_index, table in enumerate(doc.tables, start=1):
        cell_data = []
        for row_index, row in enumerate(table.rows[:3], start=1):
            cell_data.append([cell.text[:160] for cell in row.cells])
        tables.append(
            {
                "index": table_index,
                "rows": len(table.rows),
                "columns": len(table.columns),
                "style": table.style.name if table.style else None,
                "alignment": str(table.alignment),
                "autofit": table.autofit,
                "sample": cell_data,
            }
        )

    with zipfile.ZipFile(args.reference) as zf:
        names = zf.namelist()
        package_parts = []
        for name in names:
            info = zf.getinfo(name)
            if name.startswith(("word/header", "word/footer", "word/media/", "word/styles", "word/numbering", "word/theme", "customXml/")):
                package_parts.append({"path": name, "size": info.file_size})
        media = [name for name in names if name.startswith("word/media/")]

    data = {
        "reference": str(args.reference),
        "sha256": sha,
        "paragraph_count": len(doc.paragraphs),
        "sections": sections,
        "styles": styles,
        "paragraphs": [paragraph_snapshot(p, i + 1) for i, p in enumerate(doc.paragraphs)],
        "tables": tables,
        "media": media,
        "package_parts": package_parts,
    }
    args.json.parent.mkdir(parents=True, exist_ok=True)
    args.json.write_text(json.dumps(data, indent=2), encoding="utf-8")

    important_styles = [name for name in ("Normal", "Title", "Heading 1", "Heading 2", "Heading 3", "Caption") if name in styles]
    p_samples = [p for p in data["paragraphs"] if p["text"]][:28]
    lines = [
        "# Template execution contract",
        "",
        f"- **Reference:** `{args.reference}`",
        f"- **SHA-256:** `{sha}`",
        "- **Render evidence:** attempted with the packaged renderer; unavailable because `soffice.exe` is not present in the bundled runtime PATH.",
        f"- **Structure:** {len(doc.paragraphs)} body paragraphs, {len(doc.tables)} tables, {len(sections)} portrait Letter section(s), and {len(media)} embedded media part(s).",
        "",
        "## Page system",
    ]
    for index, section in enumerate(sections, start=1):
        lines.extend(
            [
                f"- Section {index}: {section['page_width']} x {section['page_height']}; margins L/R/T/B = {section['left_margin']} / {section['right_margin']} / {section['top_margin']} / {section['bottom_margin']}; header/footer = {section['header_distance']} / {section['footer_distance']}; different first page = {section['different_first_page']}.",
                f"  - Header text: {section['header'] or ['(empty)']}",
                f"  - Footer text: {section['footer'] or ['(empty)']}",
            ]
        )
    lines.extend(["", "## Typography and heading roles"])
    for name in important_styles:
        item = styles[name]
        lines.append(
            f"- {name}: font={item['font']}; size={item['size']}; bold={item['bold']}; italic={item['italic']}; caps={item['caps']}; color={item['color']}; alignment={item['alignment']}; before/after={item['space_before']}/{item['space_after']}; line={item['line_spacing']}; indents={item['left_indent']}/{item['first_line_indent']}."
        )
    lines.extend(["", "## Content flow and editable slots"])
    for item in p_samples:
        lines.append(f"- Body paragraph {item['index']} | style `{item['style']}` | `{item['text']}`")
    lines.extend(["", "## Tables"])
    if tables:
        for table in tables:
            lines.append(f"- Table {table['index']}: {table['rows']} x {table['columns']}; style={table['style']}; alignment={table['alignment']}; autofit={table['autofit']}; sample={table['sample']}.")
    else:
        lines.append("- No native tables.")
    lines.extend(["", "## Preservation and fidelity gates"])
    lines.append("- Retain the supplied reference unchanged. Use it solely as the source of page geometry, font hierarchy, title layout, and existing header/footer pattern.")
    lines.append("- The output may add repeated academic sections, tables, citations, and figures because the research manuscript is materially longer than the reference; those additions must inherit the documented page and typography system.")
    lines.append("- Preserve all final-research content, figures, table values, evidence language, and reference entries; apply formatting only.")
    args.artifact.write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
