"""Aggregate the research-expansion validation items into one summary.

Reads results/research/validation/*.json (one file per workstream; a file is either a list of items or a
dict with an "items" list) and writes

  results/research/validation/summary.json
  docs/validation/research_validation.md

The core validation matrix (results/validation/validation_matrix.json) is neither read nor changed. Items whose
id starts with "EXISTING-" are copies of core-matrix rows that a workstream mirrored for context; they are counted
(nothing is hidden) but also reported separately so they are not double counted against the core matrix.

Deterministic: no timestamps, sorted inputs, content hashes of the inputs in the provenance block.
Run:  python scripts/research/build_research_validation.py
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
VAL_DIR = ROOT / "results" / "research" / "validation"
OUT_JSON = VAL_DIR / "summary.json"
OUT_MD = ROOT / "docs" / "validation" / "research_validation.md"
STATUSES = ("pass", "fail", "informational", "not_available")
CAUSE_KEYS = ("cause", "root_cause_recorded", "note", "remark", "comment")
# The four kinds of evidence (docs/internal/phase2_brief.md). AmCraX has no independent experimental validation:
# an item of that kind may only exist as a "not_available" placeholder and is never counted as evidence.
EVIDENCE_KINDS = ("numerical_verification", "python_vs_aspen", "literature_comparison", "experimental_validation")
UNSPECIFIED = "unspecified"


def _load(path: Path) -> list[dict]:
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    return data["items"] if isinstance(data, dict) else data


FEHE_DIAGNOSIS = ROOT / "results" / "research" / "heat_exchanger" / "fehe_duty_diagnosis.json"


def _documented_cause(item: dict) -> str | None:
    """Cause documented outside the item (read, never invented). Only the FEHE duty diagnosis exists so far."""
    if not FEHE_DIAGNOSIS.is_file() or not str(item.get("id", "")).endswith("-HI-heat"):
        return None
    for row in json.loads(FEHE_DIAGNOSIS.read_text(encoding="utf-8")).get("rows", []):
        if row.get("source_file") and row["source_file"] in str(item.get("source_files")):
            return (f"documented in results/research/heat_exchanger/fehe_duty_diagnosis.json: Python minus Aspen "
                    f"{row['difference_kW']:.1f} kW, of which {row['state_effect_kW']:.1f} kW from the dew-point state of "
                    f"the cold-side stream and {row['property_effect_kW']:.1f} kW from the NH3 residual-enthalpy basis; "
                    "tolerance unchanged, item still fails")
    return None


def _cause(item: dict) -> str:
    parts = []
    for k in CAUSE_KEYS:
        v = item.get(k)
        if v:
            parts.append(str(v))
    if not parts:
        doc = _documented_cause(item)
        if doc:
            parts.append(doc)
    return " | ".join(parts) if parts else "no cause recorded in the item"


def _counts(items: list[dict]) -> dict:
    c = {s: 0 for s in STATUSES}
    for i in items:
        c[i["status"]] = c.get(i["status"], 0) + 1
    c["total"] = len(items)
    return c


def _kind(item: dict) -> str:
    k = item.get("evidence_kind")
    if k is None:
        return UNSPECIFIED
    if k not in EVIDENCE_KINDS:
        raise SystemExit(f"{item.get('id')}: unknown evidence_kind {k!r}")
    return k


def _by_kind(items: list[dict]) -> dict:
    out = {}
    for k in EVIDENCE_KINDS + (UNSPECIFIED,):
        sel = [i for i in items if _kind(i) == k]
        if sel or k != UNSPECIFIED:
            out[k] = _counts(sel)
    return out


def _check_experimental(items: list[dict], name: str) -> None:
    for i in items:
        if _kind(i) == "experimental_validation" and i["status"] != "not_available":
            raise SystemExit(f"{name}: item {i['id']} is labelled experimental_validation with status {i['status']}; "
                             "AmCraX has no independent experimental validation")


def build() -> dict:
    files = sorted(p for p in VAL_DIR.glob("*.json") if p.name != "summary.json")
    areas: dict[str, dict] = {}
    all_items: list[dict] = []
    hashes = {}
    for p in files:
        hashes[p.name] = hashlib.sha256(p.read_bytes()).hexdigest()
        items = _load(p)
        bad = [i.get("id") for i in items if i.get("status") not in STATUSES]
        if bad:
            raise SystemExit(f"{p.name}: unknown status in {bad}")
        failures = []
        for i in items:
            if i["status"] == "fail":
                failures.append({
                    "id": i["id"],
                    "description": i.get("description"),
                    "observed": i.get("observed"),
                    "expected": i.get("expected"),
                    "tolerance": i.get("tolerance"),
                    "unit": i.get("unit"),
                    "cause": _cause(i),
                    "mirrors_core_matrix": i["id"].startswith("EXISTING-"),
                    "source_files": i.get("source_files", []),
                })
        _check_experimental(items, p.name)
        areas[p.stem] = {"file": f"results/research/validation/{p.name}",
                         **_counts(items), "failures": failures, "by_evidence_kind": _by_kind(items),
                         "items_without_evidence_kind": [i["id"] for i in items if _kind(i) == UNSPECIFIED]}
        all_items.extend(items)
    mirrored = [i for i in all_items if i["id"].startswith("EXISTING-")]
    new_items = [i for i in all_items if not i["id"].startswith("EXISTING-")]
    placeholders = [i["id"] for i in all_items if _kind(i) == "experimental_validation"]
    return {
        "provenance": {
            "script": "scripts/research/build_research_validation.py",
            "source_type": "python",
            "inputs_summary": "results/research/validation/*.json (one file per workstream); core matrix not read",
            "input_sha256": hashes,
            "separate_from": "results/validation/validation_matrix.json (core matrix, unchanged)",
        },
        "totals": _counts(all_items),
        "totals_excluding_items_mirrored_from_core_matrix": _counts(new_items),
        "mirrored_core_items": _counts(mirrored),
        "by_evidence_kind": _by_kind(all_items),
        "by_area_and_evidence_kind": {name: a["by_evidence_kind"] for name, a in areas.items()},
        "experimental_validation": {
            "items_counted_as_evidence": 0,
            "placeholder_items_not_available": placeholders,
            "statement": "AmCraX has no independent experimental validation. Items of kind experimental_validation "
                         "exist only as not_available placeholders and are never counted as evidence. Pass counts "
                         "are numerical verification, Python against Aspen comparison or comparison with published "
                         "literature, never experimental validation.",
        },
        "areas": areas,
    }


def _fmt(v) -> str:
    if isinstance(v, float):
        return f"{v:.6g}"
    return str(v)


def render_md(s: dict) -> str:
    L = ["# Research expansion validation summary", "",
         "Generated by `scripts/research/build_research_validation.py` from `results/research/validation/*.json`; "
         "machine-readable copy in `results/research/validation/summary.json`. This summary is separate from the "
         "core validation matrix (`results/validation/validation_matrix.json`, `docs/validation/validation_matrix.md`), "
         "which is unchanged. Failures are reported as recorded and are not softened or re-scored.", "",
         "## Totals", "", "| Scope | Pass | Fail | Informational | Not available | Total |", "|---|---|---|---|---|---|"]
    def row(name, c):
        return f"| {name} | {c['pass']} | {c['fail']} | {c['informational']} | {c['not_available']} | {c['total']} |"
    for name, a in s["areas"].items():
        L.append(row(name, a))
    L.append(row("**All research items**", s["totals"]))
    L.append(row("of which mirrored from the core matrix", s["mirrored_core_items"]))
    L.append(row("All items excluding mirrored core rows", s["totals_excluding_items_mirrored_from_core_matrix"]))
    L += ["", "Mirrored rows are items with ids starting `EXISTING-`: copies of core-matrix rows that the kinetics "
          "workstream listed for context without re-running them. They are already counted in the core matrix.", "",
          "## By kind of evidence", "",
          "The four kinds of evidence are kept apart: numerical verification, Python against Aspen comparison, "
          "comparison with published literature, and independent experimental validation. "
          + s["experimental_validation"]["statement"], "",
          "| Kind of evidence | Pass | Fail | Informational | Not available | Total |", "|---|---|---|---|---|---|"]
    for k, c in s["by_evidence_kind"].items():
        L.append(row(k, c))
    L += ["", "| Area | " + " | ".join(EVIDENCE_KINDS) + " |", "|---|" + "---|" * len(EVIDENCE_KINDS)]
    for name, kinds in s["by_area_and_evidence_kind"].items():
        L.append(f"| {name} | " + " | ".join(
            f"{kinds[k]['total']} ({kinds[k]['pass']} pass, {kinds[k]['fail']} fail)" for k in EVIDENCE_KINDS) + " |")
    L += ["", "## Failures", ""]
    n = 0
    for name, a in s["areas"].items():
        for f in a["failures"]:
            n += 1
            L += [f"### {n}. `{f['id']}` ({name})", "",
                  f"- Description: {f['description']}",
                  f"- Observed: {_fmt(f['observed'])} {f['unit'] or ''}".rstrip(),
                  f"- Expected: {_fmt(f['expected'])}",
                  f"- Tolerance: {_fmt(f['tolerance'])}",
                  f"- Mirrors a core-matrix row: {'yes' if f['mirrors_core_matrix'] else 'no'}",
                  f"- Cause as recorded: {f['cause']}",
                  f"- Source files: {', '.join('`'+x+'`' for x in f['source_files']) or 'none listed'}", ""]
    if n == 0:
        L.append("No failures.")
    L += ["", "## Reading the informational items", "",
          "Informational items record literature checks that could not be run as pass/fail (for example sources "
          "whose full text was inaccessible) and comparisons without a defined tolerance. They are not passes.", ""]
    return "\n".join(L)


def main() -> None:
    s = build()
    OUT_JSON.write_text(json.dumps(s, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    OUT_MD.parent.mkdir(parents=True, exist_ok=True)
    OUT_MD.write_text(render_md(s), encoding="utf-8")
    t = s["totals"]
    print(f"research validation: {t['pass']} pass, {t['fail']} fail, {t['informational']} informational, "
          f"{t['not_available']} not available of {t['total']}")
    print("by evidence kind:", {k: c["total"] for k, c in s["by_evidence_kind"].items()})


if __name__ == "__main__":
    main()
