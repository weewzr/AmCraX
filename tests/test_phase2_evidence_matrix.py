"""Phase 2 tests for the evidence matrix (methodology version 2).

- the generic component and hypothesis rules on synthetic inputs (all five outcomes at both levels);
- the row-role table in the builder equals the table in docs/research/verdict_methodology_v2.md;
- version 1 verdicts equal the preserved 23 November release;
- every value that carries a source_file and key anywhere in the matrix equals the file value;
- one exchange rate, equal to the reference scenario, for every SGD value;
- the four evidence kinds are kept apart and no experimental validation is claimed;
- the findings-changed table reproduces supersession.json.
Deterministic, no network, no Aspen.
"""
from __future__ import annotations

import importlib.util
import json
import math
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
MATRIX = ROOT / "results" / "research" / "evidence_matrix.json"
MD = ROOT / "docs" / "research" / "evidence_matrix.md"
SCRIPT = ROOT / "scripts" / "research" / "build_evidence_matrix.py"
METHOD = ROOT / "docs" / "research" / "verdict_methodology_v2.md"
RELEASE = ROOT / "results" / "research_releases" / "2026-11-23" / "evidence_matrix.json"
BASELINE = ROOT / "results" / "research" / "reference_scenario" / "baseline.json"
REF_YAML = ROOT / "backend" / "amcrax" / "data" / "reference_scenario.yaml"
VAL_SUMMARY = ROOT / "results" / "research" / "validation" / "summary.json"
FC_JSON = ROOT / "results" / "research" / "phase2_findings_changed.json"
FC_MD = ROOT / "docs" / "research" / "phase2_findings_changed.md"
S, C, I, M, P = "SUPPORTED", "CONTRADICTED", "INCONCLUSIVE", "MIXED", "PARTIALLY SUPPORTED"


@pytest.fixture(scope="module")
def builder():
    spec = importlib.util.spec_from_file_location("build_evidence_matrix_p2", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def matrix():
    return json.loads(MATRIX.read_text(encoding="utf-8"))


def _rows(m):
    for h in m["hypotheses"]:
        for r in h["rows"]:
            yield h, r


# ---- generic rules on synthetic rows ---------------------------------------------------------
@pytest.mark.parametrize("rows, expected", [
    ([S, S], S),
    ([S], S),
    ([C, C], C),
    ([C, I], C),           # no SUPPORTED, half CONTRADICTED
    ([C], C),
    ([S, C], M),
    ([S, C, I], M),
    ([S, I], P),
    ([S, I, I], P),
    ([I, I], I),
    ([C, I, I], I),        # fewer than half CONTRADICTED
    ([I], I),
])
def test_component_rule_synthetic(builder, rows, expected):
    assert builder.component_verdict(rows) == expected


@pytest.mark.parametrize("comps, expected", [
    ([S, S, S], S),
    ([S], S),
    ([C, C], C),
    ([C, I], C),
    ([C, M], C),           # MIXED is neither support nor contradiction; half CONTRADICTED
    ([S, C], M),
    ([P, C, S], M),
    ([P, S, I], P),
    ([P], P),
    ([S, I], P),
    ([S, M], P),           # not all SUPPORTED, none CONTRADICTED
    ([I, I], I),
    ([M, M], I),
    ([C, I, I], I),
])
def test_hypothesis_rule_synthetic(builder, comps, expected):
    assert builder.hypothesis_verdict_v2(comps) == expected


def test_rules_reject_bad_input(builder):
    with pytest.raises(builder.EvidenceError):
        builder.component_verdict([])
    with pytest.raises(builder.EvidenceError):
        builder.component_verdict(["MIXED"])  # rows only use the three row verdicts
    with pytest.raises(builder.EvidenceError):
        builder.hypothesis_verdict_v2(["MAYBE"])


# ---- role table ----------------------------------------------------------------------------
def _method_table():
    text = METHOD.read_text(encoding="utf-8")
    sec = text.split("## Row roles (fixed here)", 1)[1].split("\n## ", 1)[0]
    out = {}
    for line in sec.splitlines():
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) != 4 or not re.match(r"^H\d$", cells[0]):
            continue
        cid = re.match(r"^(H\d-[A-Z])\b", cells[1]).group(1)
        prim = re.findall(r"\bH\d-[a-f]\b", cells[2])
        sec_rows = re.findall(r"\bH\d-[a-f]\b", cells[3])
        out.setdefault(cells[0], []).append((cid, prim, sec_rows))
    return out


def test_role_table_equals_methodology_document(builder):
    doc = _method_table()
    code = {h: [(cid, prim, sec) for cid, _t, prim, sec in comps] for h, comps in builder.COMPONENTS.items()}
    assert doc == code


def test_rows_carry_role_and_component(matrix, builder):
    ids = []
    for h, r in _rows(matrix):
        hid, cid, role = builder.role_of(r["row_id"])
        assert (hid, cid, role) == (h["id"], r["component"], r["role"]), r["row_id"]
        ids.append(r["row_id"])
    assert len(ids) == 20 and len(set(ids)) == 20
    for h in matrix["hypotheses"]:
        roles = [r["role"] for r in h["rows"]]
        assert roles == sorted(roles, key=lambda x: x != "primary"), h["id"]  # primary rows first


# ---- version 1 verdicts --------------------------------------------------------------------
def test_v1_verdicts_equal_release(matrix):
    rel = json.loads(RELEASE.read_text(encoding="utf-8"))
    hv = {h["id"]: h["verdict"] for h in rel["hypotheses"]}
    rv = {r["row_id"]: r["verdict"] for h in rel["hypotheses"] for r in h["rows"]}
    for h, r in _rows(matrix):
        assert h["verdict_v1"] == hv[h["id"]]
        assert r["verdict_v1"] == rv[r["row_id"]], r["row_id"]
    assert set(rv) == {r["row_id"] for _, r in _rows(matrix)}


# ---- schema of version 2 fields ------------------------------------------------------------
ROW_V2 = {"role", "component", "verdict_v1", "envelope", "threshold", "numerical_conclusions", "assumptions",
          "uncertainty", "validation_status", "evidence_kinds", "verdict_rule"}
HYP_V2 = {"verdict", "verdict_v1", "verdict_v1_rule_on_current_rows", "primary_hypothesis", "components",
          "strongest_defensible_statement", "findings_against_essay"}


def test_v2_schema(matrix):
    for h in matrix["hypotheses"]:
        assert HYP_V2 <= set(h), h["id"]
        for c in h["components"]:
            assert {"id", "title", "verdict", "primary_rows", "secondary_rows", "envelope", "note"} <= set(c)
            if c["verdict"] in ("SUPPORTED", "PARTIALLY SUPPORTED"):
                assert c["envelope"] and not c["envelope"].startswith("none"), c["id"]
        assert isinstance(h["findings_against_essay"], list)
    assert "cross_claim" in next(h for h in matrix["hypotheses"] if h["id"] == "H2")
    for _, r in _rows(matrix):
        assert ROW_V2 <= set(r), (r["row_id"], ROW_V2 - set(r))
        assert r["numerical_conclusions"] and all(isinstance(x, str) and x for x in r["numerical_conclusions"])
        assert r["verdict_rule"] == r["conclusion_conditions"]
        assert r["threshold"] is None or {"parameter", "values", "sourced_values", "comparison"} <= set(r["threshold"])


def test_h2e_modes(matrix):
    h2 = next(h for h in matrix["hypotheses"] if h["id"] == "H2")
    e = next(r for r in h2["rows"] if r["row_id"] == "H2-e")
    assert set(e["verdict_by_mode"]) == {"actual_sg", "hypothetical_lca"}
    assert e["verdict"] == e["verdict_by_mode"]["actual_sg"]  # the actual-policy verdict votes
    assert "not Singapore law" in e["verdict_rule"]
    assert "not Singapore law" in h2["cross_claim"]["statement"]


# ---- every value equals its file value -----------------------------------------------------
def _walk(node):
    if isinstance(node, dict):
        if {"source_file", "key", "value"} <= set(node):
            yield node
        for v in node.values():
            yield from _walk(v)
    elif isinstance(node, list):
        for v in node:
            yield from _walk(v)


def test_every_sourced_value_in_matrix_equals_file(matrix, builder):
    builder._CACHE.clear()
    n = 0
    for x in _walk(matrix["hypotheses"]):
        raw = builder.resolve(x["source_file"], x["key"])
        exp = builder.as_number(raw, x["source_file"], x["key"])
        assert isinstance(x["value"], (int, float)) and not isinstance(x["value"], bool)
        assert math.isfinite(x["value"])
        assert x["value"] == exp, (x["source_file"], x["key"], x["value"], exp)
        n += 1
    assert n > 200


# ---- currency ------------------------------------------------------------------------------
def test_single_exchange_rate(matrix):
    base = json.loads(BASELINE.read_text(encoding="utf-8"))
    cur = matrix["provenance"]["currency"]
    assert cur["calculation_currency"] == "USD"
    assert cur["fx_SGD_per_USD"] == base["fx_SGD_per_USD"]
    assert cur["fx_date"] == base["fx_date"]
    yaml_text = REF_YAML.read_text(encoding="utf-8")
    assert str(base["fx_SGD_per_USD"]) in yaml_text
    fx = cur["fx_SGD_per_USD"]
    pairs = 0
    for _, r in _rows(matrix):
        for n in r["numerical_findings"]:
            if n["unit"].startswith("SGD") and "usd_counterpart" in n:
                usd = next(m["value"] for m in r["numerical_findings"]
                           if m["source_file"] == n["usd_counterpart"]["source_file"] and m["key"] == n["usd_counterpart"]["key"])
                assert n["value"] == pytest.approx(usd * fx, rel=1e-9), r["row_id"]
                pairs += 1
    assert pairs >= 1
    blob = json.dumps(matrix) + MD.read_text(encoding="utf-8") + FC_MD.read_text(encoding="utf-8")
    for rate in re.findall(r"(\d+\.\d+) SGD/USD", blob):
        assert float(rate) == fx, rate


# ---- evidence kinds ------------------------------------------------------------------------
def test_evidence_kinds_and_no_experimental_claim(matrix):
    allowed = {"numerical_verification", "python_vs_aspen", "literature_comparison"}
    for _, r in _rows(matrix):
        assert r["evidence_kinds"] and set(r["evidence_kinds"]) <= allowed, r["row_id"]
    blob = (json.dumps(matrix) + MD.read_text(encoding="utf-8")).lower()
    assert "experimentally validated" not in blob
    assert "84.3 % validated" not in blob


def test_validation_summary_by_kind():
    s = json.loads(VAL_SUMMARY.read_text(encoding="utf-8"))
    for k in ("totals", "areas", "by_evidence_kind", "by_area_and_evidence_kind", "experimental_validation"):
        assert k in s
    assert s["experimental_validation"]["items_counted_as_evidence"] == 0
    ev = s["by_evidence_kind"]["experimental_validation"]
    assert ev["pass"] == 0 and ev["fail"] == 0 and ev["informational"] == 0
    assert sum(c["total"] for c in s["by_evidence_kind"].values()) == s["totals"]["total"]
    for st in ("pass", "fail", "informational", "not_available"):
        assert sum(c[st] for c in s["by_evidence_kind"].values()) == s["totals"][st]
        assert sum(a[st] for a in s["areas"].values()) == s["totals"][st]


# ---- findings that changed -----------------------------------------------------------------
def test_findings_changed_from_supersession(builder):
    fc = json.loads(FC_JSON.read_text(encoding="utf-8"))
    sup = json.loads((ROOT / "results/research/reference_scenario/supersession.json").read_text(encoding="utf-8"))
    assert len(fc["all_supersession_rows"]) == len(sup["rows"])
    for a, b in zip(fc["all_supersession_rows"], sup["rows"]):
        assert (a["old"], a["new"], a["key"]) == (b.get("old_value"), b.get("new_value"), b["key"])
    for x in fc["headline"]:
        if x["source"]["source_file"].endswith("supersession.json"):
            i = int(x["source"]["key"].split("/")[1])
            assert (x["old"], x["new"]) == (sup["rows"][i]["old_value"], sup["rows"][i]["new_value"])
    text = FC_MD.read_text(encoding="utf-8")
    assert "—" not in text


def test_no_em_dash_in_matrix_markdown():
    assert "—" not in MD.read_text(encoding="utf-8")


# ---- fix pass of 24 November 2026 (docs/internal/phase2_fix_plan.md sections 1 to 3) -----------------
FIX_ROWS = {"H2-b": I, "H3-d": I, "H4-e": I}
FIX_COMPONENTS = {"H1-P": I, "H1-Q": I, "H2-E": P, "H2-C": S, "H2-X": C, "H3-T": P, "H3-H": I, "H3-K": I, "H4-B": I}
FIX_HYPOTHESES = {"H1": I, "H2": M, "H3": P, "H4": I}


def test_fix_plan_verdicts_derived(matrix, builder):
    """The derived verdicts equal the fix plan; the builder's EXPECTED table equals the derived rows."""
    rows = {r["row_id"]: r["verdict"] for _, r in _rows(matrix)}
    assert rows == builder.EXPECTED_ROW_V2
    for rid, v in FIX_ROWS.items():
        assert rows[rid] == v, rid
    comps = {c["id"]: c["verdict"] for h in matrix["hypotheses"] for c in h["components"]}
    assert comps == FIX_COMPONENTS
    assert {h["id"]: h["verdict"] for h in matrix["hypotheses"]} == FIX_HYPOTHESES


def _row(matrix, rid):
    return next(r for _, r in _rows(matrix) if r["row_id"] == rid)


@pytest.mark.parametrize("fn, forced, expected", [
    ("v2_h2b", "above", S), ("v2_h2b", "below", C), ("v2_h2b", "straddle", I),
    ("v2_h4e", "above", S), ("v2_h4e", "below", C), ("v2_h4e", "straddle", I),
    ("v2_h3d", "above", S), ("v2_h3d", "straddle", I),
])
def test_fix_pass_rules_can_fail(builder, monkeypatch, fn, forced, expected):
    """The rewritten coded rules have every branch: the outcome follows the comparison with the sourced values."""
    monkeypatch.setattr(builder, "side", lambda thresholds, lo, hi: forced)
    out = getattr(builder, fn)(builder.Row(), {})
    assert out["verdict"] == expected


def test_h2b_compares_full_sourced_ranges_and_names_both_benchmarks(matrix):
    r = _row(matrix, "H2-b")
    src = r["threshold"]["sourced_values"]
    assert any(x["quantity"].endswith(", low") for x in src) and any(x["quantity"].endswith(", high") for x in src)
    assert len(r["threshold"]["comparison"]) == 2  # one comparison per named benchmark
    for txt in (r["verdict_rule"], r["envelope"], r["conclusion"]):
        assert "3.06 USD/kg" in txt and "6.0 USD/kg" in txt
    assert any("conditional on the assumed" in x for x in r["numerical_conclusions"])


def test_h3d_needs_both_halves(matrix):
    r = _row(matrix, "H3-d")
    comp = r["threshold"]["comparison"]
    assert comp["energy_half"] == S and comp["cost_half"] == I and r["verdict"] == I
    assert r["threshold"]["sourced_values"], "the cost half compares with the sourced coefficient range"
    assert "Break-even capital recovery factor (solved)" in r["envelope"]


def test_h4e_threshold_against_sourced_recoveries(matrix):
    r = _row(matrix, "H4-e")
    vals = [x["value"] for x in r["threshold"]["sourced_values"]]
    thr = r["threshold"]["values"][0]["value"]
    assert min(vals) < thr < max(vals) and r["threshold"]["comparison"] == "straddle"
    assert "restates the flowsheet" in r["verdict_rule"]


def test_disclosures_and_text_corrections(matrix):
    prov = matrix["provenance"]
    assert len(prov["disclosures"]) >= 3 and "f233509" in prov["disclosures"][0] and "7447308" in prov["disclosures"][1]
    md = MD.read_text(encoding="utf-8")
    assert "## Disclosures" in md and all(d in md for d in prov["disclosures"])
    blob = json.dumps(matrix) + md
    for stale in ("about 60 K", "Infinite H2/N2 selectivity", "applied as USD at parity", "only green passes",
                  "necessity statement", "x1.50.;"):
        assert stale not in blob, stale
    h1 = next(h for h in matrix["hypotheses"] if h["id"] == "H1")
    assert "single sourced gain" in h1["strongest_defensible_statement"]
    h3 = next(h for h in matrix["hypotheses"] if h["id"] == "H3")
    assert h3["strongest_defensible_statement"].startswith(h3["verdict"] + ", resting only on")
    for c in h3["components"]:
        assert f"{c['id']} {c['verdict']}" in h3["strongest_defensible_statement"]
    assert "72 K or more" in _row(matrix, "H3-a")["envelope"]


def test_fix_pass_record_in_findings_changed(builder):
    fc = json.loads(FC_JSON.read_text(encoding="utf-8"))
    fp = fc["fix_pass_2026_11_24"]
    rows = {x["quantity"]: (x["old"], x["new"]) for x in fp["verdict_changes"]}
    for rid in FIX_ROWS:
        assert rows[f"row {rid}"] == (S, I), rid
    assert rows["hypothesis H4"] == (P, I)
    keys = {x["key"] for x in fp["number_changes"]}
    assert "specs/fuel_cell_grade_D/thresholds/psa_recovery_at_parity_with_central_membrane" in keys
    assert "## Fix pass of 24 November 2026" in FC_MD.read_text(encoding="utf-8")
