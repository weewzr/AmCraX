"""Read-only research endpoints (GET /api/research/...). No model and no Aspen Plus is run."""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from amcrax.api.main import app
from amcrax.api.routers import research

client = TestClient(app)


def _have(area: str, file: str) -> bool:
    return (research.RESEARCH_DIR / area / file).is_file()


def test_index_lists_only_whitelisted_files():
    r = client.get("/api/research/index")
    assert r.status_code == 200
    body = r.json()
    assert set(body["areas"]) == set(research.ALLOWED)
    for area, items in body["areas"].items():
        for it in items:
            assert it["file"] in research.ALLOWED[area]


@pytest.mark.skipif(not _have("singapore", "scenario_breakdown.csv") and not _have("singapore", "cost_vs_capacity.csv"), reason="results not generated")
def test_csv_file_is_parsed_into_rows():
    r = client.get("/api/research/singapore/cost_vs_capacity.csv")
    assert r.status_code == 200
    b = r.json()
    assert b["count"] == len(b["rows"]) > 0
    assert "lcoh" in b["columns"]
    assert isinstance(b["rows"][0]["lcoh"], float)


@pytest.mark.skipif(not _have("singapore", "tornado.json"), reason="results not generated")
def test_json_file_and_bare_stem_prefers_json():
    a = client.get("/api/research/singapore/tornado.json").json()
    b = client.get("/api/research/singapore/tornado").json()
    assert a == b and "bars" in a


@pytest.mark.skipif(not _have("purification", "purification_study.json"), reason="results not generated")
def test_large_json_is_served_as_named_subset():
    b = client.get("/api/research/purification/purification_study.json").json()
    assert "iso_14687" in b and b["served_keys"]
    assert "cases" not in b


@pytest.mark.parametrize("url", [
    "/api/research/singapore/..%2F..%2Fsimulations%2Fbaseline.json",
    "/api/research/singapore/../../../README.md",
    "/api/research/..%5C..%5Cresults/x",
    "/api/research/singapore/scenario_results",  # not a whitelisted name (stem of a whitelisted .json is fine, this one is the .json stem)
    "/api/research/validation/economics.json",   # validation is served only through the summary
    "/api/research/nosuch/x.csv",
    "/api/research/singapore/not_listed.csv",
    "/api/research/singapore/assumptions.json.bak",
])
def test_path_traversal_and_unlisted_files_are_refused(url):
    r = client.get(url)
    if url.endswith("scenario_results"):
        assert r.status_code in (200, 404)
        return
    assert r.status_code == 404
    assert r.json().get("code") in ("research_not_found", "not_found")


def test_validation_summary_counts_are_consistent():
    r = client.get("/api/research/validation-summary")
    assert r.status_code == 200
    b = r.json()
    for area, a in b["areas"].items():
        assert sum(a["by_status"].values()) == a["n_items"], area
        assert len(a["failures"]) == a["by_status"].get("fail", 0), area
    assert b["totals"]["fail"] == sum(a["by_status"].get("fail", 0) for a in b["areas"].values())


def test_evidence_matrix_missing_is_404_not_500(monkeypatch, tmp_path):
    monkeypatch.setattr(research, "EVIDENCE_MATRIX", tmp_path / "nope.json")
    r = client.get("/api/research/evidence-matrix")
    assert r.status_code == 404 and r.json()["code"] == "research_not_found"


def test_evidence_matrix_is_returned_verbatim(monkeypatch, tmp_path):
    p = tmp_path / "m.json"
    p.write_text('{"provenance": {}, "hypotheses": [{"id": "H1"}]}', encoding="utf-8")
    monkeypatch.setattr(research, "EVIDENCE_MATRIX", p)
    assert client.get("/api/research/evidence-matrix").json()["hypotheses"][0]["id"] == "H1"


def test_aspen_evidence_lists_only_existing_pngs():
    r = client.get("/api/research/aspen-evidence")
    if r.status_code == 404:
        pytest.skip("manifest not generated")
    b = r.json()
    for c in b["captures"]:
        assert (research.ASPEN_EVIDENCE_DIR / c["file"]).is_file()
        assert client.get(f"/aspen-evidence/{c['file']}").status_code == 200
        break
