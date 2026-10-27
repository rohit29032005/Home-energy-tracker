"""Apply a narrowly scoped native-OMML equation formatting patch.

Only the two raw mathematical expressions in the REFIT preprocessing
paragraph are replaced.  All surrounding paragraph XML is preserved.
"""

from __future__ import annotations

import sys
from copy import deepcopy
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

from lxml import etree


W_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
M_NS = "http://schemas.openxmlformats.org/officeDocument/2006/math"
NS = {"w": W_NS, "m": M_NS}


def qn(namespace: str, tag: str) -> str:
    return f"{{{namespace}}}{tag}"


def m(tag: str) -> etree._Element:
    return etree.Element(qn(M_NS, tag))


def w_run(text: str) -> etree._Element:
    run = etree.Element(qn(W_NS, "r"))
    node = etree.SubElement(run, qn(W_NS, "t"))
    if text.startswith(" ") or text.endswith(" "):
        node.set("{http://www.w3.org/XML/1998/namespace}space", "preserve")
    node.text = text
    return run


def math_run(text: str, *, roman: bool = False) -> etree._Element:
    run = m("r")
    if roman:
        rpr = etree.SubElement(run, qn(M_NS, "rPr"))
        etree.SubElement(rpr, qn(M_NS, "nor"))
    node = etree.SubElement(run, qn(M_NS, "t"))
    node.text = text
    return run


def subscript(base: str, sub: str, *, sub_roman: bool = False) -> etree._Element:
    element = m("sSub")
    base_node = etree.SubElement(element, qn(M_NS, "e"))
    base_node.append(math_run(base))
    sub_node = etree.SubElement(element, qn(M_NS, "sub"))
    sub_node.append(math_run(sub, roman=sub_roman))
    return element


def fraction(numerator_children: list[etree._Element], denominator: str) -> etree._Element:
    element = m("f")
    numerator = etree.SubElement(element, qn(M_NS, "num"))
    for child in numerator_children:
        numerator.append(child)
    denominator_node = etree.SubElement(element, qn(M_NS, "den"))
    denominator_node.append(math_run(denominator, roman=True))
    return element


def energy_equation() -> etree._Element:
    equation = m("oMath")
    equation.append(subscript("E", "kWh", sub_roman=True))
    equation.append(math_run(" = "))
    equation.append(subscript("P", "start,W", sub_roman=True))
    equation.append(math_run(" × "))
    equation.append(subscript("Δt", "s", sub_roman=True))
    equation.append(math_run(" / "))
    equation.append(math_run("3,600,000", roman=True))
    return equation


def interval_condition() -> etree._Element:
    equation = m("oMath")
    equation.append(math_run("0 < "))
    equation.append(subscript("Δt", "s", sub_roman=True))
    equation.append(math_run(" ≤ 16 "))
    equation.append(math_run("s", roman=True))
    return equation


def text_of(element: etree._Element) -> str:
    return "".join(element.xpath(".//w:t/text()", namespaces=NS))


def patch_document_xml(xml: bytes) -> bytes:
    root = etree.fromstring(xml)
    expected = "E_kWh = P_start,W * delta_t,s / 3,600,000 Time intervals are integrated only for $0 < \\delta_t \\leq 16$ s."
    candidates = root.xpath(".//w:p", namespaces=NS)
    matches = [p for p in candidates if expected in text_of(p)]
    if len(matches) != 1:
        raise ValueError(f"Expected exactly one target paragraph; found {len(matches)}")
    paragraph = matches[0]
    children = list(paragraph)
    start = next(
        idx
        for idx, child in enumerate(children)
        if child.tag == qn(W_NS, "r") and text_of(child) == "E_kWh"
    )
    end = next(
        idx
        for idx, child in enumerate(children[start:], start)
        if child.tag == qn(W_NS, "r") and text_of(child).startswith(" 16$ s. No longer cross gap periods")
    )
    tail = text_of(children[end])
    if not tail.startswith(" 16$ s."):
        raise ValueError("Unexpected interval-condition tail")
    replacement = [
        energy_equation(),
        w_run(" Time intervals are integrated only for "),
        interval_condition(),
        w_run(tail[len(" 16$ s") :]),
    ]
    for child in children[start : end + 1]:
        paragraph.remove(child)
    for offset, child in enumerate(replacement):
        paragraph.insert(start + offset, child)
    return etree.tostring(root, xml_declaration=True, encoding="UTF-8", standalone=True)


def main() -> None:
    if len(sys.argv) != 3:
        raise SystemExit("Usage: format_equations.py INPUT.docx OUTPUT.docx")
    source = Path(sys.argv[1])
    destination = Path(sys.argv[2])
    destination.parent.mkdir(parents=True, exist_ok=True)
    with ZipFile(source, "r") as source_zip, ZipFile(destination, "w", ZIP_DEFLATED) as output_zip:
        for info in source_zip.infolist():
            data = source_zip.read(info.filename)
            if info.filename == "word/document.xml":
                data = patch_document_xml(data)
            output_zip.writestr(info, data)


if __name__ == "__main__":
    main()
