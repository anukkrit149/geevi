"""Fixed fictional demonstration policy (Product Contract: actors A1-A6).

These grants describe development identities only. They are not institutional qualifications.
"""
READ = "records.read"

DEV_ACCOUNTS: dict[str, dict] = {
    "rao": {
        "display_name": "Dr. Rao", "role_title": "Treating clinician, evidence author, protocol/SOP lead and publisher",
        "capabilities": [READ, "note.write", "patient.register", "source.import", "source.review", "clinical.assess", "discussion.record",
                         "evidence.author", "protocol.author", "protocol.publish", "sop.author", "sop.publish",
                         "plan.author", "plan.approve", "exception.request", "exception.decide.operational",
                         "exception.decide.clinical", "task.assign", "care.record", "concern.record", "concern.review",
                         "followup.manage", "followup.decide", "impact.resolve", "transfer.request"],
    },
    "sen": {
        "display_name": "Dr. Sen", "role_title": "Independent clinical reviewer and evidence reviewer",
        "capabilities": [READ, "note.write", "evidence.review", "protocol.review", "sop.review", "exception.decide.clinical"],
    },
    "mira": {
        "display_name": "Mira", "role_title": "Coordinator and trained source reviewer (assigned transcription scope)",
        "capabilities": [READ, "note.write", "patient.register", "source.import", "source.review", "discussion.record",
                         "task.assign", "concern.record", "followup.manage"],
    },
    "isha": {
        "display_name": "Isha", "role_title": "Receiving care-team member",
        "capabilities": [READ, "note.write", "task.act", "care.record", "concern.record", "concern.respond", "transfer.receive"],
    },
    "operator": {
        "display_name": "Development operator", "role_title": "Workspace import/export and recovery; no clinical authority",
        "capabilities": ["workspace.manage", "archive.export", "archive.import", "legacy.import"],
    },
}

# Review policy version referenced by every protocol/SOP/appraisal review packet in the demonstration.
REVIEW_POLICY = {
    "id": "demo-review-policy", "version": 1,
    "rules": {
        "evidence_appraisal": {"review_capability": "evidence.review", "independent_of_author": True},
        "protocol_version": {"review_capability": "protocol.review", "independent_of_author": True, "publish_capability": "protocol.publish"},
        "sop_version": {"review_capability": "sop.review", "independent_of_author": True, "publish_capability": "sop.publish"},
    },
    "exceptions": {
        "operational": {"approvals": 1, "capability": "exception.decide.operational"},
        "clinical": {"approvals": 2, "capability": "exception.decide.clinical"},
    },
    "note": "Fictional demonstration policy; not an institutional review or signature policy.",
}
