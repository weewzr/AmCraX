"""Record the Phase 2 addendum of 24 November 2026: three papers that earlier could only be seen as abstracts or search
summaries were read in full (Halim et al. 2025; Abdoos et al. 2025; Sayas et al. 2020).

Same discipline as scripts/research/record_fix_pass.py: old values are read from git commit PRE_ADDENDUM (the last commit
before the addendum), new values from the working tree. Writes results/research/addendum_2026-11-24.json, which
build_evidence_matrix.py copies into docs/research/phase2_findings_changed.md (section "Addendum after reading three
papers in full"). Run from the project root after the re-runs and before the matrix:

    python scripts/research/record_addendum.py

Nothing here changes a model, a rule or a verdict. The frozen baseline LCOH is checked to 1e-12.
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PRE_ADDENDUM = "227961c"
OUT = ROOT / "results" / "research" / "addendum_2026-11-24.json"
FROZEN_LCOH = 4.015461254695034
PAPERS = {"halim2025ammonia": "Halim, Zain and Khoo (2025), Applied Energy 386, 125581",
          "abdoos2025psa": "Abdoos, Di Benedetto and Russo (2025), Chemical Engineering Journal 526, 170994",
          "sayas2020rukcao": "Sayas et al. (2020), Catalysis Science & Technology 10, 5027-5035"}

# (file, key regex on the flattened path, what, reason): stored TEXT and data corrections of record (strings and numbers)
TEXT_SELECT = [
    ("research/data/enduse_cost_literature.json", r"^entries/\[halim_numbers\]/", "Halim status and the 30-60 vol% H-25 attribution",
     "full text read: all four numbers located; the 40 % is a fuel cost at the turbine inlet; the H-25 range is in the paper (not a mis-attribution)"),
    ("research/data/turbine_efficiency_literature.json", r"\[(halim2025_status|h2_blend_limits_vendor)\]/", "Halim status; origin of the 30-60 vol% figure",
     "full text read; the NETL Baker Hughes statement is not the origin of the essay's H-25 figure"),
    ("research/data/purification_literature.json", r"^entries/\[S0[78]\]/", "Abdoos search-summary numbers (S07) and PSA specific energy (S08)",
     "Table 8 values entered; '5.2 MJ/kg' joined two points; '35 bar, 99.97 %, 79 %' is Moon et al. 2016 (syngas); SEC is feed compression"),
    ("research/references.json", r"^\[(halim2025ammonia|sayas2020rukcao|sayas2020high)\]/", "reference records of Halim and Sayas",
     "full text read on 24 November 2026; one record per paper"),
    ("results/research/enduse/turbine_threshold.json", r"^(forty_percent_figure/halim_status|row_evidence/H1-b/(uncertainty|reason))",
     "stored Halim status and H1-b row evidence text", "full text read; the row tests the essay's sentence about power"),
    ("results/research/enduse/enduse_results.json", r"^(halim_claim_check/(halim_statement|verdict_note)|limitations/4|fuel_flexibility/source_type)$",
     "stored Halim texts of the end-use results", "full text read"),
    ("results/research/enduse/nox_n2o_blends.json", r"^blends_and_cracked_gas/blend_limits$", "blend-limit statement",
     "the H-25 range is printed in Halim et al. p. 3 (trade press)"),
    ("results/research/validation/enduse.json", r"^\[EU-halim-(claim|plant)\]/(reference_source|method|observed)$",
     "validation items on the Halim figures", "full text read; the plant numbers are located"),
    ("results/research/purification/phase2_comparison.json", r"^(inputs/psa_recovery/[^/]+/(central|high)/note|row_evidence/H4-(a|d)/(uncertainty|reason|threshold))$",
     "labels of the PSA recovery cases and H4 row evidence text",
     "Abdoos front: mass-balance central recoveries are pessimistic, not optimistic; 0.85 lies above the front; two published relations"),
    ("results/research/kinetics/validity_classification.json", r"^laws/\[sayas2020rukcao\]/(reason|experimental/[^/]+|class_evidence)",
     "Ru-K/CaO validity text (class unchanged: unmodelled)", "main text read: no complete rate law (rate constant and equilibrium term in the "
     "supplementary information, not obtained); nothing fitted"),
    ("results/research/validation/kinetics.json", r"^\[(KINR-LIT-SAYAS2020|K1P2-SEARCH-MISSING-KINETICS)\]/(method|reference_source|observed|expected|note|source_files/\d)",
     "kinetics validation items on Sayas", "essay values verified in the main text; still no usable complete law"),
]
# reference-addition entries removed so that one record per paper is used (old entries kept in this record)
REMOVED_REFS = [("research/reference_additions/phase2_kinetics.json", "sayas2020rukcao"),
                ("research/reference_additions/kinetics.json", "sayas2020rukcao"),
                ("research/reference_additions/phase2_purification.json", "abdoos2025psa"),
                ("research/reference_additions/enduse_lca.json", "halim2025ammoniapower"),
                ("research/reference_additions/economics.json", "halim2025ammonia")]
TEXT_FILES = [  # corrections in prose and code comments (no key structure); summary of each
    ("research/notes/enduse_turbine_literature.md", "sections 3 and 7: the H-25 30-60 vol% figure is in Halim et al. p. 3; full text read; the four numbers located"),
    ("research/notes/carrier_cost_literature.md", "(d): the quoted 40 % is not a power generation cost but a fuel cost per kg of hydrogen-equivalent energy (1 - LCOA/LCOH)"),
    ("research/notes/purification_phase2.md", "Abdoos 2025 read: Table 8 entered; search-summary numbers corrected; 'optimistic' label of the mass-balance cases withdrawn"),
    ("research/notes/sayas2020rukcao.md", "superseded status: main text read; Ea and orders verified; K/Ru 0.9 inconsistent with the loadings (8.6); '40 times' is a pressure multiplication"),
    ("research/notes/phase2_kinetics_search.md", "Sayas main text read; essay values verified; still no rate constant"),
    ("research/notes/xu2025review.md", "the '40 times' Sayas claim checked against the original"),
    ("research/model_parameters.yaml", "ru_k_cao_sayas_power_law: 111 kJ/mol and K0 8584.8 not in the main text (75 kJ/mol apparent at 350 degC, 1 atm; supplementary information not obtained); K/Ru ratio inconsistency"),
    ("backend/amcrax/enduse/params.py", "comment on the H-25 blend range: source located (Halim et al. p. 3)"),
    ("backend/amcrax/data/singapore.yaml", "policy_context halim_2025: full text read; LCOH and 60.1 MW located; the 40 % is a fuel cost (text only, no number used)"),
    ("research/references.json", "halim2025ammonia, sayas2020rukcao and sayas2020high: full text read on 24 November 2026; one record per paper"),
    ("scripts/research/enduse_run.py", "Halim texts written into enduse_results.json and validation/enduse.json"),
    ("scripts/research/enduse_threshold.py", "halim_status, blend_limits, H1-b row evidence text; new computed block fuel_cost_gap_on_paper_basis"),
    ("scripts/research/economics_singapore.py", "abstract-only Halim reference entry removed (one record per paper)"),
    ("scripts/research/purification_phase2.py", "labels of the recovery cases; H4 row evidence text; new labelled case abdoos2025_sourced_case"),
    ("scripts/research/kinetics_validity_classification.py", "Ru-K/CaO reason and experimental fields; Sayas comparison points and cross-catalyst context"),
    ("scripts/research/kinetics_validation.py", "KINR-LIT-SAYAS2020 verified in the main text"),
    ("scripts/research/kinetics_phase2_validation.py", "search item note; new items K1P2-SAYAS-POINTS and K1P2-SAYAS-RUAL2O3-CONTEXT"),
    ("scripts/research/economics_reference_scenario.py", "new computed block psa_recovery_sensitivity beside the fuel-efficiency envelope"),
    ("scripts/research/build_evidence_matrix.py", "texts that were false (full text not accessible; only sourced slope; published-figures wording; Halim and Sayas literature labels and keys) and the new numbers in the rows' numerical conclusions; no rule changed"),
]
NEW_BLOCKS = [
    ("results/research/enduse/turbine_threshold.json", "forty_percent_figure/fuel_cost_gap_on_paper_basis",
     "H1-b on the paper's own basis: 1 - direct NH3 fuel cost / cracked H2 cost per kg of hydrogen-equivalent energy, grey/blue/green and the paper's prices, heat integration on and off; reconciliation with the paper"),
    ("results/research/purification/phase2_comparison.json", "abdoos2025_sourced_case",
     "Abdoos et al. 2025 Table 8 as a labelled sourced case: LCOH per kg usable H2 at both grades, purity-only increment on each relation against the resolution, position against parity and furnace-balance recoveries, boundary differences"),
    ("results/research/reference_scenario/baseline.json", "psa_recovery_sensitivity",
     "baseline LCOH, NPV and break-even NH3 price at PSA recovery 0.8192 and 0.7744 (same code path as every recovery change); reference unchanged"),
    ("results/research/kinetics/validity_classification.json", "literature_comparison_points_sayas2020",
     "15 measured Sayas conversions at 10-40 bar (figure readings), not used by any model"),
    ("results/research/kinetics/validity_classification.json", "cross_catalyst_context_sayas2020",
     "the Ru/Al2O3 law at the Sayas conditions with equal Ru per mol NH3: cross-catalyst context, not a test of the law"),
]
VERDICT_FILE = "results/research/evidence_matrix.json"


def git_text(rel: str) -> str | None:
    out = subprocess.run(["git", "show", f"{PRE_ADDENDUM}:{rel}"], cwd=ROOT, capture_output=True, text=True, encoding="utf-8")
    return out.stdout if out.returncode == 0 else None


def walk(o, path=""):
    if isinstance(o, dict):
        for k, v in o.items():
            yield from walk(v, f"{path}/{k}" if path else str(k))
    elif isinstance(o, list):
        for i, v in enumerate(o):
            idk = (v.get("id") or v.get("citekey")) if isinstance(v, dict) else None
            yield from walk(v, f"{path}/[{idk}]" if idk is not None else f"{path}/{i}")
    else:
        yield path, o


def get(o, path):
    for seg in path.split("/"):
        if isinstance(o, list):
            o = o[int(seg)]
        else:
            o = o[seg]
    return o


def verdicts(m) -> dict:
    out = {}
    for h in m["hypotheses"]:
        out[f"hypothesis {h['id']}"] = h["verdict"]
        for c in h.get("components", []):
            out[f"component {c['id']}"] = c["verdict"]
        for r in h["rows"]:
            out[f"row {r['row_id']}"] = r["verdict"]
    return out


def main() -> int:
    text_rows = []
    for rel, rx, what, why in TEXT_SELECT:
        old_t = git_text(rel)
        if old_t is None:
            print(f"{rel}: not in {PRE_ADDENDUM}", file=sys.stderr)
            return 2
        o, n = dict(walk(json.loads(old_t))), dict(walk(json.loads((ROOT / rel).read_text(encoding="utf-8"))))
        for k in sorted(set(o) | set(n)):
            if not re.search(rx, k) or k.endswith("generated_utc"):
                continue
            a, b = o.get(k), n.get(k)
            if a != b:
                text_rows.append({"what": what, "file": rel, "key": k, "old": a, "new": b, "reason": why})
    removed = []
    for rel, key in REMOVED_REFS:
        old = [x for x in json.loads(git_text(rel)) if x.get("citekey") == key]
        now = [x for x in json.loads((ROOT / rel).read_text(encoding="utf-8")) if x.get("citekey") == key]
        removed.append({"file": rel, "citekey": key, "removed": bool(old) and not now, "old_entry": old[0] if old else None,
                        "superseded_by": "research/references.json (full-text record) and research/reference_additions/phase2_fulltext_*.json"})
    # new computed values (selected numbers, with file and key)
    tt = json.loads((ROOT / "results/research/enduse/turbine_threshold.json").read_text(encoding="utf-8"))
    pc = json.loads((ROOT / "results/research/purification/phase2_comparison.json").read_text(encoding="utf-8"))
    bl = json.loads((ROOT / "results/research/reference_scenario/baseline.json").read_text(encoding="utf-8"))
    kv = json.loads((ROOT / "results/research/kinetics/validity_classification.json").read_text(encoding="utf-8"))
    assert abs(bl["lcoh_USD_per_kg"] - FROZEN_LCOH) <= 1e-12, "frozen baseline changed"
    nv = []
    fb = tt["forty_percent_figure"]["fuel_cost_gap_on_paper_basis"]
    for i, c in enumerate(fb["cases"]):
        nv.append({"file": "results/research/enduse/turbine_threshold.json",
                   "key": f"forty_percent_figure/fuel_cost_gap_on_paper_basis/cases/{i}/gap_pct_1_minus_direct_over_cracked",
                   "label": f"paper-basis fuel-cost gap, {c['price_case']} {c['NH3_USD_per_t']:g} USD/t, heat integration {c['heat_integration']}",
                   "value": c["gap_pct_1_minus_direct_over_cracked"], "unit": "%"})
    for k in ("green", "blue"):
        for j, s in enumerate(fb["reconciliation"][k]["steps"]):
            nv.append({"file": "results/research/enduse/turbine_threshold.json",
                       "key": f"forty_percent_figure/fuel_cost_gap_on_paper_basis/reconciliation/{k}/steps/{j}/gap_pct",
                       "label": f"reconciliation {k}: {s['step']}", "value": s["gap_pct"], "unit": "%"})
    ab = pc["abdoos2025_sourced_case"]
    for spec, d in ab["lcoh_by_specification"].items():
        for pid, x in d.items():
            nv.append({"file": "results/research/purification/phase2_comparison.json",
                       "key": f"abdoos2025_sourced_case/lcoh_by_specification/{spec}/{pid}/lcoh_usd_per_kg_usable",
                       "label": f"LCOH per kg usable H2, {spec}, PSA recovery {x['recovery']:g} (Abdoos {x['purity_of_point'] * 100:.2f} %)",
                       "value": x["lcoh_usd_per_kg_usable"], "unit": "USD/kg H2"})
    for k, x in ab["equal_delivery_increment"].items():
        nv.append({"file": "results/research/purification/phase2_comparison.json",
                   "key": f"abdoos2025_sourced_case/equal_delivery_increment/{k}/increment",
                   "label": f"purity-only Grade D increment at 30 bar, {k} (above resolution {x['above_resolution']})",
                   "value": x["increment"], "unit": "USD/kg H2"})
    for i, x in enumerate(ab["equal_delivery_increment_surrogate_scatter"]):
        nv.append({"file": "results/research/purification/phase2_comparison.json",
                   "key": f"abdoos2025_sourced_case/equal_delivery_increment_surrogate_scatter/{i}/increment",
                   "label": f"Abdoos-relation increment with {x['scatter_points']:g} surrogate scatter, {x['direction']}",
                   "value": x["increment"], "unit": "USD/kg H2"})
    nv.append({"file": "results/research/purification/phase2_comparison.json", "key": "abdoos2025_sourced_case/model_resolution_USD_per_kg",
               "label": "model resolution (Python against Aspen LCOH offset), read", "value": ab["model_resolution_USD_per_kg"], "unit": "USD/kg H2"})
    nv.append({"file": "results/research/purification/phase2_comparison.json",
               "key": "abdoos2025_sourced_case/position/furnace_balance/grade_D_point_margin",
               "label": "Abdoos Grade D recovery minus the furnace-balance recovery", "value": ab["position"]["furnace_balance"]["grade_D_point_margin"], "unit": "-"})
    for i, c in enumerate(bl["psa_recovery_sensitivity"]["cases"]):
        for q, u in (("lcoh_USD_per_kg", "USD/kg H2"), ("npv_USD", "USD"), ("breakeven_nh3_USD_per_t_vs_marker", "USD/t")):
            nv.append({"file": "results/research/reference_scenario/baseline.json", "key": f"psa_recovery_sensitivity/cases/{i}/{q}",
                       "label": f"baseline at PSA recovery {c['psa_recovery']:g}: {q}", "value": c[q], "unit": u})
    cx = kv["cross_catalyst_context_sayas2020"]
    for i, o in enumerate(cx["cases"]):
        for j, rr in enumerate(o["rows"]):
            if rr["P_bar"] == 20.0 and rr["T_C"] == 500.0:
                nv.append({"file": "results/research/kinetics/validity_classification.json",
                           "key": f"cross_catalyst_context_sayas2020/cases/{i}/rows/{j}/X_RuAl2O3_law_equal_Ru",
                           "label": f"Ru/Al2O3 law at 20 bar, 500 degC, equal Ru per NH3 ({o['flow_reference_state']} flow basis); measured Ru-K/CaO {rr['X_measured_RuK_CaO']:g}",
                           "value": rr["X_RuAl2O3_law_equal_Ru"], "unit": "conversion"})
    sys.path.insert(0, str(ROOT / "scripts" / "research"))
    import build_evidence_matrix as bem  # noqa: E402
    vo, vn = verdicts(json.loads(git_text(VERDICT_FILE))), verdicts(bem.build())
    vrows = [{"quantity": k, "old": vo.get(k), "new": vn.get(k)} for k in sorted(set(vo) | set(vn)) if vo.get(k) != vn.get(k)]
    OUT.write_text(json.dumps({
        "provenance": {"script": "scripts/research/record_addendum.py", "old_values": f"git commit {PRE_ADDENDUM}",
                       "new_values": "working tree after the addendum re-runs",
                       "papers_read_in_full_on_2026_11_24": PAPERS,
                       "notes": ["research/notes/halim2025_full_text.md", "research/notes/abdoos2025_full_text.md", "research/notes/sayas2020_full_text.md"],
                       "extracts": ["research/data/halim2025_extract.json", "research/data/abdoos2025_extract.json", "research/data/sayas2020_extract.json"],
                       "rule": "no model, rule or verdict changed; the frozen baseline is unchanged; new evidence is reported as computed sensitivities and literature comparisons beside the existing results"},
        "description": "Every correction of record and every new computed value of the addendum of 24 November 2026.",
        "baseline_check": {"lcoh_USD_per_kg": bl["lcoh_USD_per_kg"], "frozen": FROZEN_LCOH, "abs_difference": abs(bl["lcoh_USD_per_kg"] - FROZEN_LCOH)},
        "verdict_changes": vrows, "verdicts_checked": len(vn),
        "text_corrections": text_rows, "reference_entries_removed": removed, "text_files_corrected": [{"file": a, "what": b} for a, b in TEXT_FILES],
        "new_computed_blocks": [{"file": a, "key": b, "what": c} for a, b, c in NEW_BLOCKS],
        "new_computed_values": nv,
    }, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"verdict changes {len(vrows)} of {len(vn)}, text corrections {len(text_rows)}, new values {len(nv)}")
    return 0 if not vrows else 3


if __name__ == "__main__":
    raise SystemExit(main())
