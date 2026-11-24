"""Tests for the research evidence matrix (results/research/evidence_matrix.json).

Checks the shared contract, that every source file exists, that every numeric value equals the value
in its source file at its key, that only the allowed verdicts and source types appear, that hypothesis
verdicts follow the stated rule, and that the stored matrix is current with the result files.
"""
from __future__ import annotations

import importlib.util
import json
import math
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
MATRIX = ROOT / "results" / "research" / "evidence_matrix.json"
MD = ROOT / "docs" / "research" / "evidence_matrix.md"
SCRIPT = ROOT / "scripts" / "research" / "build_evidence_matrix.py"

ALLOWED_VERDICTS = {"SUPPORTED", "CONTRADICTED", "INCONCLUSIVE"}  # row level (unchanged vocabulary)
ALLOWED_V2_VERDICTS = ALLOWED_VERDICTS | {"MIXED", "PARTIALLY SUPPORTED"}  # component and hypothesis level (methodology v2)
ALLOWED_SOURCE_TYPES = {"aspen", "python", "literature", "assumption"}
HYP_FIELDS = {"id", "statement", "verdict", "verdict_conditions", "summary", "rows"}
ROW_FIELDS = {"row_id", "sub_claim", "singapore_scenario", "aspen_model", "python_model", "case_ids",
              "input_assumptions", "literature", "validation_method", "numerical_findings",
              "uncertainty_range", "limitations", "conclusion", "conclusion_conditions", "provenance", "links"}
FINDING_FIELDS = {"quantity", "value", "unit", "source_type", "source_file", "key"}


def _load_builder():
    spec = importlib.util.spec_from_file_location("build_evidence_matrix", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def matrix():
    assert MATRIX.is_file(), "run scripts/research/build_evidence_matrix.py"
    return json.loads(MATRIX.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def builder():
    return _load_builder()


def _rows(m):
    for h in m["hypotheses"]:
        for r in h["rows"]:
            yield h, r


def test_top_level_schema(matrix):
    assert set(matrix) == {"provenance", "hypotheses", "methodology_version", "methodology"}
    assert matrix["methodology_version"] == 2
    assert matrix["methodology"] == "docs/research/verdict_methodology_v2.md"
    for k in ("generated_utc", "script", "source_type", "inputs_summary", "model_versions"):
        assert k in matrix["provenance"]
    assert [h["id"] for h in matrix["hypotheses"]] == ["H1", "H2", "H3", "H4"]


def test_hypothesis_and_row_schema(matrix):
    for h in matrix["hypotheses"]:
        assert HYP_FIELDS <= set(h), h["id"]
        assert isinstance(h["rows"], list) and h["rows"]
        ids = [r["row_id"] for r in h["rows"]]
        assert len(ids) == len(set(ids))
        for r in h["rows"]:
            missing = ROW_FIELDS - set(r)
            assert not missing, (r["row_id"], missing)
            assert r["row_id"].startswith(h["id"] + "-")
            for k in ("case_ids", "input_assumptions", "literature", "numerical_findings", "limitations"):
                assert isinstance(r[k], list), (r["row_id"], k)
            assert r["numerical_findings"], r["row_id"]
            assert set(r["links"]) == {"data", "figures", "screenshots"}
            for lit in r["literature"]:
                assert set(lit) >= {"key", "label"}
            for k in ("sub_claim", "conclusion", "conclusion_conditions", "uncertainty_range", "key_uncertainty"):
                assert isinstance(r[k], str) and r[k].strip(), (r["row_id"], k)


def test_allowed_verdicts_and_source_types(matrix):
    for h, r in _rows(matrix):
        assert h["verdict"] in ALLOWED_V2_VERDICTS
        assert r["verdict"] in ALLOWED_VERDICTS, r["row_id"]
        for n in r["numerical_findings"]:
            assert FINDING_FIELDS <= set(n)
            assert n["source_type"] in ALLOWED_SOURCE_TYPES, (r["row_id"], n)


def test_hypothesis_verdict_follows_rule(matrix, builder):
    for h in matrix["hypotheses"]:
        # version 1 rule, applied to the current rows, is kept beside the version 2 verdict
        assert h["verdict_v1_rule_on_current_rows"] == builder.hypothesis_verdict(h["rows"]), h["id"]
        # version 2: components from primary rows, hypothesis from components
        rows = {r["row_id"]: r for r in h["rows"]}
        for c in h["components"]:
            assert c["verdict"] == builder.component_verdict([rows[x]["verdict"] for x in c["primary_rows"]]), c["id"]
        assert h["verdict"] == builder.hypothesis_verdict_v2([c["verdict"] for c in h["components"]]), h["id"]


def test_every_source_and_link_exists(matrix):
    for _, r in _rows(matrix):
        for n in r["numerical_findings"]:
            assert (ROOT / n["source_file"]).is_file(), n["source_file"]
        for group in ("data", "figures", "screenshots"):
            for p in r["links"][group]:
                assert not Path(p).is_absolute() and not p.startswith("/"), p
                assert (ROOT / p).is_file(), p


def test_every_value_equals_file_value(matrix, builder):
    builder._CACHE.clear()
    for _, r in _rows(matrix):
        for n in r["numerical_findings"]:
            raw = builder.resolve(n["source_file"], n["key"])
            expected = builder.as_number(raw, n["source_file"], n["key"])
            assert isinstance(n["value"], (int, float)) and not isinstance(n["value"], bool)
            assert math.isfinite(n["value"])
            assert n["value"] == expected, (r["row_id"], n["quantity"], n["value"], expected)


def test_literature_keys_in_reference_library(matrix, builder):
    keys = builder.ref_keys()
    for _, r in _rows(matrix):
        for lit in r["literature"]:
            assert lit["key"] in keys, (r["row_id"], lit["key"])


def test_validation_status_matches_files(matrix, builder):
    for _, r in _rows(matrix):
        for s in r["validation_status"]:
            area = Path(s["file"]).stem
            assert builder.validation_status(area) == s


def test_matrix_is_current_with_result_files(matrix, builder):
    builder._CACHE.clear()
    fresh = builder.build()
    for h_old, h_new in zip(matrix["hypotheses"], fresh["hypotheses"]):
        assert h_old["verdict"] == h_new["verdict"], h_old["id"]
        assert [c["verdict"] for c in h_old["components"]] == [c["verdict"] for c in h_new["components"]], h_old["id"]
        for r_old, r_new in zip(h_old["rows"], h_new["rows"]):
            assert r_old["row_id"] == r_new["row_id"]
            assert r_old["verdict"] == r_new["verdict"], r_old["row_id"]
            assert [n["value"] for n in r_old["numerical_findings"]] == [n["value"] for n in r_new["numerical_findings"]], r_old["row_id"]


def test_missing_key_fails_loudly(builder):
    with pytest.raises(builder.EvidenceError):
        builder.resolve("results/research/enduse/enduse_results.json", "no_such_key")
    with pytest.raises(builder.EvidenceError):
        builder.resolve("results/research/no_such_file.json", "x")


def test_markdown_generated_from_json(matrix):
    assert MD.is_file()
    text = MD.read_text(encoding="utf-8")
    for h, r in _rows(matrix):
        assert f"## {h['id']}: {h['verdict']}" in text
        assert f"### {r['row_id']}: {r['verdict']}" in text


def test_no_private_paths(matrix):
    import os
    blob = json.dumps(matrix) + MD.read_text(encoding="utf-8")
    bad = ["C:\\", "C:/", "Users\\", "/Users/", str(ROOT), str(Path.home())]
    for var in ("USERNAME", "USER", "COMPUTERNAME"):
        if os.environ.get(var):
            bad.append(os.environ[var])
    for b in bad:
        assert b not in blob, "private path or name in the evidence matrix"
