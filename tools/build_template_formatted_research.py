"""Create a VIT-template-formatted copy of the verified Home Energy Tracker paper.

The supplied VIT paper template is retained unchanged. This tool copies its page
system and styles, replaces its placeholder body with the existing verified
research manuscript body, and carries over only the image relationships required
by that manuscript.
"""

from __future__ import annotations

import argparse
import copy
import shutil
import zipfile
from pathlib import Path

from docx import Document
from docx.enum.table import WD_CELL_VERTICAL_ALIGNMENT, WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import nsmap, qn
from docx.shared import Inches, Pt, RGBColor
from lxml import etree


W_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
R_NS = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
REL_NS = "http://schemas.openxmlformats.org/package/2006/relationships"
CT_NS = "http://schemas.openxmlformats.org/package/2006/content-types"
NS = {"w": W_NS, "r": R_NS, "pr": REL_NS, "ct": CT_NS}

SOURCE_REL_PATH = "word/_rels/document.xml.rels"
DOCUMENT_PATH = "word/document.xml"
CONTENT_TYPES_PATH = "[Content_Types].xml"


def set_cell_shading(cell, fill: str) -> None:
    tc_pr = cell._tc.get_or_add_tcPr()
    shd = tc_pr.find(qn("w:shd"))
    if shd is None:
        shd = OxmlElement("w:shd")
        tc_pr.append(shd)
    shd.set(qn("w:fill"), fill)
    shd.set(qn("w:val"), "clear")


def set_cell_borders(cell) -> None:
    tc_pr = cell._tc.get_or_add_tcPr()
    borders = tc_pr.first_child_found_in("w:tcBorders")
    if borders is None:
        borders = OxmlElement("w:tcBorders")
        tc_pr.append(borders)
    for edge in ("top", "left", "bottom", "right"):
        tag = qn(f"w:{edge}")
        element = borders.find(tag)
        if element is None:
            element = OxmlElement(f"w:{edge}")
            borders.append(element)
        element.set(qn("w:val"), "single")
        element.set(qn("w:sz"), "4")
        element.set(qn("w:color"), "000000")


def set_repeat_table_header(row) -> None:
    tr_pr = row._tr.get_or_add_trPr()
    marker = OxmlElement("w:tblHeader")
    marker.set(qn("w:val"), "true")
    tr_pr.append(marker)


def set_font(run, size: float = 11, bold: bool | None = None, italic: bool | None = None) -> None:
    run.font.name = "Times New Roman"
    run._element.rPr.rFonts.set(qn("w:eastAsia"), "Times New Roman") if run._element.rPr is not None else None
    run.font.size = Pt(size)
    if bold is not None:
        run.font.bold = bold
    if italic is not None:
        run.font.italic = italic
    run.font.color.rgb = RGBColor(0, 0, 0)


def copy_body_and_images(template: Path, source: Path, destination: Path) -> None:
    """Clone source body blocks into the template and map the required image rels."""
    with zipfile.ZipFile(template, "r") as template_zip, zipfile.ZipFile(source, "r") as source_zip:
        template_files = {name: template_zip.read(name) for name in template_zip.namelist()}
        source_doc = etree.fromstring(source_zip.read(DOCUMENT_PATH))
        template_doc = etree.fromstring(template_files[DOCUMENT_PATH])
        source_rels = etree.fromstring(source_zip.read(SOURCE_REL_PATH))
        template_rels = etree.fromstring(template_files[SOURCE_REL_PATH])

        source_body = source_doc.find("w:body", NS)
        template_body = template_doc.find("w:body", NS)
        template_sect_pr = template_body.find("w:sectPr", NS)
        for child in list(template_body):
            if child.tag != f"{{{W_NS}}}sectPr":
                template_body.remove(child)

        relation_map = {}
        existing_ids = {rel.get("Id") for rel in template_rels.findall("pr:Relationship", NS)}
        next_id = 100
        for rel in source_rels.findall("pr:Relationship", NS):
            target = rel.get("Target", "")
            rel_type = rel.get("Type", "")
            if "media/" not in target and not rel_type.endswith("/hyperlink"):
                continue
            old_id = rel.get("Id")
            new_id = old_id
            while new_id in existing_ids:
                new_id = f"rId{next_id}"
                next_id += 1
            existing_ids.add(new_id)
            relation_map[old_id] = new_id
            new_rel = copy.deepcopy(rel)
            new_rel.set("Id", new_id)
            template_rels.append(new_rel)
            if "media/" in target:
                source_part = f"word/{target.lstrip('/') }" if not target.startswith("/") else target.lstrip("/")
                if source_part in source_zip.namelist():
                    template_files[source_part] = source_zip.read(source_part)

        for child in list(source_body):
            if child.tag == f"{{{W_NS}}}sectPr":
                continue
            new_child = copy.deepcopy(child)
            for element in new_child.iter():
                for attribute in (f"{{{R_NS}}}id", f"{{{R_NS}}}embed", f"{{{R_NS}}}link"):
                    if element.get(attribute) in relation_map:
                        element.set(attribute, relation_map[element.get(attribute)])
            template_body.insert(len(template_body) - 1 if template_sect_pr is not None else len(template_body), new_child)

        template_files[DOCUMENT_PATH] = etree.tostring(template_doc, xml_declaration=True, encoding="UTF-8", standalone=True)
        template_files[SOURCE_REL_PATH] = etree.tostring(template_rels, xml_declaration=True, encoding="UTF-8", standalone=True)

        # Add content types for transferred media if the template did not need them.
        content_types = etree.fromstring(template_files[CONTENT_TYPES_PATH])
        source_content_types = etree.fromstring(source_zip.read(CONTENT_TYPES_PATH))
        existing_defaults = {node.get("Extension") for node in content_types.findall("ct:Default", NS)}
        for node in source_content_types.findall("ct:Default", NS):
            if node.get("Extension") not in existing_defaults:
                content_types.append(copy.deepcopy(node))
                existing_defaults.add(node.get("Extension"))
        template_files[CONTENT_TYPES_PATH] = etree.tostring(content_types, xml_declaration=True, encoding="UTF-8", standalone=True)

    with zipfile.ZipFile(destination, "w", zipfile.ZIP_DEFLATED) as output_zip:
        for name, contents in template_files.items():
            output_zip.writestr(name, contents)


def apply_template_format(path: Path) -> None:
    doc = Document(path)
    section = doc.sections[0]
    section.page_width = Inches(8.5)
    section.page_height = Inches(11)
    section.left_margin = Inches(1)
    section.right_margin = Inches(1)
    section.top_margin = Inches(1)
    section.bottom_margin = Inches(1)
    section.header_distance = Inches(0.49)
    section.footer_distance = Inches(0.49)

    normal = doc.styles["Normal"]
    normal.font.name = "Times New Roman"
    normal._element.rPr.rFonts.set(qn("w:eastAsia"), "Times New Roman")
    normal.font.size = Pt(11)
    normal.font.color.rgb = RGBColor(0, 0, 0)
    normal.paragraph_format.space_after = Pt(8)
    normal.paragraph_format.line_spacing = 1.15

    title = doc.styles["Title"]
    title.font.name = "Times New Roman"
    title._element.rPr.rFonts.set(qn("w:eastAsia"), "Times New Roman")
    title.font.size = Pt(16)
    title.font.bold = True
    title.font.color.rgb = RGBColor(0, 0, 0)
    title.paragraph_format.space_after = Pt(8)
    title.paragraph_format.line_spacing = 1.0

    for style_name, size, before, after in (("Heading 1", 14, 10, 4), ("Heading 2", 12, 8, 4), ("Heading 3", 11, 6, 3)):
        style = doc.styles[style_name]
        style.font.name = "Times New Roman"
        style._element.rPr.rFonts.set(qn("w:eastAsia"), "Times New Roman")
        style.font.size = Pt(size)
        style.font.bold = True
        style.font.color.rgb = RGBColor(0, 0, 0)
        style.paragraph_format.space_before = Pt(before)
        style.paragraph_format.space_after = Pt(after)
        style.paragraph_format.keep_with_next = True

    for paragraph_index, paragraph in enumerate(doc.paragraphs):
        text = paragraph.text.strip()
        if not text:
            continue
        paragraph.paragraph_format.widow_control = True
        if paragraph_index == 0:
            paragraph.style = doc.styles["Title"]
            paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
            paragraph.paragraph_format.space_after = Pt(8)
            paragraph.paragraph_format.line_spacing = 1.0
            for run in paragraph.runs:
                set_font(run, 16, bold=True)
            continue
        if paragraph.style.name == "Title":
            paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
            for run in paragraph.runs:
                set_font(run, 16, bold=True)
            continue
        if paragraph.style.name in {"Heading 1", "Heading 2", "Heading 3"}:
            for run in paragraph.runs:
                set_font(run, {"Heading 1": 14, "Heading 2": 12, "Heading 3": 11}[paragraph.style.name], bold=True)
            continue
        # The template places author/contact details directly below the centered title.
        if paragraph._p.getprevious() is not None and paragraph_index < 6:
            paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
            paragraph.paragraph_format.space_after = Pt(3)
            paragraph.paragraph_format.line_spacing = 1.0
        # Table and figure captions use compact, centered, italic text in the template.
        if text.startswith(("Table ", "Fig. ", "Figure ")):
            paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
            paragraph.paragraph_format.space_before = Pt(3)
            paragraph.paragraph_format.space_after = Pt(6)
            paragraph.paragraph_format.line_spacing = 1.0
            for run in paragraph.runs:
                set_font(run, 10.5, italic=True)
            continue
        for run in paragraph.runs:
            set_font(run, 11)

    for table in doc.tables:
        table.style = "Table Grid"
        table.alignment = WD_TABLE_ALIGNMENT.CENTER
        table.autofit = True
        if table.rows:
            set_repeat_table_header(table.rows[0])
        for row_index, row in enumerate(table.rows):
            for cell in row.cells:
                cell.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER
                set_cell_borders(cell)
                if row_index == 0:
                    set_cell_shading(cell, "D9E2F3")
                elif row_index % 2 == 0:
                    set_cell_shading(cell, "F2F2F2")
                for paragraph in cell.paragraphs:
                    paragraph.paragraph_format.space_after = Pt(2)
                    paragraph.paragraph_format.line_spacing = 1.0
                    for run in paragraph.runs:
                        set_font(run, 10, bold=True if row_index == 0 else None)
    doc.core_properties.title = "A Microservices Based Home Energy Tracker for Real Time Monitoring Intelligent Alerting and AI Driven Energy Insights"
    doc.core_properties.subject = "Review 2 Research Paper"
    doc.core_properties.keywords = "home energy, microservices, IoT, Wokwi, InfluxDB, energy analytics"
    doc.core_properties.comments = "Formatted using the supplied project documentation template."
    doc.save(path)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--template", type=Path, required=True)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    copy_body_and_images(args.template, args.source, args.output)
    apply_template_format(args.output)


if __name__ == "__main__":
    main()
