"""U13 complete archive and staged restore (R30/R31, KTD8).

Export takes one consistent database snapshot of every container record plus the original bytes.
Restore validates into a separate staging container that preserves logical record ids; nothing in
an archive can grant permissions or rewrite active records, and activation is a separate command.
"""
import base64
import binascii
import datetime as dt
import uuid
from decimal import Decimal
from typing import Any
from uuid import UUID

from sqlalchemy import DateTime, LargeBinary, select, text
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.errors import DomainError, not_found, not_permitted
from app.core.security import digest, sha256_bytes
from app.db.base import Base
from app.models.identity import Account, Workspace, WorkspaceContainer
from app.models.imports import RecoverySnapshot
from app.schemas.archives import ARCHIVE_SCHEMA
from app.services.command_service import Ctx, load_grant

FORBIDDEN = {"accounts", "auth_sessions", "sessions", "workspace_grants", "grants", "capabilities", "passwords", "password_hash",
             "workspaces", "workspace_containers", "import_jobs"}
EXCLUDED = ["accounts", "password hashes", "sessions", "capability grants", "server secrets", "import staging jobs"]


def record_tables() -> list:
    """Every container-scoped table, in dependency order."""
    return [t for t in Base.metadata.sorted_tables if "container_id" in t.c]


def _encode(value: Any) -> Any:
    if isinstance(value, UUID | Decimal):
        return str(value)
    if isinstance(value, dt.datetime | dt.date):
        return value.isoformat()
    return value


def export(db: Session, account: Account, workspace_id: UUID, mode: str = "full") -> dict:
    db.rollback()
    grant = load_grant(db, workspace_id, account)
    if "archive.export" not in grant.capabilities:
        raise not_permitted("Exporting a workspace archive needs the archive.export grant.", details={"required_capability": "archive.export"})
    # One consistent read snapshot for every table and every original.
    db.connection(execution_options={"isolation_level": "REPEATABLE READ"})
    ws = db.get(Workspace, workspace_id)
    if ws is None or ws.active_container_id is None:
        raise not_found("workspace", workspace_id)
    container = db.get(WorkspaceContainer, ws.active_container_id)
    tables: dict[str, list[dict]] = {}
    originals: list[dict] = []
    reasons: list[str] = []
    for table in record_tables():
        rows = db.execute(select(table).where(table.c.container_id == container.id).order_by(table.c.recorded_seq, table.c.id)).mappings().all()
        out = []
        for row in rows:
            out.append({k: _encode(v) for k, v in row.items() if k != "container_id" and not isinstance(table.c[k].type, LargeBinary)})
            if table.name == "source_blobs":
                data = bytes(row["data"]) if row["data"] is not None else None
                intact = data is not None and sha256_bytes(data) == row["sha256"] and len(data) == row["length"]
                if data is None:
                    reasons.append(f"Original {row['sha256'][:12]}… is missing: its bytes were never supplied.")
                elif not intact:
                    reasons.append(f"Original {row['sha256'][:12]}… is corrupt: stored bytes do not match the recorded hash.")
                originals.append({"sha256": row["sha256"], "length": row["length"], "media_type": row["media_type"], "available": intact,
                                  "base64": base64.b64encode(data).decode() if intact and mode == "full" else None})
        tables[table.name] = out
    if mode != "full":
        reasons.insert(0, "Review-only packet: original bytes are not included, so this is not a backup.")
    archive = {
        "schema": ARCHIVE_SCHEMA, "archive_version": 1, "kind": "full_backup" if mode == "full" else "review_packet",
        "complete": mode == "full" and not reasons, "incomplete_reasons": reasons,
        "workspace": {"logical_id": str(ws.id), "name": ws.name, "data_label": ws.data_label},
        "container": {"id": str(container.id), "origin": container.origin, "provenance": container.provenance},
        "snapshot": {"sequence": ws.sequence, "taken_at": dt.datetime.now(dt.UTC).isoformat(), "exported_by": account.display_name},
        "labels": {"data": ws.data_label, "contains_real_patient_data": False,
                   "signatures": "Demonstration records by fictional development identities; not institutionally authenticated."},
        "counts": {name: len(rows) for name, rows in tables.items()}, "excluded": EXCLUDED, "tables": tables, "originals": originals,
    }
    archive["content_digest"] = digest({"tables": tables, "originals": [(o["sha256"], o["length"], o["available"]) for o in originals]})
    db.rollback()
    return archive


def prepare(archive: dict) -> dict:
    """Validate schema, content and originals before any transaction. Returns decoded material."""
    if not isinstance(archive, dict) or archive.get("schema") != ARCHIVE_SCHEMA or archive.get("archive_version") != 1:
        raise DomainError(422, "unsupported_archive_schema", "This archive schema or version is not supported.",
                          details={"supported": ARCHIVE_SCHEMA, "found": archive.get("schema") if isinstance(archive, dict) else None})
    tables = archive.get("tables")
    if not isinstance(tables, dict) or not isinstance(archive.get("originals"), list):
        raise DomainError(422, "unsupported_archive_schema", "The archive is missing its tables or originals sections.")
    known = {t.name: t for t in record_tables()}
    injected = (set(archive) | set(tables)) & FORBIDDEN
    if injected:
        raise DomainError(422, "forbidden_archive_content", "Archives cannot carry accounts, sessions, grants or workspace catalog records.",
                          next_action="Remove the listed sections; permissions are never imported.", details={"sections": sorted(injected)})
    unknown = set(tables) - set(known)
    if unknown:
        raise DomainError(422, "unsupported_archive_content", "The archive contains record groups this application does not know.",
                          details={"tables": sorted(unknown)})
    blobs: dict[str, bytes | None] = {}
    reasons = list(archive.get("incomplete_reasons") or [])
    for original in archive["originals"]:
        sha, encoded = original.get("sha256"), original.get("base64")
        if encoded is None:
            blobs[sha] = None
            continue
        try:
            data = base64.b64decode(encoded, validate=True)
        except (binascii.Error, ValueError) as exc:
            raise DomainError(422, "original_hash_mismatch", f"Original {str(sha)[:12]}… cannot be decoded.") from exc
        if len(data) != original.get("length") or sha256_bytes(data) != sha:
            raise DomainError(422, "original_hash_mismatch", f"Original {str(sha)[:12]}… does not match its declared length and hash.",
                              next_action="Supply an intact archive.", details={"sha256": sha})
        blobs[sha] = data
    rows_by_table: dict[str, list[dict]] = {}
    for name, rows in tables.items():
        table = known[name]
        converted = []
        for row in rows:
            if not isinstance(row, dict) or set(row) - set(table.c.keys()):
                raise DomainError(422, "unsupported_archive_content", f"A {name} record has fields this application does not know.",
                                  details={"table": name, "fields": sorted(set(row) - set(table.c.keys())) if isinstance(row, dict) else None})
            item: dict[str, Any] = {}
            try:
                for key, value in row.items():
                    if key == "container_id":
                        continue  # scope is always the staging container, whatever the archive says
                    column = table.c[key]
                    if value is not None and isinstance(column.type, PGUUID):
                        value = UUID(str(value))
                    elif value is not None and isinstance(column.type, DateTime):
                        value = dt.datetime.fromisoformat(value)
                    item[key] = value
            except (ValueError, TypeError) as exc:
                raise DomainError(422, "unsupported_archive_content", f"A {name} record has an invalid identity or timestamp.") from exc
            if name == "source_blobs":
                if item.get("sha256") not in blobs:
                    raise DomainError(422, "original_hash_mismatch", "A source blob has no matching original entry in the archive.")
                item["data"] = blobs[item["sha256"]]
                item["availability"] = "available" if item["data"] is not None else "missing"
                if item["data"] is None and not any(str(item["sha256"])[:12] in r for r in reasons):
                    reasons.append(f"Original {str(item['sha256'])[:12]}… is missing from the archive.")
            converted.append(item)
        rows_by_table[name] = converted
    header = {k: v for k, v in archive.items() if k not in ("tables", "originals")}
    fingerprint = digest({"header": {k: header.get(k) for k in ("schema", "workspace", "container", "snapshot", "content_digest")},
                          "tables": tables, "originals": sorted(blobs)})
    return {"rows": rows_by_table, "header": header, "fingerprint": fingerprint, "reasons": reasons,
            "complete": bool(archive.get("complete")) and archive.get("kind") == "full_backup" and not reasons}


def restore(ctx: Ctx, prepared: dict) -> dict:
    """Insert every record into the staging container with its original logical id."""
    ctx.db.execute(text("SET CONSTRAINTS ALL DEFERRED"))
    counts = {}
    for table in record_tables():
        rows = prepared["rows"].get(table.name) or []
        if rows:
            ctx.db.execute(table.insert(), [{**row, "container_id": ctx.container_id} for row in rows])
        counts[table.name] = len(rows)
    sequence = int((prepared["header"].get("snapshot") or {}).get("sequence") or 0)
    ctx.db.add(RecoverySnapshot(container_id=ctx.container_id, id=uuid.uuid4(), recorded_seq=sequence, recorded_by=ctx.account.id,
                                recorded_by_name=ctx.account.display_name, source_kind="archive", source_fingerprint=prepared["fingerprint"],
                                preserved_payload=prepared["header"],
                                validation_state={"complete": prepared["complete"], "incomplete_reasons": prepared["reasons"]},
                                note="Restored from a portable archive. Imported signer identities and histories grant no current permissions "
                                     "and are not evidence of institutionally authenticated signatures."))
    return {"kind": "archive", "complete": prepared["complete"], "incomplete_reasons": prepared["reasons"], "counts": counts,
            "sequence": sequence, "source_workspace": prepared["header"].get("workspace"), "fingerprint": prepared["fingerprint"],
            "disclosures": ["Accounts, sessions and capability grants are never imported.",
                            "Restored histories keep their provenance; they are not evidence of institutional authentication."]}


def check_size(content_length: str | None) -> None:
    limit = get_settings().max_archive_bytes
    if content_length and content_length.isdigit() and int(content_length) > limit:
        raise DomainError(413, "archive_too_large", "The archive exceeds the configured size limit.", details={"max_bytes": limit})
