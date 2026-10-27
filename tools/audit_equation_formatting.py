"""Static integrity audit for the equation-formatting-only deliverables."""

from __future__ import annotations

import sys
from pathlib import Path
from zipfile import ZipFile

from lxml import etree


W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
M = "http://schemas.openxmlformats.org/officeDocument/2006/math"
NS = {"w": W, "m": M}


def canonical(node: etree._Element) -> bytes:
    return etree.tostring(node, method="c14n")


def main() -> None:
    if len(sys.argv) != 3:
        raise SystemExit("Usage: audit_equation_formatting.py SOURCE.docx FINAL.docx")
    source = Path(sys.argv[1])
    final = Path(sys.argv[2])

    with ZipFile(source) as src_zip, ZipFile(final) as out_zip:
        src_names = set(src_zip.namelist())
        out_names = set(out_zip.namelist())
        assert src_names == out_names, "DOCX package entry set changed"
        changed_entries = []
        for name in sorted(src_names):
            if src_zip.read(name) != out_zip.read(name):
                changed_entries.append(name)
        assert changed_entries == ["word/document.xml"], changed_entries
        assert src_zip.testzip() is None and out_zip.testzip() is None, "ZIP integrity failure"
        src_root = etree.fromstring(src_zip.read("word/document.xml"))
        out_root = etree.fromstring(out_zip.read("word/document.xml"))

    src_paras = src_root.xpath(".//w:body//w:p", namespaces=NS)
    out_paras = out_root.xpath(".//w:body//w:p", namespaces=NS)
    assert len(src_paras) == len(out_paras), "Paragraph count changed"
    target_indices = []
    for index, (src_p, out_p) in enumerate(zip(src_paras, out_paras)):
        if canonical(src_p) != canonical(out_p):
            target_indices.append(index)
    assert len(target_indices) == 1, target_indices
    target = target_indices[0]

    src_target_text = "".join(src_paras[target].xpath(".//w:t/text()", namespaces=NS))
    assert "E_kWh = P_start,W * delta_t,s / 3,600,000" in src_target_text
    assert "$0 < \\delta_t \\leq 16$ s" in src_target_text

    out_target = out_paras[target]
    math_objects = out_target.xpath("./m:oMath", namespaces=NS)
    assert len(math_objects) == 2, len(math_objects)
    math_text = ["".join(obj.xpath(".//m:t/text()", namespaces=NS)) for obj in math_objects]
    assert math_text == [
        "EkWh = Pstart,W × Δts / 3,600,000",
        "0 < Δts ≤ 16 s",
    ], math_text
    subscripts = out_target.xpath(".//m:sSub", namespaces=NS)
    assert len(subscripts) == 4, len(subscripts)
    subscript_pairs = [
        (
            "".join(node.xpath("./m:e//m:t/text()", namespaces=NS)),
            "".join(node.xpath("./m:sub//m:t/text()", namespaces=NS)),
        )
        for node in subscripts
    ]
    assert subscript_pairs == [
        ("E", "kWh"),
        ("P", "start,W"),
        ("Δt", "s"),
        ("Δt", "s"),
    ], subscript_pairs

    raw_commands = out_root.xpath(".//w:t/text()", namespaces=NS)
    raw_text = "".join(raw_commands)
    assert "E_kWh = P_start,W * delta_t,s / 3,600,000" not in raw_text
    assert "$0 < \\delta_t \\leq 16$ s" not in raw_text

    src_tables = src_root.xpath(".//w:body//w:tbl", namespaces=NS)
    out_tables = out_root.xpath(".//w:body//w:tbl", namespaces=NS)
    assert len(src_tables) == len(out_tables), "Table count changed"
    assert all(canonical(a) == canonical(b) for a, b in zip(src_tables, out_tables)), "Table content changed"

    print("ZIP integrity: PASS")
    print("Changed package entries: word/document.xml only")
    print(f"Body paragraphs: {len(src_paras)}; altered paragraph index: {target}")
    print(f"Tables: {len(src_tables)}; all unchanged")
    print("Native OMML objects in target paragraph: 2")
    print("Mathematical meaning retained: PASS")
    print("No raw target formula/LaTeX remains as ordinary Word text: PASS")


if __name__ == "__main__":
    main()
