"""U2 explicit legacy import.

Converts explicitly supplied captures of the old prototype's stores (or its exported case packets)
plus user-supplied original files. Originals are matched by exact SHA-256, never by filename.
Legacy prose plans, sign-offs and approvals are preserved as unmapped history: they never become
reviewed publications or fresh signatures, and nothing is merged into existing records.
"""
import base64
import binascii
import uuid
from dataclasses import dataclass
from typing import Any

from app.core.config import get_settings
from app.core.errors import DomainError
from app.core.security import digest, sha256_bytes
from app.models import sources as m
from app.models.imports import LegacyRecord, RecoverySnapshot
from app.services import extraction
from app.services.command_service import Ctx

INTAKE, RESEARCH = "casebook-intake-v1", "casebook-research-lab-v1"
EXCLUDED = {"casebook-evidence-demo-v2"}
LEGACY_SYSTEM = "legacy-casebook"
PEOPLE = {"meera": ("Meera", "DEMO-MEERA"), "arun": ("Arun", "DEMO-ARUN")}
CATEGORY_DIMENSION = {"diagnosis": "biology", "biomarker": "biology", "condition": "current", "history": "history",
                      "extent": "extent", "priorities": "priorities", "context": "current"}
GOVERNANCE = {"plan", "protocol", "profileSignoff", "encounters", "history", "sessions"}
GOVERNANCE_NOTE = ("Legacy prose plan/approval history. Preserved for reference only: it is not a reviewed departmental "
                   "publication and is not a current clinical signature in this application.")
UNMAPPED_NOTE = "Legacy record with no equivalent reviewed structure here; preserved verbatim and left unmapped."


@dataclass
class Prepared:
    cases: list[tuple[str, dict, dict | None]]  # (legacy key, case state, packet patient info)
    research: list[Any]
    originals: dict[str, dict]
    fingerprint: str
    preserved: dict
    from_packets: int


def prepare(body) -> Prepared:
    """Validate the explicit input before any transaction; reject excluded or unknown formats."""
    unknown = set(body.snapshots) - {INTAKE, RESEARCH}
    if unknown & EXCLUDED:
        raise DomainError(422, "unsupported_legacy_format", "The older standalone evidence demo format is excluded from conversion.",
                          next_action="Keep that data in the legacy app; supply casebook-intake-v1 / casebook-research-lab-v1 captures instead.",
                          details={"excluded": sorted(unknown & EXCLUDED)})
    if unknown:
        raise DomainError(422, "unsupported_legacy_format", "Only explicitly supported legacy stores can be converted.",
                          details={"unsupported": sorted(unknown), "supported": [INTAKE, RESEARCH]})
    cases: list[tuple[str, dict, dict | None]] = []
    intake = body.snapshots.get(INTAKE) or {}
    if not isinstance(intake, dict):
        raise DomainError(422, "unsupported_legacy_format", "The intake snapshot must be the captured JSON object of the legacy store.")
    for key, state in intake.items():
        cases.append((str(key), state, None))
    for packet in body.packets:
        if not isinstance(packet, dict) or not packet.get("prototype") or not isinstance(packet.get("case"), dict):
            raise DomainError(422, "unsupported_legacy_format", "A packet is not a recognised legacy case export.")
        cases.append((str(packet["case"].get("id") or (packet.get("patient") or {}).get("id") or "unknown"), packet["case"], packet.get("patient")))
    research = body.snapshots.get(RESEARCH) or []
    if not cases and not research:
        raise DomainError(422, "unsupported_legacy_format", "No supported legacy snapshot or packet was supplied.",
                          next_action="Capture the legacy stores explicitly; this application cannot read the old origin's browser storage.")
    for _, state, _ in cases:
        if not isinstance(state, dict) or not isinstance(state.get("documents", []), list) or not isinstance(state.get("facts", []), list):
            raise DomainError(422, "unsupported_legacy_format", "A legacy case does not have the expected documents/facts structure.")
    known_hashes = {d.get("hash") for _, state, _ in cases for d in state.get("documents", [])}
    originals: dict[str, dict] = {}
    mismatched = []
    for item in body.originals:
        try:
            data = base64.b64decode(item.content_base64, validate=True)
        except (binascii.Error, ValueError) as exc:
            raise DomainError(422, "invalid_upload", f"Original '{item.filename}' is not valid base64.") from exc
        if len(data) > get_settings().max_upload_bytes:
            raise DomainError(413, "upload_too_large", f"Original '{item.filename}' exceeds the upload size limit.")
        sha = sha256_bytes(data)
        if sha not in known_hashes:
            mismatched.append({"filename": item.filename, "sha256": sha})
            continue
        if extraction.sniff_media_type(data, item.media_type) is None:
            raise DomainError(415, "unsupported_media", f"Original '{item.filename}' is not a PDF, PNG or JPEG matching its declared type.")
        originals[sha] = {"data": data, "media_type": item.media_type, "filename": item.filename}
    if mismatched:
        raise DomainError(422, "original_hash_mismatch", "A supplied file does not match the hash of any document in the legacy data.",
                          next_action="Supply the exact original files; originals are matched by hash, never by filename.",
                          details={"mismatched": mismatched})
    preserved = {"snapshots": body.snapshots, "packets": body.packets}
    fingerprint = digest({"payload": preserved, "originals": sorted(originals)})
    return Prepared(cases, research if isinstance(research, list) else [research], originals, fingerprint, preserved, len(body.packets))


def _region(boxes: list) -> list[float] | None:
    valid = [b for b in boxes or [] if isinstance(b, list) and len(b) == 4]
    if not valid:
        return None
    return [round(min(b[0] for b in valid), 5), round(min(b[1] for b in valid), 5),
            round(max(b[0] + b[2] for b in valid), 5), round(max(b[1] + b[3] for b in valid), 5)]


def convert(ctx: Ctx, prepared: Prepared) -> dict:
    report: dict[str, Any] = {"kind": "legacy", "fingerprint": prepared.fingerprint, "patients": 0, "documents": 0, "originals_supplied": 0,
                              "missing_originals": [], "candidates": 0, "candidates_without_geometry": 0, "unmapped": {}, "sequence": ctx.seq}
    ctx.new(RecoverySnapshot, source_kind="legacy", source_fingerprint=prepared.fingerprint, preserved_payload=prepared.preserved,
            validation_state={"stage": "converted"}, note="Raw legacy payload preserved verbatim alongside the conversion.")

    def unmapped(kind: str, payload: Any, patient_id=None, ref=None) -> None:
        ctx.new(LegacyRecord, legacy_kind=kind, legacy_ref=ref, patient_id=patient_id, payload=payload,
                note=GOVERNANCE_NOTE if kind in GOVERNANCE else UNMAPPED_NOTE)
        report["unmapped"][kind] = report["unmapped"].get(kind, 0) + 1

    for key, state, info in prepared.cases:
        name, legacy_id = PEOPLE.get(key, ((info or {}).get("name") or key, (info or {}).get("id") or f"legacy:{key}"))
        if info:
            name, legacy_id = info.get("name") or name, info.get("id") or legacy_id
        patient = ctx.new(m.Patient, display_name=f"{name} (legacy import)", summary="Imported from the legacy casebook prototype (fictional).")
        ctx.db.flush()
        ctx.new(m.ExternalIdentifier, owner_kind="patient", owner_id=patient.id, system=LEGACY_SYSTEM, value=legacy_id)
        episode = ctx.new(m.Episode, patient_id=patient.id, title="Legacy casebook case", service="Legacy prototype (fictional)",
                          responsible_team="Unassigned (legacy import)")
        ctx.db.flush()
        report["patients"] += 1
        documents: dict[str, m.SourceDocument] = {}
        reports: dict[str, m.ReportVersion] = {}
        for legacy_doc in state.get("documents", []):
            sha = str(legacy_doc.get("hash") or "")
            supplied = prepared.originals.get(sha)
            is_image = legacy_doc.get("kind") == "image"
            blob = ctx.db.query(m.SourceBlob).filter_by(container_id=ctx.container_id, sha256=sha).one_or_none()
            if blob is None:
                blob = ctx.new(m.SourceBlob, sha256=sha, length=len(supplied["data"]) if supplied else 0,
                               media_type=supplied["media_type"] if supplied else ("image/png" if is_image else "application/pdf"),
                               availability="available" if supplied else "missing", data=supplied["data"] if supplied else None)
                ctx.db.flush()
            title = legacy_doc.get("title") or legacy_doc.get("name") or f"Legacy document {legacy_doc.get('id')}"
            checked = legacy_doc.get("identity") == "checked"
            doc = ctx.new(
                m.SourceDocument, family_id=uuid.uuid4(), blob_id=blob.id, patient_id=patient.id, episode_id=episode.id,
                doc_kind="legacy_intake", title=title, filename=legacy_doc.get("name") or title, issuer=LEGACY_SYSTEM,
                external_id=f"{legacy_id}/{legacy_doc.get('id')}",
                claimed_identity={"value": legacy_doc.get("claimed"), "legacy": True},
                association_status="associated" if checked else "pending",
                association_review={"legacy": True, **(legacy_doc.get("identityReview") or {}), "sequence": ctx.seq} if checked else None,
                page_count=int(legacy_doc.get("pageCount") or len(legacy_doc.get("pages") or []) or 1), pages=[],
                extraction_limits={"text_layer": bool(legacy_doc.get("pages")), "layout_supported": False,
                                   "note": "Legacy import: text and geometry are preserved as captured by the old prototype."},
                legacy={"id": legacy_doc.get("id"), "pages": legacy_doc.get("pages"), "layouts": legacy_doc.get("layouts"),
                        "receivedAt": legacy_doc.get("receivedAt"), "identity": legacy_doc.get("identity"),
                        "identityReview": legacy_doc.get("identityReview"), "kind": legacy_doc.get("kind")})
            ctx.db.flush()
            family = ctx.new(m.ReportFamily, patient_id=patient.id, issuer=LEGACY_SYSTEM, accession=f"{legacy_id}/{legacy_doc.get('id')}/{sha[:12]}",
                             report_type="legacy_intake")
            ctx.db.flush()
            reports[str(legacy_doc.get("id"))] = ctx.new(m.ReportVersion, family_id=family.id, patient_id=patient.id, document_ids=[str(doc.id)],
                                                         scope_note="Legacy document: issuer, accession and report status were not recorded by the old prototype.")
            documents[str(legacy_doc.get("id"))] = doc
            report["documents"] += 1
            if supplied:
                report["originals_supplied"] += 1
            else:
                report["missing_originals"].append({"patient": name, "document": title, "sha256": sha})
        ctx.db.flush()
        for fact in state.get("facts", []):
            doc = documents.get(str(fact.get("docId")))
            if doc is None:
                unmapped("fact_without_document", fact, patient.id, str(fact.get("id")))
                continue
            region = _region(fact.get("boxes"))
            state_guess, rule = extraction.classify_state(str(fact.get("value") or ""))
            ctx.new(m.ExtractionCandidate, document_id=doc.id, report_version_id=reports[str(fact.get("docId"))].id, patient_id=patient.id,
                    extractor="legacy-casebook-intake", extractor_version="1",
                    assertion={"analyte": fact.get("label"), "dimension": CATEGORY_DIMENSION.get(fact.get("category"), "current"),
                               "exact_wording": fact.get("quote") or "", "value_text": fact.get("value"), "value_number": None, "units": None,
                               "reference_range": None, "result_state": state_guess, "specimen_label": None,
                               "normalization": {"rule": "legacy-label-value", "state_rule": rule},
                               "legacy": {"id": fact.get("id"), "status": fact.get("status"), "review": fact.get("review"),
                                          "originalValue": fact.get("originalValue"), "category": fact.get("category")}},
                    source_ref={"document_id": str(doc.id), "page": fact.get("page"), "region": region, "units": "fraction",
                                "span": [fact.get("start"), fact.get("end")], "legacy_boxes": fact.get("boxes")})
            report["candidates"] += 1
            if region is None:
                report["candidates_without_geometry"] += 1
        for annotation in state.get("annotations", []):
            unmapped("annotation", annotation, patient.id, str(annotation.get("id")))
        for key_name in ("plan", "protocol", "profileSignoff"):
            if state.get(key_name):
                unmapped(key_name, state[key_name], patient.id)
        for key_name in ("encounters", "history", "sessions", "tasks", "audit", "messages"):
            for index, entry in enumerate(state.get(key_name) or []):
                unmapped(key_name, entry, patient.id, str(entry.get("id", index)) if isinstance(entry, dict) else str(index))
    for question in prepared.research:
        unmapped("research_question", question, None, str(question.get("id")) if isinstance(question, dict) else None)

    missing = len(report["missing_originals"])
    report["complete"] = missing == 0 and prepared.from_packets == 0
    disclosures = ["Only the explicitly supplied snapshot/packet was converted; this application cannot read the legacy app's browser storage.",
                   "Legacy plans, sign-offs and approvals are preserved as unmapped history and are not signatures or publications here.",
                   "Imported findings arrive as unreviewed candidates; earlier legacy reviews are retained as history, not as current verification."]
    if prepared.from_packets:
        disclosures.append("Exported case packets may omit original bytes and full history; this is not a complete migration.")
    if missing:
        disclosures.append(f"{missing} original file(s) were not supplied. Those documents stay unavailable and their findings cannot be verified.")
    if report["candidates_without_geometry"]:
        disclosures.append(f"{report['candidates_without_geometry']} finding(s) have no captured source geometry.")
    report["disclosures"] = disclosures
    return report
