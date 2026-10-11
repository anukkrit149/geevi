"""U4: the fictional source pack is coherent, reproducible and separated from gold and real data."""
import hashlib
import json

import pytest

from app.services import extraction, fixture_loader
from scripts import make_fixtures
from tests.helpers import FIXTURES, INPUTS, MANIFEST, SCENARIO, W, raw


def test_manifest_files_hashes_and_time_anchors_resolve():
    for entry in [*MANIFEST["inputs"], *MANIFEST["research"]]:
        data = (FIXTURES / entry["file"]).read_bytes()
        assert hashlib.sha256(data).hexdigest() == entry["sha256"] and len(data) == entry["length"]
        assert entry["file"].startswith("inputs/") and entry["label"] in ("fictional", "synthetic")
    for entry in MANIFEST["inputs"]:
        assert entry["patient"] in MANIFEST["patients"] and entry["received_time"]["anchor"] == "episode-day-0"
        assert (FIXTURES / "gold" / f"{entry['id']}.json").exists()


def test_fixture_generation_is_reproducible():
    for spec in make_fixtures.SPECS:
        assert hashlib.sha256(make_fixtures.render(spec)).hexdigest() == INPUTS[spec["id"]]["sha256"], spec["id"]


def test_inputs_are_visibly_fictional_and_not_joined_to_real_cohorts():
    for entry in MANIFEST["inputs"]:
        if entry["media_type"] != "application/pdf":
            continue
        text = " ".join(line["text"] for page in extraction.parse_pdf(raw(entry["id"])) for line in page["lines"])
        assert "FICTIONAL DEMONSTRATION DOCUMENT" in text and "GEEVI-DEMO-" in text
        for real_marker in ("BeatAML", "Beat AML", "TCGA", "GDC", "dbGaP"):
            assert real_marker not in text
    refs = json.loads((FIXTURES / "references" / "public-references.json").read_text())
    assert refs["label"] == "public_reference" and all(r["use"] and "patient" not in r for r in refs["references"])
    assert "unvalidated" in SCENARIO["validation_status"].lower()


def test_gold_is_independent_expected_output_for_each_variant():
    """Runtime extraction is compared with the authored gold; known rule limits are explicit in gold notes."""
    mismatches = {}
    for entry in MANIFEST["inputs"]:
        gold = json.loads((FIXTURES / "gold" / f"{entry['id']}.json").read_text())
        if entry["media_type"] != "application/pdf":
            assert gold["expected"] == {"candidates": 0, "manual_entry_required": True}
            continue
        got = [(c["assertion"]["analyte"], c["assertion"]["specimen_label"], c["assertion"]["result_state"])
               for c in extraction.extract_candidates(entry["doc_kind"], extraction.parse_pdf(raw(entry["id"])))]
        want = [(a["analyte"], a["specimen_label"], a["result_state"]) for a in gold["assertions"]]
        if got != want:
            mismatches[entry["id"]] = [w for w in want if w not in got]
    # Exactly one authored disagreement: the flow line the layout rule over-reads (reviewer must correct it).
    assert mismatches == {"meera-flow": [("Myeloid markers", "Part A", "reported_value")]}
    correction = json.loads((FIXTURES / "gold" / "meera-marrow-correction.json").read_text())["expected"]
    assert correction["relation_kind"] == "correction" and correction["supersedes"][0]["previous_value"] == "90 %"
    assert json.loads((FIXTURES / "gold" / "meera-marrow-addendum.json").read_text())["expected"]["supersedes"] == []


def test_runtime_never_reads_gold_and_rejects_arbitrary_paths():
    from pathlib import Path

    import app.services as services
    for source in Path(services.__file__).parent.parent.rglob("*.py"):
        text = source.read_text()
        assert "gold" not in text.replace("never the test gold", "").replace("never reads the gold", "").replace("(gold, arbitrary", "(arbitrary").lower(), source
    for bad in ("gold/meera-marrow.json", "../../apps/api/pyproject.toml", "/etc/hosts", "manifest.json", "inputs/../gold/meera-flow.json"):
        with pytest.raises(Exception) as exc:
            fixture_loader.input_path(bad)
        assert getattr(exc.value, "code", "") == "fixture_path_rejected"


def test_gold_and_local_paths_are_not_served_by_the_api(api, workspace):
    rao = api("rao")
    paths = list(rao.http.app.openapi()["paths"])
    assert not any("gold" in p or "fixture" in p for p in paths)
    for probe in ("/api/v1/dev/fixtures/gold/meera-marrow.json", "/api/v1/dev/scenario/../gold/meera-flow.json", "/gold/meera-marrow.json",
                  f"/api/v1{W(workspace)}/sources/..%2F..%2Fgold%2Fmeera-marrow.json/content"):
        assert rao.http.get(probe).status_code in (404, 422)
    assert "assertions" not in json.dumps(rao.get("/dev/scenario"))


def test_demo_seeding_requires_dev_mode_and_creates_no_approvals(api, monkeypatch):
    operator = api("operator")
    assert api("rao").http.post("/api/v1/dev/workspaces", json={"name": "x"}, headers=api("rao").headers()).status_code == 403
    r = operator.http.post("/api/v1/dev/workspaces", json={"name": "Seeded", "load": "sources"}, headers=operator.headers())
    assert r.status_code == 200, r.text
    ws, patients = r.json()["workspace_id"], r.json()["patients"]
    docs = api("mira").get(f"{W(ws)}/sources?patient_id={patients['meera']}")
    assert len(docs) == 5 and all(d["association_status"] == "pending" for d in docs)
    assert all("Fixture loader" in d["recorded_by_name"] for d in docs)
    assert api("rao").get(f"{W(ws)}/observations?patient_id={patients['meera']}") == []  # nothing is pre-verified
    from app.core.config import get_settings
    monkeypatch.setenv("GEEVI_DEV_MODE", "false")
    get_settings.cache_clear()
    try:
        blocked = operator.http.post("/api/v1/dev/workspaces", json={"name": "No", "load": "sources"}, headers=operator.headers())
        assert blocked.status_code == 403 and blocked.json()["error"]["code"] == "dev_mode_required"
        assert operator.http.get("/api/v1/dev/identities").status_code == 404
        assert operator.http.get("/api/v1/dev/scenario").status_code == 403
    finally:
        monkeypatch.undo()
        get_settings.cache_clear()


def test_packaged_runtime_copy_matches_the_inputs_and_carries_no_gold():
    from app.core.config import PACKAGED_FIXTURES
    assert not (PACKAGED_FIXTURES / "gold").exists()
    for name in ("manifest.json", "scenario.json"):
        assert (PACKAGED_FIXTURES / name).read_bytes() == (FIXTURES / name).read_bytes()
    packaged = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in (PACKAGED_FIXTURES / "inputs").iterdir()}
    source = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in (FIXTURES / "inputs").iterdir()}
    assert packaged == source and len(packaged) == 16
