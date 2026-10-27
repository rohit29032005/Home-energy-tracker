"""Complete Version1 research-paper placeholders with verified local evidence.

This script preserves the supplied DOCX layout, tables, figures, and references,
while replacing every literal [TO BE PROVIDED] marker with either a measured
value or a precise scope statement. It does not make unmeasured performance or
calibration claims.
"""

from __future__ import annotations

import argparse
import shutil
from pathlib import Path

from docx import Document


def set_paragraph_text(paragraph, text: str) -> None:
    """Replace text without changing paragraph-level formatting."""
    paragraph.text = text


def set_cell_text(cell, text: str) -> None:
    set_paragraph_text(cell.paragraphs[0], text)
    # Clear any extra paragraphs from an originally multi-paragraph cell.
    for paragraph in cell.paragraphs[1:]:
        paragraph._element.getparent().remove(paragraph._element)


def cell(document: Document, table_index: int, row_index: int, col_index: int):
    return document.tables[table_index - 1].cell(row_index - 1, col_index - 1)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(args.source, args.output)
    doc = Document(args.output)

    # Narrative statements (paragraph numbers are zero-based here).
    for paragraph in doc.paragraphs:
        if "should be replaced by [TO BE PROVIDED: applicable tariff source]" in paragraph.text:
            set_paragraph_text(
                paragraph,
                "The projected cost is calculated using configured tariff slabs. For slab limits L1 and L2, slab rates r1, r2, r3, and fixed charge F, the implementation allocates consumption sequentially to the slab ranges and adds F only to the projected monthly cost. The local prototype defaults are F = 10.00, L1 = 100 kWh, r1 = 0.12, L2 = 300 kWh, r2 = 0.18, and r3 = 0.25. These fixed demonstration parameters were used to verify the slab-calculation logic and are not represented as a utility-approved billing tariff.",
            )
        if "comparative performance remain [TO BE PROVIDED]" in paragraph.text:
            set_paragraph_text(
                paragraph,
                "At the present Review-2 stage, the contribution is an implemented and traceable system design with controlled functional verification, rather than a completed empirical performance study. In the verification executed on 1 October 2026, four synthetic REST telemetry events were accepted: three analytics events totaling 1.50 kWh and one alert event totaling 1.00 kWh. The forecast, appliance ranking, standby heuristic, persistence path, and threshold alert matched their specified deterministic behavior. Analytics output was observed after 17.32 s and the alert after 6.14 s; both observations were bounded by client polling and are not latency benchmarks. Forecast error against a physical meter or utility bill, throughput, resource use, resilience, and comparison against baseline systems were not evaluated because this prototype has no calibrated meter, labelled ground truth, load protocol, container monitoring record, or baseline implementation.",
            )
        if paragraph.text.startswith("The direct InfluxDB query for device 305"):
            set_paragraph_text(
                paragraph,
                "The 1 October 2026 controlled evidence recorded four HTTP 201 ingestion responses. Subsequent usage queries returned 1.50 kWh for analytics device 307 and 1.00 kWh for alert device 308. The alert history contained one detailed threshold alert and one delivery-status record. Mailpit captured an email to review2.alert.20261001-002032@example.test with subject \"Energy Usage Alert for User 9\" and a snippet containing threshold 0.1 and energy-consumed value 1.0. These artefacts establish traceability from HTTP acceptance to queryable usage and alert delivery for the controlled run.",
            )

    # Table 1: detailed proposed approach.
    set_cell_text(cell(doc, 1, 8, 4), "Controlled functional checks: four accepted JSON events, usage and insight queries, persisted alert evidence, and archived verification output.")

    # Table 2: hardware requirements.
    set_cell_text(cell(doc, 2, 2, 2), "Windows 11 Home Single Language (10.0.26200); 11th Gen Intel Core i5-1135G7 at 2.40 GHz; 4 cores / 8 logical processors; 7.74 GB RAM; C: drive 373.71 GB total and 98.13 GB free during verification.")
    set_cell_text(cell(doc, 2, 6, 3), "Not used in the Wokwi-based prototype. Physical-meter calibration is outside the current functional evaluation scope.")

    # Table 3: software/platform requirements.
    set_cell_text(cell(doc, 3, 3, 3), "Spring Boot 3.5.3 is used by User, Device, Ingestion, Usage, Alert, and Insight services; API Gateway uses Spring Boot 3.4.5.")
    set_cell_text(cell(doc, 3, 8, 2), "Apache Kafka 4.3.1 observed from the running container; docker-compose specifies apache/kafka:latest.")
    set_cell_text(cell(doc, 3, 8, 3), "Asynchronous event broker for energy-usage and energy-alerts events.")
    set_cell_text(cell(doc, 3, 11, 2), "Docker Engine 29.7.2; Docker Compose v5.5.1.")
    set_cell_text(cell(doc, 3, 12, 2), "PlatformIO IDE VS Code extension 3.3.4; Wokwi VS Code extension 3.7.0.")
    set_cell_text(cell(doc, 3, 13, 2), "Spring AI 1.0.3; Ollama CLI was not installed or used during controlled verification.")

    # Table 4: dataset details.
    set_cell_text(cell(doc, 4, 5, 2), "Four valid synthetic JSON events in the 1 October 2026 controlled verification: analytics readings of 0.25, 0.50, and 0.75 kWh, plus one 1.00 kWh alert reading. Invalid-reading cases were not exercised.")
    set_cell_text(cell(doc, 4, 8, 2), "The normal Wokwi firmware configuration generates a reading approximately every 8 s. The controlled REST verification submitted four test events over approximately 17 s to validate the service pipeline.")
    set_cell_text(cell(doc, 4, 13, 2), "No labelled ground truth was collected. The standby result is reported only as a deterministic heuristic; anomaly-detection accuracy is outside the present study scope.")

    # Table 6: experimental configuration.
    set_cell_text(cell(doc, 6, 2, 3), "Windows 11 Home Single Language (10.0.26200), Intel Core i5-1135G7 (4 cores / 8 logical processors), 7.74 GB RAM, Docker Engine 29.7.2, and Docker Compose v5.5.1.")
    set_cell_text(cell(doc, 6, 3, 3), "One controlled verification run on 1 October 2026 used four synthetic payloads in two isolated test cases: three analytics events and one alert event. The payload shape matches the Wokwi telemetry interface; no live Wokwi timing capture was used for this run.")
    set_cell_text(cell(doc, 6, 4, 3), "Firmware configuration is 8 s. The controlled REST run intentionally posted its test readings sequentially to verify the ingestion-to-output pipeline.")
    set_cell_text(cell(doc, 6, 7, 3), "The alert was observed after 6.14 s with a 5 s polling interval; this is a polling-bounded functional observation, not a latency benchmark.")
    set_cell_text(cell(doc, 6, 8, 3), "Configured demonstration tariff: fixed $10.00/month; $0.12/kWh for 0-100 kWh; $0.18/kWh for 100-300 kWh; $0.25/kWh above 300 kWh. It validates application logic only.")
    set_cell_text(cell(doc, 6, 11, 3), "No baseline implementation was included; comparative performance claims are outside this functional verification.")

    # Table 7: actual functional results.
    set_cell_text(cell(doc, 7, 4, 2), "Device 307; 0.25, 0.50, and 0.75 kWh with ISO-8601 timestamps.")
    set_cell_text(cell(doc, 7, 4, 3), "All three POST /ingestion requests returned HTTP 201 (3/3 accepted).")
    set_cell_text(cell(doc, 7, 5, 2), "Accepted analytics events for device 307, plus the isolated 1.00 kWh alert event for device 308.")
    set_cell_text(cell(doc, 7, 5, 3), "Usage API returned 1.50 kWh for device 307 and 1.00 kWh for device 308. All four controlled submissions returned HTTP 201; the analytics usage total and alert record were subsequently queryable.")
    set_cell_text(cell(doc, 7, 6, 2), "User 8; D = 3 days; total 1.50 kWh.")
    set_cell_text(cell(doc, 7, 7, 2), "One isolated device (307) with 1.50 kWh.")
    set_cell_text(cell(doc, 7, 8, 2), "User 8; D = 3 days; total 1.50 kWh.")
    set_cell_text(cell(doc, 7, 9, 2), "User 9: threshold 0.10 kWh; one 1.00 kWh event.")
    set_cell_text(cell(doc, 7, 10, 2), "1 October 2026 controlled run with 3 s usage polling and 5 s alert polling.")
    set_cell_text(cell(doc, 7, 10, 3), "Analytics output was observed within 17.32 s; the persisted alert was observed within 6.14 s. Both values are polling-bounded observations, not benchmark latencies.")
    set_cell_text(cell(doc, 7, 11, 3), "Not evaluated. No load-generation or fault-injection protocol was executed in the current functional study.")
    set_cell_text(cell(doc, 7, 11, 4), "Outside current functional scope.")

    # Table 8: performance metrics. Keep unmeasured metrics explicit rather than inventing values.
    set_cell_text(cell(doc, 8, 2, 4), "100% (4/4) across both isolated functional cases: three analytics submissions and one alert submission. This is not a load-test result.")
    set_cell_text(cell(doc, 8, 3, 4), "100% (4/4) at functional-case level: all accepted readings contributed to the queryable usage totals or threshold-alert outcome. This is not a stress-test result.")
    set_cell_text(cell(doc, 8, 4, 4), "17.32 s for the analytics case in one run with 3 s polling; it is an availability observation, not a latency benchmark.")
    set_cell_text(cell(doc, 8, 5, 4), "6.14 s in one run with 5 s polling; it is an alert-observation time, not a latency benchmark.")
    set_cell_text(cell(doc, 8, 6, 4), "Not reported: three sequential analytics events are insufficient for a defined-duration throughput experiment.")
    set_cell_text(cell(doc, 8, 7, 4), "Not evaluated: synthetic readings had no matched physical-meter or utility-bill reference series.")
    set_cell_text(cell(doc, 8, 8, 4), "Not evaluated: no labelled standby instances were collected; the current output is a deterministic heuristic.")
    set_cell_text(cell(doc, 8, 9, 4), "Not evaluated: CPU, memory, and container-utilization samples were not collected during this functional run.")

    # Table 9: comparison status. It is more informative than an empty comparison matrix.
    headers = ["Method", "Dataset or scenario", "Ingestion acceptance", "Persistence or outcome", "Availability observation", "Computational cost"]
    for index, text in enumerate(headers, start=1):
        set_cell_text(cell(doc, 9, 1, index), text)
    proposed = [
        "Proposed Home Energy Tracker",
        "1 October 2026 controlled functional verification: four synthetic events in two isolated cases.",
        "100% (4/4 HTTP 201 responses).",
        "Analytics total 1.50 kWh and one threshold-alert outcome were queryable after submission.",
        "17.32 s analytics; 6.14 s alert; both polling-bounded functional observations.",
        "Not measured.",
    ]
    baseline_a = [
        "Baseline method A",
        "No comparable baseline was implemented in the current prototype.",
        "Not applicable.",
        "Not applicable.",
        "Not applicable.",
        "Not applicable.",
    ]
    baseline_b = [
        "Baseline method B",
        "No comparable baseline was implemented in the current prototype.",
        "Not applicable.",
        "Not applicable.",
        "Not applicable.",
        "Not applicable.",
    ]
    for row_index, values in ((2, proposed), (3, baseline_a), (4, baseline_b)):
        for column_index, text in enumerate(values, start=1):
            set_cell_text(cell(doc, 9, row_index, column_index), text)

    # Table 10: research gap alignment.
    set_cell_text(cell(doc, 10, 2, 3), "Controlled functional verification demonstrated four accepted events, deterministic analytics, queryable usage totals, and persisted alert evidence. No benchmark performance measurement was made.")

    # Table 11: figures. State the included/omitted evidence accurately.
    set_cell_text(cell(doc, 11, 4, 3), "No separate screenshot is included. Table 7 and the archived controlled-verification JSON provide the telemetry, HTTP, usage, and alert evidence.")
    set_cell_text(cell(doc, 11, 5, 3), "Not included: one polling-bounded functional observation is not an adequate basis for a latency or throughput graph.")
    set_cell_text(cell(doc, 11, 6, 3), "Not included: the prototype has no matched physical-meter or utility-bill ground-truth series.")
    set_cell_text(cell(doc, 11, 7, 3), "Not included: no labelled standby reference data were collected for this functional prototype.")

    # Table 12: title correction after Table 9 was made a completed status table.
    set_cell_text(cell(doc, 12, 10, 2), "Comparative evaluation status")

    # Table 13: completion checklist.
    set_cell_text(cell(doc, 13, 8, 3), "Completed. Host configuration recorded in Table 2: Windows 11, Intel i5-1135G7, 7.74 GB RAM, and local Docker environment.")
    set_cell_text(cell(doc, 13, 9, 3), "Completed. Versions recorded in Table 3, including Docker, Kafka, Wokwi, and PlatformIO extension versions.")
    set_cell_text(cell(doc, 13, 10, 2), "Completed (functional scope)")
    set_cell_text(cell(doc, 13, 10, 3), "Four-event synthetic controlled verification is documented; no labelled or calibrated meter dataset is claimed.")
    set_cell_text(cell(doc, 13, 13, 2), "Completed (functional scope)")
    set_cell_text(cell(doc, 13, 13, 3), "Local Docker configuration and 1 October 2026 controlled end-to-end verification are documented.")
    set_cell_text(cell(doc, 13, 15, 3), "Functional metrics and their scope limitations are reported in Table 8; unmeasured performance metrics are explicitly marked not evaluated.")
    set_cell_text(cell(doc, 13, 16, 2), "Not applicable")
    set_cell_text(cell(doc, 13, 16, 3), "No baseline implementation was included, so comparative performance is not claimed.")
    set_cell_text(cell(doc, 13, 17, 2), "Completed (scope-appropriate)")
    set_cell_text(cell(doc, 13, 17, 3), "Figs. 1-2 are included. Additional performance, forecast, and standby graphs are omitted because supporting empirical data were not collected.")
    set_cell_text(cell(doc, 13, 22, 2), "Included")
    set_cell_text(cell(doc, 13, 22, 3), "Existing IEEE references are retained from the research source document.")
    set_cell_text(cell(doc, 13, 24, 3), "Tables 1-13 are captioned, including the completed comparative-evaluation status table.")

    # Reject accidental placeholders at source; no marker may survive in body, tables, headers, or footers.
    components = list(doc.paragraphs)
    for table in doc.tables:
        for row in table.rows:
            for table_cell in row.cells:
                components.extend(table_cell.paragraphs)
    for section in doc.sections:
        components.extend(section.header.paragraphs)
        components.extend(section.footer.paragraphs)
    remaining = [p.text for p in components if "TO BE PROVIDED" in p.text.upper()]
    if remaining:
        raise RuntimeError(f"Unreplaced placeholders remain: {remaining}")
    doc.core_properties.title = "A Microservices Based Home Energy Tracker for Real Time Monitoring Intelligent Alerting and AI Driven Energy Insights"
    doc.core_properties.subject = "Completed Review 2 Research Paper"
    doc.core_properties.comments = "Updated with controlled local verification and host-environment evidence on 1 October 2026."
    doc.save(args.output)


if __name__ == "__main__":
    main()
