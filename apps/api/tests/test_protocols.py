"""U6: one independently reviewed protocol version, frozen content and distinct lifecycle states."""
from datetime import UTC, datetime, timedelta

from tests.helpers import (
    W,
    accepted_evidence,
    decide,
    draft_appraisal,
    protocol_body,
    publish_protocol_v1,
    publish_protocol_v2,
)


def _submit(api, ws, evidence):
    pid = api("rao").post(f"{W(ws)}/protocols", protocol_body("v1", evidence))["target"]["id"]
    packet = api("rao").post(f"{W(ws)}/protocols/{pid}/submit", {"expected_revision": 1, "reviewer_username": "sen"})["data"]["packet_id"]
    return pid, packet


def test_sen_approval_and_rao_publication_produce_v1(api, workspace):
    _, _, appraisal = accepted_evidence(api, workspace)
    pid, packet = _submit(api, workspace, [appraisal])
    # Absent review blocks publication; approval and publication are separate decisions.
    api("rao").fail(f"{W(workspace)}/protocols/{pid}/publish", {"expected_revision": 2}, code="required_review_absent")
    decide(api, workspace, "sen", packet)
    assert api("rao").get(f"{W(workspace)}/protocols/{pid}")["version"]["lifecycle"] == "approved"
    api("sen").fail(f"{W(workspace)}/protocols/{pid}/publish", {"expected_revision": 3}, code="actor_not_permitted")
    api("rao").post(f"{W(workspace)}/protocols/{pid}/publish", {"expected_revision": 3})
    detail = api("mira").get(f"{W(workspace)}/protocols/{pid}")
    version = detail["version"]
    assert version["lifecycle"] == "effective" and version["selectable"] is True and version["version_no"] == 1
    assert version["approved_at"] and version["published_at"] and version["effective_from"]
    assert [r["id"] for r in version["requirements"]] == ["REQ-IDENTITY", "REQ-CONTEXT", "REQ-DISCUSSION", "REQ-VENUE", "REQ-MOLECULAR"]
    assert detail["reviews"][0]["decisions"][0]["recorded_by_name"] == "Dr. Sen"
    publication = detail["publications"][0]
    assert publication["recorded_by_name"] == "Dr. Rao" and publication["target_digest"] == version["content_digest"]
    assert publication["policy"]["id"] == "demo-review-policy" and "unvalidated" in detail["validation_notice"]


def test_rejected_review_blocks_publication(api, workspace):
    _, _, appraisal = accepted_evidence(api, workspace)
    pid, packet = _submit(api, workspace, [appraisal])
    decide(api, workspace, "sen", packet, "object", "REQ-VENUE wording needs the branch stated.")
    assert api("rao").get(f"{W(workspace)}/protocols/{pid}")["version"]["lifecycle"] == "changes_requested"
    api("rao").fail(f"{W(workspace)}/protocols/{pid}/publish", {"expected_revision": 3}, code="required_review_absent")


def test_protocol_needs_accepted_evidence(api, workspace):
    _, _, draft = draft_appraisal(api, workspace)
    pid = api("rao").post(f"{W(workspace)}/protocols", protocol_body("v1", [draft]))["target"]["id"]
    api("rao").fail(f"{W(workspace)}/protocols/{pid}/submit", {"expected_revision": 1, "reviewer_username": "sen"}, code="evidence_not_accepted")
    empty = api("rao").post(f"{W(workspace)}/protocols", protocol_body("v1", []))["target"]["id"]
    api("rao").fail(f"{W(workspace)}/protocols/{empty}/submit", {"expected_revision": 1, "reviewer_username": "sen"}, code="evidence_required")


def test_same_account_cannot_satisfy_independence_by_roles_or_client_fields(api, workspace, db):
    _, _, appraisal = accepted_evidence(api, workspace)
    pid = api("rao").post(f"{W(workspace)}/protocols", protocol_body("v1", [appraisal]))["target"]["id"]
    # Even if Rao's account were also granted the review capability, the author cannot review their own version.
    from sqlalchemy import select

    from app.models.identity import Account, WorkspaceGrant
    rao_id = db.scalar(select(Account.id).where(Account.username == "rao"))
    grant = db.scalar(select(WorkspaceGrant).where(WorkspaceGrant.workspace_id == workspace, WorkspaceGrant.account_id == rao_id))
    grant.capabilities = [*grant.capabilities, "protocol.review"]
    db.commit()
    api("rao").fail(f"{W(workspace)}/protocols/{pid}/submit", {"expected_revision": 1, "reviewer_username": "rao"}, code="independent_reviewer_required")
    packet = api("rao").post(f"{W(workspace)}/protocols/{pid}/submit", {"expected_revision": 1, "reviewer_username": "sen"})["data"]["packet_id"]
    forged = {"X-Actor": "sen", "X-Role": "reviewer"}
    error = api("rao").fail(f"{W(workspace)}/review-packets/{packet}/decide",
                            {"expected_revision": 1, "decision": "approve", "reviewer": "sen", "actor_id": api("sen").account_id}, headers=forged)
    assert error["code"] == "actor_not_permitted"
    assert api("rao").get(f"{W(workspace)}/protocols/{pid}")["version"]["lifecycle"] == "in_review"


def test_future_effective_approved_content_cannot_change(api, workspace):
    _, _, appraisal = accepted_evidence(api, workspace)
    future = (datetime.now(UTC) + timedelta(days=30)).isoformat()
    pid = publish_protocol_v1(api, workspace, [appraisal], effective_from=future)
    version = api("rao").get(f"{W(workspace)}/protocols/{pid}")["version"]
    assert version["lifecycle"] == "published" and version["selectable"] is False  # published, not yet effective
    digest = version["content_digest"]
    changed = protocol_body("v1", [appraisal])
    changed["requirements"][0]["text"] = "Silently loosened requirement text."
    api("rao").fail(f"{W(workspace)}/protocols/{pid}/save", {"expected_revision": version["revision"], **changed}, code="immutable_version")
    after = api("rao").get(f"{W(workspace)}/protocols/{pid}")["version"]
    assert after["content_digest"] == digest and after["requirements"][0]["text"].startswith("Patient identity")
    past = (datetime.now(UTC) - timedelta(days=3)).isoformat()
    _, _, second = accepted_evidence(api, workspace, "v2", "research-caregiver-contact")
    other = api("rao").post(f"{W(workspace)}/protocols", protocol_body("v1", [second]))["target"]["id"]
    packet = api("rao").post(f"{W(workspace)}/protocols/{other}/submit", {"expected_revision": 1, "reviewer_username": "sen"})["data"]["packet_id"]
    decide(api, workspace, "sen", packet)
    api("rao").fail(f"{W(workspace)}/protocols/{other}/publish", {"expected_revision": 3, "effective_from": past}, code="invalid_effective_date")


def test_review_due_is_owned_work_not_expiry_and_withdrawal_blocks_new_selection(api, workspace):
    _, _, appraisal = accepted_evidence(api, workspace)
    due = (datetime.now(UTC) + timedelta(seconds=1)).isoformat()
    pid = publish_protocol_v1(api, workspace, [appraisal], review_due=due)
    import time
    time.sleep(1.2)
    version = api("rao").get(f"{W(workspace)}/protocols/{pid}")["version"]
    assert version["review_due_reached"] is True and version["lifecycle"] == "effective" and version["selectable"] is True
    work = [w for w in api("rao").get(f"{W(workspace)}/work-items") if w["work_kind"] == "review_due"]
    assert len(work) == 1 and work[0]["owner_name"] == "Dr. Rao" and work[0]["target_id"] == pid
    api("sen").fail(f"{W(workspace)}/protocols/{pid}/withdraw", {"expected_revision": version["revision"], "reason": "Reviewer cannot withdraw"}, code="actor_not_permitted")
    api("rao").post(f"{W(workspace)}/protocols/{pid}/withdraw", {"expected_revision": version["revision"], "reason": "Withdrawn pending rewrite of the venue branch."})
    after = api("rao").get(f"{W(workspace)}/protocols/{pid}")
    assert after["version"]["lifecycle"] == "withdrawn" and after["version"]["selectable"] is False and after["version"]["published_at"]
    assert [p["decision"] for p in after["publications"]] == ["publish", "withdraw"]  # history is preserved


def test_successor_supersedes_only_when_effective_and_keeps_v1_intact(api, workspace):
    _, _, appraisal = accepted_evidence(api, workspace)
    v1 = publish_protocol_v1(api, workspace, [appraisal])
    before = api("rao").get(f"{W(workspace)}/protocols/{v1}")["version"]
    _, _, second = accepted_evidence(api, workspace, "v2", "research-caregiver-contact")
    v2, _ = publish_protocol_v2(api, workspace, v1, [appraisal, second])
    detail = api("rao").get(f"{W(workspace)}/protocols/{v2}")
    assert [(v["version_no"], v["lifecycle"]) for v in detail["family"]] == [(1, "superseded"), (2, "effective")]
    assert detail["proposal"]["status"] == "accepted" and "requirements" in detail["proposal"]["diff"] and detail["proposal"]["base_version_id"] == v1
    after = api("rao").get(f"{W(workspace)}/protocols/{v1}")["version"]
    assert after["content_digest"] == before["content_digest"] and after["requirements"] == before["requirements"]
    assert [r["id"] for r in detail["version"]["requirements"]][-1] == "REQ-CAREGIVER"
