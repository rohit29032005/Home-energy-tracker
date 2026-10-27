# Retained manuscript template contract

## Reference identity and inspection evidence

- Retained reference: `C:\Users\anju2\Desktop\Home-Energy-Tracker\research-output\Home_Energy_Tracker_Final_Verified_Research_Paper.docx`
- SHA-256: `95557B159CD6FAE12F206DB85EA6CB01A593BE612656C8365349B47323A95B13`
- Rendered reference: `C:\Users\anju2\Desktop\Home-Energy-Tracker\experiments\publication_final\_docx_work\template_reference_render\template_reference.pdf` and `page-1.png` through `page-9.png`.
- Render source: read-only Microsoft Word PDF export because the bundled LibreOffice renderer was not available on this host. The PDF has 9 Letter portrait pages.
- Static audits: `template_style_evidence.json`; direct section, heading, image, field, footnote, and SDT checks. There is one section, eight tables, three inline PNG figures, no fields, no footnotes/endnotes, and no Word content controls.

## Page system and repeating furniture

- Page size: US Letter, portrait, 612 x 792 pt.
- Section count: 1; no landscape or multi-column section was observed.
- Margins: top 0.6493 in, bottom 0.6104 in, left/right 0.6694 in; header/footer distance 0.2757 in.
- Header: a small grey, centered manuscript label above a thin pale-blue rule.
- Footer: small grey, centered evidence-review date statement.
- The reference has no page-number field. Keep the one-section geometry, header treatment, footer treatment, and blue heading system unless a content correction explicitly requires a change.

## Typography and component patterns

- Body text: predominantly Times New Roman, justified, black, approximately 10.5–11 pt, with compact but readable academic paragraph spacing.
- Main numbered headings: dark navy, bold, uppercase, Times New Roman, approximately 16 pt.
- Secondary headings: dark navy, bold, approximately 12 pt.
- Title block: centred dark navy bold serif title; centred bold author line; italic affiliation; compact blue-grey contact line. Preserve authorship and affiliation exactly.
- Abstract and index terms: bold labels followed by a continuous justified paragraph. The abstract is placed on page 1 before the first main heading.
- Tables: italic centred uppercase caption immediately above the table; dark-navy header fill with white bold text; black borders; alternating pale blue-grey rows; readable small serif text.
- Figures: centred inline PNGs, centred italic captions below. Existing architecture (Fig. 1), workflow (Fig. 2), and confusion-matrix (Fig. 3) are retainable assets if their captions are made evidence-accurate.
- Algorithm: dark navy bold label plus monospaced/indented numbered steps.

## Content flow and editable slot map

| Locator | Source role | Action for final manuscript |
| --- | --- | --- |
| `word/document.xml:P0-P5` | Title, authors, affiliation, email, abstract, index terms | Replace title and abstract/index terms; preserve author, affiliation, and author-contact content. |
| `P6-P18` | Introduction, objectives/contributions, related work, research gap | Rewrite claims/citations around the verified evidence and explicit gap. |
| `P19-P47` + image relationships `rId9-rId11` | Architecture/methodology, figures, workflow, algorithm | Preserve architecture and workflow figures; revise surrounding prose/captions/algorithm to distinguish code features from experimentally demonstrated behavior. |
| `P48-P65` and Table I-IV | Implementation, environment, dataset, models, procedures | Preserve useful implementation detail while updating the environment and procedures to identify B/C/A evidence classes and safe boundaries. |
| `P66-P91`, Table V-VIII, Fig. 3 | Results and discussion | Rewrite with the reproduced metrics, bootstrap uncertainty, input-scale finding, component results, microbenchmark, and explicitly historical integration/load observations. |
| `P92-P96` | Limitations, conclusion | Replace with concise limits and evidence-based conclusion; no Q1 readiness claim. |
| `P97-P121` | References | Replace citations/references with the small set of verified, directly relevant sources; remove unsupported or unverified entries. |
| `word/header1.xml`, `word/footer1.xml` | Repeating furniture | Update only the dated label/statement to reflect the final evidence review date while retaining the visual treatment. |

## Package-preservation contract

Preserve unchanged unless an intended edit explicitly touches it: `word/styles.xml`, `word/stylesWithEffects.xml`, `word/numbering.xml`, `word/theme/theme1.xml`, `word/fontTable.xml`, all three existing `word/media/image*.png`, header/footer relationships, and `customXml/*`. The source contains no comments, tracked changes, footnotes, endnotes, fields, or controls that require migration.

The final document may update `word/document.xml`, `word/header1.xml`, `word/footer1.xml`, relationship parts only if adding/removing a figure requires it, core metadata, and `word/settings.xml` if field-update-on-open is needed. Because this revision uses the retained three figures only, no new image relationship is planned.

## Fidelity gates

1. The retained reference hash must remain unchanged.
2. The final document must retain its one-section Letter portrait format, header/footer system, existing author block, three retained figures, and recognisable dark-navy heading/table style.
3. All updated tables and captions must fit without clipping or broken page continuation.
4. A final Microsoft Word PDF export and page-by-page PNG inspection must verify page flow, tables, figures, header/footer alignment, and references.
5. Content claims must trace to `experiments/publication_final/experiment_results.csv` or a path in `evidence_manifest.md`; historical claims must be labelled as historical.
