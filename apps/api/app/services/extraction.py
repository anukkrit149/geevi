"""Bounded, report-specific candidate extraction.

Deterministic label/row matching over the PDF text layer for a small set of known report layouts.
It is not OCR, not a model and carries no extraction-accuracy claim: every output is a candidate
that a source reviewer must check against the original region. Unsupported layouts and image-only
files produce no candidates and use the manual entry path.
"""
import io
import re
from typing import Any

EXTRACTOR = "geevi-layout-rules"
EXTRACTOR_VERSION = "1"

MAGIC = {"application/pdf": b"%PDF-", "image/png": b"\x89PNG\r\n\x1a\n", "image/jpeg": b"\xff\xd8\xff"}

# Known labels per report type -> profile dimension. Anything else is left for manual entry.
VOCAB: dict[str, dict[str, str]] = {
    "referral": {"Reason for referral": "current", "Presenting symptoms": "current", "Prior treatment": "history",
                 "Relevant history": "history", "Performance status": "fitness", "Comorbidities": "fitness",
                 "Home support": "priorities"},
    "marrow": {"Blast percentage": "biology", "Cellularity": "biology", "Morphology": "biology", "Reported diagnosis": "biology"},
    "flow": {"Blast immunophenotype": "biology", "Myeloid markers": "biology", "Lymphoid markers": "biology"},
    "cytogenetics": {"Karyotype": "biology", "Metaphases analysed": "biology", "FISH panel": "biology"},
    "molecular": {"NPM1": "biology", "FLT3-ITD": "biology", "FLT3-TKD": "biology", "TP53": "biology", "IDH1": "biology",
                  "IDH2": "biology", "CEBPA": "biology"},
    "organ_assessment": {"LVEF": "fitness", "Kidney function": "fitness", "Liver function": "fitness"},
}
TABLE_TYPES = {"blood_panel": "current"}
HEADER_KEYS = {"patient id": "patient_identifier", "patient": "patient_name", "laboratory": "issuer", "issuer": "issuer",
               "accession": "accession", "report type": "report_type", "report status": "issued_status",
               "reported by": "author", "author": "author", "collected": "collected", "received": "received",
               "issued": "issued", "method": "method", "panel": "panel", "limitations": "limitations",
               "relation": "relation", "affects": "affects"}

_STATE_RULES = [
    (r"\binsufficient (sample|material|specimen)\b", "insufficient_sample"),
    (r"\b(pending|awaited|to follow|in progress)\b", "pending"),
    (r"\bnot (tested|performed|requested|done)\b", "untested"),
    (r"\bnot (reported|stated|recorded)\b", "unreported"),
    (r"\b(unavailable|not available)\b", "unavailable"),
    (r"\b(indeterminate|equivocal|inconclusive)\b", "indeterminate"),
    (r"\b(not detected|negative|absent|none detected)\b", "not_detected"),
    (r"\b(detected|positive|present)\b", "detected"),
]
_ROW = re.compile(r"^(?P<analyte>[A-Za-z][A-Za-z /%-]+?)\s+(?P<value>[<>]?\d+(?:\.\d+)?)\s+(?P<units>\S+)\s+(?P<range>\d+(?:\.\d+)?\s*-\s*\d+(?:\.\d+)?)$")
_PART = re.compile(r"^(?:Specimen\s+)?Part\s+([A-Z])\b", re.I)
_DAY = re.compile(r"Day\s*([+-]?\d+)", re.I)


def sniff_media_type(data: bytes, declared: str) -> str | None:
    """Accept only PDF/PNG/JPEG whose bytes match the declared type. HTML/SVG and others are rejected."""
    magic = MAGIC.get(declared)
    return declared if magic and data.startswith(magic) else None


def parse_pdf(data: bytes) -> list[dict[str, Any]]:
    import pdfplumber
    pages = []
    with pdfplumber.open(io.BytesIO(data)) as pdf:
        for number, page in enumerate(pdf.pages, start=1):
            lines = [{"text": line["text"].strip(), "bbox": [round(line["x0"], 2), round(line["top"], 2), round(line["x1"], 2), round(line["bottom"], 2)]}
                     for line in page.extract_text_lines() if line["text"].strip()]
            pages.append({"number": number, "width": float(page.width), "height": float(page.height), "lines": lines})
    return pages


def classify_state(wording: str) -> tuple[str, str | None]:
    lowered = wording.lower()
    for pattern, state in _STATE_RULES:
        if re.search(pattern, lowered):
            return state, pattern
    return "reported_value", None


def rel_day(text: str | None, anchor: str = "episode-day-0") -> dict | None:
    match = _DAY.search(text or "")
    if not match:
        return None
    return {"value": int(match.group(1)), "unit": "day", "anchor": anchor, "precision": "day",
            "basis": "fictional relative demonstration day"}


def read_header(pages: list[dict]) -> dict[str, Any]:
    header: dict[str, Any] = {"specimens": []}
    for page in pages:
        for line in page["lines"]:
            text = line["text"]
            part = _PART.match(text)
            if part and ":" in text:
                label, _, rest = text.partition(":")
                header["specimens"].append({"label": f"Part {part.group(1).upper()}", "description": rest.strip(),
                                            "collection_time": rel_day(rest)})
                continue
            key, sep, value = text.partition(":")
            mapped = HEADER_KEYS.get(key.strip().lower())
            if sep and mapped and mapped not in header and value.strip():
                header[mapped] = value.strip()
    return header


def extract_candidates(report_type: str, pages: list[dict]) -> list[dict[str, Any]]:
    vocab, table_dimension = VOCAB.get(report_type), TABLE_TYPES.get(report_type)
    if not vocab and not table_dimension:
        return []
    candidates: list[dict[str, Any]] = []
    for page in pages:
        part = None
        for line in page["lines"]:
            text = line["text"]
            heading = _PART.match(text)
            if heading:
                part = f"Part {heading.group(1).upper()}"
            assertion = None
            if table_dimension and (row := _ROW.match(text)):
                assertion = {"analyte": row["analyte"].strip(), "dimension": table_dimension, "value_text": row["value"],
                             "value_number": row["value"].lstrip("<>"), "units": row["units"], "reference_range": row["range"],
                             "result_state": "reported_value", "normalization": {"rule": "table-row-v1"}}
            elif vocab and ":" in text:
                label, _, value = text.partition(":")
                label, value = label.strip(), value.strip()
                if label in vocab and value:
                    state, rule = classify_state(value)
                    number = re.match(r"^[<>]?(\d+(?:\.\d+)?)\s*(%|[A-Za-z/]+)?", value) if state == "reported_value" else None
                    assertion = {"analyte": label, "dimension": vocab[label], "value_text": value,
                                 "value_number": number.group(1) if number else None,
                                 "units": number.group(2) if number else None, "reference_range": None,
                                 "result_state": state,
                                 "normalization": {"rule": "label-value-v1", "state_rule": rule}}
            if assertion:
                assertion.update(exact_wording=text, specimen_label=part)
                candidates.append({"assertion": assertion,
                                   "source_ref": {"page": page["number"], "region": line["bbox"],
                                                  "page_size": [page["width"], page["height"]]}})
    return candidates
