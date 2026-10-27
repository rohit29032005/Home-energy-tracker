"""Targeted OOXML revision of the supplied master publication DOCX.

This script deliberately edits only word/document.xml and the two existing PNG
media parts in a working copy. It does not reconstruct the DOCX or alter its
section breaks, styles, drawing anchors, table grids, headers/footers, or
reference block.
"""

from __future__ import annotations

import copy
import os
import shutil
import sys
import tempfile
import zipfile
from pathlib import Path

from lxml import etree
from PIL import Image, ImageDraw, ImageFont


SOURCE = Path(r"C:\Users\anju2\Desktop\Advance_java_research\version-1.1aHome_Energy_Tracker-publication.docx")
OUTPUT = Path(r"C:\Users\anju2\Desktop\Home-Energy-Tracker\research-output\version-1.1aHome_Energy_Tracker-publication_updated.docx")
TEMP = Path(r"C:\Users\anju2\Desktop\Home-Energy-Tracker\.tmp\master-publication-update")

W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
XML_SPACE = "{http://www.w3.org/XML/1998/namespace}space"

NAVY = (31, 78, 121)
PALE = (234, 242, 248)
ARROW = (70, 84, 97)
BLUE = (45, 105, 155)
INK = (30, 35, 40)
WHITE = (255, 255, 255)


def element_text(el: etree._Element) -> str:
    return "".join(el.xpath(".//w:t/text()", namespaces={"w": W[1:-1]}))


def clone_rpr_from_paragraph(p: etree._Element, preferred_index: int = 0):
    runs = p.findall(W + "r")
    if not runs:
        return None
    index = min(max(preferred_index, 0), len(runs) - 1)
    rpr = runs[index].find(W + "rPr")
    return copy.deepcopy(rpr) if rpr is not None else None


def append_run(p: etree._Element, text: str, rpr: etree._Element | None) -> None:
    run = etree.Element(W + "r")
    if rpr is not None:
        run.append(copy.deepcopy(rpr))
    t = etree.SubElement(run, W + "t")
    if text[:1].isspace() or text[-1:].isspace():
        t.set(XML_SPACE, "preserve")
    t.text = text
    p.append(run)


def clear_paragraph_content(p: etree._Element) -> None:
    ppr = p.find(W + "pPr")
    for child in list(p):
        if child is not ppr:
            p.remove(child)


def set_paragraph(p: etree._Element, text: str) -> None:
    rpr = clone_rpr_from_paragraph(p)
    clear_paragraph_content(p)
    append_run(p, text, rpr)


def set_label_body_paragraph(p: etree._Element, label: str, body: str) -> None:
    label_rpr = clone_rpr_from_paragraph(p, 0)
    body_rpr = clone_rpr_from_paragraph(p, 1)
    clear_paragraph_content(p)
    append_run(p, label, label_rpr)
    append_run(p, body, body_rpr)


def set_cell(tc: etree._Element, text: str) -> None:
    paragraphs = tc.findall(W + "p")
    if paragraphs:
        p = paragraphs[0]
        rpr = clone_rpr_from_paragraph(p)
        clear_paragraph_content(p)
        append_run(p, text, rpr)
        for extra in paragraphs[1:]:
            tc.remove(extra)
    else:
        p = etree.SubElement(tc, W + "p")
        append_run(p, text, None)


def get_font(size: int, bold: bool = False):
    names = (
        [r"C:\Windows\Fonts\arialbd.ttf", r"C:\Windows\Fonts\calibrib.ttf"]
        if bold
        else [r"C:\Windows\Fonts\arial.ttf", r"C:\Windows\Fonts\calibri.ttf"]
    )
    for name in names:
        if Path(name).exists():
            return ImageFont.truetype(name, size=size)
    return ImageFont.load_default()


def wrap(draw: ImageDraw.ImageDraw, text: str, font, max_width: int) -> list[str]:
    words = text.split()
    lines: list[str] = []
    line = ""
    for word in words:
        trial = word if not line else line + " " + word
        if draw.textbbox((0, 0), trial, font=font)[2] <= max_width:
            line = trial
        else:
            if line:
                lines.append(line)
            line = word
    if line:
        lines.append(line)
    return lines


def centered(draw: ImageDraw.ImageDraw, xy: tuple[int, int], text: str, font, fill=INK):
    x, y = xy
    box = draw.textbbox((0, 0), text, font=font)
    draw.text((x - (box[2] - box[0]) / 2, y), text, font=font, fill=fill)


def academic_box(draw: ImageDraw.ImageDraw, x: int, y: int, w: int, h: int, title: str, body: str,
                 title_size: int = 24, body_size: int = 18) -> None:
    draw.rectangle((x, y, x + w, y + h), fill=PALE, outline=NAVY, width=4)
    header_h = 42
    draw.rectangle((x, y, x + w, y + header_h), fill=NAVY, outline=NAVY)
    centered(draw, (x + w // 2, y + 7), title, get_font(title_size, True), WHITE)
    body_font = get_font(body_size, False)
    lines = wrap(draw, body, body_font, w - 28)
    line_h = max(20, body_size + 4)
    total = line_h * len(lines)
    cy = y + header_h + (h - header_h - total) // 2
    for line in lines:
        centered(draw, (x + w // 2, cy), line, body_font, INK)
        cy += line_h


def arrow(draw: ImageDraw.ImageDraw, start: tuple[int, int], end: tuple[int, int], label: str = "",
          label_offset: tuple[int, int] = (0, 0), dashed: bool = False) -> None:
    x1, y1 = start
    x2, y2 = end
    width = 4
    if dashed:
        total = max(abs(x2 - x1), abs(y2 - y1))
        steps = max(1, total // 20)
        for i in range(0, steps, 2):
            a = i / steps
            b = min(1, (i + 1) / steps)
            draw.line((x1 + (x2 - x1) * a, y1 + (y2 - y1) * a,
                       x1 + (x2 - x1) * b, y1 + (y2 - y1) * b), fill=ARROW, width=width)
    else:
        draw.line((x1, y1, x2, y2), fill=ARROW, width=width)
    # A compact triangular arrowhead, adequate for horizontal and vertical paths.
    if abs(x2 - x1) >= abs(y2 - y1):
        sign = 1 if x2 >= x1 else -1
        pts = [(x2, y2), (x2 - sign * 16, y2 - 9), (x2 - sign * 16, y2 + 9)]
    else:
        sign = 1 if y2 >= y1 else -1
        pts = [(x2, y2), (x2 - 9, y2 - sign * 16), (x2 + 9, y2 - sign * 16)]
    draw.polygon(pts, fill=ARROW)
    if label:
        lf = get_font(15, False)
        mx = (x1 + x2) // 2 + label_offset[0]
        my = (y1 + y2) // 2 + label_offset[1]
        centered(draw, (mx, my), label, lf, BLUE)


def create_architecture(path: Path) -> None:
    canvas = Image.new("RGB", (2200, 1160), WHITE)
    d = ImageDraw.Draw(canvas)
    layer_font = get_font(22, True)
    for x, text in [(245, "Input and Access Layer"), (750, "Event Processing Layer"),
                    (1260, "Data and Analytics Layer"), (1850, "Persistence and Observation Layer")]:
        centered(d, (x, 22), text, layer_font, BLUE)

    academic_box(d, 55, 120, 370, 155, "Telemetry and Dashboard",
                 "Wokwi-compatible ESP32 telemetry or authenticated web request")
    academic_box(d, 55, 420, 370, 180, "API Gateway and Keycloak",
                 "JWT roles and ownership checks for user routes; X-Device-Token for machine ingestion")
    academic_box(d, 530, 120, 365, 155, "Ingestion Service",
                 "Validates payload and publishes the energy-usage event")
    academic_box(d, 530, 420, 365, 155, "Kafka",
                 "energy-usage, energy-alerts, anomaly-results, and failure topics")
    academic_box(d, 1010, 90, 390, 165, "Usage Service and InfluxDB",
                 "Persist time-series usage and compute selected-window aggregates")
    academic_box(d, 1010, 355, 390, 185, "ML Worker and FastAPI RF",
                 "Fixed Random Forest artifact evaluates an event and publishes anomaly-results")
    academic_box(d, 1010, 650, 390, 145, "Insight Service",
                 "Deterministic bill, ranking, and standby outputs from aggregates")
    academic_box(d, 1615, 215, 495, 190, "Alert Service and 15-min Deduplication",
                 "Consumes threshold and ML anomaly paths; suppresses duplicate alert keys")
    academic_box(d, 1615, 530, 495, 150, "MySQL and Mailpit",
                 "Metadata and alert history; local SMTP capture for notification evidence")
    academic_box(d, 1615, 805, 495, 120, "Prometheus and Grafana",
                 "Service metrics and target health observation")

    arrow(d, (240, 275), (240, 420), "REST", (-52, -4))
    arrow(d, (425, 505), (530, 195), "route", (0, -8))
    arrow(d, (712, 275), (712, 420), "energy-usage", (75, -4))
    arrow(d, (895, 500), (1010, 175), "consume", (-10, -18))
    arrow(d, (895, 500), (1010, 448), "consume", (0, -24))
    arrow(d, (1205, 255), (1205, 355), "aggregate", (-85, -2))
    arrow(d, (1400, 448), (1615, 310), "anomaly-results", (0, -23))
    arrow(d, (1400, 175), (1615, 300), "threshold path", (20, -20))
    arrow(d, (1400, 722), (1615, 350), "insight query", (0, 22))
    arrow(d, (1862, 405), (1862, 530), "persist / notify", (95, -3))
    arrow(d, (1900, 805), (1900, 680), "scrape metrics", (115, 7), dashed=True)

    note = "Solid arrows: implemented request/event flow. Dashed arrow: monitoring observation. Wokwi values remain synthetic, not calibrated meter readings."
    d.text((55, 1087), note, font=get_font(14, False), fill=ARROW)
    canvas.save(path, "PNG")


def create_workflow(path: Path) -> None:
    canvas = Image.new("RGB", (2200, 860), WHITE)
    d = ImageDraw.Draw(canvas)
    label_font = get_font(19, True)
    d.text((55, 40), "Offline model path", font=label_font, fill=BLUE)
    top = [
        (55, "CSV data", "5,000 supplied records; labels Normal/Abnormal"),
        (390, "Preprocessing", "Chronological sort; Hour, DayOfWeek, deviation feature"),
        (725, "Selection", "Train/validation split; choose F1 threshold"),
        (1060, "RF artifact", "Fixed model loaded by FastAPI inference service"),
    ]
    for x, title, body in top:
        academic_box(d, x, 85, 270, 135, title, body, 18, 14)
    for i in range(len(top) - 1):
        arrow(d, (top[i][0] + 270, 152), (top[i + 1][0], 152))

    d.text((55, 300), "Runtime telemetry and evidence path", font=label_font, fill=BLUE)
    bottom = [
        (35, "Input", "Wokwi or dashboard telemetry"),
        (330, "Access", "Gateway JWT / device token controls"),
        (625, "Ingest and Kafka", "Validate and publish energy-usage"),
        (920, "Usage and InfluxDB", "Persist and aggregate usage"),
        (1215, "ML and Insight", "RF anomaly results plus deterministic insights"),
        (1510, "Alert dedup", "Threshold/ML paths; 15-min suppression"),
        (1805, "Output", "MySQL, Mailpit, dashboard, metrics"),
    ]
    for x, title, body in bottom:
        academic_box(d, x, 350, 260, 160, title, body, 18, 14)
    for i in range(len(bottom) - 1):
        arrow(d, (bottom[i][0] + 260, 430), (bottom[i + 1][0], 430))
    arrow(d, (1195, 220), (1345, 350), "fixed artifact", (2, -10))

    academic_box(d, 195, 620, 1810, 130, "Controlled local evaluation",
                 "Offline held-out model assessment  |  E2E analytics and alert checks  |  gateway-security status cases  |  duplicate-event suppression  |  Prometheus targets  |  k6 ingress measurement  |  separate Mailpit and ML-service outage availability checks",
                 20, 17)
    d.text((55, 807), "The evaluation path records bounded local evidence; it does not establish physical-meter accuracy, production security, or production-scale resilience.",
           font=get_font(14, False), fill=ARROW)
    canvas.save(path, "PNG")


def update_document_xml(xml_bytes: bytes) -> bytes:
    root = etree.fromstring(xml_bytes)
    body = root.find(W + "body")
    paragraphs = [child for child in body if child.tag == W + "p"]
    if len(paragraphs) != 97:
        raise RuntimeError(f"Unexpected direct paragraph count: {len(paragraphs)} (expected 97)")

    expected = {
        0: "A Microservices-Based Home Energy Tracker for Real-Time Monitoring, Intelligent Alerting, and AI-Driven Energy Insights",
        7: "I. INTRODUCTION",
        17: "III. PROPOSED SYSTEM AND METHODOLOGY",
        55: "V. RESULTS AND DISCUSSION",
        72: "REFERENCES",
    }
    for idx, phrase in expected.items():
        if phrase not in element_text(paragraphs[idx]):
            raise RuntimeError(f"Master paragraph P{idx:03d} does not match the audited document")

    replacements = {
        0: "A Microservices-Based Home Energy Tracker for Event-Driven Monitoring, Deduplicated Alerting, and ML-Based Anomaly Detection",
        8: ("Residential electricity bills provide limited visibility into when energy is consumed, which registered device contributes most, or when a configured threshold is exceeded. A practical Home Energy Management System therefore needs an auditable path from telemetry to stored records, interpretable outputs, and controlled notification. Recent IoT systems demonstrate affordable sensing and remote visualisation, whereas other studies focus on energy analytics or anomaly detection [3]-[6], [13], [16], [18]-[21], [23]."),
        9: ("This work addresses the integration of a local, event-driven energy platform rather than the accuracy of a physical meter. The deployed composition separates user and device metadata, ingestion, usage, insight, alert, API gateway, and ML inference functions, and includes Kafka, InfluxDB, MySQL, Mailpit, Keycloak, Prometheus, Grafana, and a frontend. Wokwi supplies timestamped synthetic JSON payloads to the same HTTP ingestion contract intended for a future meter; Kafka decouples request acceptance from downstream persistence and analysis."),
        10: ("The study makes three bounded contributions: it implements a 17-service local Docker path from simulated telemetry to time-series storage and access-controlled APIs; it trains and deploys a fixed anomaly-inference artifact while retaining deterministic bill, ranking, standby, and threshold functions; and it records controlled local evidence for end-to-end behavior, gateway security, alert deduplication, observability, ingress load, and selected outage conditions. The scope excludes calibrated sensing, utility-bill validation, physical-field generalisation, production penetration testing, and production-scale resilience claims."),
        13: ("The literature represented in the source paper spans three complementary directions. Low-cost IoT systems use ESP32-class controllers and energy sensors to expose consumption or power-quality information [3]-[6], [13], [16], [18]-[21], [23]. Their measurement evidence cannot be transferred to the Wokwi-generated values used here. A second direction uses machine-learning or statistical methods for appliance classification, anomaly detection, and behavioural analysis [1], [7]-[11], [15], [22]. The present system evaluates a binary classifier only on its supplied labelled CSV and does not equate those results with real-household anomaly performance."),
        14: ("A third direction considers microservices, cloud organisation, or distributed control for energy-management systems [2], [12], [14], [17], [24]. These works motivate service separation, event processing, and maintainability, while leaving a practical need for a traceable prototype that links a telemetry contract, access-controlled API boundary, event broker, time-series persistence, deterministic insights, anomaly inference, and duplicate-aware notification. The present work adopts this integration focus without claiming equivalence to the scale or fault tolerance targeted by prior architectural research."),
        16: ("The research gap is limited implementation-level linkage between residential telemetry, event-driven services, controlled access, historical storage, transparent analytics, anomaly inference, and alert delivery with explicit verification boundaries. The proposed system addresses that gap through Wokwi-compatible telemetry, gateway admission control, Spring Boot microservices, Kafka, InfluxDB, MySQL, a deployed Random Forest artifact, deterministic insight functions, and Mailpit-backed alerting with a configured deduplication window. Remaining gaps include calibrated sensing, documented dataset provenance, per-household contextual labels, field validation, production-grade security assessment, and distributed resilience evaluation."),
        19: ("The runtime input contains deviceId, energyConsumed, and timestamp. Wokwi firmware emits this JSON payload at an approximately 8 s interval; Eco, Heavy, and Alert Test modes generate controlled values for integration demonstration and are not calibrated physical measurements. User-facing requests enter through the API Gateway with Keycloak JWT, realm-role, and ownership checks, while Wokwi-compatible ingestion uses an X-Device-Token. The Ingestion Service validates accepted payloads and publishes energy-usage events to Kafka."),
        20: ("The Usage Service consumes energy-usage events, writes time-stamped energy_usage points to InfluxDB, and derives selected-window aggregates. User and Device Services maintain household, appliance, and alert-setting metadata in MySQL. In parallel, an ML worker calls a FastAPI service that loads a fixed Random Forest artifact and publishes anomaly-results. Threshold and anomaly paths reach the Alert Service, which persists notifications and uses a configured 15-min deduplication window. Prometheus and Grafana provide service-level target and metric observation."),
        26: ("The Insight Service derives deterministic outputs from aggregated usage. It computes a daily rate and a 30-day energy projection from total energy E over D selected days. The configured local tariff uses a fixed 10.00 charge and slab rates of 0.12 per kWh for 0-100 kWh, 0.18 per kWh for 100-300 kWh, and 0.25 per kWh above 300 kWh. Device ranking uses each device total divided by the household total, and the standby estimate remains 20% of average load. These are demonstration rules, not a utility tariff or an appliance-level standby measurement."),
        28: ("The anomaly branch uses the supplied smart_meter_data.csv with 5,000 records and seven columns, including Electricity_Consumed, weather/context fields, Avg_Past_Consumption, and Anomaly_Label (4,750 Normal and 250 Abnormal). Records are stably ordered by timestamp; Hour, DayOfWeek, and ConsumptionDeviation = Electricity_Consumed - Avg_Past_Consumption are derived. A chronological 3,500/750/750 train/validation/test split compares a balanced logistic-regression pipeline with a 300-tree balanced-subsample Random Forest. The Random Forest threshold 0.31 is selected by validation F1 and its saved artifact is loaded at FastAPI startup; missing optional context is median-imputed. The dataset source, licence, and label-generation provenance are not documented."),
        30: ("For threshold alerting, a scheduler evaluates the preceding one-hour household sum every 10 s. When alerting is enabled and the sum exceeds the user-defined threshold, an energy-alerts event is published. The Alert Service consumes threshold and ML anomaly paths, persists alerts in MySQL, and attempts SMTP delivery with Mailpit as the local demonstration inbox. Its deduplication key is userId:deviceId-or-HOUSEHOLD:alertType; matching keys are suppressed during the configured 15-min window. The ML worker includes a bounded default of three attempts and an anomaly-processing-failures topic as implemented handling, not as a separately evaluated recovery guarantee."),
        37: ("Fig. 2 summarises the verified offline and runtime paths. The upper lane prepares the supplied CSV, selects the model and threshold on validation data, and produces a fixed inference artifact. The runtime lane keeps authorised telemetry admission, ingestion, Kafka publication, usage persistence, ML inference, deterministic insight generation, alert deduplication, and output delivery distinct. Controlled E2E, security, deduplication, target-health, ingress-load, and selected outage checks are evaluation branches rather than evidence of a single production benchmark."),
        44: ("The system was exercised as a local, single-host Docker deployment on Windows 11 Home Single Language (10.0.26300) with eight logical processors and 7.74 GiB RAM. The compose configuration defines 17 services covering relational, event, time-series, e-mail, identity, application, frontend, and observability functions. The environment supports controlled implementation and verification; it is not a replicated cloud or production deployment."),
        57: ("Table III separates model, functional, security, monitoring, load, and fault evidence because these measurements were collected by different controlled procedures. The latest successful E2E run confirms request-to-output traceability, while the supplied CSV assessment quantifies only data-specific model performance. The historical Java summary records 28 completed tests with no failures or errors and three skips; three Python tests passed, and the post-fix gateway regression passed 4/4. These records should not be interpreted as one unified production-readiness score."),
        64: ("On the supplied held-out CSV, the Random Forest achieved substantially stronger precision, F1, ROC-AUC, and PR-AUC than the logistic-regression baseline. This supports the selection of the saved Random Forest artifact for this dataset and split, but it does not validate field anomaly detection. The E2E analytics and alert observations demonstrate a traceable local integration path from synthetic REST input to stored usage, deterministic outputs, and a captured notification; they do not establish physical-meter accuracy or utility-bill agreement."),
        65: ("The eight expected gateway statuses provide functional evidence for the tested authentication, authorization, ownership, administrator, device-token, and expiry scenarios. The duplicate-event experiment demonstrates one controlled suppression within the 15-min window. The Prometheus snapshot shows eight active targets up, and the k6 result measures only local gateway ingestion under the stated workload. The two outage checks show that ingress returned HTTP 201 while Mailpit or ML inference was stopped and that manual restart recovered the container; they do not demonstrate automatic recovery, replay, notification delivery, or general fault tolerance."),
        66: ("The data and runtime boundaries remain material. The CSV has no documented source, licence, label provenance, household/device identifier, or provenance for Avg_Past_Consumption. Its Electricity_Consumed values are in an undocumented 0-1 range, whereas Wokwi modes send direct values in approximately the 1-40 range; optional Wokwi context is median-imputed and no range-validation or calibration experiment is reported. No runtime ML latency is reported because the observed inference-latency counter had zero samples."),
        68: ("The principal limitations are synthetic, non-calibrated Wokwi telemetry; the anonymous dataset and missing provenance; the training-to-Wokwi unit/range mismatch; and the absence of physical-meter, utility-bill, and external-field validation. The evaluation uses one local Docker host with a bounded ingress test, no distributed tracing or Kafka-lag study, and only selected manually recovered service-outage checks. Keycloak and gateway controls were functionally checked in eight HTTP cases, but no TLS/cloud deployment or penetration assessment was performed. The deterministic standby estimate remains a 20% average-load heuristic."),
        69: ("Future work should collect consented, documented, calibrated interval-meter data with per-device and household context; establish label and feature provenance; and add range or out-of-distribution checks before model deployment. It should repeat end-to-end and load measurements over longer workloads, add tracing and Kafka-lag instrumentation, and perform automated fault, retry, failure-topic, replay, and recovery experiments. Production hardening should address TLS, secret rotation, device provisioning, and an independent security assessment before any real-world deployment claim."),
        71: ("This paper presents a microservices-based Home Energy Tracker updated from an integration baseline to a locally evaluated event-driven system with gateway access controls, Kafka-mediated processing, InfluxDB and MySQL persistence, deterministic insights, a deployed Random Forest inference artifact, alert deduplication, and Prometheus/Grafana observation. Controlled evidence includes the supplied CSV model assessment, synthetic E2E analytics and alert checks, eight gateway-security cases, duplicate suppression, an eight-target snapshot, local k6 ingress measurement, and two limited outage-availability observations. The work demonstrates implementation-level integration and bounded local verification; it does not establish meter accuracy, externally generalisable anomaly detection, production-scale performance, comprehensive resilience, or production security."),
        23: "Fig. 1. Verified service architecture and data paths of the Home Energy Tracker.",
        33: "Verified System Components and Traceable Data Flow",
        40: "Fig. 2. Verified telemetry-to-alert workflow and evaluation path.",
        47: "Local Experimental Environment and Evidence Conditions",
        60: "Verified Local Evaluation Results",
    }
    for idx, text in replacements.items():
        set_paragraph(paragraphs[idx], text)

    set_label_body_paragraph(
        paragraphs[5],
        "Abstract - ",
        "Residential energy platforms require a traceable route from meter-like telemetry to controlled feedback. This study implements a local 17-service Docker composition combining Wokwi-compatible ESP32 telemetry, API-gateway admission control, Apache Kafka, InfluxDB, MySQL, deterministic insights, and duplicate-aware alert delivery. User-facing routes apply Keycloak JWT, role, and ownership checks, while simulated-device ingestion uses a device token. A Random Forest anomaly model is selected by validation F1 from the supplied CSV and deployed as a fixed FastAPI artifact; its held-out precision, recall, F1, ROC-AUC, and PR-AUC are 0.880952, 0.925000, 0.902439, 0.997430, and 0.948532, respectively. Controlled local checks recorded a 1.50 kWh analytics case, a 1.00 kWh threshold-alert case, eight expected security statuses, duplicate suppression within 15 min, eight active Prometheus targets, and 450/450 accepted k6 ingestion requests. The results demonstrate implementation-level integration and bounded local evidence, not physical-meter accuracy, field-model generalisation, production security, or production-scale resilience.",
    )
    set_label_body_paragraph(
        paragraphs[6],
        "Keywords - ",
        "Home Energy Tracker, Internet of Things, microservices, Apache Kafka, anomaly detection, Keycloak, alert deduplication, Wokwi simulation.",
    )
    set_label_body_paragraph(
        paragraphs[51],
        "1. ",
        "The latest successful controlled local E2E case submitted 0.25, 0.50, and 0.75 kWh analytics inputs for user 15/device 314 and a separate 1.00 kWh threshold input for user 16/device 315, whose configured threshold was 0.10 kWh.",
    )
    set_label_body_paragraph(
        paragraphs[52],
        "2. ",
        "The offline procedure stably sorted the supplied CSV, produced chronological train/validation/test partitions of 3,500/750/750 records, selected the threshold by validation F1, and evaluated the chosen and logistic-regression baseline models once on the held-out partition.",
    )
    set_label_body_paragraph(
        paragraphs[53],
        "3. ",
        "Gateway-security checks covered owned access, missing, invalid, and expired JWTs, cross-user access, administrator access, and device-token ingestion. Separate controlled checks examined duplicate-event suppression and the Prometheus target snapshot.",
    )
    set_label_body_paragraph(
        paragraphs[54],
        "4. ",
        "Local ingress was measured with k6 at 2, 5, and 10 requests/s for 30 s stages plus ramp-down; separate Mailpit and ML-service outage checks recorded ingress availability and manual container recovery. Historic Java tests (28 completed, three skipped), three Python in-process tests, and a later four-test gateway regression are reported without being merged into one fresh suite total.",
    )

    tables = [child for child in body if child.tag == W + "tbl"]
    if len(tables) != 3:
        raise RuntimeError(f"Unexpected table count: {len(tables)}")
    table_rows = [[tr for tr in tbl.findall(W + "tr")] for tbl in tables]
    expected_shapes = [(6, 3), (7, 2), (9, 3)]
    for rows, shape in zip(table_rows, expected_shapes):
        if len(rows) != shape[0] or any(len(row.findall(W + "tc")) != shape[1] for row in rows):
            raise RuntimeError("Master table geometry does not match the preservation contract")

    table_data = [
        [
            ["Stage", "Implemented component and technique", "Output"],
            ["Access and telemetry", "Keycloak JWT, roles, and ownership protect user routes; Wokwi-compatible ingestion uses X-Device-Token.", "Authorised request or machine admission."],
            ["Ingestion and event transfer", "Ingestion validates payloads and publishes Kafka energy-usage events.", "Asynchronous energy event."],
            ["Storage and aggregation", "Usage writes InfluxDB energy_usage points; User/Device metadata and alert records use MySQL.", "Selected-window device and household totals."],
            ["Model and insight", "ML worker calls the fixed FastAPI Random Forest artifact and publishes anomaly-results; Insight computes bill, ranking, and standby.", "Anomaly probability and deterministic outputs."],
            ["Alerting and observation", "Threshold and ML paths reach Alert Service, which applies 15-min deduplication and uses Mailpit; Prometheus/Grafana observe services.", "Alert/email evidence and service metrics."],
        ],
        [
            ["Element", "Documented configuration"],
            ["Runtime and deployment", "Windows 11 Home Single Language 10.0.26300; local single-host Docker with eight logical processors and 7.74 GiB RAM. The compose file defines 17 services across data, application, identity, monitoring, and frontend functions."],
            ["Application and data stack", "Java 17 Spring Boot services and API Gateway; React/Vite frontend; Apache Kafka, MySQL, InfluxDB, Mailpit, Keycloak, Prometheus, and Grafana. The source configuration defines this local service composition."],
            ["IoT simulation", "Wokwi ESP32 DevKit with potentiometer, pushbuttons, and SSD1306 OLED. It posts Wokwi-compatible synthetic telemetry and is not a calibrated physical meter."],
            ["CSV data and model", "smart_meter_data.csv: 5,000 records, seven columns, and Normal/Abnormal labels of 4,750/250. A chronological 3,500/750/750 split selects the Random Forest by validation F1. Source, licence, and label provenance are undocumented."],
            ["Controlled local E2E", "0.25, 0.50, and 0.75 kWh analytics inputs for user 15/device 314; a 1.00 kWh threshold input for user 16/device 315. These are synthetic REST observations."],
            ["Evaluation protocols", "Gateway-security status cases; duplicate-event check; Prometheus target snapshot; k6 POST arrival-rate stages of 2/5/10 requests/s; separate Mailpit and ML-service outage availability checks with manual restart."],
        ],
        [
            ["Verification item", "Condition", "Observed result"],
            ["Random Forest held-out test", "750 records; selected threshold = 0.31.", "TN 705, FP 5, FN 3, TP 37; precision 0.880952; recall 0.925000; F1 0.902439; ROC-AUC 0.997430; PR-AUC 0.948532."],
            ["Logistic-regression baseline", "Same held-out partition; threshold = 0.28.", "Precision 0.053333; recall 1.000000; F1 0.101266; ROC-AUC 0.422852; PR-AUC 0.059710."],
            ["Controlled E2E analytics", "Three inputs total 1.50 kWh.", "3/3 HTTP 201; cost $0.18; daily 0.50 kWh; projected 15.00 kWh/$11.80; rank 100%; standby 4.17 W/LOW; observed within polling-bounded 3.79 s."],
            ["Threshold alert and Mailpit", "1.00 kWh input exceeds 0.10 kWh threshold.", "HTTP 201; persisted sent THRESHOLD alert and matching Mailpit email; observed within polling-bounded 13.64 s."],
            ["Gateway security", "Eight configured access-control cases.", "8/8 expected statuses: owned 200; missing/invalid/expired JWT 401; cross-user 403; administrator 200; device-token ingestion 201."],
            ["Alert deduplication", "Two identical 1.00-kWh events at the same timestamp.", "One ML_ANOMALY alert was stored and a duplicate was explicitly suppressed within 15 min."],
            ["Observability", "Prometheus target snapshot.", "8/8 active targets up. No runtime inference latency is reported because the observed counter had zero samples."],
            ["Local ingress and fault checks", "k6 2/5/10 requests/s; Mailpit and ML separately stopped.", "450/450 accepted; mean 39.442 ms; p95 109.773 ms; 0% HTTP failure. During each outage, ingestion returned 201 and manual restart recovered the container."],
        ],
    ]
    for rows, values in zip(table_rows, table_data):
        for row, row_values in zip(rows, values):
            for cell, value in zip(row.findall(W + "tc"), row_values):
                set_cell(cell, value)

    return etree.tostring(root, xml_declaration=True, encoding="UTF-8", standalone=True)


def rebuild_docx(updated_xml: bytes, fig1: Path, fig2: Path) -> None:
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(SOURCE, OUTPUT)
    replacement = {
        "word/document.xml": updated_xml,
        "word/media/image1.png": fig1.read_bytes(),
        "word/media/image2.png": fig2.read_bytes(),
    }
    with zipfile.ZipFile(OUTPUT, "r") as zin:
        infos = zin.infolist()
        contents = {info.filename: zin.read(info.filename) for info in infos}
    missing = set(replacement) - set(contents)
    if missing:
        raise RuntimeError(f"Missing DOCX package parts: {sorted(missing)}")
    temp_output = OUTPUT.with_suffix(".patched.docx")
    with zipfile.ZipFile(temp_output, "w", compression=zipfile.ZIP_DEFLATED) as zout:
        for info in infos:
            data = replacement.get(info.filename, contents[info.filename])
            cloned = copy.copy(info)
            cloned.file_size = 0
            cloned.compress_size = 0
            cloned.CRC = 0
            zout.writestr(cloned, data)
    temp_output.replace(OUTPUT)


def verify_structure() -> None:
    with zipfile.ZipFile(OUTPUT, "r") as z:
        xml = z.read("word/document.xml")
        root = etree.fromstring(xml)
        body = root.find(W + "body")
        paragraphs = [child for child in body if child.tag == W + "p"]
        tables = [child for child in body if child.tag == W + "tbl"]
        media = {n: z.read(n) for n in ["word/media/image1.png", "word/media/image2.png"]}
    if len(paragraphs) != 97 or len(tables) != 3:
        raise RuntimeError("Structural verification failed: unexpected body paragraph/table count")
    if "Deduplicated Alerting" not in element_text(paragraphs[0]):
        raise RuntimeError("Structural verification failed: title update is missing")
    if any(len(b) < 10_000 for b in media.values()):
        raise RuntimeError("Structural verification failed: a replacement figure is unexpectedly small")
    # Drawing extents and relationships are intentionally left unmodified.
    if len(root.xpath(".//wp:inline", namespaces={"wp": "http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing"})) != 2:
        raise RuntimeError("Structural verification failed: inline figure count changed")


def main() -> None:
    if not SOURCE.exists():
        raise FileNotFoundError(SOURCE)
    TEMP.mkdir(parents=True, exist_ok=True)
    fig1 = TEMP / "updated-architecture.png"
    fig2 = TEMP / "updated-workflow.png"
    create_architecture(fig1)
    create_workflow(fig2)
    with zipfile.ZipFile(SOURCE, "r") as z:
        updated_xml = update_document_xml(z.read("word/document.xml"))
    rebuild_docx(updated_xml, fig1, fig2)
    verify_structure()
    print(OUTPUT)


if __name__ == "__main__":
    main()
