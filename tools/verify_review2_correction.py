"""Regression checks for the Review-2 targeted correction."""

from __future__ import annotations

import hashlib
import re
import sys
import zipfile
from pathlib import Path

from docx import Document
from pypdf import PdfReader


SOURCE = Path(
    r"C:\Users\anju2\Desktop\Home-Energy-Tracker\artifacts\review2_work\Home_Energy_Tracker_Review2_Final.docx"
)
OUTPUT = Path(
    r"C:\Users\anju2\Desktop\Home-Energy-Tracker\artifacts\review2_correction\Home_Energy_Tracker_Review2_Final_Corrected.docx"
)
PDF = OUTPUT.with_suffix(".pdf")

EXPECTED_CHANGED_PARAGRAPHS = {11, 13, 14, 15, 17, 19, 44, 139}
EXPECTED_TITLE = (
    "A Microservices-Based Home Energy Tracker for Event-Driven Monitoring, "
    "Deduplicated Alerting, and ML-Based Anomaly Detection"
)
AUTHOR_MARKERS = (
    "Rohit Shrivastava",
    "Harsh Gupta",
    "Anshika Rai",
    "Syamasudha Veeragandham",
    "Vellore Institute of Technology",
)


def cells(document: Document) -> list[str]:
    return [cell.text for table in document.tables for row in table.rows for cell in row.cells]


def media_hashes(path: Path) -> dict[str, str]:
    with zipfile.ZipFile(path) as archive:
        return {
            entry: hashlib.sha256(archive.read(entry)).hexdigest()
            for entry in archive.namelist()
            if entry.startswith("word/media/")
        }


def body_before_references(document: Document) -> str:
    records = []
    for paragraph in document.paragraphs:
        if paragraph.text.strip() == "References":
            break
        records.append(paragraph.text)
    return "\n".join(records)


def citation_numbers(text: str) -> set[int]:
    # Each bracketed number gets parsed; this handles individual citations and ranges.
    return {int(value) for value in re.findall(r"\[(\d{1,2})\]", text)}


def native_equation_count(path: Path) -> int:
    with zipfile.ZipFile(path) as archive:
        document_xml = archive.read("word/document.xml")
    return document_xml.count(b"<m:oMath")


def main() -> None:
    source = Document(SOURCE)
    output = Document(OUTPUT)

    if len(source.paragraphs) != len(output.paragraphs):
        raise AssertionError("Paragraph count changed")
    changed = {
        index
        for index, (before, after) in enumerate(zip(source.paragraphs, output.paragraphs))
        if before.text != after.text
    }
    if changed != EXPECTED_CHANGED_PARAGRAPHS:
        raise AssertionError(f"Unexpected paragraph changes: {sorted(changed)}")
    for index, (before, after) in enumerate(zip(source.paragraphs, output.paragraphs)):
        if index not in EXPECTED_CHANGED_PARAGRAPHS and before.text != after.text:
            raise AssertionError(f"Unapproved text change at paragraph {index}")

    if source.tables.__len__() != output.tables.__len__() or cells(source) != cells(output):
        raise AssertionError("A table count or table-cell value changed")
    if media_hashes(SOURCE) != media_hashes(OUTPUT):
        raise AssertionError("Embedded figure media changed")
    if native_equation_count(SOURCE) != native_equation_count(OUTPUT):
        raise AssertionError("Native equation count changed")
    if [paragraph.text for paragraph in source.paragraphs[:10]] != [
        paragraph.text for paragraph in output.paragraphs[:10]
    ]:
        raise AssertionError("Title, author, affiliation, or abstract text changed")

    full_text = "\n".join(paragraph.text for paragraph in output.paragraphs)
    if EXPECTED_TITLE not in full_text:
        raise AssertionError("Title did not survive unchanged")
    for marker in AUTHOR_MARKERS:
        if marker not in full_text:
            raise AssertionError(f"Author or affiliation marker is missing: {marker}")

    references = [p.text for p in output.paragraphs if re.match(r"^\[\d+\]", p.text.strip())]
    if len(references) != 18:
        raise AssertionError(f"Expected 18 bibliography entries, found {len(references)}")
    reference_numbers = {int(re.match(r"^\[(\d+)\]", reference).group(1)) for reference in references}
    if reference_numbers != set(range(1, 19)):
        raise AssertionError(f"Unexpected bibliography sequence: {sorted(reference_numbers)}")

    citations = citation_numbers(body_before_references(output) + "\n" + "\n".join(cells(output)))
    if not citations.issubset(reference_numbers):
        raise AssertionError(f"Citation has no bibliography entry: {sorted(citations - reference_numbers)}")
    if "Dr. Karthika" in output.paragraphs[139].text:
        raise AssertionError("Honorific remains in Reference [11]")
    if "arXiv preprint arXiv:2404.04311" not in output.paragraphs[138].text:
        raise AssertionError("Reference [10] preprint status changed")
    if "10.15129/9ab14b0e-19ac-4279-938f-27f643078cec" not in output.paragraphs[134].text:
        raise AssertionError("Reference [6] changed")
    if "10.5281/zenodo.5063428" not in output.paragraphs[135].text:
        raise AssertionError("Reference [7] changed")

    required_headings = (
        "1. Introduction",
        "1.1 Research Objectives",
        "2. Related Work",
        "2.1 Research Gaps Identified",
        "Summary of Research Gaps",
        "3. Materials and Methods",
        "3.2 Proposed System Architecture",
        "4. Experimental Results and Discussion",
        "5. Limitations and Future Work",
        "6. Conclusion",
        "References",
    )
    paragraph_values = {paragraph.text.strip() for paragraph in output.paragraphs}
    missing_headings = [heading for heading in required_headings if heading not in paragraph_values]
    if missing_headings:
        raise AssertionError(f"Required headings missing: {missing_headings}")
    research_gap_count = sum(
        1 for paragraph in output.paragraphs if paragraph.text.strip().startswith("Research Gap ")
    )
    if research_gap_count != 3:
        raise AssertionError(f"Expected 3 research gaps, found {research_gap_count}")

    abstract_index = next(
        index
        for index, paragraph in enumerate(output.paragraphs)
        if paragraph.text.strip().lower().startswith("abstract")
    )
    abstract = re.sub(r"(?i)^abstract(?:—|-|:)?\s*", "", output.paragraphs[abstract_index].text.strip())
    abstract_words = len(re.findall(r"\b[\w'-]+\b", abstract))
    keywords_index = next(
        index
        for index, paragraph in enumerate(output.paragraphs)
        if paragraph.text.strip().lower().startswith("keywords")
    )
    keyword_paragraph = output.paragraphs[keywords_index].text
    keyword_text = re.sub(r"(?i)^keywords(?:—|-|:)?\s*", "", keyword_paragraph.strip())
    keyword_count = len([item for item in re.split(r"[;,]", keyword_text) if item.strip()])
    objectives_heading = next(
        index
        for index, paragraph in enumerate(output.paragraphs)
        if paragraph.text.strip().lower() == "1.1 research objectives"
    )
    next_major_heading = next(
        index
        for index, paragraph in enumerate(output.paragraphs[objectives_heading + 1 :], objectives_heading + 1)
        if paragraph.text.strip().lower() == "2. related work"
    )
    objective_count = sum(
        1
        for paragraph in output.paragraphs[objectives_heading + 1 : next_major_heading]
        if re.match(r"^[1-4][.]\s", paragraph.text.strip())
    )

    if not PDF.is_file():
        raise AssertionError("Final PDF has not been exported")
    pdf_reader = PdfReader(str(PDF))
    if len(pdf_reader.pages) != 12:
        raise AssertionError(f"Expected 12 PDF pages, found {len(pdf_reader.pages)}")
    first_page = pdf_reader.pages[0]
    width = float(first_page.mediabox.width)
    height = float(first_page.mediabox.height)
    if not (594 < width < 596 and 841 < height < 843):
        raise AssertionError(f"PDF paper size is not A4: {width} x {height}")
    pdf_text = "\n".join(page.extract_text() or "" for page in pdf_reader.pages)
    if "Fig. 1." not in pdf_text or "Fig. 2." not in pdf_text:
        raise AssertionError("A figure caption did not survive PDF export")

    print("PASS: targeted-diff regression checks")
    print(f"Paragraph changes: {sorted(changed)}")
    print(f"Tables unchanged: {len(output.tables)}")
    print(f"Figures/media unchanged: {len(media_hashes(OUTPUT))}")
    print(f"Native equations unchanged: {native_equation_count(OUTPUT)}")
    print(f"References: {len(references)} unique entries; citations resolve within [1]-[18]")
    print(f"Abstract words: {abstract_words}; keywords: {keyword_count}; objective markers: {objective_count}")
    print(f"Faculty-section check: {len(required_headings)} required headings; 3 research gaps")
    print(f"PDF check: {len(pdf_reader.pages)} A4 pages with both figure captions present")


if __name__ == "__main__":
    try:
        main()
    except Exception as error:  # pragma: no cover - invoked as a command-line verifier
        print(f"FAIL: {error}", file=sys.stderr)
        raise
