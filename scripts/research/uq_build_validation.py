"""Task U1: collect the UQ acceptance checks into results/research/validation/uq.json and write the row-evidence
notes for rows H2-a and H2-b (results/research/uq/row_evidence.json). Run after uq_gsa_sobol.py,
uq_kinetic_propagation.py and uq_takahashi_calibration.py. Deterministic.
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))
from amcrax.economics.reference import load_reference_scenario, provenance_stamp  # noqa: E402
from amcrax.economics.singapore import breakeven_nh3_price, evaluate, extract_summary, load_singapore_data  # noqa: E402
from amcrax.uq import LABEL  # noqa: E402

UQ = ROOT / "results" / "research" / "uq"
VAL = ROOT / "results" / "research" / "validation"
SCRIPT = "scripts/research/uq_build_validation.py"
REF = load_reference_scenario()
SD = load_singapore_data()


def jl(p):
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else None


def feed_share_threshold(S, ov):
    """NH3 price (USD/t) at which the feed-NH3 cost equals all other LCOH items (feed share 50 %)."""
    e0, e1 = evaluate(S, 0.0, ov), evaluate(S, 1000.0, ov)
    f0, f1 = e0["breakdown_USD_per_kg"]["ammonia_feed"], e1["breakdown_USD_per_kg"]["ammonia_feed"]
    r0, r1 = e0["lcoh_USD_per_kg"] - f0, e1["lcoh_USD_per_kg"] - f1
    # f(p) = f0 + a p ; r(p) = r0 + b p ; f = r  ->  p = (r0 - f0) / (a - b)
    a, b = (f1 - f0) / 1000.0, (r1 - r0) / 1000.0
    return (r0 - f0) / (a - b) if a > b else None


def main():
    items = []
    t1 = jl(UQ / "checks_t1.json") or []
    t2a = (jl(UQ / "kinetic_param_propagation.json") or {}).get("acceptance_checks", [])
    t2b = jl(UQ / "checks_t2b.json") or []
    for group, lst, default_kind in (("T1", t1, "numerical_verification"), ("T2a", t2a, "numerical_verification"),
                                     ("T2b", t2b, "numerical_verification")):
        for c in lst:
            it = {"study": group, **c}
            it.setdefault("evidence_kind", default_kind)
            items.append(it)
    counts = {s: sum(1 for i in items if i["status"] == s) for s in ("pass", "fail", "informational")}
    VAL.mkdir(parents=True, exist_ok=True)
    (VAL / "uq.json").write_text(json.dumps({
        "provenance": {"generated_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"), "script": SCRIPT, "source_type": "python",
                       "reference_scenario": provenance_stamp()},
        "label": LABEL, "note": "All items are numerical verification of the UQ code, except the T2b posterior-predictive coverage "
                                "(literature_comparison against digitised published figures, informational). None is experimental validation; "
                                "AmCraX has no experimental validation.",
        "counts": counts, "items": items}, indent=1, default=float), encoding="utf-8")

    # ---------------------------------------------------------------- row evidence H2-a, H2-b
    gsa = jl(UQ / "gsa_sobol.json")
    dec = jl(UQ / "gsa_cost_decomposition.json")
    S = extract_summary(json.loads((ROOT / "results/simulations/baseline.json").read_text(encoding="utf-8")))
    S_off = extract_summary(json.loads((ROOT / "results/simulations/baseline_no_hi.json").read_text(encoding="utf-8")))
    thr = {"base": feed_share_threshold(S, {}),
           "adverse_capex1.5_psa0.756_cat_life1_price2x_hours7000": feed_share_threshold(
               S, {"capex_multiplier": 1.5, "psa_recovery": 0.756, "catalyst_lifetime_yr": 1.0,
                   "catalyst_price_USD_per_kg": 66.8, "operating_hours_h_per_yr": 7000.0, "discount_rate": 0.10,
                   "electricity_price_USD_per_kWh": REF.sens("electricity_USD_per_kWh")[1]}),
           "heat_integration_off_base": feed_share_threshold(S_off, {})}
    sourced = {k: {"low": v["low"], "base": v["value"], "high": v["high"]} for k, v in SD["nh3_price_scenarios_USD_per_t"].items()}
    lowest_sourced = min(v["low"] for v in sourced.values())
    st = {k.split("|")[0]: {"S1": v["outputs"]["lcoh_USD_per_kg"]["indices"]["nh3_price_USD_per_t"]["S1"],
                            "S1_ci": v["outputs"]["lcoh_USD_per_kg"]["indices"]["nh3_price_USD_per_t"]["S1_ci"],
                            "ST": v["outputs"]["lcoh_USD_per_kg"]["indices"]["nh3_price_USD_per_t"]["ST"],
                            "ST_ci": v["outputs"]["lcoh_USD_per_kg"]["indices"]["nh3_price_USD_per_t"]["ST_ci"],
                            "ST_capital_group": v["outputs"]["lcoh_USD_per_kg"]["groups"]["group:capital"]["ST"],
                            "ST_operation_group": v["outputs"]["lcoh_USD_per_kg"]["groups"]["group:operation"]["ST"],
                            "ST_catalyst_group": v["outputs"]["lcoh_USD_per_kg"]["groups"]["group:catalyst"]["ST"],
                            "lcoh_mean": v["outputs"]["lcoh_USD_per_kg"]["mean"], "lcoh_p5": v["outputs"]["lcoh_USD_per_kg"]["p5"],
                            "lcoh_p95": v["outputs"]["lcoh_USD_per_kg"]["p95"]}
          for k, v in gsa["cases"].items() if k.endswith("|heat_integration_on")}
    rec_st = gsa["cases"]["grey|heat_integration_on"]["outputs"]["rec_USD_per_kg"]
    share = {k.split("|")[0]: v["breakdown_share"]["ammonia_feed"] for k, v in dec["cases"].items() if k.endswith("|heat_integration_on")}
    share_fuel = {k.split("|")[0]: v["breakdown_share"]["ammonia_feed"] + v["breakdown_share"]["heat_fuel"]
                  for k, v in dec["cases"].items() if k.endswith("|heat_integration_on")}
    h2p = REF.h2_selling_price_USD_per_kg
    be = breakeven_nh3_price(S, h2p)
    be_best = breakeven_nh3_price(S, h2p, {"capex_multiplier": 0.5, "psa_recovery": 0.95, "catalyst_lifetime_yr": 4.0,
                                           "operating_hours_h_per_yr": 8000.0, "discount_rate": 0.085,
                                           "electricity_price_USD_per_kWh": REF.sens("electricity_USD_per_kWh")[0]})
    rows = {
        "H2-a": {
            "proposed_verdict": "SUPPORTED",
            "numbers": {"feed_NH3_share_of_LCOH_base_HIon": share, "feed_plus_heat_fuel_share_base_HIon": share_fuel,
                        "sobol_nh3_price_lcoh_HIon": st,
                        "rec_grey_HIon_top_inputs_ST": {k: rec_st["indices"][k]["ST"] for k in ("capex_multiplier", "psa_recovery", "nh3_price_USD_per_t")},
                        "nh3_price_threshold_feed_share_50pct_USD_per_t": thr,
                        "lowest_sourced_nh3_price_USD_per_t": lowest_sourced},
            "assumptions": ["NH3 price ranges are scenario inputs (data/singapore.yaml; Cho 2026 Table 8 and secondary web), not Singapore transaction prices",
                            "the feed share is accounting at fixed stoichiometry of the stored Aspen baseline; the Sobol indices depend on the stated input ranges",
                            "CAPEX cho2026_itemised_v1 with multiplier 0.5-1.5; no Singapore location factor"],
            "uncertainty": "Sobol ST of the NH3 price: grey 0.896 [0.875, 0.917], blue 0.726, green_current 0.636, green_2030 0.944 (95 % bootstrap CI in gsa_sobol.json); "
                           "S1 CIs are wide (Saltelli 2010 estimator variance), ST CIs narrow; top-3 ranking unchanged under a right-skewed lognormal CAPEX",
            "envelope": "NH3 price above the 50 %-feed-share threshold (see numbers) at capacity scale 1, both heat-integration cases, reference CAPEX with multiplier up to 1.5 and PSA recovery down to 0.756",
            "threshold": {"quantity": "NH3 delivered price at which feed cost equals all other LCOH items",
                          "values_USD_per_t": thr, "sourced_range_USD_per_t": [lowest_sourced, max(v["high"] for v in sourced.values())],
                          "side": "all sourced prices above the threshold" if all(t is not None and t < lowest_sourced for t in thr.values()) else "straddles or above"},
            "reason": "Feed dominance does not rest only on the assumed price: the threshold price for a 50 % feed share lies below every sourced NH3 price "
                      "even with adverse CAPEX/PSA/operation values. The variance attribution (ST) is range-dependent and is reported as supporting, not as the basis. "
                      "Note against over-reading: the reconversion cost (REC) is driven by CAPEX and PSA recovery, not by the NH3 price.",
        },
        "H2-b": {
            "proposed_verdict": "INCONCLUSIVE",
            "numbers": {"h2_benchmark_USD_per_kg": h2p, "breakeven_nh3_price_base_USD_per_t": be,
                        "breakeven_nh3_price_favourable_nonfeed_inputs_USD_per_t": be_best,
                        "lowest_sourced_nh3_price_USD_per_t": lowest_sourced,
                        "lcoh_p5_p95_by_scenario_HIon": {k: [v["lcoh_p5"], v["lcoh_p95"]] for k, v in st.items()},
                        "npv_mean_grey_HIon_USD": gsa["cases"]["grey|heat_integration_on"]["outputs"]["npv_USD"]["mean"],
                        "npv_p95_grey_HIon_USD": gsa["cases"]["grey|heat_integration_on"]["outputs"]["npv_USD"]["p95"]},
            "assumptions": ["single H2 benchmark of the reference scenario (3.06 USD/kg, NE Asia SMR, secondary web); other benchmarks in breakeven_ammonia_price.json are not re-evaluated here"],
            "uncertainty": "LCOH 90 % ranges from the Sobol base sample per scenario (see numbers); NPV at 3.06 USD/kg negative over the 5-95 % range for grey",
            "envelope": "reference scenario, capacity scale 1, benchmark 3.06 USD/kg",
            "threshold": {"quantity": "NH3 price for LCOH = 3.06 USD/kg", "base_USD_per_t": be, "with_favourable_non_feed_inputs_USD_per_t": be_best,
                          "sourced_min_USD_per_t": lowest_sourced},
            "reason": (f"Break-even NH3 price for the {h2p:g} USD/kg benchmark: {be:.0f} USD/t at base and {be_best:.0f} USD/t with every non-feed "
                       f"input at its favourable bound. Sourced scenario prices span {lowest_sourced:g}-{max(v['high'] for v in sourced.values()):g} USD/t: "
                       "only the lower part of the grey range (and the low bound of the green_2050 projection) lies below the threshold; every current "
                       "green and blue price lies above. Competitiveness therefore requires ammonia at or below about the bottom of the grey range, "
                       "and the sourced values straddle the threshold, so by rule the row stays INCONCLUSIVE from the UQ side and the threshold is the finding. "
                       "The result depends on the single benchmark used (other benchmarks are another workstream's)."),
        },
    }
    (UQ / "row_evidence.json").write_text(json.dumps({"provenance": {"generated_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                                                                     "script": SCRIPT, "reference_scenario": provenance_stamp()},
                                                      "note": "Proposed row evidence only; the orchestrator decides the verdicts.",
                                                      "row_evidence": rows}, indent=1, default=float), encoding="utf-8")
    print(json.dumps(counts), json.dumps({"thr": thr, "be": be, "be_best": be_best, "share": share}, default=float))
    print([i["id"] for i in items if i["status"] == "fail"])


if __name__ == "__main__":
    main()
