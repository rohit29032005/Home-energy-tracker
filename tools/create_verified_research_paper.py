from __future__ import annotations

from pathlib import Path
from typing import Iterable, Sequence

from PIL import Image, ImageDraw, ImageFont
from docx import Document
from docx.enum.section import WD_SECTION
from docx.enum.table import WD_CELL_VERTICAL_ALIGNMENT, WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_BREAK, WD_LINE_SPACING
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Inches, Pt, RGBColor


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "research-output"
FIGURES = OUTPUT / "figures"
PAPER_PATH = OUTPUT / "Home_Energy_Tracker_Final_Verified_Research_Paper.docx"
AUDIT_PATH = OUTPUT / "Paper_Revision_Evidence_Audit_Pack.docx"
CM_PATH = ROOT / "evidence" / "04_ml_evaluation" / "confusion_matrix_random_forest.png"


# ---------- Low-level document formatting helpers ----------

def set_cell_shading(cell, fill: str) -> None:
    tc_pr = cell._tc.get_or_add_tcPr()
    shd = tc_pr.find(qn("w:shd"))
    if shd is None:
        shd = OxmlElement("w:shd")
        tc_pr.append(shd)
    shd.set(qn("w:fill"), fill)


def set_cell_margins(cell, top=80, start=80, bottom=80, end=80) -> None:
    tc = cell._tc
    tc_pr = tc.get_or_add_tcPr()
    tc_mar = tc_pr.first_child_found_in("w:tcMar")
    if tc_mar is None:
        tc_mar = OxmlElement("w:tcMar")
        tc_pr.append(tc_mar)
    for m, v in (("top", top), ("start", start), ("bottom", bottom), ("end", end)):
        node = tc_mar.find(qn(f"w:{m}"))
        if node is None:
            node = OxmlElement(f"w:{m}")
            tc_mar.append(node)
        node.set(qn("w:w"), str(v))
        node.set(qn("w:type"), "dxa")


def set_repeat_table_header(row) -> None:
    tr_pr = row._tr.get_or_add_trPr()
    tbl_header = OxmlElement("w:tblHeader")
    tbl_header.set(qn("w:val"), "true")
    tr_pr.append(tbl_header)


def set_table_widths(table, widths: Sequence[float]) -> None:
    for row in table.rows:
        for index, width in enumerate(widths):
            if index < len(row.cells):
                row.cells[index].width = Inches(width)


def set_keep_with_next(paragraph) -> None:
    p_pr = paragraph._p.get_or_add_pPr()
    node = OxmlElement("w:keepNext")
    p_pr.append(node)


def set_keep_together(paragraph) -> None:
    p_pr = paragraph._p.get_or_add_pPr()
    node = OxmlElement("w:keepLines")
    p_pr.append(node)


def set_run_font(run, name: str = "Times New Roman", size: float | None = None,
                 bold: bool | None = None, italic: bool | None = None,
                 color: str | None = None) -> None:
    run.font.name = name
    run._element.rPr.rFonts.set(qn("w:eastAsia"), name)
    if size is not None:
        run.font.size = Pt(size)
    if bold is not None:
        run.bold = bold
    if italic is not None:
        run.italic = italic
    if color:
        run.font.color.rgb = RGBColor.from_string(color)


def configure_document(doc: Document, audit: bool = False) -> None:
    section = doc.sections[0]
    section.top_margin = Cm(1.65)
    section.bottom_margin = Cm(1.55)
    section.left_margin = Cm(1.7)
    section.right_margin = Cm(1.7)
    section.header_distance = Cm(0.7)
    section.footer_distance = Cm(0.7)

    normal = doc.styles["Normal"]
    normal.font.name = "Times New Roman"
    normal._element.rPr.rFonts.set(qn("w:eastAsia"), "Times New Roman")
    normal.font.size = Pt(10 if not audit else 9.5)
    normal.paragraph_format.space_after = Pt(5)
    normal.paragraph_format.line_spacing = 1.08
    normal.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY

    for name, size, color in (
        ("Title", 15, "17365D"),
        ("Heading 1", 12, "17365D"),
        ("Heading 2", 10.5, "17365D"),
        ("Heading 3", 10, "17365D"),
    ):
        style = doc.styles[name]
        style.font.name = "Times New Roman"
        style._element.rPr.rFonts.set(qn("w:eastAsia"), "Times New Roman")
        style.font.size = Pt(size)
        style.font.bold = True
        style.font.color.rgb = RGBColor.from_string(color)
        style.paragraph_format.space_before = Pt(10 if name == "Heading 1" else 6)
        style.paragraph_format.space_after = Pt(3)

    header = section.header.paragraphs[0]
    header.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = header.add_run("Home Energy Tracker — Evidence-Based Final Manuscript")
    set_run_font(run, size=8, color="666666")
    border = OxmlElement("w:pBdr")
    bottom = OxmlElement("w:bottom")
    bottom.set(qn("w:val"), "single")
    bottom.set(qn("w:sz"), "4")
    bottom.set(qn("w:space"), "3")
    bottom.set(qn("w:color"), "B7C9DC")
    border.append(bottom)
    header._p.get_or_add_pPr().append(border)

    footer = section.footer.paragraphs[0]
    footer.alignment = WD_ALIGN_PARAGRAPH.CENTER
    frun = footer.add_run("Local implementation and experimental evidence reviewed: 5 October 2026")
    set_run_font(frun, size=8, color="666666")


def para(doc: Document, text: str = "", *, bold_prefix: str | None = None,
         italic: bool = False, size: float | None = None, align=None,
         before: float | None = None, after: float | None = None) -> object:
    p = doc.add_paragraph()
    if align is not None:
        p.alignment = align
    if before is not None:
        p.paragraph_format.space_before = Pt(before)
    if after is not None:
        p.paragraph_format.space_after = Pt(after)
    if bold_prefix and text.startswith(bold_prefix):
        r1 = p.add_run(bold_prefix)
        set_run_font(r1, size=size, bold=True)
        r2 = p.add_run(text[len(bold_prefix):])
        set_run_font(r2, size=size, italic=italic)
    else:
        r = p.add_run(text)
        set_run_font(r, size=size, italic=italic)
    set_keep_together(p)
    return p


def heading(doc: Document, text: str, level: int = 1):
    p = doc.add_paragraph(style=f"Heading {level}")
    p.alignment = WD_ALIGN_PARAGRAPH.LEFT
    r = p.add_run(text)
    set_run_font(r, size={1: 12, 2: 10.5, 3: 10}.get(level, 10), bold=True, color="17365D")
    set_keep_with_next(p)
    return p


def caption(doc: Document, text: str) -> object:
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_before = Pt(2)
    p.paragraph_format.space_after = Pt(6)
    r = p.add_run(text)
    set_run_font(r, size=8.5, italic=True)
    return p


def add_table(doc: Document, headers: Sequence[str], rows: Sequence[Sequence[str]],
              widths: Sequence[float] | None = None, font_size: float = 8.1) -> object:
    table = doc.add_table(rows=1, cols=len(headers))
    table.style = "Table Grid"
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    table.autofit = False
    header_cells = table.rows[0].cells
    for i, header_text in enumerate(headers):
        cell = header_cells[i]
        cell.text = ""
        set_cell_shading(cell, "17365D")
        set_cell_margins(cell)
        cell.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER
        p = cell.paragraphs[0]
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        r = p.add_run(header_text)
        set_run_font(r, size=font_size, bold=True, color="FFFFFF")
    set_repeat_table_header(table.rows[0])

    for row_index, row_data in enumerate(rows):
        cells = table.add_row().cells
        for col_index, value in enumerate(row_data):
            cell = cells[col_index]
            cell.text = ""
            if row_index % 2 == 1:
                set_cell_shading(cell, "EEF3F8")
            set_cell_margins(cell)
            cell.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.TOP
            p = cell.paragraphs[0]
            p.alignment = WD_ALIGN_PARAGRAPH.LEFT
            p.paragraph_format.space_after = Pt(0)
            r = p.add_run(str(value))
            set_run_font(r, size=font_size)
    if widths:
        set_table_widths(table, widths)
    doc.add_paragraph().paragraph_format.space_after = Pt(1)
    return table


def bullet(doc: Document, text: str, level: int = 0) -> object:
    p = doc.add_paragraph(style="List Bullet" if level == 0 else "List Bullet 2")
    p.paragraph_format.left_indent = Cm(0.45 + 0.45 * level)
    p.paragraph_format.first_line_indent = Cm(-0.25)
    r = p.add_run(text)
    set_run_font(r, size=9.5)
    return p


def numbered(doc: Document, text: str) -> object:
    p = doc.add_paragraph(style="List Number")
    p.paragraph_format.left_indent = Cm(0.6)
    p.paragraph_format.first_line_indent = Cm(-0.35)
    r = p.add_run(text)
    set_run_font(r, size=9.5)
    return p


def add_figure(doc: Document, path: Path, width: float, caption_text: str) -> None:
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = p.add_run()
    r.add_picture(str(path), width=Inches(width))
    caption(doc, caption_text)


def page_break(doc: Document) -> None:
    doc.add_paragraph().add_run().add_break(WD_BREAK.PAGE)


# ---------- Publication-quality source figures ----------

def font(size: int, bold: bool = False):
    candidates = [
        r"C:\Windows\Fonts\timesbd.ttf" if bold else r"C:\Windows\Fonts\times.ttf",
        r"C:\Windows\Fonts\arialbd.ttf" if bold else r"C:\Windows\Fonts\arial.ttf",
    ]
    for candidate in candidates:
        if Path(candidate).exists():
            return ImageFont.truetype(candidate, size)
    return ImageFont.load_default()


def pcolor(value: str) -> str:
    """Pillow accepts CSS hex only with a leading '#'."""
    return f"#{value}" if len(value) == 6 and all(char in "0123456789abcdefABCDEF" for char in value) else value


def text_box(draw, xy, lines: Sequence[str], *, fill="F7FAFD", outline="2F5D8A",
             title_fill="DCEAF7", line_color="1D1D1D", title=False, size=30):
    x1, y1, x2, y2 = xy
    draw.rounded_rectangle((x1, y1, x2, y2), radius=16, fill=pcolor(fill), outline=pcolor(outline), width=4)
    if title:
        draw.rounded_rectangle((x1, y1, x2, y1 + 50), radius=16, fill=pcolor(title_fill), outline=pcolor(outline), width=0)
    f = font(size, bold=False)
    fbold = font(size, bold=True)
    spacing = 8
    total_h = len(lines) * (size + spacing) - spacing
    y = y1 + (y2 - y1 - total_h) / 2
    for i, line in enumerate(lines):
        active = fbold if i == 0 and title else f
        bbox = draw.textbbox((0, 0), line, font=active)
        tx = x1 + ((x2 - x1) - (bbox[2] - bbox[0])) / 2
        draw.text((tx, y), line, font=active, fill=pcolor(line_color))
        y += size + spacing


def arrow(draw, p1, p2, *, fill="2F5D8A", width=5, label: str | None = None, label_offset=(0, 0)):
    draw.line((p1, p2), fill=pcolor(fill), width=width)
    x1, y1 = p1
    x2, y2 = p2
    import math
    angle = math.atan2(y2 - y1, x2 - x1)
    head = 18
    left = (x2 - head * math.cos(angle - math.pi / 6), y2 - head * math.sin(angle - math.pi / 6))
    right = (x2 - head * math.cos(angle + math.pi / 6), y2 - head * math.sin(angle + math.pi / 6))
    draw.polygon([(x2, y2), left, right], fill=pcolor(fill))
    if label:
        f = font(22, bold=False)
        mx = (x1 + x2) / 2 + label_offset[0]
        my = (y1 + y2) / 2 + label_offset[1]
        bbox = draw.textbbox((0, 0), label, font=f)
        pad = 5
        draw.rectangle((mx - (bbox[2]-bbox[0])/2-pad, my - (bbox[3]-bbox[1])/2-pad,
                        mx + (bbox[2]-bbox[0])/2+pad, my + (bbox[3]-bbox[1])/2+pad), fill=pcolor("FFFFFF"))
        draw.text((mx - (bbox[2]-bbox[0])/2, my - (bbox[3]-bbox[1])/2), label, font=f, fill=pcolor("334E68"))


def draw_architecture(path: Path) -> None:
    image = Image.new("RGB", (2200, 1420), pcolor("FFFFFF"))
    draw = ImageDraw.Draw(image)
    draw.text((80, 42), "FINAL SYSTEM ARCHITECTURE — LOCAL EVALUATED DEPLOYMENT", font=font(40, True), fill=pcolor("17365D"))
    draw.line((80, 105, 2120, 105), fill=pcolor("B7C9DC"), width=3)

    layers = [
        (150, "Telemetry, client and identity layer"),
        (380, "Gateway boundary"),
        (610, "Event-processing layer"),
        (970, "Storage, alerts and monitoring layer"),
    ]
    for y, label in layers:
        draw.text((85, y), label, font=font(26, True), fill=pcolor("496C89"))
        draw.line((85, y + 40, 2110, y + 40), fill=pcolor("D6E1EB"), width=2)

    wokwi = (160, 225, 575, 365)
    keycloak = (875, 225, 1325, 365)
    frontend = (1625, 225, 2040, 365)
    gateway = (760, 455, 1440, 605)
    ingestion = (190, 710, 640, 850)
    kafka = (875, 700, 1325, 870)
    usage = (1560, 675, 2040, 810)
    ml = (1560, 855, 2040, 990)
    prometheus = (145, 1065, 580, 1200)
    insight = (640, 1065, 1050, 1200)
    alert = (1110, 1065, 1500, 1200)
    influx = (1560, 1065, 2040, 1200)
    mysql = (1020, 1270, 1450, 1390)
    mailpit = (1580, 1270, 2040, 1390)

    text_box(draw, wokwi, ["Wokwi ESP32", "simulated telemetry", "device token"], title=True, size=34)
    text_box(draw, keycloak, ["Keycloak", "JWT issuance and roles"], title=True, size=34)
    text_box(draw, frontend, ["React dashboard", "authenticated API use"], title=True, size=34)
    text_box(draw, gateway, ["API Gateway", "JWT / role validation • ownership", "device-token ingestion check"], fill="F2F7FC", outline="17365D", title=True, size=34)
    text_box(draw, ingestion, ["Ingestion Service", "validate payload", "publish energy-usage"], title=True, size=33)
    text_box(draw, kafka, ["Apache Kafka", "energy-usage", "energy-alerts / anomaly-results"], fill="F2F7FC", outline="17365D", title=True, size=33)
    text_box(draw, usage, ["Usage Service", "write usage / emit threshold event"], title=True, size=32)
    text_box(draw, ml, ["ML Inference Service", "Random Forest / anomaly result"], title=True, size=31)
    text_box(draw, prometheus, ["Prometheus + Grafana", "Actuator and ML metrics", "local dashboards"], title=True, size=31)
    text_box(draw, insight, ["Insight Service", "query InfluxDB", "forecast • ranking • standby"], title=True, size=29)
    text_box(draw, alert, ["Alert Service", "15-minute deduplication", "notification attempt"], title=True, size=31)
    text_box(draw, influx, ["InfluxDB", "timestamped usage series"], title=True, size=33)
    text_box(draw, mysql, ["MySQL", "users • devices • alerts"], title=True, size=32)
    text_box(draw, mailpit, ["Mailpit", "local mail capture"], title=True, size=33)

    arrow(draw, (575, 295), (760, 525), label="telemetry", label_offset=(-8, -28))
    arrow(draw, (1100, 365), (1100, 455), label="JWT", label_offset=(65, 0))
    arrow(draw, (1625, 295), (1440, 525), label="protected APIs", label_offset=(40, -20))
    arrow(draw, (760, 535), (640, 780), label="route", label_offset=(-36, -5))
    arrow(draw, (640, 780), (875, 780), label="energy-usage", label_offset=(0, -28))
    arrow(draw, (1325, 760), (1560, 742), label="consume", label_offset=(0, -28))
    arrow(draw, (1325, 815), (1560, 922), label="consume", label_offset=(0, 22))
    arrow(draw, (1800, 810), (1800, 1065), label="write", label_offset=(78, 0))
    arrow(draw, (1325, 850), (1305, 1065), label="events", label_offset=(95, 0))
    arrow(draw, (1305, 1200), (1235, 1270), label="persist", label_offset=(-80, -8))
    arrow(draw, (1500, 1130), (1810, 1270), label="SMTP", label_offset=(28, -22))
    # A single dashed monitoring connector prevents a visually misleading data-flow path.
    draw.line((760, 565, 580, 1130), fill=pcolor("7B8FA1"), width=3)
    draw.text((210, 1015), "scrapes gateway, Java services and ML service", font=font(22), fill=pcolor("5B7083"))
    image.save(path)


def draw_workflow(path: Path) -> None:
    image = Image.new("RGB", (2200, 1120), pcolor("FFFFFF"))
    draw = ImageDraw.Draw(image)
    draw.text((80, 42), "EVIDENCE-ORIENTED OPERATIONAL WORKFLOW", font=font(38, True), fill=pcolor("17365D"))
    draw.line((80, 98, 2120, 98), fill=pcolor("B7C9DC"), width=3)

    boxes = [
        ((120, 250, 450, 415), ["1. Generate input", "Wokwi ESP32 or", "controlled REST telemetry"]),
        ((530, 250, 860, 415), ["2. Authenticate / validate", "JWT or machine token", "payload validation"]),
        ((940, 250, 1270, 415), ["3. Publish event", "Ingestion Service", "Kafka: energy-usage"]),
        ((1350, 160, 1680, 325), ["4a. Persist and analyse", "Usage → InfluxDB", "Insight Service"]),
        ((1350, 430, 1680, 595), ["4b. Classify", "Random Forest", "Kafka: anomaly-results"]),
        ((1760, 295, 2090, 460), ["5. Alert and expose", "deduplicate / persist", "dashboard + Mailpit"]),
    ]
    for xy, lines in boxes:
        text_box(draw, xy, lines, title=True, size=27)
    arrow(draw, (450, 332), (530, 332))
    arrow(draw, (860, 332), (940, 332))
    arrow(draw, (1270, 315), (1350, 240))
    arrow(draw, (1270, 365), (1350, 510))
    arrow(draw, (1680, 242), (1760, 340), label="threshold event", label_offset=(10, -35))
    arrow(draw, (1680, 510), (1760, 410), label="anomaly event", label_offset=(10, 30))

    # Evaluation band
    draw.rounded_rectangle((120, 720, 2080, 990), radius=16, fill=pcolor("F2F7FC"), outline=pcolor("2F5D8A"), width=4)
    draw.text((165, 755), "Evaluation and evidence layer", font=font(28, True), fill=pcolor("17365D"))
    evals = [
        (200, "Offline ML evaluation", "chronological split; held-out metrics"),
        (650, "Security validation", "8 controlled API cases"),
        (1060, "Load validation", "k6 local ingestion scenario"),
        (1450, "Fault scenarios", "manual restoration after service stop"),
        (1800, "E2E verification", "synthetic workflow and Mailpit capture"),
    ]
    for x, first, second in evals:
        draw.rounded_rectangle((x - 130, 830, x + 130, 945), radius=12, fill=pcolor("FFFFFF"), outline=pcolor("86A8C5"), width=3)
        f1 = font(20, True)
        f2 = font(18)
        y = 850
        for line in first.split(";"):
            bbox = draw.textbbox((0, 0), line, font=f1)
            draw.text((x - (bbox[2]-bbox[0])/2, y), line, font=f1, fill=pcolor("1D3557"))
            y += 25
        for line in second.split(";"):
            bbox = draw.textbbox((0, 0), line, font=f2)
            draw.text((x - (bbox[2]-bbox[0])/2, y+5), line, font=f2, fill=pcolor("334E68"))
            y += 22
    image.save(path)


def generate_figures() -> tuple[Path, Path]:
    FIGURES.mkdir(parents=True, exist_ok=True)
    architecture = FIGURES / "final_system_architecture.png"
    workflow = FIGURES / "evidence_oriented_workflow.png"
    draw_architecture(architecture)
    draw_workflow(workflow)
    return architecture, workflow


# ---------- Paper content ----------

def title_block(doc: Document) -> None:
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_after = Pt(9)
    run = p.add_run("An Event-Driven Microservices Home Energy Tracker with Gateway Authentication and ML-Based Anomaly Detection")
    set_run_font(run, size=15, bold=True, color="17365D")

    authors = doc.add_paragraph()
    authors.alignment = WD_ALIGN_PARAGRAPH.CENTER
    authors.paragraph_format.space_after = Pt(2)
    r = authors.add_run("Rohit Shrivastava, Anshika Rai, Harsh Gupta, and Syamasudha Veeragandham")
    set_run_font(r, size=10.5, bold=True)

    affiliation = doc.add_paragraph()
    affiliation.alignment = WD_ALIGN_PARAGRAPH.CENTER
    affiliation.paragraph_format.space_after = Pt(2)
    r = affiliation.add_run("School of Computer Science and Engineering, Vellore Institute of Technology, Vellore, Tamil Nadu, India")
    set_run_font(r, size=9.5, italic=True)

    emails = doc.add_paragraph()
    emails.alignment = WD_ALIGN_PARAGRAPH.CENTER
    emails.paragraph_format.space_after = Pt(10)
    r = emails.add_run("rohit.lalbahadur2023@vitstudent.ac.in; anshika.rai2023@vitstudent.ac.in; harsh.gupta2023@vitstudent.ac.in; syamasudha.v@vit.ac.in")
    set_run_font(r, size=8.8, color="4E6173")


def add_abstract(doc: Document) -> None:
    p = doc.add_paragraph()
    p.paragraph_format.left_indent = Cm(0.5)
    p.paragraph_format.right_indent = Cm(0.5)
    p.paragraph_format.space_after = Pt(5)
    r = p.add_run("Abstract—")
    set_run_font(r, size=9.5, bold=True)
    text = (
        "Residential energy applications require a verifiable path from telemetry ingestion to historical storage, user-facing analysis, and notification, while preserving access control at the system boundary. This paper presents an event-driven microservices Home Energy Tracker evaluated in a local Docker Compose environment. The implementation routes Wokwi-compatible ESP32 telemetry through an API gateway with Keycloak JWT validation, resource-ownership enforcement, and a machine-token path. Ingestion events are distributed through Apache Kafka to time-series usage storage, deterministic insight functions, an alert service with a 15-minute deduplication policy, and a persisted Random Forest anomaly-inference service. The offline model was evaluated on a 5,000-record CSV using a chronological 70/15/15 split; on the held-out interval it obtained precision 0.88095, recall 0.92500, F1-score 0.90244, ROC-AUC 0.99743, and PR-AUC 0.94853. Local validation recorded expected outcomes for 8/8 security cases, 450/450 accepted k6 ingestion requests with 109.77 ms p95 response time, and a controlled end-to-end synthetic run in which analytics became available in 3.79 s and a threshold alert was captured by Mailpit in 13.64 s. These observations establish local integration and evaluation evidence, not physical-meter accuracy, external ML generalization, production capacity, or comprehensive fault tolerance."
    )
    r = p.add_run(text)
    set_run_font(r, size=9.5)

    p = doc.add_paragraph()
    p.paragraph_format.left_indent = Cm(0.5)
    p.paragraph_format.right_indent = Cm(0.5)
    p.paragraph_format.space_after = Pt(10)
    r = p.add_run("Index Terms—")
    set_run_font(r, size=9.5, bold=True)
    r = p.add_run("home energy monitoring, microservices, Apache Kafka, anomaly detection, Keycloak, JWT, Wokwi, Prometheus.")
    set_run_font(r, size=9.5, italic=True)


def build_paper() -> None:
    architecture, workflow = generate_figures()
    doc = Document()
    configure_document(doc)
    title_block(doc)
    add_abstract(doc)

    heading(doc, "I. INTRODUCTION", 1)
    para(doc, "Residential energy bills provide limited visibility into the timing, distribution, and abnormality of household electricity consumption. Existing IoT studies demonstrate low-cost sensing and visualisation, while other work considers anomaly detection, appliance-level analysis, and distributed energy-management architectures [1]–[24]. A useful engineering contribution in this space is therefore not a generic claim of intelligence or scalability, but a traceable and testable integration of telemetry, storage, analysis, alerting, and access control.")
    para(doc, "The present work revises an earlier functional prototype into an evidence-bounded final implementation. It combines a Wokwi ESP32 simulator, Spring Boot services, FastAPI-based ML inference, Apache Kafka, InfluxDB, MySQL, Keycloak, Prometheus, Grafana, a React dashboard, and Mailpit. The system is deliberately evaluated under local Docker Compose conditions. The simulator and controlled REST submissions use the same ingestion contract, but neither substitutes for calibrated electricity-meter validation.")

    heading(doc, "A. Objectives and Contributions", 2)
    para(doc, "The final objectives were to: (i) implement an event-driven telemetry-to-storage path; (ii) enforce gateway-level authentication, authorization, ownership, and device-token controls; (iii) provide deterministic forecasting, ranking, standby estimation, and deduplicated alerts; (iv) train, evaluate, persist, and integrate a supervised anomaly classifier; and (v) collect bounded local evidence from security, functional, performance, observability, and controlled fault scenarios.")
    bullet(doc, "An implemented 17-service local architecture that separates identity, telemetry ingestion, event processing, time-series usage, metadata, deterministic insights, ML inference, alerting, and monitoring.")
    bullet(doc, "An offline chronological evaluation of a persisted Random Forest model against a Logistic Regression comparator, reported separately from simulator and runtime integration evidence.")
    bullet(doc, "A reproducible local validation record covering gateway security cases, dashboard-route regression checks, alert deduplication, Prometheus targets, a k6 ingestion scenario, two controlled service-stop scenarios, and an end-to-end synthetic workflow.")

    heading(doc, "II. RELATED WORK AND RESEARCH GAP", 1)
    heading(doc, "A. Existing Approaches", 2)
    para(doc, "Low-cost monitoring systems based on ESP32-class controllers, smart meters, and IoT dashboards motivate the telemetry interface used in this study [3]–[6], [13], [16], [18]–[21], [23]. Research on anomaly detection and appliance-aware analysis illustrates the value of labelled time series and careful evaluation [1], [7]–[11], [15], [22]. Microservice and cloud-oriented approaches further motivate service separation and event-mediated processing [2], [12], [14], [17], [24]. These directions are complementary: sensing work does not by itself validate software architecture, and architectural work does not automatically establish valid energy-model performance.")
    heading(doc, "B. Revised Research Gap", 2)
    para(doc, "The original gap concerned the absence of a concise, inspectable linkage between household telemetry, event-driven services, time-series history, transparent energy insights, and notification. The completed system now addresses this integration gap more broadly by adding an evaluated supervised classifier, gateway-based identity controls, deduplicated alerting, and local operational evidence. It only partially addresses the surrounding research gaps: the source and label-generation process of the training data are undocumented; Wokwi inputs are synthetic; evaluation is single-host and short-duration; and physical-meter, multi-household, utility-bill, and production-scale validation remain unresolved.")

    heading(doc, "III. FINAL SYSTEM ARCHITECTURE AND METHODOLOGY", 1)
    add_figure(doc, architecture, 7.0, "Fig. 1. Final architecture of the locally evaluated Home Energy Tracker. Solid arrows denote implemented request or event flow; Prometheus/Grafana represent monitoring rather than a data-processing dependency.")
    heading(doc, "A. Telemetry, Gateway, and Event Processing", 2)
    para(doc, "The Wokwi ESP32 simulator constructs a JSON payload containing deviceId, energyConsumed, and timestamp and posts it to the simulator-compatible ingestion endpoint. Gateway access is separated by caller type. User-facing API routes require Keycloak-issued JWTs and are subject to role mapping and path-based resource-ownership checks. The telemetry endpoint accepts either an authenticated JWT or a configured X-Device-Token. The gateway does not establish production-grade security; it provides the evaluated local boundary controls described in Section V-C.")
    para(doc, "The Ingestion Service validates the telemetry contract and emits an energy-usage event to Kafka. The Usage Service consumes this event, writes timestamped usage data to InfluxDB, and evaluates threshold-based conditions. The User and Device services, along with persisted alert records, use MySQL. This separation permits the ingestion request to be acknowledged without waiting for downstream analytics or local mail capture.")

    heading(doc, "B. Deterministic Energy Insights", 2)
    para(doc, "The Insight Service is intentionally deterministic and is not represented as machine learning. For a selected D-day window with aggregate energy E, the implementation derives a daily rate E/D and a 30-day projection 30E/D. It applies a demonstration tariff (a fixed monthly charge and three energy slabs) to calculate indicative cost. Devices are ranked by their share of total energy. The standby routine estimates baseline demand using a configured 20% average-load heuristic and categorizes the estimated level. These outputs are traceable application transformations, not a validated forecast against a utility bill or an appliance-level standby measurement.")

    heading(doc, "C. Supervised ML Pipeline", 2)
    para(doc, "Offline anomaly-model development used smart_meter_data.csv. The retained CSV has 5,000 rows sampled at 30-minute intervals from 1 January 2024 to 14 April 2024, with five numeric consumption/context fields, a timestamp, and Anomaly_Label. The preprocessing implementation removes invalid timestamps, invalid numeric values, negative energy values, and complete duplicates; no such rows were removed in the retained data. It then chronologically sorts the records, encodes Normal as 0 and Abnormal as 1, and derives Hour, DayOfWeek, and ConsumptionDeviation = Electricity_Consumed − Avg_Past_Consumption. The model uses eight features: the five raw numeric fields plus the three engineered features.")
    para(doc, "A 70%/15%/15% chronological train/validation/test split was used. The decision threshold was selected by validation F1 across candidate thresholds. Logistic Regression with standardization served as a baseline. The selected Random Forest uses 300 trees, min_samples_leaf = 2, class_weight = balanced_subsample, and random_state = 42. The saved artifact is loaded by the inference service; runtime payloads that omit environmental/context fields receive stored median imputations. Since the source of Avg_Past_Consumption and label construction is not documented, the workflow should not be described as completely leakage-free or externally representative.")
    para(doc, "At runtime, the ML service consumes energy-usage events, generates an anomaly probability with the persisted model, and publishes anomaly-results for the Alert Service. A bounded retry/failure-topic path is implemented, but no dedicated retry or failure-topic experiment was retained; it is therefore described here as an implementation feature rather than an evaluated resilience result.")

    heading(doc, "D. Alerting, Deduplication, and Monitoring", 2)
    para(doc, "The Alert Service consumes both threshold energy-alerts and ML anomaly-results. Before persistence and notification, it forms a deduplication key userId:deviceId-or-HOUSEHOLD:alertType and checks whether a matching alert exists within the configured 15-minute window. This mechanism was exercised in a controlled duplicate-event case; it is not evidence of a general duplicate-reduction rate. Mailpit acts as a local SMTP capture environment, so an observed message demonstrates local sink capture rather than external email delivery.")
    para(doc, "Observability is provided by Spring Actuator and ML metrics exposed to Prometheus, with Grafana available for local dashboards. The final recorded snapshot contained eight active Prometheus targets, all reported as up. The implementation exposes counters for alert creation and suppression; their recorded values are cumulative local-process counters and must not be interpreted as per-experiment rates. Distributed tracing, Kafka-lag analysis, and measured ML-inference latency were not retained as evidence.")

    heading(doc, "E. Operational Workflow", 2)
    add_figure(doc, workflow, 7.0, "Fig. 2. Evidence-oriented workflow. Offline model evaluation, local functional tests, and runtime demonstrations are reported as distinct forms of evidence.")
    para(doc, "The workflow in Fig. 2 distinguishes processing from evaluation. The left-to-right path represents the implemented system; the lower band records how different parts were assessed. This distinction prevents a functional Kafka or Wokwi demonstration from being misreported as an ML accuracy study, a performance benchmark, or physical-meter validation.")

    heading(doc, "Algorithm 1. Secure telemetry-to-alert event processing", 2)
    algo = [
        "Input: telemetry t = {deviceId, energyConsumed, timestamp}; caller credential c.",
        "Output: accepted event status; downstream usage, insight, and alert artifacts when their asynchronous consumers complete.",
        "1: If t is invalid or energyConsumed < 0, reject the request.",
        "2: If c is neither a valid JWT nor the configured device token, return unauthorized.",
        "3: Route the accepted request through the API Gateway to the Ingestion Service.",
        "4: Publish t to Kafka topic energy-usage and return the ingestion acceptance status.",
        "5: Usage consumer writes a time-series record and may publish a threshold event.",
        "6: ML consumer builds the available feature vector, imputes missing optional context with stored medians, and publishes an anomaly-result event.",
        "7: Alert consumer forms key userId:deviceId-or-HOUSEHOLD:alertType. If a matching alert lies inside the 15-minute window, suppress it; otherwise persist it and attempt local notification delivery.",
    ]
    for item in algo:
        p = doc.add_paragraph()
        p.paragraph_format.left_indent = Cm(0.55)
        p.paragraph_format.right_indent = Cm(0.25)
        p.paragraph_format.space_after = Pt(1)
        r = p.add_run(item)
        set_run_font(r, size=9.2, name="Courier New")

    heading(doc, "IV. IMPLEMENTATION AND EXPERIMENTAL SETUP", 1)
    heading(doc, "A. Local Deployment and Software Components", 2)
    caption(doc, "TABLE I. Final implemented components and evidence boundaries")
    add_table(doc,
              ["Layer", "Implemented component(s)", "Role in this study"],
              [
                  ["Input", "Wokwi ESP32 simulator; controlled REST client", "Generate Wokwi-compatible synthetic telemetry; not a calibrated meter."],
                  ["Identity and gateway", "Keycloak; API Gateway", "JWT role mapping, ownership checks, device-token telemetry route."],
                  ["Event processing", "Ingestion, Usage, ML Inference, Alert services; Kafka", "Event distribution, time-series persistence, inference, threshold and anomaly handling."],
                  ["Data", "InfluxDB; MySQL", "Usage series; user, device, and alert metadata."],
                  ["Presentation and notification", "React frontend; Mailpit", "Authenticated dashboard use and local mail capture."],
                  ["Monitoring", "Prometheus; Grafana; Actuator / ML metrics", "Dated local health and metric observations."],
              ], widths=[1.25, 2.45, 3.25], font_size=8.0)
    caption(doc, "TABLE II. Retained local experimental environment")
    add_table(doc,
              ["Item", "Recorded configuration", "Scope"],
              [
                  ["Host operating system", "Windows 11 Home Single Language, build 26300", "Host used for recorded local validation."],
                  ["Compute record", "8 logical processors; 8,311,836,672 bytes physical memory (about 7.74 GiB)", "Hardware record captured with the k6 evidence."],
                  ["Deployment", "Docker Compose, 17 configured services", "Local single-host deployment; not a distributed cluster."],
                  ["Load tool", "Grafana k6 Docker image", "One specified ingestion scenario; no repeated-trial confidence interval."],
                  ["Mail test endpoint", "Mailpit", "Local capture only; not an external mail-provider evaluation."],
              ], widths=[1.55, 3.35, 2.05], font_size=8.0)

    heading(doc, "B. Dataset and Model Configuration", 2)
    caption(doc, "TABLE III. Dataset characteristics and split configuration")
    add_table(doc,
              ["Characteristic", "Verified value"],
              [
                  ["Dataset identity", "smart_meter_data.csv; source, licence, and label-generation provenance are absent from the repository."],
                  ["Raw shape", "5,000 rows; 7 CSV columns: Timestamp, Electricity_Consumed, Temperature, Humidity, Wind_Speed, Avg_Past_Consumption, Anomaly_Label."],
                  ["Time coverage", "2024-01-01 00:00:00 to 2024-04-14 03:30:00 at uniform 30-minute intervals."],
                  ["Data-quality checks", "0 missing raw values; 0 complete duplicate rows; 0 invalid timestamp/numeric/negative-energy rows in the retained data."],
                  ["Class distribution", "4,750 Normal (95.0%); 250 Abnormal (5.0%)."],
                  ["Chronological split", "Train 3,500 (3,335/165); validation 750 (705/45); held-out test 750 (710/40), reported as Normal/Abnormal."],
                  ["Feature set", "Five raw numeric fields plus Hour, DayOfWeek, and ConsumptionDeviation."],
              ], widths=[1.75, 5.25], font_size=8.0)
    caption(doc, "TABLE IV. Candidate model configuration")
    add_table(doc,
              ["Model", "Configuration", "Threshold selection"],
              [
                  ["Logistic Regression", "StandardScaler → LogisticRegression(max_iter=1000, class_weight=balanced, random_state=42)", "Validation F1, 0.05–0.95 search in 0.01 increments."],
                  ["Random Forest (selected)", "300 trees; min_samples_leaf=2; class_weight=balanced_subsample; random_state=42; n_jobs=-1", "Validation F1; selected threshold 0.31."],
              ], widths=[1.65, 3.6, 1.75], font_size=8.0)

    heading(doc, "C. Test Procedures", 2)
    numbered(doc, "Offline ML evaluation: audit the CSV, apply the chronological split and feature transformation, select the threshold by validation F1, and report untouched held-out test metrics.")
    numbered(doc, "Security validation: obtain local Keycloak tokens and execute eight expected-status scenarios for owned access, unauthorized access, ownership rejection, administration, machine token, and token expiry.")
    numbered(doc, "Functional/E2E verification: create a controlled profile and device, submit synthetic telemetry through the gateway, poll the downstream APIs, and compare deterministic results and Mailpit capture with predeclared expected values.")
    numbered(doc, "Alert deduplication: submit identical records, inspect alert persistence and the suppression log inside the configured 15-minute window.")
    numbered(doc, "Performance validation: run the recorded k6 ingestion profile (1 request/s start; 2, 5, and 10 requests/s for 30 s stages; 15 s ramp-down) using authenticated local ingestion requests.")
    numbered(doc, "Fault scenarios: stop Mailpit or the ML service, test whether gateway ingestion is accepted, manually restart the stopped service, and record container-state recovery. This procedure does not assert end-to-end replay or delivery.")

    heading(doc, "V. RESULTS AND DISCUSSION", 1)
    heading(doc, "A. Offline ML Evaluation", 2)
    para(doc, "Table V reports model results on the held-out chronological test interval. Random Forest was selected by validation F1 and substantially outperformed the Logistic Regression comparator on this specific retained interval. The Random Forest confusion matrix contains 705 true negatives, 5 false positives, 3 false negatives, and 37 true positives. Although an accuracy of 742/750 (98.93%) follows from this matrix, F1, PR-AUC, and recall are more informative in the 5% abnormal-class setting and are therefore emphasized.")
    caption(doc, "TABLE V. Offline anomaly-detection results on the held-out CSV interval")
    add_table(doc,
              ["Model", "Threshold", "Precision", "Recall", "F1", "ROC-AUC", "PR-AUC"],
              [
                  ["Logistic Regression", "0.28", "0.05333", "1.00000", "0.10127", "0.42285", "0.05971"],
                  ["Random Forest", "0.31", "0.88095", "0.92500", "0.90244", "0.99743", "0.94853"],
              ], widths=[1.4, 0.75, 0.9, 0.75, 0.65, 0.9, 0.8], font_size=7.7)
    if CM_PATH.exists():
        add_figure(doc, CM_PATH, 4.7, "Fig. 3. Random Forest confusion matrix on the 750-record held-out CSV interval.")
    para(doc, "The metric results characterize one anonymous, labelled CSV stream. They do not establish physical deployment performance. In particular, the dataset does not document its source, licence, entity identity, or label-generation method. Moreover, the Wokwi modes emit 1–40 kWh values while the recorded training Electricity_Consumed range is 0–1 with undocumented units; optional contextual features are median-imputed at runtime. Consequently, the offline metrics must not be extrapolated to simulated heavy-load modes, household meters, or utility data.")

    heading(doc, "B. Controlled Functional and End-to-End Verification", 2)
    para(doc, "The latest successful E2E record used synthetic REST telemetry submitted through the Wokwi-compatible endpoint. Three analytics inputs (0.25, 0.50, and 0.75 kWh) resulted in a 1.50 kWh total. The documented forecast, ranking, and standby assertions passed. A separate 1.00 kWh input against a 0.10 kWh user threshold produced a persisted THRESHOLD alert with sent = true and a matching Mailpit message. The record also contained an ML_ANOMALY alert with probability 0.792945, but the E2E script's formal pass condition was the threshold alert and email, not prediction quality.")
    caption(doc, "TABLE VI. Latest controlled E2E functional observations")
    add_table(doc,
              ["Case", "Predeclared / observed result", "Interpretation and boundary"],
              [
                  ["Analytics path", "1.50 kWh; current estimate $0.18; daily rate 0.50 kWh; monthly projection 15.00 kWh and $11.80; 100% one-device ranking; 4.17 W standby estimate.", "Configured deterministic transformations passed for the synthetic case; not bill or meter ground truth."],
                  ["Analytics availability", "3.79 s observation after submissions.", "Polling-bounded local functional observation; not an end-to-end latency benchmark."],
                  ["Threshold alert", "1.00 kWh > 0.10 kWh; persisted THRESHOLD alert sent = true; matching Mailpit capture.", "Local threshold-to-mail-sink path was observed."],
                  ["Alert observation", "13.64 s observation.", "Includes polling; not SMTP or service latency."],
                  ["Runtime ML observation", "One ML_ANOMALY record with probability 0.792945 and threshold 0.31.", "Integration observation only; not an E2E ML-quality assertion."],
              ], widths=[1.35, 3.0, 2.65], font_size=7.9)

    heading(doc, "C. Gateway Security and Dashboard Regression Validation", 2)
    para(doc, "The local security suite passed all eight configured cases on 5 October 2026. These results show that the expected HTTP behavior was observed for the tested gateway boundary paths. They are not a penetration test, cryptographic assessment, privacy assessment, or evidence of production security.")
    caption(doc, "TABLE VII. Local gateway security validation")
    add_table(doc,
              ["Control exercised", "Expected / observed status", "Result"],
              [
                  ["JWT-owned profile access", "200", "Pass"],
                  ["Missing JWT", "401", "Pass"],
                  ["Invalid JWT", "401", "Pass"],
                  ["Cross-user profile access", "403", "Pass"],
                  ["Cross-user device-list access", "403", "Pass"],
                  ["Administrator user listing", "200", "Pass"],
                  ["Machine-token telemetry ingestion", "201", "Pass"],
                  ["Expired JWT", "401", "Pass"],
              ], widths=[3.25, 1.55, 1.2], font_size=8.2)
    para(doc, "After a reactive gateway response-body correction, four focused regression tests passed and eight protected dashboard routes returned non-empty HTTP 200 JSON responses in the dated local runtime validation. Historical broader service tests (28 Java tests with 3 skipped) and 3 ML API tests are reported as earlier, separate runs; they are not combined into a falsely contemporaneous total.")

    heading(doc, "D. Alert Deduplication and Observability", 2)
    para(doc, "In the duplicate-event validation, two identical submissions were accepted by ingestion, one ML_ANOMALY alert was persisted, and an explicit suppression log was observed inside the 15-minute window. Unit tests also covered first-alert creation, inside-window suppression, post-window creation, and independent deduplication keys. This supports correct behavior for the tested scenario, but it does not quantify duplicate reduction under arbitrary retries, partitions, or concurrent consumers.")
    para(doc, "The final Prometheus snapshot reported eight active targets, each with health up, and local health checks returned HTTP 200 for the frontend, gateway health endpoint, Prometheus readiness endpoint, Grafana health endpoint, and Mailpit API. Cumulative suppression counters existed for ML_ANOMALY and THRESHOLD alert types. No derived alert rate, Kafka lag, distributed trace, or measured ML latency is reported because such evidence was not retained.")

    heading(doc, "E. Local Load and Controlled Fault Results", 2)
    caption(doc, "TABLE VIII. Local load and controlled fault observations")
    add_table(doc,
              ["Experiment", "Observed result", "Evidence-bound interpretation"],
              [
                  ["k6 ingestion scenario", "450/450 acceptance checks; 0.00% HTTP failure; mean 39.44 ms; median 24.85 ms; p90 74.78 ms; p95 109.77 ms; maximum 503.36 ms; mean 4.281 requests/s.", "Single-host local validation under the recorded ramp to 10 requests/s; not a production capacity or distributed scalability result."],
                  ["Mailpit service-stop scenario", "Gateway ingestion returned HTTP 201 while Mailpit was stopped; the harness later restored the container and recorded recovered = true.", "Shows recorded ingress availability and manual restoration only; it does not establish notification queuing, automatic recovery, or eventual mail delivery."],
                  ["ML-service stop scenario", "Gateway ingestion returned HTTP 201 while the ML service was stopped; the harness later restored the container and recorded recovered = true.", "Shows recorded ingress availability and manual restoration only; it does not establish replay, post-restart inference, or alert delivery."],
              ], widths=[1.55, 3.1, 2.55], font_size=7.8)
    para(doc, "The k6 result demonstrates that the gateway accepted the recorded workload in the specified local configuration. It cannot establish multi-node scalability, cloud performance, resource efficiency, or behavior under a broker/database failure. Similarly, the two controlled service-stop scenarios show that synchronous gateway ingestion did not fail in the recorded cases; they do not demonstrate comprehensive fault tolerance.")

    heading(doc, "F. Discussion of the Revised Contribution", 2)
    para(doc, "The principal contribution is an implementation-level, evidence-bounded integration: event-driven telemetry processing with time-series persistence; deterministic user-facing analysis; a separately evaluated supervised anomaly classifier; gateway authentication and ownership controls; deduplicated alert handling; and local operational checks. The model comparison establishes that the selected Random Forest performed better than the baseline on the retained test interval, while the E2E run establishes a synthetic integration path rather than generalizable ML efficacy. The security, k6, and fault results support localized claims about the executed cases only.")

    heading(doc, "VI. LIMITATIONS AND FUTURE WORK", 1)
    para(doc, "Several limitations remain. First, Wokwi values and controlled REST inputs are synthetic and have not been calibrated against a physical energy meter. The demonstration tariff, ranking logic, and standby heuristic have not been validated against utility bills, device-level instrumentation, or user behavior. Second, smart_meter_data.csv has no documented source, licence, household identity, or label-generation procedure. Its consumption scale and units do not align demonstrably with all Wokwi modes, and runtime imputation of absent context limits interpretability. Third, all runtime work was performed on a single local Docker host using one load scenario and a short evidence window. Mailpit represents local message capture rather than external delivery.")
    para(doc, "Future research should obtain consented, calibrated, multi-household energy data with documented labels and provenance; align live measurement units and contextual features with model training; assess temporal drift and external generalization; validate forecasts and tariff calculations against bills; and investigate appliance-level disaggregation. Systems work should evaluate multi-node deployment, durable retry/DLQ behavior, broker/database failures, longer-duration monitoring, stronger device provisioning, TLS/cloud configurations, distributed tracing, and repeated performance experiments with confidence intervals.")

    heading(doc, "VII. CONCLUSION", 1)
    para(doc, "This paper presents the final, evidence-based form of a Home Energy Tracker built as an event-driven local microservices system. The implementation integrates Wokwi-compatible telemetry, gateway JWT and device-token controls, Kafka, InfluxDB, MySQL, deterministic insights, a persisted Random Forest anomaly service, deduplicated alerts, and Prometheus/Grafana monitoring. The retained evidence includes a chronological offline ML evaluation, eight expected security outcomes, a controlled alert-deduplication case, an eight-target Prometheus snapshot, a 450-request local ingestion scenario, two controlled service-stop records, and a successful synthetic end-to-end workflow with local Mailpit capture. These results support claims of local integration and bounded evaluation. They do not establish physical-meter accuracy, utility-bill validity, external ML generalization, production security, production capacity, or comprehensive resilience. The most defensible next step is therefore field-quality data and evaluation rather than stronger claims from the present local prototype.")

    heading(doc, "REFERENCES", 1)
    references = [
        '[1] A. Shuaibu, S. U. Haq, B. Almadani, F. Aliyu, and E. Al-Nahari, "Smart Metering Meets AI: Real-Time Appliance Monitoring and Anomaly Detection Over DDS Middleware," IEEE Transactions on Industry Applications, 2026, doi: 10.1109/TIA.2025.3608687.',
        '[2] I. Núñez, C. A. Rovetto, E. Cruz, A. Smolarz, D. H. Concepción, and E. Cano, "Design of a microservices-based architecture for residential energy efficiency monitoring," International Journal of Electronics and Telecommunications, 2024, doi: 10.24425/ijet.2024.152511.',
        '[3] W. Agustiarmi et al., "Real-Time IoT-based Energy Power Consumption Monitoring System for Smart Homes," International Journal on Advanced Science, Engineering and Information Technology, 2025, doi: 10.18517/ijaseit.15.5.20918.',
        '[4] M. Islam, N. Jobaida, M. S. Hossain, M. R. Uddin, and M. Hasan, "IoT-Based Smart Energy Monitoring and Energy Demand Response System," 2024 IEEE 3rd International Conference on Electrical Power and Energy Systems (ICEPES), 2024, doi: 10.1109/ICEPES60647.2024.10653605.',
        '[5] S. S. Shashank, Yogesh, M. Krishnamoorthy, N. Karuppiah, P. Mounica, and R. Abinaya, "Smart Energy Monitoring for Real-Time Power Consumption Tracking and Optimization Using an IoT-Based Cost-Effective System," 2025 11th International Conference on Electrical Energy Systems (ICEES), 2025, doi: 10.1109/ICEES67011.2025.11212888.',
        '[6] T. B. D. Sousa and R. Rabelo, "Smart Metering Enabled by the Internet of Things for Monitoring Residential Energy Consumption and Power Quality," IEEE Access, 2025, doi: 10.1109/ACCESS.2025.3627191.',
        '[7] B. Jyothi et al., "Empowering energy management: anomaly detection in smart meter data for proactive consumption control," Bulletin of Electrical Engineering and Informatics, 2026, doi: 10.11591/eei.v15i3.10957.',
        '[8] K. Kulkarni, "Anomaly Detection in Smart Electric Meters for Detecting Faults and Misuse of Electric Energy Consumption," International Journal of Scientific Research in Engineering and Management, 2024, doi: 10.55041/ijsrem34689.',
        '[9] M. AbuArqoub, A. A. Titinchi, and R. Marie, "A Scalable IoT-AI Framework for Real-Time Energy Anomaly Detection in Smart Grid Networks," 2026 2nd International Conference on Computational Intelligence Approaches and Applications (ICCIAA), 2026, doi: 10.1109/ICCIAA68481.2026.11543846.',
        '[10] Ó. Hernández et al., "Detection of Anomalies in Daily Activities Using Data from Smart Meters," Sensors, vol. 24, no. 2, 2024, doi: 10.3390/s24020515.',
        '[11] S. Maitra, S. Kundu, and A. Shankar, "A Real-time Anomaly Detection Using Convolutional Autoencoder with Dynamic Threshold," arXiv, 2024, doi: 10.48550/arXiv.2404.04311.',
        '[12] A. F. S. Veloso, J. Reis, and R. Rabelo, "A Microservices-Based Solution with Hybrid Communication for Energy Management in Smart Grid Environments," Sensors, 2026, doi: 10.3390/s26051714.',
        '[13] D. K, "Smart Energy Monitoring System," International Journal of Innovative Research in Information Security, 2025, doi: 10.26562/ijiris.2025.v1109.15.',
        '[14] L. L. Motta, W. S. Alvarez, H. R. Carvajal, F. B. Neto, E. D. Lima, and L. F. P. Meloni, "A cloud architecture for home energy management systems: a conceptual model," Energy Informatics, 2025, doi: 10.1186/s42162-025-00599-1.',
        '[15] J. Liu and Y. Hsiao, "Smart plug-based home energy management with IoT and anomaly detection," Journal of the Chinese Institute of Engineers, 2025, doi: 10.1080/02533839.2025.2557233.',
        '[16] K. M. W. Hidayat and M. G. Al-Faris, "IoT-Based Electrical Power Consumption Monitoring System in Households Using ESP32 and PZEM-004T," Brilliance: Research of Artificial Intelligence, 2025, doi: 10.47709/brilliance.v5i2.6368.',
        '[17] S. Sirisumrannukul, T. Intaraumnauy, and N. Piamvilai, "Optimal control of cooling management system for energy conservation in smart home with ANNs-PSO data analytics microservice platform," Heliyon, 2024, doi: 10.1016/j.heliyon.2024.e26937.',
        '[18] M. S. Hossain and M. Hassan, "Smart Energy Meter with Real Time Monitoring System," 2024 13th International Conference on Electrical and Computer Engineering (ICECE), 2024, doi: 10.1109/ICECE64886.2024.11024970.',
        '[19] D. G. S, T. Gangakhedkar, A. P, A. Ashwija, and C. B. T. Rambapuri, "IOT-Enabled Electrical Consumption Tracking for Intelligent Energy Saving," International Journal of Scientific Research in Engineering and Management, 2025, doi: 10.55041/ijsrem54847.',
        '[20] Y. Zhu and M. Yue, "Design of an IoT-Based Smart City Energy Management System," 2025 4th International Conference on Green Energy and Power Systems (ICGEPS), 2025, doi: 10.1109/ICGEPS65133.2025.11034388.',
        '[21] S. Susikala, R. K, J. K, S. K, and Y. M, "IoT-Based Smart Electricity Monitoring System with Real-Time Alerts and Remote Control," International Journal of Engineering & Extended Technologies Research, 2026, doi: 10.15662/ijeetr.2026.0802420.',
        '[22] C. S. Sinha, "Smart Meter-Based Power Consumption Detection System: An Integrated Approach Using LSTM Networks and Real-Time Web Interface," International Journal For Multidisciplinary Research, 2025, doi: 10.36948/ijfmr.2025.v07i01.37948.',
        '[23] F. Dinmohammadi, A. M. Farook, and M. Shafiee, "Improving Energy Efficiency in Buildings with an IoT-Based Smart Monitoring System," Energies, 2025, doi: 10.3390/en18051269.',
        '[24] S. Son, S. Ko, H. Lee, S. Lee, and B. Lee, "SIMA: Scalable IoT Microservice Architecture With Users and Things Joint Load Balancing," IEEE Internet of Things Journal, 2024, doi: 10.1109/JIOT.2023.3317430.',
    ]
    for ref in references:
        p = doc.add_paragraph()
        p.paragraph_format.left_indent = Cm(0.45)
        p.paragraph_format.first_line_indent = Cm(-0.45)
        p.paragraph_format.space_after = Pt(3)
        r = p.add_run(ref)
        set_run_font(r, size=8.5)

    OUTPUT.mkdir(parents=True, exist_ok=True)
    doc.save(PAPER_PATH)


# ---------- Audit pack ----------

def audit_title(doc: Document) -> None:
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = p.add_run("Paper Revision Evidence Audit Pack")
    set_run_font(r, size=16, bold=True, color="17365D")
    p.paragraph_format.space_after = Pt(5)
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = p.add_run("Home Energy Tracker — final implementation-and-evaluation revision")
    set_run_font(r, size=10.5, italic=True, color="4E6173")
    p.paragraph_format.space_after = Pt(12)
    para(doc, "Purpose: This companion record explains how the manuscript was revised from the earlier prototype paper. It classifies each important statement by implementation and evidence status, records superseded claims, and identifies what must not be claimed in a presentation or publication.", size=9.5)


def build_audit_pack() -> None:
    doc = Document()
    configure_document(doc, audit=True)
    audit_title(doc)

    heading(doc, "1. Revision Basis and Title Decision", 1)
    para(doc, "Source paper reviewed: version-1.1aHome_Energy_Tracker-publication.docx. The requested copy with “(1)” was not found; the matching paper was used. The paper was treated as historical context only. Current source code, Docker configuration, retained dataset/evidence records, and the completed testing guide were used as the source of truth.")
    caption(doc, "TABLE A1. Title candidates evaluated")
    add_table(doc,
              ["Candidate", "Assessment"],
              [
                  ["A Microservices-Based Home Energy Tracker for Real-Time Monitoring, Intelligent Alerting, and AI-Driven Energy Insights", "Rejected: “real-time,” “intelligent,” and “AI-driven” were too broad and the old paper omitted the evaluated ML subsystem."],
                  ["A Secure Event-Driven Microservices Home Energy Tracker with ML-Based Anomaly Detection and Deterministic Energy Insights", "Not selected: “secure” may overstate local API validation; title is long."],
                  ["An Event-Driven Microservices Home Energy Tracker with Gateway Authentication and ML-Based Anomaly Detection", "Selected: names the demonstrated architectural and ML contributions without asserting physical accuracy, production scale, or universal security."],
              ], widths=[3.25, 3.75], font_size=8.2)

    heading(doc, "2. Paper Revision Change Log", 1)
    caption(doc, "TABLE A2. Material claim replacements")
    add_table(doc,
              ["Old section / claim", "Revision", "Reason and evidence"],
              [
                  ["Abstract and introduction: no supervised anomaly detection or validated predictive model.", "Describe the evaluated Random Forest and separate offline metrics from runtime integration.", "ML training code, model metadata, held-out metrics, and persisted artifact."],
                  ["Introduction: authentication, authorization, load and resilience testing excluded.", "Report bounded gateway security, k6, and service-stop observations.", "Security results (8 cases), k6 summary, fault records."],
                  ["Architecture: gateway, six Java services, Kafka, InfluxDB, MySQL, Mailpit only.", "Add Keycloak, device token, ML Inference, anomaly-results, 15-minute deduplication, Prometheus/Grafana, frontend.", "docker-compose.yml and service source code."],
                  ["Alert method: repeated threshold alerts are not deduplicated.", "Describe the configured key and 15-minute window; qualify as one controlled functional observation.", "AlertService.java and deduplication evidence."],
                  ["Workflow: no train/test split or empirical classifier evaluation.", "Add chronological split, model comparison, held-out results, and integration boundary.", "ML code and evidence/01–05."],
                  ["Functional tests: 19 discovered, 16 executed, 3 skipped.", "Separate historical 28 Java/3 skipped, 3 ML API, 4 gateway regression, 8 security, and other experiments by scope/date.", "evidence/11 and evidence/15."],
                  ["Results: 17.32 s analytics and 6.14 s alert observation.", "Replace with latest E2E record: 3.79 s analytics availability and 13.64 s threshold-alert/email observation.", "Latest successful E2E JSON; explicitly polling-bounded."],
                  ["Future work: add auth, ML, observability, deduplication, load and fault testing.", "Remove as already implemented; retain calibration, provenance, field trials, multi-node testing, and broader failures.", "Current implementation/evidence audit."],
              ], widths=[2.15, 2.45, 2.4], font_size=7.6)

    heading(doc, "3. Evidence-to-Paper Matrix", 1)
    caption(doc, "TABLE A3. Claim classification used in the final manuscript")
    add_table(doc,
              ["Claim", "Paper location", "Actual evidence", "Status"],
              [
                  ["17-service local architecture", "III-A; IV-A", "docker-compose.yml; final validation report", "Implemented + functionally observed"],
                  ["JWT roles, ownership, and machine token", "III-A; V-C", "Gateway source; 8-case security JSON/CSV", "Implemented + functionally tested"],
                  ["Time-series usage and deterministic insights", "III-B; V-B", "Usage/Insight source; latest E2E JSON", "Implemented + functionally tested"],
                  ["Random Forest model", "III-C; V-A", "train.py; joblib; model metadata; metrics", "Implemented + experimentally evaluated offline"],
                  ["Kafka ML event path", "III-C; V-B", "Kafka worker, AlertService, E2E observation", "Implemented + runtime observation"],
                  ["15-minute deduplication", "III-D; V-D", "AlertService; unit and live dedup records", "Implemented + functionally tested"],
                  ["Prometheus/Grafana", "III-D; V-D", "compose/config; dated 8-target snapshot", "Implemented + dated runtime snapshot"],
                  ["k6 ingestion behavior", "IV-C; V-E", "k6 config and JSON summary", "Experimentally evaluated locally"],
                  ["Mailpit and ML service-stop behavior", "IV-C; V-E", "fault records", "Controlled manual-restoration observation"],
                  ["Physical-meter / field validity", "VI", "No matching evidence", "Not evaluated"],
              ], widths=[1.55, 1.15, 2.7, 1.6], font_size=7.4)

    heading(doc, "4. Stale-Claim Audit", 1)
    para(doc, "The following obsolete claims were removed or rewritten. None remain in the revised manuscript.")
    stale = [
        "No trained classifier or classification metrics.",
        "No supervised-learning train/test evaluation.",
        "No Keycloak, JWT, authorization, or ownership enforcement.",
        "No device/machine authentication for telemetry.",
        "No alert-deduplication window.",
        "No observability, Prometheus, or Grafana.",
        "No load or fault-injection testing.",
        "Only four-event prototype evidence with 17.32 s / 6.14 s observations as current results.",
        "Future work to add authentication, ML, deduplication, observability, load testing, and fault injection.",
    ]
    for item in stale:
        bullet(doc, item)

    heading(doc, "5. Experiment Summary", 1)
    caption(doc, "TABLE A4. Experiment-by-experiment result summary")
    add_table(doc,
              ["Experiment", "Objective and method", "Observed result", "Interpretation / limitation"],
              [
                  ["Dataset audit", "Inspect CSV schema, quality, timestamp distribution and labels.", "5,000 rows, 7 columns, 30-min interval, 95%/5% normal/abnormal; no missing/duplicate/invalid retained rows.", "Dataset provenance, licence, label generation, and entity identity are unavailable."],
                  ["Offline ML", "Chronological 70/15/15 split; compare LR and RF; select by validation F1.", "RF test F1 0.90244, PR-AUC 0.94853; LR F1 0.10127.", "Single retained CSV interval; no field or Wokwi generalization."],
                  ["Security", "Eight gateway-level expected-status API cases.", "8/8 expected statuses observed.", "Local API validation; neither penetration test nor production-security proof."],
                  ["Deduplication", "Submit duplicate input and inspect alert/log outcome.", "One persisted ML anomaly alert plus logged suppression within 15 min.", "One functional scenario; no general duplicate-rate claim."],
                  ["Observability", "Inspect Prometheus targets and health endpoints.", "8 active targets all up in dated snapshot.", "Target reachability only; no long-duration availability or tracing evidence."],
                  ["k6 load", "Local authenticated ingestion ramp to 10 req/s.", "450/450 checks; 0 failures; p95 109.77 ms.", "One local scenario; no capacity or scalability conclusion."],
                  ["Fault scenarios", "Stop Mailpit/ML service, submit ingestion, manually restart container.", "Ingestion 201 during both; recovered=true recorded.", "No automated healing, message replay, or end-to-end delivery result."],
                  ["E2E", "Synthetic Wokwi-compatible telemetry with expected analytics and alert assertions.", "overallPassed=true; analytics 3.79 s; threshold mail capture 13.64 s.", "Synthetic/polling-bounded local functional observations."],
              ], widths=[1.2, 2.0, 1.9, 2.0], font_size=7.15)

    heading(doc, "6. Reviewer Risk Report", 1)
    para(doc, "The following are legitimate weaknesses, not defects to conceal. They were retained as limitations or claim boundaries in the revised manuscript.")
    caption(doc, "TABLE A5. Reviewer questions and safe response")
    add_table(doc,
              ["Likely question", "Evidence-based response / action"],
              [
                  ["Is this a physical smart-meter study?", "No. Wokwi and REST records are simulated. The manuscript explicitly avoids meter-accuracy, bill-accuracy, and field-deployment claims."],
                  ["Are ML metrics valid for Wokwi or homes?", "Only for the retained held-out CSV interval. Dataset provenance/labels are undocumented, runtime features are partly imputed, and simulator values may exceed the training range."],
                  ["Does 450 requests prove scalability?", "No. It is a single-host local k6 scenario with a reported p95, not a cloud or distributed capacity study."],
                  ["Do the service-stop tests prove fault tolerance?", "No. They only show accepted ingress during two component stops and manual restoration of the stopped containers."],
                  ["Does Keycloak prove full security?", "No. It demonstrates the eight tested gateway authentication/authorization cases under local conditions."],
                  ["Does Mailpit prove notification delivery?", "It proves local mail-sink capture only, not external SMTP reliability."],
                  ["Is this a novel algorithm?", "No new ML algorithm is claimed. The contribution is evidence-bounded integration and evaluation of existing components."],
              ], widths=[2.25, 4.85], font_size=8.0)

    heading(doc, "7. Claims That Must Not Be Made", 1)
    forbidden = [
        "“Real-time” without a qualified functional-observation context.",
        "“Production ready,” “fully secure,” “fault tolerant,” or “highly scalable.”",
        "Physical-meter accuracy, utility-bill accuracy, appliance-level ground truth, or external email delivery.",
        "Wokwi or household anomaly-detection accuracy derived from the offline CSV metrics.",
        "Automatic recovery, Kafka replay, or end-to-end delivery after the recorded fault scenarios.",
        "ML runtime latency, Kafka lag, distributed tracing, or alert-suppression rates not recorded in the evidence.",
        "A combined post-fix test total that merges historical and later test suites into one fresh run.",
    ]
    for item in forbidden:
        bullet(doc, item)

    heading(doc, "8. Final Quality Gate", 1)
    checks = [
        ("Current architecture represented", "Pass — Figure 1 and Section III match Compose/source."),
        ("ML pipeline and metrics correct", "Pass — uses held-out CSV evidence and separate runtime boundary."),
        ("Dataset details verified", "Pass with limitation — source/licence/label provenance unavailable."),
        ("Security/deduplication claims bounded", "Pass — describes exact local checks only."),
        ("Performance/resilience claims bounded", "Pass — local k6 and manual-restoration limits stated."),
        ("Old stale claims removed", "Pass — audit list reviewed against final content."),
        ("Conclusion aligned with results", "Pass — local integration/evaluation only."),
        ("No fabricated metrics", "Pass — every number is from retained evidence or direct arithmetic identified in text."),
        ("References", "Retained from the existing manuscript; no new unverified bibliographic entry was invented in this revision."),
    ]
    add_table(doc, ["Quality gate", "Result"], checks, widths=[2.7, 4.3], font_size=8.1)

    OUTPUT.mkdir(parents=True, exist_ok=True)
    doc.save(AUDIT_PATH)


if __name__ == "__main__":
    build_paper()
    build_audit_pack()
    print(PAPER_PATH)
    print(AUDIT_PATH)
