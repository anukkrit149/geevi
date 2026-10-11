"""U7 scoped review currency (KTD4).

A plan packet freezes its read set (exact input versions) and its watch set (revision counters of
relevant scopes). Both are re-checked under the workspace lock when the signature is committed, so
frontend freshness can never authorise a signature and unrelated writes never stale a decision.
"""
from datetime import UTC, datetime
from uuid import UUID

from app.core.errors import DomainError
from app.models.department import ProtocolVersion
from app.models.exceptions import ExceptionRequest
from app.models.reviews import ApplicabilityReview
from app.models.sources import ObservationVersion, ProfileSnapshot
from app.services import scopes
from app.services.command_service import Ctx

BASE_AREAS = ("assessment", "discussion", "exceptions", "applicability")


def protocol_scope(family_id) -> str:
    return f"protocol/{family_id}"


def watch_keys(ctx: Ctx, patient_id: UUID, protocol: ProtocolVersion) -> list[str]:
    areas = set(BASE_AREAS)
    for requirement in protocol.requirements:
        areas.update(requirement.get("watch") or [])
    return [*(scopes.patient_scope(patient_id, a) for a in sorted(areas)), protocol_scope(protocol.family_id)]


def freeze(ctx: Ctx, plan) -> tuple[list[dict], dict[str, int]]:
    protocol = ctx.get(ProtocolVersion, plan.protocol_version_id)
    applicability = ctx.get(ApplicabilityReview, plan.applicability_id)
    snapshot = ctx.get(ProfileSnapshot, applicability.snapshot_id)
    read_set = [{"kind": "protocol_version", "id": str(protocol.id), "digest": protocol.content_digest},
                {"kind": "applicability_review", "id": str(applicability.id), "digest": applicability.content_digest},
                {"kind": "profile_snapshot", "id": str(snapshot.id), "digest": snapshot.digest, "knowledge_cutoff_seq": snapshot.knowledge_cutoff_seq}]
    if plan.discussion_id:
        read_set.append({"kind": "patient_discussion", "id": str(plan.discussion_id)})
    for exception_id in plan.exception_ids:
        read_set.append({"kind": "exception_request", "id": exception_id, "digest": ctx.get(ExceptionRequest, UUID(exception_id)).content_digest})
    read_set += [{"kind": "observation_version", "id": o} for o in snapshot.observation_ids]
    watch = {key: value["revision"] for key, value in scopes.current(ctx, watch_keys(ctx, plan.patient_id, protocol)).items()}
    return read_set, watch


def changes_since(ctx: Ctx, read_set: list[dict], watch_set: dict[str, int]) -> list[dict]:
    """Exact explanation of what changed: scope, who changed it and which pinned input is no longer current."""
    changes: list[dict] = []
    now = scopes.current(ctx, list(watch_set))
    for key, frozen in watch_set.items():
        if now[key]["revision"] != frozen:
            changes.append({"scope": key, "frozen_revision": frozen, "current_revision": now[key]["revision"], "last_change": now[key]["last_change"]})
    for item in read_set:
        if item["kind"] == "observation_version":
            obs = ctx.find(ObservationVersion, UUID(item["id"]))
            if obs is None or obs.status != "current":
                changes.append({"read": item, "reason": f"{obs.analyte if obs else 'A pinned fact'} is no longer current"
                                                         f"{': ' + obs.superseded_reason if obs and obs.superseded_reason else ''}."})
        elif item["kind"] == "applicability_review":
            review = ctx.find(ApplicabilityReview, UUID(item["id"]))
            if review is None or review.status != "accepted":
                changes.append({"read": item, "reason": "The pinned applicability review is no longer the accepted version."})
    return changes


def check_current(ctx: Ctx, target: tuple, read_set: list[dict], watch_set: dict[str, int]) -> None:
    changes = changes_since(ctx, read_set, watch_set)
    if changes:
        raise DomainError(409, "stale_dependency", "Relevant material changed after this exact version was frozen for signature.",
                          target=target, next_action="Review the listed changes, reopen the draft and re-submit before signing.",
                          details={"changes": changes})


def exception_state(request: ExceptionRequest, now: datetime | None = None) -> str:
    now = now or datetime.now(UTC)
    if request.status == "approved" and request.expires_at and request.expires_at <= now:
        return "expired"
    return request.status


def gate_report(ctx: Ctx, protocol: ProtocolVersion, applicability: ApplicabilityReview, exceptions: list[ExceptionRequest], gate: str) -> list[dict]:
    """Evaluate each requirement behind a gate. Unknown stays unknown; only a permitted, approved, unexpired
    exception for that exact requirement can cover a difference or unknown."""
    criteria = {c["requirement_id"]: c for c in applicability.criteria}
    report = []
    for requirement in protocol.requirements:
        if requirement["gate"] != gate:
            continue
        assessment = (criteria.get(requirement["id"]) or {}).get("assessment")
        entry = {"requirement_id": requirement["id"], "assessment": assessment, "satisfied": False, "code": None, "message": None,
                 "exception_id": None, "exception_state": None}
        if assessment in ("match", "not_applicable"):
            entry["satisfied"] = True
        elif assessment in ("difference", "unknown"):
            waiver = requirement.get("waiver") or {}
            covering = [e for e in exceptions if e.requirement_id == requirement["id"] and e.protocol_version_id == protocol.id and e.status != "superseded"]
            if not waiver.get("allowed"):
                entry.update(code="required_input_missing" if assessment == "unknown" else "non_waivable_requirement_unmet",
                             message=f"{requirement['id']} is {assessment} and cannot be waived.")
            elif not covering:
                entry.update(code="exception_required", message=f"{requirement['id']} is {assessment}; a {waiver['exception_type']} exception is required.")
            else:
                request = covering[-1]
                state = exception_state(request)
                entry.update(exception_id=str(request.id), exception_state=state)
                if state == "approved":
                    entry["satisfied"] = True
                else:
                    entry.update(code="exception_not_approved", message=f"The {request.exception_type} exception for {requirement['id']} is {state}.")
        else:
            entry.update(code="required_input_missing", message=f"{requirement['id']} has not been assessed.")
        report.append(entry)
    return report
