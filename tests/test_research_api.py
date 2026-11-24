"""Read-only research endpoints (GET /api/research/...). No model and no Aspen Plus is run."""
from __future__ import annotations

import json

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


def test_phase2_files_and_research_data_are_whitelisted():
    for area, files in research.PHASE2_FILES.items():
        for f, keys in files.items():
            assert research.ALLOWED[area][f] == keys, (area, f)
    assert set(research.ALLOWED["data"]) == set(research.PHASE2_DATA_FILES)
    # the earlier areas keep their files
    assert "purification_study.json" in research.ALLOWED["purification"] and "phase2_comparison.json" in research.ALLOWED["purification"]


@pytest.mark.parametrize("area,file", [(a, f) for a, fs in research.PHASE2_FILES.items() for f in fs])
def test_phase2_file_is_served_in_live_mode(area, file):
    if not _have(area, file):
        pytest.skip("result not generated")
    r = client.get(f"/api/research/{area}/{file}")
    assert r.status_code == 200, r.text[:200]
    b = r.json()
    if file.endswith(".csv"):
        assert b["count"] == len(b["rows"]) and b["file"] == file
    elif research.PHASE2_FILES[area][file] is not None:
        assert set(b["served_keys"]) <= set(research.PHASE2_FILES[area][file])
    assert any(it["file"] == file for it in client.get("/api/research/index").json()["areas"][area])


@pytest.mark.skipif(not _have("reference_scenario", "baseline.json"), reason="results not generated")
def test_baseline_serves_the_fuel_efficiency_envelope():
    b = client.get("/api/research/reference_scenario/baseline.json").json()
    cases = b["fuel_efficiency_sensitivity"]["cases"]
    assert cases[0]["fuel_efficiency"] == 1.0
    assert cases[0]["lcoh_USD_per_kg"] == pytest.approx(b["lcoh_USD_per_kg"], rel=1e-9)
    assert all(c2["lcoh_USD_per_kg"] > c1["lcoh_USD_per_kg"] for c1, c2 in zip(cases, cases[1:]))


@pytest.mark.skipif(not _have("enduse", "turbine_threshold.json"), reason="results not generated")
def test_turbine_threshold_subset_includes_the_fuel_sensitivity():
    b = client.get("/api/research/enduse/turbine_threshold.json").json()
    assert "cracker_heat_fuel_efficiency_sensitivity" in b["served_keys"]
    assert "twoway_map" not in b
    # addendum of 24 November 2026: the paper-basis fuel-cost comparison and its reconciliation are served
    fc = b["forty_percent_figure"]["fuel_cost_gap_on_paper_basis"]
    assert fc["cases"] and set(fc["reconciliation"]) == {"green", "blue"}


@pytest.mark.skipif(not (_have("reference_scenario", "baseline.json") and _have("purification", "phase2_comparison.json")
                         and _have("kinetics", "validity_classification.json")), reason="results not generated")
def test_addendum_blocks_are_served():
    b = client.get("/api/research/reference_scenario/baseline.json").json()
    assert [c["psa_recovery"] for c in b["psa_recovery_sensitivity"]["cases"]] == [0.85, 0.8192, 0.7744]
    p = client.get("/api/research/purification/phase2_comparison.json").json()
    assert {"abdoos2025_table8", "psa_yanez_different_feed", "psa_mass_balance_assumption"} <= set(
        p["abdoos2025_sourced_case"]["equal_delivery_increment"])
    k = client.get("/api/research/kinetics/validity_classification.json").json()
    assert k["literature_comparison_points_sayas2020"]["n_points"] == 15
    assert k["cross_catalyst_context_sayas2020"]["cases"]


def test_addendum_record_is_served_or_404(monkeypatch, tmp_path):
    if research.ADDENDUM.is_file():
        r = client.get("/api/research/addendum")
        assert r.status_code == 200 and r.json()["verdict_changes"] == []
    monkeypatch.setattr(research, "ADDENDUM", tmp_path / "nope.json")
    r = client.get("/api/research/addendum")
    assert r.status_code == 404 and r.json()["code"] == "research_not_found"


@pytest.mark.skipif(not _have("uq", "gsa_sobol.json"), reason="results not generated")
def test_sobol_is_served_without_convergence_arrays():
    b = client.get("/api/research/uq/gsa_sobol.json").json()
    assert b["cases"] and "served_keys" in b
    for c in b["cases"].values():
        for o in c["outputs"].values():
            assert set(o) <= {"V", "mean", "sd", "p5", "p95", "indices", "groups"}


def test_research_data_files_are_served_from_research_data():
    for name in research.PHASE2_DATA_FILES:
        p = research.DATA_DIR / name
        r = client.get(f"/api/research/data/{name}")
        if not p.is_file():
            assert r.status_code == 404
            continue
        assert r.status_code == 200
        assert r.json() == json.loads(p.read_text(encoding="utf-8-sig"))
    assert client.get("/api/research/data/..%2F..%2FREADME.md").status_code == 404
    assert client.get("/api/research/data/references.json").status_code == 404


def test_validation_by_kind_counts_match_the_summary():
    r = client.get("/api/research/validation/by_kind")
    assert r.status_code == 200
    b = r.json()
    assert b["evidence_kinds"] == list(research.EVIDENCE_KINDS)
    assert set(research.EVIDENCE_KINDS) <= set(b["kinds"])
    s = client.get("/api/research/validation-summary").json()
    assert sum(k["total"] for k in b["kinds"].values()) == s["n_items"]
    assert sum(len(k["failures"]) for k in b["kinds"].values()) == s["totals"]["fail"]
    for k in b["kinds"].values():
        assert sum(k["by_status"].values()) == k["total"]
    assert "no independent experimental validation" in b["statement"].lower()


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
