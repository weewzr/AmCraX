"""Phase 2 task C1: unified techno-economic reference scenario. Deterministic; run from the project root:

    python scripts/research/economics_reference_scenario.py                 # baseline.json + capex_audit.json
    python scripts/research/economics_reference_scenario.py --supersession  # after all workstream scripts re-ran

Writes results/research/reference_scenario/{baseline.json, capex_audit.json, supersession.json}.
All inputs come from backend/amcrax/data/reference_scenario.yaml (amcrax.economics.reference).
"""
from __future__ import annotations

import json
import math
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))
from amcrax.economics.lcoh import compute_lcoh, estimate_capex  # noqa: E402
from amcrax.economics.models import EconomicAssumptions, load_economics_data  # noqa: E402
from amcrax.economics.reference import (load_reference_scenario, provenance_stamp, reference_capex,  # noqa: E402
                                        reference_item_costs)
from amcrax.economics.singapore import evaluate, extract_summary  # noqa: E402
from amcrax.schemas import MOLAR_MASS, SimulationResult  # noqa: E402

OUT = ROOT / "results" / "research" / "reference_scenario"
OUT.mkdir(parents=True, exist_ok=True)
OLD = ROOT / "results" / "research_releases" / "2026-11-23"   # Phase 1 release copy (read only)
SCRIPT = "scripts/research/economics_reference_scenario.py"
REF = load_reference_scenario()
FX = REF.fx_SGD_per_USD


def prov(inputs: str) -> dict:
    return {"generated_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"), "script": SCRIPT,
            "source_type": "python", "inputs_summary": inputs, "reference_scenario": provenance_stamp(),
            "model_versions": {"economics_module": "amcrax.economics.singapore/2 + amcrax.economics.reference/1",
                               "capex_method": REF.capex_method, "cost_basis": REF.raw["price_year_label"]}}


def dump(name: str, obj) -> None:
    (OUT / name).write_text(json.dumps(obj, indent=2, default=float), encoding="utf-8")


def flat_inputs(d: dict, prefix: str = "") -> dict:
    out = {}
    for k, v in d.items():
        if isinstance(v, dict) and "value" in v:
            out[prefix + k] = {kk: v.get(kk) for kk in ("value", "unit", "source_type", "source", "note") if kk in v}
        elif isinstance(v, dict):
            out.update(flat_inputs(v, prefix + k + "."))
    return out


def baseline() -> None:
    hi = json.loads((ROOT / "results/simulations/baseline.json").read_text(encoding="utf-8"))
    nohi = json.loads((ROOT / "results/simulations/baseline_no_hi.json").read_text(encoding="utf-8"))
    s = extract_summary(hi)
    assert abs(s["h2_kg_h"] - REF.h2_product_kg_h) < 1e-9 and abs(s["nh3_feed_kmol_h"] - REF.nh3_feed_kmol_h) < 1e-9, \
        "reference_scenario.yaml plant block does not match the stored Aspen baseline"
    e = evaluate(hi, REF.default_nh3_scenario)
    e_nohi = evaluate(nohi, REF.default_nh3_scenario)
    scen = {sc: {"lcoh_USD_per_kg": (x := evaluate(hi, sc))["lcoh_USD_per_kg"], "lcoh_SGD_per_kg": x["lcoh_SGD_per_kg"],
                 "rec_USD_per_kg": x["rec_USD_per_kg"], "rec_SGD_per_kg": x["rec_SGD_per_kg"],
                 "nh3_price_USD_per_t": x["nh3_price_USD_per_t"]} for sc in REF.nh3_prices_USD_per_t}
    leg = REF.reproduction("legacy_v1")
    legacy = evaluate(hi, leg["nh3_price_USD_per_t"], {"capex_mode": "legacy",
                                                        "electricity_price_USD_per_kWh": leg["electricity_price_USD_per_kWh"]})
    stored = json.loads((ROOT / "results/simulations/economics_baseline.json").read_text(encoding="utf-8"))
    p1 = evaluate(hi, "grey", {"capex_mode": "equipment"})
    cap = e["capex"]
    out = {
        "provenance": prov("Aspen Plus V15 stored baseline (results/simulations/baseline.json) costed on the unified "
                           "reference scenario by amcrax.economics.singapore.evaluate"),
        "description": "AUTHORITATIVE AmCraX techno-economic baseline (Phase 2). Grey NH3 scenario, heat integration on, "
                       "plant gate, H2 at PSA outlet pressure (19.5 bar), no product compression or storage.",
        "case_id": "baseline", "input_source": e["input_source"], "scenario": e["scenario"],
        "currency": "USD", "price_year": REF.raw["price_year_label"], "fx_SGD_per_USD": FX, "fx_date": REF.fx_date,
        "h2_product_kg_h": e["h2_product_kg_h"], "annual_h2_kg": e["annual_h2_kg"], "nh3_feed_kmol_h": REF.nh3_feed_kmol_h,
        "nh3_price_USD_per_t": e["nh3_price_USD_per_t"],
        "lcoh_USD_per_kg": e["lcoh_USD_per_kg"], "lcoh_SGD_per_kg": e["lcoh_SGD_per_kg"],
        "rec_USD_per_kg": e["rec_USD_per_kg"], "rec_SGD_per_kg": e["rec_SGD_per_kg"],
        "breakdown_USD_per_kg": e["breakdown_USD_per_kg"], "breakdown_SGD_per_kg": e["breakdown_SGD_per_kg"],
        "annual_USD_per_yr": e["annual_USD_per_yr"], "fixed_opex_detail_USD_per_yr": e["fixed_opex_detail_USD_per_yr"],
        "npv_USD": e["npv_USD"], "npv_SGD": e["npv_SGD"], "irr": e["irr"], "payback_yr": e["payback_yr"],
        "npv_basis": f"selling price {e['h2_price_USD_per_kg']} USD/kg H2 (Argus NE Asia SMR marker), pre-tax, constant prices",
        "capex_total_USD": cap["total_capex_USD"], "capex_total_SGD": cap["total_capex_USD"] * FX,
        "capex_isbl_by_item_USD": cap["isbl_USD"], "capex_tci_by_item_USD": cap["tci_by_item_USD"],
        "capex_indirects_USD": cap["indirects_USD"], "capex_method": cap["method"], "capex_basis": cap["basis"],
        "capex_size_ratio": cap["size_ratio"], "crf": e["crf"],
        "purification_memo_USD_per_kg": e["purification_memo_USD_per_kg"],
        "kg_nh3_feed_per_kg_h2": e["kg_nh3_feed_per_kg_h2"], "kg_nh3_fuel_per_kg_h2": e["kg_nh3_fuel_per_kg_h2"],
        "catalyst_mass_kg": e["catalyst_mass_kg"], "carbon_tax_liable": e["carbon_tax_liable"],
        "direct_emissions_tCO2e_per_yr": e["direct_emissions_tCO2e_per_yr"],
        "heat_integration_off": {"lcoh_USD_per_kg": e_nohi["lcoh_USD_per_kg"], "lcoh_SGD_per_kg": e_nohi["lcoh_SGD_per_kg"],
                                 "rec_USD_per_kg": e_nohi["rec_USD_per_kg"], "breakdown_USD_per_kg": e_nohi["breakdown_USD_per_kg"]},
        "nh3_scenarios": scen,
        "superseded_bases": {
            "legacy_v1_correlation": {"lcoh_USD_per_kg": legacy["lcoh_USD_per_kg"], "stored_lcoh_USD_per_kg": stored["lcoh_USD_per_kg"],
                                      "capex_total_USD": legacy["capex"]["total_capex_USD"],
                                      "basis": "amcrax.economics.lcoh (Ahmad 2025 Fig. 6), electricity 0.084; core stored results"},
            "phase1_equipment": {"lcoh_USD_per_kg": p1["lcoh_USD_per_kg"], "capex_total_USD": p1["capex"]["total_capex_USD"],
                                 "basis": "Farokhi 2025 PEC x 5.93 scaled by feed^0.8 (Phase 1 singapore.py default), at the reference FX and electricity"}},
        "inputs": flat_inputs(REF.raw),
        "boundary_notes": e["notes"],
    }
    dump("baseline.json", out)
    dump("capex_audit.json", capex_audit(s, e, legacy, p1))
    print("baseline LCOH", e["lcoh_USD_per_kg"], "SGD", e["lcoh_SGD_per_kg"], "CAPEX", cap["total_capex_USD"])


def capex_audit(s: dict, e: dict, legacy: dict, p1: dict) -> dict:
    """Both Phase 1 methods and the reference method, plus published plant costs normalised to AmCraX."""
    h2 = s["h2_kg_h"]
    lib = load_economics_data()["capex_references"]
    rows = []

    def norm(label, c_usd, s_ref_kg_h, scope, src, note, exps=(0.6, 0.7451, 0.8)):
        rows.append({"source": label, "reference_capex_USD": c_usd, "reference_h2_kg_h": s_ref_kg_h, "scope": scope,
                     "citation": src, "normalised_to_amcrax_USD": {f"n={n:g}": c_usd * (h2 / s_ref_kg_h) ** n for n in exps},
                     "scale_ratio": h2 / s_ref_kg_h, "note": note})

    ic = reference_item_costs()
    cho_total = sum(v for v in ic["installed_USD"].values()) * ic["indirect_factor"]
    cho_excomp = cho_total - ic["installed_USD"]["compressor"] * ic["indirect_factor"]
    norm("Cho 2026 Ni-24.34 bar, total C_C", cho_total, ic["reference_h2_kg_h"],
         "ISBL (boiler, HX, compressor, T/PSA, reactor) + OSBL + engineering + contingency, 2024 USD",
         "cho2026nickel p. 13 Table 7 (unit CAPEX 0.586 USD/kg x 82.3 kg/h x 8000 h / CRF(8.5 %, 25 y))",
         "basis of the reference method; not an independent check of it")
    norm("Cho 2026 Ni-24.34 bar, without the 180 bar product compressor", cho_excomp, ic["reference_h2_kg_h"],
         "as above, compressor item removed", "same", "basis of the reference method (scaled on H2 here, on NH3 feed in the method)")
    r = lib["chopra2026_point"]
    c = r["capex_MUSD"] * 1e6 * (1 - r["compressor_share_of_TCI"]["value"]) / r["location_factor_india"]["value"]
    norm("Chopra 2026, 400 kg/d, compressor share removed, India factor removed", c, r["capacity_kg_H2_per_d"] / 24.0,
         "complete NH3-cracking H2 plant (Turton/Guthrie), cost year 2025", "chopra2026decentralized p. 7 Sec. 3.2; Fig. 5(a)",
         "independent; 15x scale-up to AmCraX; compressor and location adjustments are AmCraX derivations")
    r = lib["farokhi2025_point"]
    norm("Farokhi 2025, 500 kmol/h NH3", r["tci_kUSD"] * 1e3, r["h2_kg_per_kg_nh3"] * r["nh3_feed_kmol_h"] * MOLAR_MASS["NH3"],
         "TCI = 5.93 x PEC incl. working capital; cost year not stated; kUSD unit inferred",
         "farokhi2025costoptimization p. 5 Table 5", "independent; basis of the Phase 1 'equipment' method")
    a = EconomicAssumptions()
    rows.append({"source": "Ahmad 2025 Fig. 6 correlation (Cesaro 2021 data)", "reference_capex_USD": None, "reference_h2_kg_h": None,
                 "scope": "plant-level NH3 cracker correlation fitted to SMR and cracker data; cost year not stated",
                 "citation": "ahmad2025gtcc p. 7 Fig. 6", "normalised_to_amcrax_USD": {"correlation": estimate_capex(h2, a).total_capex_USD},
                 "scale_ratio": None, "note": "independent of Cho; basis of the legacy model"})
    eur = REF.usd_per_eur
    norm("Mehr 2026 base case (EUR 642.7 M at 5726 kg/h), converted at the reference USD/EUR", 642.7e6 * eur, 5726.0,
         "high-capacity terminal-scale cracking plant (APEA); scope includes large-scale handling",
         "mehr2026highcapacity p. 14", "paper has many internal inconsistencies (research/notes/mehr2026highcapacity.md); informational only")
    not_compared = [
        {"source": "Kum 2026", "reason": "total FCI/TCI not recorded in research/notes/kum2026heatintegrated.md; PEC coefficients not given in the paper"},
        {"source": "Deka 2025", "reason": "paper not in the library (values in the brief only); primary source not obtained"},
        {"source": "Makhloufi & Kezibri 2021", "reason": "only quoted inside Cho 2026 Table 1 (4.83 EUR2019/kg LCOH, 200 t/d); no CAPEX in the library"},
        {"source": "Lee et al. 2022 (lee2022ammonia)", "reason": "ammonia PRODUCTION pathways, not cracking; relevant to NH3 prices only"}]
    methods = {
        "reference_cho2026_itemised_v1": {"capex_total_USD": e["capex"]["total_capex_USD"], "lcoh_USD_per_kg": e["lcoh_USD_per_kg"]},
        "phase1_equipment_farokhi": {"capex_total_USD": p1["capex"]["total_capex_USD"], "lcoh_USD_per_kg": p1["lcoh_USD_per_kg"]},
        "legacy_ahmad_correlation": {"capex_total_USD": legacy["capex"]["total_capex_USD"], "lcoh_USD_per_kg": legacy["lcoh_USD_per_kg"],
                                     "note": "electricity 0.084 (legacy v1 basis)"}}
    indep = [v for r_ in rows if r_["note"].startswith("independent") for v in r_["normalised_to_amcrax_USD"].values()]
    return {"provenance": prov("library CAPEX data (economics.yaml capex_references, reference_scenario.yaml) normalised to the "
                               "AmCraX H2 capacity; informational"),
            "amcrax_h2_kg_h": h2, "methods_on_amcrax_baseline": methods, "published_normalised": rows,
            "independent_range_USD": [min(indep), max(indep)], "not_compared": not_compared,
            "note": "Normalisation uses capacity exponents 0.6-0.8 (assumption range). No CEPCI escalation. These are "
                    "literature comparisons (evidence kind 3), not validation."}


# ------------------------------------------------------------------------------------------ supersession
def _walk(o, path=""):
    if isinstance(o, dict):
        for k, v in o.items():
            yield from _walk(v, f"{path}.{k}" if path else str(k))
    elif isinstance(o, list):
        for i, v in enumerate(o):
            idk = v.get("id") or v.get("config") or v.get("parameter") if isinstance(v, dict) else None
            yield from _walk(v, f"{path}[{idk if idk is not None else i}]")
    elif isinstance(o, (int, float)) and not isinstance(o, bool):
        yield path, float(o)


SUPERSEDE = [  # (file relative to results/research, key regex on the flattened path, quantity, unit, reason)
    ("singapore/scenario_results.json", r"^results\.[^.]+\.(lcoh_USD_per_kg|rec_USD_per_kg|capex_total_USD|npv_USD)$", "Singapore scenario LCOH/REC/CAPEX/NPV", "USD/kg H2 or USD",
     "CAPEX method Farokhi feed-scaled -> cho2026_itemised_v1; FX 1.290 -> 1.288444"),
    ("singapore/tornado.json", r"^lcoh_base_USD_per_kg$", "tornado base LCOH", "USD/kg H2", "reference CAPEX method"),
    ("singapore/monte_carlo.json", r"^results\.[^.]+\.lcoh_p(5|50|95)$", "Monte Carlo LCOH percentile", "USD/kg H2", "reference CAPEX method"),
    ("singapore/breakeven_ammonia_price.json", r"breakeven_nh3_USD_per_t$", "break-even NH3 price", "USD/t", "reference CAPEX method"),
    ("enduse/enduse_results.json", r"^hydrogen_pathways\[[^\]]+\]\.cost_USD_per_kg_at_grey_450$", "H1 hydrogen pathway cost", "USD/kg H2",
     "legacy correlation (3.92 basis) -> reference scenario; purification rows follow H4"),
    ("enduse/enduse_results.json", r"^power_pathways\[[^\]]+\]\.(cost_USD_per_MWh_at_450|TCI_MUSD)$", "H1 power pathway LCOE / TCI", "USD/MWh or MUSD",
     "cracker CAPEX Ahmad correlation -> cho2026_itemised_v1 (sized on NH3 through the cracker)"),
    ("purification/purification_study.json", r"^cases\.20bar_baseline\.configs\[[^\]]+\]\.costs\..+\.usd_per_kg_usable_h2$", "H4 cost per kg usable H2 (20 bar)", "USD/kg H2",
     "legacy CAPEX split and 0.084 USD/kWh -> reference scenario (CAPEX items, 0.140 USD/kWh, USD/EUR 1.099, pump electricity included)"),
    ("catalyst_comparison/catalyst_comparison.json", r"(lcoh|rec)_USD_per_kg$", "H3 catalyst LCOH/REC", "USD/kg H2", "reference CAPEX method and FX"),
]


def supersession() -> None:
    rows = [
        {"quantity": "baseline LCOH, legacy correlation (version 1 basis, core stored results)", "file": "results/simulations/economics_baseline.json",
         "key": "lcoh_USD_per_kg", "old_value": json.loads((ROOT / "results/simulations/economics_baseline.json").read_text(encoding="utf-8"))["lcoh_USD_per_kg"],
         "new_value": json.loads((OUT / "baseline.json").read_text(encoding="utf-8"))["lcoh_USD_per_kg"], "unit": "USD/kg H2",
         "reason": "legacy correlation superseded for research outputs by the reference scenario; the stored core file itself is NOT changed",
         "new_file": "results/research/reference_scenario/baseline.json"},
    ]
    old_sg = json.loads((OLD / "singapore/scenario_results.json").read_text(encoding="utf-8"))
    rows.append({"quantity": "baseline LCOH, Phase 1 equipment-level CAPEX (grey, HI on)", "file": "results/research/singapore/scenario_results.json",
                 "key": "results.grey|heat_integration_on.lcoh_USD_per_kg",
                 "old_value": old_sg["results"]["grey|heat_integration_on"]["lcoh_USD_per_kg"],
                 "new_value": json.loads((OUT / "baseline.json").read_text(encoding="utf-8"))["lcoh_USD_per_kg"], "unit": "USD/kg H2",
                 "reason": "Farokhi feed-scaled CAPEX (2.78 MUSD) -> cho2026_itemised_v1 (reference scenario)",
                 "new_file": "results/research/reference_scenario/baseline.json"})
    rows.append({"quantity": "electricity price used by H4 and the legacy model", "file": "results/research/purification/assumptions.json",
                 "key": "Electricity price", "old_value": 0.084,
                 "new_value": REF.electricity_USD_per_kWh, "unit": "USD/kWh", "reason": "one electricity price (reference scenario)"})
    rows.append({"quantity": "FX", "file": "backend/amcrax/data/singapore.yaml", "key": "fx_SGD_per_USD.value", "old_value": 1.290,
                 "new_value": FX, "unit": "SGD per USD", "reason": "ECB reference rates 20 Nov 2026 read at source (cross rate)"})
    rows.append({"quantity": "USD per EUR (membrane price conversion)", "file": "scripts/research/purification_study.py", "key": "EURUSD_PARITY",
                 "old_value": 1.0, "new_value": REF.usd_per_eur, "unit": "USD per EUR", "reason": "parity assumption replaced by the ECB rate"})
    missing = []
    for rel, rx, qty, unit, why in SUPERSEDE:
        po, pn = OLD / rel, ROOT / "results" / "research" / rel
        if not po.exists() or not pn.exists():
            missing.append(rel)
            continue
        old = dict(_walk(json.loads(po.read_text(encoding="utf-8"))))
        new = dict(_walk(json.loads(pn.read_text(encoding="utf-8"))))
        for k, nv in new.items():
            if re.search(rx, k) and k in old:
                ov = old[k]
                if not (math.isfinite(ov) and math.isfinite(nv)):
                    continue
                if abs(nv - ov) > 1e-9 * max(1.0, abs(ov)):
                    rows.append({"quantity": qty, "file": f"results/research/{rel}", "key": k, "old_value": ov, "new_value": nv,
                                 "unit": unit, "reason": why})
    dump("supersession.json", {"provenance": prov("Phase 1 release copies (results/research_releases/2026-11-23) against the "
                                                 "regenerated results/research files"),
                               "description": "Every headline number that changed when the research outputs moved to the unified "
                                              "reference scenario. old = Phase 1 release value, new = current value.",
                               "n_rows": len(rows), "files_not_compared": missing, "rows": rows})
    print("supersession rows", len(rows), "missing", missing)


if __name__ == "__main__":
    if "--supersession" in sys.argv:
        supersession()
    else:
        baseline()
