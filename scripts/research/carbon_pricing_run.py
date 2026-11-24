"""Phase 2 task C3: H2 feedstock dominance and carbon pricing (actual Singapore boundary and hypothetical life-cycle price).

Writes results/research/carbon_pricing/*.json|csv, results/research/validation/carbon_pricing.json and
results/figures/research/carbon_*.png. Deterministic (fixed seeds), no network, no Aspen run (stored Aspen baseline only).
Economic basis: backend/amcrax/data/reference_scenario.yaml through amcrax.economics.singapore.evaluate (default output
unchanged). Mode B outputs are HYPOTHETICAL and never Singapore law.
"""
from __future__ import annotations

import csv
import json
import sys
from datetime import datetime, timezone
from itertools import product
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))

import matplotlib  # noqa: E402
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

from amcrax.economics import carbon_pricing as cp  # noqa: E402
from amcrax.economics import singapore  # noqa: E402
from amcrax.economics.reference import load_reference_scenario, provenance_stamp  # noqa: E402
from amcrax.environmental import lca  # noqa: E402

OUT = ROOT / "results" / "research" / "carbon_pricing"
VAL = ROOT / "results" / "research" / "validation"
FIG = ROOT / "results" / "figures" / "research"
for p in (OUT, VAL, FIG):
    p.mkdir(parents=True, exist_ok=True)

REF = load_reference_scenario()
FX = REF.fx_SGD_per_USD
BASE = json.loads((ROOT / "results" / "simulations" / "baseline.json").read_text(encoding="utf-8"))
SD = singapore.load_singapore_data()["nh3_price_scenarios_USD_per_t"]
ROUTES = ("grey", "blue", "green_current", "green_2030", "green_2050")
COLORS = {"grey": "#2a78d6", "blue": "#eb6834", "green_current": "#1baf7a", "green_2030": "#eda100", "green_2050": "#e87ba4"}
INK, INK2 = "#0b0b0b", "#52514e"
EU_ETS = cp.eu_ets_SGD_per_t()
SG_RATE = cp.legislated_rate_SGD(2026)
AIM = cp.POLICY["aim_2030_SGD_per_tCO2e"]
PRICE_LEVELS = [0.0, SG_RATE, AIM[0], AIM[1], EU_ETS, 200.0, 300.0, 500.0]
SMR_CI = lca.f("smr_h2_unabated")          # [10, 12] kg CO2e/kg H2, IEA GHR 2024
SMR_CI_C = 0.5 * (SMR_CI[0] + SMR_CI[1])
NOW = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def prov(summary: str) -> dict:
    return {"generated_utc": NOW, "script": "scripts/research/carbon_pricing_run.py", "source_type": "python",
            "inputs_summary": summary, "reference_scenario": provenance_stamp(),
            "model_versions": {"carbon_pricing": "amcrax.economics.carbon_pricing/1", "economics": "amcrax.economics.singapore (reference scenario, default output unchanged)",
                               "carbon_intensity": "carbon.ts-equivalent simplified accounting, gate factors amcrax.environmental.lca.route_spec"},
            "hypothetical_warning": "Every quantity under mode 'hypothetical_lca' is a HYPOTHETICAL life-cycle carbon price, not Singapore law."}


def wj(path: Path, obj) -> None:
    path.write_text(json.dumps(obj, indent=2, default=float), encoding="utf-8")


def foot(fig, text="AmCraX Phase 2 C3 | stored Aspen Plus V15 baseline costed on the reference scenario (reference_scenario.yaml) | Python"):
    fig.text(0.01, 0.005, text, fontsize=6, color=INK2)


E = singapore.evaluate(BASE)                                   # frozen default
CI_IN = cp.ci_inputs_from_result(BASE)

# ===================================================================== 1. feed dominance (H2-E)
bd = E["breakdown_USD_per_kg"]
L = E["lcoh_USD_per_kg"]
shares = {k: v / L for k, v in bd.items()}
e0, e1 = singapore.evaluate(BASE, 0.0), singapore.evaluate(BASE, 1000.0)
slope = (e1["lcoh_USD_per_kg"] - e0["lcoh_USD_per_kg"]) / 1000.0     # USD/kg H2 per USD/t NH3 (feed + fuel)
feed_per = e1["breakdown_USD_per_kg"]["ammonia_feed"] / 1000.0
l0 = e0["lcoh_USD_per_kg"]
p_share50 = 0.5 * l0 / (feed_per - 0.5 * slope)
cap_fixed = bd["capex"] + bd["fixed_opex"]
p_feed_eq_capfixed = cap_fixed / feed_per
p_feed_eq_capex = bd["capex"] / feed_per


def at_price_and_mult(price, m):
    return singapore.evaluate(BASE, price, {"capex_multiplier": m})["breakdown_USD_per_kg"]


def capex_multiple(price):
    """CAPEX multiplier at which (a) capital charge, (b) capital + fixed opex reach the feed cost; (c) feed share 50 %."""
    b1, b2 = at_price_and_mult(price, 1.0), at_price_and_mult(price, 2.0)
    feed = b1["ammonia_feed"]
    c1, c2 = b1["capex"], b2["capex"]
    cf1, cf2 = b1["capex"] + b1["fixed_opex"], b2["capex"] + b2["fixed_opex"]
    tot1, tot2 = sum(b1.values()), sum(b2.values())
    ma = feed / c1                                     # capex charge is proportional to m
    mb = 1.0 + (feed - cf1) / (cf2 - cf1)
    mc = 1.0 + (2 * feed - tot1) / (tot2 - tot1)       # feed = 0.5 total
    return {"nh3_price_USD_per_t": price, "capex_charge_equals_feed": ma, "capital_plus_fixed_opex_equals_feed": mb,
            "feed_share_falls_to_50pct": mc}


mults = [capex_multiple(p) for p in (300.0, 450.0, 610.0)]
# capacity scale at which capital + fixed opex reach the feed cost (smaller plants)
def capfix_minus_feed(sc):
    b = singapore.evaluate(BASE, "grey", {"capacity_scale": sc})["breakdown_USD_per_kg"]
    return b["capex"] + b["fixed_opex"] - b["ammonia_feed"]
lo_s, hi_s = 1e-4, 1.0
for _ in range(80):
    mid = (lo_s * hi_s) ** 0.5
    if capfix_minus_feed(mid) > 0:
        lo_s = mid
    else:
        hi_s = mid
scale_star = (lo_s * hi_s) ** 0.5
audit = json.loads((ROOT / "results" / "research" / "reference_scenario" / "capex_audit.json").read_text(encoding="utf-8"))
ind_range = audit["independent_range_USD"]
ref_capex = E["capex_total_USD"] if "capex_total_USD" in E else E["capex"]["total_capex_USD"]
tor = json.loads((ROOT / "results" / "research" / "singapore" / "tornado.json").read_text(encoding="utf-8"))
bars = sorted(tor["bars"], key=lambda b: -b["swing"])
be_json = json.loads((ROOT / "results" / "research" / "singapore" / "breakeven_ammonia_price.json").read_text(encoding="utf-8"))
be_hi = be_json["results"]["heat_integration_on"]

# break-even vs CAPEX multiplier (sourced Cho Table 8 range and the independent published range)
def be_at(m, target):
    return singapore.breakeven_nh3_price(BASE, target, {"capex_multiplier": m})
m_ind = [ind_range[0] / ref_capex, ind_range[1] / ref_capex]
be_env = {f"capex_multiplier_{m:.3f}": be_at(m, REF.h2_selling_price_USD_per_kg) for m in (0.5, m_ind[0], m_ind[1], 1.0, 1.5)}

# Monte Carlo (same distributions as results/research/singapore/monte_carlo.json; own seed stream)
SEED, N = 20261123, 5000
rng = np.random.default_rng(SEED)
ELO, EHI = REF.sens("electricity_USD_per_kWh") if hasattr(REF, "sens") else (0.084, 0.221898)
DLO, DHI = REF.sens("discount_rate")
OLO, OHI = REF.sens("operating_hours_h_per_yr")
PLO, PHI = REF.sens("plant_life_yr")
dr = {"elec": rng.uniform(ELO, EHI, N), "cat": rng.triangular(16.7, 33.4, 66.8, N), "life": rng.uniform(1, 4, N),
      "capx": rng.triangular(0.5, 1.0, 1.5, N), "dr": rng.uniform(DLO, DHI, N), "oh": rng.uniform(OLO, OHI, N), "pl": rng.uniform(PLO, PHI, N)}
g = SD["grey"]
nh3 = rng.triangular(g["low"], g["value"], g["high"], N)
fs, largest, lc, capf = [], [], [], []
for i in range(N):
    e = singapore.evaluate(BASE, float(nh3[i]), {"electricity_price_USD_per_kWh": dr["elec"][i], "catalyst_price_USD_per_kg": dr["cat"][i],
                                                 "catalyst_lifetime_yr": dr["life"][i], "capex_multiplier": dr["capx"][i], "discount_rate": dr["dr"][i],
                                                 "operating_hours_h_per_yr": dr["oh"][i], "plant_life_yr": dr["pl"][i]})
    b = e["breakdown_USD_per_kg"]
    fs.append(b["ammonia_feed"] / e["lcoh_USD_per_kg"])
    largest.append(max(b, key=b.get) == "ammonia_feed")
    capf.append(b["ammonia_feed"] > b["capex"] + b["fixed_opex"])
    lc.append(e["lcoh_USD_per_kg"])
fs, lc = np.array(fs), np.array(lc)
mc_feed = {"n": N, "seed": SEED, "nh3_price": f"triangular({g['low']}, {g['value']}, {g['high']}) USD/t (grey, Cho Table 8)",
           "other_distributions": "as results/research/singapore/monte_carlo.json (electricity, catalyst price and life, CAPEX multiplier 0.5-1.5, discount rate, hours, life)",
           "feed_share_p5_p50_p95": [float(np.percentile(fs, q)) for q in (5, 50, 95)], "feed_share_min": float(fs.min()),
           "P_feed_share_above_0p5": float((fs > 0.5).mean()), "P_feed_largest_item": float(np.mean(largest)),
           "P_feed_above_capital_plus_fixed_opex": float(np.mean(capf)),
           "lcoh_p5_p50_p95": [float(np.percentile(lc, q)) for q in (5, 50, 95)],
           "P_lcoh_below_ne_asia_smr_3p06": float((lc < REF.h2_selling_price_USD_per_kg).mean())}

scen_prices = {r: {"value": SD[r]["value"], "low": SD[r]["low"], "high": SD[r]["high"]} for r in ROUTES}
feed = {
    "provenance": prov("stored Aspen baseline (results/simulations/baseline.json) costed by amcrax.economics.singapore.evaluate on the reference scenario; tornado and break-even read from results/research/singapore; CAPEX range from results/research/reference_scenario/capex_audit.json"),
    "basis": "grey 450 USD/t, heat integration on, reference CAPEX cho2026_itemised_v1, plant gate",
    "lcoh_USD_per_kg": L, "lcoh_SGD_per_kg": E["lcoh_SGD_per_kg"], "breakdown_USD_per_kg": bd, "share_of_lcoh": shares,
    "feed_share": shares["ammonia_feed"], "feed_plus_fuel_share": shares["ammonia_feed"] + shares["heat_fuel"],
    "capital_plus_fixed_opex_share": (bd["capex"] + bd["fixed_opex"]) / L,
    "feed_share_at_scenarios": {r: singapore.evaluate(BASE, r)["breakdown_USD_per_kg"]["ammonia_feed"] / singapore.evaluate(BASE, r)["lcoh_USD_per_kg"] for r in ROUTES},
    "feed_share_at_cho_range": {str(p): singapore.evaluate(BASE, p)["breakdown_USD_per_kg"]["ammonia_feed"] / singapore.evaluate(BASE, p)["lcoh_USD_per_kg"] for p in (300.0, 610.0)},
    "lcoh_slope_USD_per_kg_per_USD_per_t": slope, "lcoh_at_zero_nh3_price_USD_per_kg": l0,
    "thresholds": {
        "nh3_price_feed_share_50pct_USD_per_t": p_share50,
        "nh3_price_feed_equals_capital_plus_fixed_opex_USD_per_t": p_feed_eq_capfixed,
        "nh3_price_feed_equals_capex_charge_USD_per_t": p_feed_eq_capex,
        "capex_multiple": mults,
        "capacity_scale_capital_plus_fixed_opex_equals_feed": scale_star,
        "capacity_scale_note": "multiplier on the stored 99.8 kmol/h NH3 feed; CAPEX items scaled with exponent 0.8, labour not scaled",
    },
    "sourced_comparison": {
        "nh3_price_scenarios_USD_per_t": scen_prices,
        "lowest_sourced_nh3_price_USD_per_t": min(v["low"] for v in scen_prices.values()),
        "reference_capex_USD": ref_capex, "independent_published_capex_range_USD": ind_range,
        "independent_range_as_capex_multiplier": m_ind, "cho_table8_capex_multiplier_range": [0.5, 1.5],
    },
    "tornado_ranked": [{"parameter": b["parameter"], "swing_USD_per_kg": b["swing"]} for b in bars],
    "tornado_source": "results/research/singapore/tornado.json",
    "monte_carlo": mc_feed,
    "breakeven_nh3_USD_per_t": {k: v["breakeven_nh3_USD_per_t"] for k, v in be_hi.items()},
    "breakeven_benchmarks_USD_per_kg": {k: v["h2_price_USD_per_kg"] for k, v in be_hi.items()},
    "breakeven_vs_ne_asia_smr_by_capex_multiplier": be_env,
    "breakeven_source": "results/research/singapore/breakeven_ammonia_price.json (recomputed here for CAPEX multipliers)",
}
wj(OUT / "feed_dominance.json", feed)

# ===================================================================== 2. carbon intensity by route (H2-C), apart from cost
ci_rows = {}
for r in ("grey", "blue", "blue_v2", "green", "green_lee"):
    spec = lca.route_spec(r)
    vals = {lvl: cp.carbon_intensity_h2(CI_IN, getattr(spec, k))["total_kgCO2e_per_kgH2"] for lvl, k in (("central", "ef"), ("low", "low"), ("high", "high"))}
    dist = {f"{d:.0f}_km": cp.carbon_intensity_h2(CI_IN, spec.ef, distance_km=d)["total_kgCO2e_per_kgH2"] for d in (2000.0, 12000.0)}
    ci_rows[r] = {"label": spec.label, "gate_ef_kgCO2e_per_kgNH3": {"central": spec.ef, "low": spec.low, "high": spec.high},
                  "ci_kgCO2e_per_kgH2": vals, "ci_at_distance_kgCO2e_per_kgH2": dist,
                  "breakdown_central": cp.carbon_intensity_h2(CI_IN, spec.ef)["breakdown_kgCO2e_per_kgH2"]}
lca_res = json.loads((ROOT / "results" / "research" / "lca" / "lca_results.json").read_text(encoding="utf-8"))
lca_by = {x["route"]: x for x in lca_res["routes"]}
ci_json = {
    "provenance": prov("carbon.ts-equivalent carbon intensity on the stored Aspen activity; gate factors and ranges from amcrax.environmental.lca.route_spec; comparators from results/research/lca/lca_results.json"),
    "statement": "Simplified carbon-intensity accounting (cradle to cracker/PSA outlet, GWP100 as reported by each source); not a full LCA. Kept apart from cost.",
    "activity": {"kg_nh3_total_per_kg_h2": (CI_IN["nh3_feed_kg_h"] + cp.carbon_intensity_h2(CI_IN, 0.0)["nh3_fuel_kg_h"]) / CI_IN["h2_kg_h"],
                 "distance_km": cp.ci_factors().distance_km, "grid_kgCO2_per_kWh": cp.ci_factors().grid_kg_per_kWh},
    "routes": ci_rows,
    "comparators_kgCO2e_per_kgH2": {"smr_unabated": SMR_CI, "smr_ccs": lca.f("smr_h2_ccs"), "smr_ccs_high": lca.f("smr_h2_ccs_high"),
                                    "eu_rfnbo_threshold": next((x["value_kgCO2e_per_kgH2"] for x in [] ), None)},
    "power_ci_from_lca_results_kgCO2e_per_MWh": {r: lca_by[r]["direct_NH3_CCGT_kgCO2e_per_MWh"] for r in ("grey", "blue", "blue_v2", "green", "green_lee")},
    "power_comparators_kgCO2e_per_MWh": {"ng_ccgt": lca_res["alternatives"]["ccgt_ng_kgCO2e_per_MWh"], "grid_average": lca_res["alternatives"]["grid_average_kgCO2e_per_MWh"]},
}
from amcrax.environmental import reference_lines  # noqa: E402
ci_json["comparators_kgCO2e_per_kgH2"]["eu_rfnbo_threshold"] = reference_lines()[0].value_kgCO2e_per_kgH2
# break-even gate EF for cracked H2 vs SMR (linear CI in EF)
X = ci_json["activity"]["kg_nh3_total_per_kg_h2"]
ci0 = cp.carbon_intensity_h2(CI_IN, 0.0)["total_kgCO2e_per_kgH2"]
ci_json["breakeven_gate_ef_kgCO2e_per_kgNH3"] = {
    "vs_smr_unabated": {f"{v:g}": (v - ci0) / X for v in (SMR_CI[0], SMR_CI_C, SMR_CI[1])},
    "vs_smr_ccs": {f"{v:g}": (v - ci0) / X for v in (*lca.f("smr_h2_ccs"), lca.f("smr_h2_ccs_high"))},
}
# direct NH3 power: CI = a + b*EF (from lca activity); break-even vs NG CCGT across the sourced/assumed efficiency range and leakage
act = lca_res["activity_per_FU"]["direct_NH3_CCGT"]["nh3_kg"]
a_pw = lca_by["green_lee"]["direct_NH3_CCGT_kgCO2e_per_MWh"]
b_pw = (lca_by["grey"]["direct_NH3_CCGT_kgCO2e_per_MWh"] - a_pw) / lca_by["grey"]["gate_kgCO2e_per_kgNH3"]
pw_be = {}
for eff, leak in product((0.50, 0.55, 0.60), (0.0, 0.015, 0.03)):
    ccgt = lca.ccgt_ci_kg_per_MWh(eff, leak)
    pw_be[f"eff_{eff:.2f}_leak_{leak:.3f}"] = {"ccgt_kgCO2e_per_MWh": ccgt, "breakeven_gate_ef": (ccgt - a_pw) / b_pw}
grid = lca_res["alternatives"]["grid_average_kgCO2e_per_MWh"]["central"]
ci_json["power_breakeven_gate_ef_kgCO2e_per_kgNH3"] = {"vs_ng_ccgt": pw_be, "vs_grid_average": (grid - a_pw) / b_pw,
                                                       "method": "direct NH3 CCGT CI is linear in the gate factor: a + b*EF with a, b from results/research/lca/lca_results.json (green_lee and grey rows); CCGT CI from amcrax.environmental.lca.ccgt_ci_kg_per_MWh",
                                                       "nh3_kg_per_MWh": act}
wj(OUT / "carbon_intensity.json", ci_json)

# ===================================================================== 3. scenarios under both modes
def ci_of(route, level="central"):
    return cp.carbon_intensity_h2(CI_IN, cp.route_gate_ef(route)[level])["total_kgCO2e_per_kgH2"]


cases = []
for r in ROUTES:
    cases.append(cp.route_case(BASE, r, "actual_sg"))
    for P in PRICE_LEVELS:
        cases.append(cp.route_case(BASE, r, "hypothetical_lca", P, benchmark_ci_kgCO2e_per_kgH2=SMR_CI_C))


def rank(mode, P):
    sel = [c for c in cases if c["mode"] == mode and (mode == "actual_sg" or abs(c["carbon_price_SGD_per_tCO2e"] - P) < 1e-9)]
    return [c["route"] for c in sorted(sel, key=lambda c: c["lcoh_USD_per_kg"])]


rankings = {"actual_sg": rank("actual_sg", 0)}
rankings.update({f"hypothetical_lca_{P:.2f}": rank("hypothetical_lca", P) for P in PRICE_LEVELS})
ab = cp.actual_boundary(BASE, "grey")
tt = cp.n2o_threshold_test(BASE, E)
hours = E["assumptions"]["economic"]["operating_hours_h_per_yr"]
ng = cp.actual_boundary(BASE, "grey", overrides={"heat_fuel": "natural_gas"})
ng_scale = cp.POLICY["threshold_tCO2e_per_yr"] / ng["direct_tCO2e_per_yr"]
mode_a = {
    "label": cp.ACTUAL_LABEL, "rate_SGD_per_tCO2e_2026_and_later": SG_RATE, "rate_source": cp.POLICY["rate_source"],
    "threshold_tCO2e_per_yr": cp.POLICY["threshold_tCO2e_per_yr"], "threshold_source": cp.POLICY["threshold_source"],
    "n2o_gwp_cpa": cp.POLICY["gwp"]["N2O"],
    "reference_plant_self_firing": {k: v for k, v in ab.items() if k != "econ"},
    "co2_from_ammonia_self_firing_t_per_yr": 0.0,
    "n2o_treatment": "N2O is a covered gas (CPA First Schedule, GWP 265). No primary emission factor for the cracker burner exists in the AmCraX library, so N2O = 0 by default; the threshold test below gives the N2O rate needed to reach 25,000 tCO2e/yr.",
    "n2o_threshold_test": tt,
    "n2o_at_ahmad_0p15_ppmv_transferred": cp.n2o_at_ppmv(0.15, tt, hours),
    "n2o_at_ahmad_0p15_ppmv_note": "0.15 ppmv is a Chemkin result for an NH3 gas turbine (Ahmad 2025 p. 9), transferred to the cracker burner as an order-of-magnitude illustration only (low confidence).",
    "natural_gas_heat_variant": {"direct_tCO2e_per_yr": ng["direct_tCO2e_per_yr"], "threshold_fraction": ng["threshold_fraction"],
                                 "liable": ng["liable"], "capacity_scale_to_reach_threshold": ng_scale,
                                 "note": "Even when liable, the taxed CO2 is that of the gas burnt at the plant; it does not depend on the ammonia route."},
    "upstream_emissions_of_imported_ammonia_taxed": False,
    "consequence": "Under the actual boundary the carbon cost is identical (zero) for grey, blue and green ammonia; low ammonia carbon intensity earns no cost advantage.",
}

# ===================================================================== 4. thresholds
def thr(a, b, la, lb):
    """Hypothetical price at which route a overtakes route b, central and CI-range interval."""
    ca = {lv: ci_of(a, lv) for lv in ("central", "low", "high")}
    cb = {lv: ci_of(b, lv) for lv in ("central", "low", "high")}
    cen = cp.crossover_price(la, ca["central"], lb, cb["central"], FX)
    corners = [cp.crossover_price(la, ca[x], lb, cb[y], FX) for x in ("low", "high") for y in ("low", "high")]
    finite = [c for c in corners if c is not None]
    return {"route": a, "overtakes": b, "lcoh_gap_at_zero_USD_per_kg": la - lb,
            "ci_gap_central_kgCO2e_per_kgH2": cb["central"] - ca["central"],
            "threshold_central_SGD_per_tCO2e": cen,
            "threshold_range_from_ci_ranges_SGD_per_tCO2e": [min(finite) if finite else None, None if any(c is None for c in corners) else max(finite)],
            "upper_unbounded": any(c is None for c in corners)}


lc0 = {r: singapore.evaluate(BASE, r)["lcoh_USD_per_kg"] for r in ROUTES}
pairs = [("blue", "grey"), ("green_current", "grey"), ("green_2030", "grey"), ("green_2050", "grey"),
         ("green_current", "blue"), ("green_2030", "blue"), ("green_2050", "blue")]
thr_rows = [thr(a, b, lc0[a], lc0[b]) for a, b in pairs]
# analytic check: threshold = delta NH3 price x fx / delta delivered gate EF (CAPEX-independent)
for t in thr_rows:
    a, b = t["route"], t["overtakes"]
    dp = SD[a]["value"] - SD[b]["value"]
    de = cp.route_gate_ef(b)["central"] - cp.route_gate_ef(a)["central"]
    t["analytic_dp_fx_over_def_SGD_per_tCO2e"] = (dp * FX / de) if (dp > 0 and de > 0) else (0.0 if dp <= 0 else None)

# joint Monte Carlo: NH3 prices (triangular, independent) and gate EFs (uniform in range, independent)
rng2 = np.random.default_rng(SEED + 1)
M = 20000
pr = {r: rng2.triangular(SD[r]["low"], SD[r]["value"], SD[r]["high"], M) for r in ROUTES}
efr = {}
for key in ("grey", "blue", "green"):
    s = cp.route_gate_ef(key)
    efr[key] = rng2.uniform(s["low"], s["high"], M)
ship = cp.ci_factors().ship_ef_kg_per_tkm * cp.ci_factors().distance_km / 1000.0
elec_ci = cp.carbon_intensity_h2(CI_IN, 0.0)["breakdown_kgCO2e_per_kgH2"]["electricity"]
def ci_vec(route):
    k = "green" if route.startswith("green") else route
    return X * (efr[k] + ship) + elec_ci
mc_thr = {}
for a, b in pairs:
    gap = slope * (pr[a] - pr[b])
    dci = ci_vec(b) - ci_vec(a)
    with np.errstate(divide="ignore", invalid="ignore"):
        P = np.where(gap <= 0, 0.0, np.where(dci > 0, gap * FX * 1000.0 / dci, np.inf))
    fin = P[np.isfinite(P)]
    mc_thr[f"{a}_over_{b}"] = {"p5_p50_p95_SGD_per_tCO2e": [float(np.percentile(P, q)) for q in (5, 50, 95)],
                               "P_below_or_at_SG_45": float((P <= SG_RATE).mean()), "P_below_or_at_80": float((P <= AIM[1]).mean()),
                               "P_below_or_at_EU_ETS": float((P <= EU_ETS).mean()), "P_below_or_at_500": float((P <= 500).mean()),
                               "P_already_cheaper_at_zero": float((P == 0).mean()), "P_never": float((~np.isfinite(P)).mean()), "n_finite": int(fin.size)}

# cheapest route at each price (central) and where low-carbon ammonia is NOT cheapest
sweep_P = np.arange(0.0, 500.0 + 1e-9, 5.0)
sweep_rows, cheapest = [], []
for P in sweep_P:
    row = {"price_SGD_per_tCO2e": float(P)}
    for r in ROUTES:
        for lv in ("central", "low", "high"):
            row[f"lcoh_{r}_{lv}_USD_per_kg"] = lc0[r] + P * ci_of(r, lv) / 1000.0 / FX
    row["benchmark_smr_carbon_adjusted_USD_per_kg"] = REF.h2_selling_price_USD_per_kg + P * SMR_CI_C / 1000.0 / FX
    cen = {r: row[f"lcoh_{r}_central_USD_per_kg"] for r in ROUTES}
    row["cheapest_central"] = min(cen, key=cen.get)
    cheapest.append(row["cheapest_central"])
    sweep_rows.append(row)
with open(OUT / "price_sweep.csv", "w", newline="", encoding="utf-8") as fh:
    w = csv.DictWriter(fh, fieldnames=list(sweep_rows[0]))
    w.writeheader()
    w.writerows(sweep_rows)
# 'today' set (exclude projections): grey, blue, green_current
today = ("grey", "blue", "green_current")
def cheapest_in(P, subset):
    v = {r: lc0[r] + P * ci_of(r) / 1000.0 / FX for r in subset}
    return min(v, key=v.get)
changes = []
for subset_name, subset in (("all_scenarios", ROUTES), ("current_prices_only", today), ("2030_set", ("grey", "blue", "green_2030"))):
    seq = [(float(P), cheapest_in(P, subset)) for P in sweep_P]
    ch = [seq[0]] + [seq[i] for i in range(1, len(seq)) if seq[i][1] != seq[i - 1][1]]
    changes.append({"set": subset_name, "routes": list(subset), "cheapest_from_price_SGD": [{"from_price": p, "cheapest": r} for p, r in ch]})

thresholds = {
    "provenance": prov("route LCOH from amcrax.economics.singapore.evaluate (reference scenario), CI from carbon_pricing.carbon_intensity_h2"),
    "label": cp.HYPOTHETICAL_LABEL,
    "reference_prices_SGD_per_tCO2e": {"singapore_legislated_2026_onward": SG_RATE, "singapore_2030_aim_not_legislated": list(AIM),
                                       "eu_ets_context_only": EU_ETS, "eu_ets_EUR": cp.POLICY["eu_ets_EUR_per_tCO2"], "eu_ets_status": cp.POLICY["eu_ets_status"]},
    "pairwise": thr_rows,
    "monte_carlo": {"n": M, "seed": SEED + 1, "draws": "NH3 prices triangular(low, value, high) per scenario (data/singapore.yaml), independent; gate EFs uniform(low, high) per route (lca.route_spec), independent; green scenarios share one EF draw; distance 5000 km",
                    "caveat": "Independent price draws ignore the correlation of grey and blue ammonia prices (both natural-gas based); the spread of the blue-grey gap is therefore probably overstated.",
                    "results": mc_thr},
    "cheapest_route_changes": changes,
    "note_time_basis": "green_2030 and green_2050 are price projections (IRENA via Cho 2026); setting them against today's grey and blue prices mixes time bases. They are reported, but the 'current_prices_only' set is the like-for-like comparison.",
}
wj(OUT / "thresholds.json", thresholds)
wj(OUT / "scenarios.json", {"provenance": prov("route_case for 5 ammonia scenarios x (Mode A + Mode B at 8 price levels)"),
                            "mode_a_actual_boundary": mode_a, "hypothetical_label": cp.HYPOTHETICAL_LABEL,
                            "price_levels_SGD_per_tCO2e": PRICE_LEVELS, "benchmark_ci_smr_kgCO2e_per_kgH2": SMR_CI_C,
                            "cases": cases, "rankings_by_lcoh": rankings,
                            "ci_kgCO2e_per_kgH2_central": {r: ci_of(r) for r in ROUTES},
                            "notes": ["Mode A LCOH equals the frozen singapore.evaluate default for every route (carbon tax 0).",
                                      "Break-even NH3 price: price before carbon cost at which LCOH equals the benchmark (3.06 USD/kg NE Asia SMR incl. capex, Argus). Under Mode B it is given against the unadjusted benchmark and against the benchmark carrying its own hypothetical carbon cost (SMR unabated CI 11 kg/kg, IEA GHR 2024 10-12).",
                                      "NPV at 3.06 USD/kg (and at the carbon-adjusted benchmark under Mode B), pre-tax, reference finance."]})

# ===================================================================== 5. row evidence
t_bg = next(t for t in thr_rows if t["route"] == "blue" and t["overtakes"] == "grey")
t_gcg = next(t for t in thr_rows if t["route"] == "green_current" and t["overtakes"] == "grey")
t_g30g = next(t for t in thr_rows if t["route"] == "green_2030" and t["overtakes"] == "grey")
t_gcb = next(t for t in thr_rows if t["route"] == "green_current" and t["overtakes"] == "blue")
t_g30b = next(t for t in thr_rows if t["route"] == "green_2030" and t["overtakes"] == "blue")
pw_min = min(v["breakeven_gate_ef"] for v in pw_be.values()); pw_max = max(v["breakeven_gate_ef"] for v in pw_be.values())
be_smr = ci_json["breakeven_gate_ef_kgCO2e_per_kgNH3"]["vs_smr_unabated"]
be_ccs = ci_json["breakeven_gate_ef_kgCO2e_per_kgNH3"]["vs_smr_ccs"]
m450 = next(m for m in mults if m["nh3_price_USD_per_t"] == 450.0)
m300 = next(m for m in mults if m["nh3_price_USD_per_t"] == 300.0)
row_evidence = {
    "H2-a": {
        "proposed_verdict": "SUPPORTED",
        "numbers": {"feed_USD_per_kg": bd["ammonia_feed"], "lcoh_USD_per_kg": L, "feed_share": shares["ammonia_feed"],
                    "feed_share_at_300_USD_per_t": feed["feed_share_at_cho_range"]["300.0"], "tornado_nh3_swing": bars[0]["swing"],
                    "tornado_next": {"parameter": bars[1]["parameter"], "swing": bars[1]["swing"]},
                    "mc_feed_share_p5": mc_feed["feed_share_p5_p50_p95"][0], "mc_P_feed_largest_item": mc_feed["P_feed_largest_item"]},
        "assumptions": ["NH3 price scenarios are inputs (Cho Table 8 300-610 USD/t; others data/singapore.yaml)", "reference CAPEX cho2026_itemised_v1 (at or above the independent published range)", "stored Aspen activity 6.756 kg NH3 feed + 0.595 kg NH3 fuel per kg H2"],
        "uncertainty": f"MC (n={N}) feed share p5-p95 {mc_feed['feed_share_p5_p50_p95'][0]:.3f}-{mc_feed['feed_share_p5_p50_p95'][2]:.3f}; feed is the largest item in {mc_feed['P_feed_largest_item']:.4f} of draws",
        # one comparator (feed above 50 % of LCOH) throughout: fix pass 24 Nov 2026, review C finding M4
        "envelope": f"feed above 50 % of LCOH for NH3 >= {p_share50:.0f} USD/t (CAPEX x1) and for CAPEX multiplier below {m450['feed_share_falls_to_50pct']:.2f} at 450 USD/t ({m300['feed_share_falls_to_50pct']:.2f} at 300 USD/t); other comparators: capital + fixed opex equal feed at x{m450['capital_plus_fixed_opex_equals_feed']:.2f} (x{m300['capital_plus_fixed_opex_equals_feed']:.2f} at 300 USD/t); plant capacity above x{scale_star:.3f} of the stored feed",
        "threshold": {"nh3_price_feed_share_50pct_USD_per_t": p_share50, "capex_multiple_capital_plus_fixed_equals_feed_at_450": m450["capital_plus_fixed_opex_equals_feed"],
                      "capex_multiple_capital_plus_fixed_equals_feed_at_300": m300["capital_plus_fixed_opex_equals_feed"],
                      "sourced_nh3_price_min_USD_per_t": feed["sourced_comparison"]["lowest_sourced_nh3_price_USD_per_t"],
                      "sourced_capex_multiplier_max": 1.5, "capacity_scale": scale_star},
        "reason": "The share follows from assumed prices, so a threshold analysis is used: feed stays the largest item unless NH3 falls below the threshold price or CAPEX rises several-fold; every sourced NH3 price (lowest 300 USD/t) and every CAPEX multiplier considered (independent published estimates x0.41-x0.85; x1.5 is the Cho Table 8 sensitivity bound, not a sourced plant cost) lies clearly on the dominant side.",
        "sourced_capex_multiplier_max_note": "1.5 is the largest CAPEX multiplier in the Cho Table 8 sensitivity, not a sourced plant cost; the independent published range is x0.41-x0.85 (reference_scenario/capex_audit.json).",
    },
    "H2-b": {
        # fix pass 24 Nov 2026 (review A B2): the sourced price ranges straddle the break-even; the threshold is the finding
        "proposed_verdict": "INCONCLUSIVE",
        "numbers": {"breakeven_vs_ne_asia_smr_USD_per_t": be_hi["ne_asia_smr_production_cost"]["breakeven_nh3_USD_per_t"],
                    "breakeven_vs_sg_wtp_USD_per_t": be_hi["sg_low_carbon_willingness_to_pay"]["breakeven_nh3_USD_per_t"],
                    "breakeven_by_capex_multiplier": be_env, "scenario_prices_USD_per_t": scen_prices,
                    "mc_P_lcoh_below_3p06_grey": mc_feed["P_lcoh_below_ne_asia_smr_3p06"]},
        "assumptions": ["benchmark 3.06 USD/kg NE Asia SMR incl. capex (Argus, production-cost marker, not a Singapore price)", "plant-gate LCOH, no compression or delivery", "reference CAPEX"],
        "uncertainty": f"break-even {min(v for v in be_env.values() if v):.0f}-{max(v for v in be_env.values() if v):.0f} USD/t over CAPEX x0.41-1.5; grey MC P(LCOH < 3.06) = {mc_feed['P_lcoh_below_ne_asia_smr_3p06']:.4f}",
        "envelope": (f"against the NE Asia SMR marker (3.06 USD/kg; the SG willingness-to-pay figure 3.0 gives {be_hi['sg_low_carbon_willingness_to_pay']['breakeven_nh3_USD_per_t']:.0f} USD/t); "
                     f"other benchmarks (6.0, 10.0 USD/kg) give {be_hi['blue_delivered_east_asia']['breakeven_nh3_USD_per_t']:.0f} and "
                     f"{be_hi['low_carbon_offer_fob_malaysia']['breakeven_nh3_USD_per_t']:.0f} USD/t; plant gate; CAPEX multiplier 0.41-1.5"),
        "threshold": {"breakeven_nh3_USD_per_t": be_hi["ne_asia_smr_production_cost"]["breakeven_nh3_USD_per_t"],
                      "sourced_central_prices_all_above": all(v["value"] > max(x for x in be_env.values() if x) for v in scen_prices.values())},
        "reason": "Competitiveness with the SMR marker needs NH3 at or below about 320 USD/t (about 371 at the lowest sourced CAPEX, x0.41); every central sourced price (450-1000) is above, only the low ends of grey (300) and green 2050 (315) reach it, so the sourced ranges straddle the break-even and the threshold is the finding (fix pass 24 Nov 2026; the earlier 'necessity' reading against central prices could not fail). Note: even central grey ammonia is not affordable enough against this marker.",
    },
    "H2-c": {
        "proposed_verdict": "SUPPORTED",
        "numbers": {"power_breakeven_gate_ef_range_kgCO2e_per_kgNH3": [pw_min, pw_max], "vs_grid": ci_json["power_breakeven_gate_ef_kgCO2e_per_kgNH3"]["vs_grid_average"],
                    "grey_gate_ef_range": ci_rows["grey"]["gate_ef_kgCO2e_per_kgNH3"], "blue_v1": ci_rows["blue"]["gate_ef_kgCO2e_per_kgNH3"],
                    "blue_v2": ci_rows["blue_v2"]["gate_ef_kgCO2e_per_kgNH3"], "green": ci_rows["green"]["gate_ef_kgCO2e_per_kgNH3"],
                    "power_ci_kgCO2e_per_MWh": ci_json["power_ci_from_lca_results_kgCO2e_per_MWh"]},
        "assumptions": ["direct NH3 CCGT activity and efficiency from results/research/lca (Ahmad-calibrated)", "CCGT efficiency 0.50-0.60 (assumption range)", "NG upstream leakage 0-3 % (low-confidence scenario values)", "5000 km shipping"],
        "uncertainty": f"break-even gate EF {pw_min:.2f}-{pw_max:.2f} kg/kg over CCGT efficiency and leakage; grey sourced range 2.0-4.6",
        "envelope": "Singapore power against NG CCGT or the grid average, GWP100, sourced gate-factor ranges",
        "threshold": {"breakeven_gate_ef_max": pw_max, "grey_gate_ef_min": ci_rows["grey"]["gate_ef_kgCO2e_per_kgNH3"]["low"]},
        "reason": "Necessity reading: grey NH3 (lowest sourced 2.0) is above every break-even (max {:.2f}), so only low-carbon NH3 can cut power-sector emissions. Not sufficient: blue v1 (1.16, range 0.77-1.92) mostly fails; blue v2 (0.77) and green pass.".format(pw_max),
    },
    "H2-d": {
        "proposed_verdict": "SUPPORTED",
        "numbers": {"ci_kgCO2e_per_kgH2": {r: ci_rows[r]["ci_kgCO2e_per_kgH2"] for r in ci_rows}, "breakeven_vs_smr_unabated": be_smr, "breakeven_vs_smr_ccs": be_ccs},
        "assumptions": ["SMR unabated 10-12 kg/kg (IEA GHR 2024 highlights)", "SMR+CCS 3.4-3.6 (low confidence), 5.3 high", "self-firing NH3 heat, 5000 km, Singapore grid"],
        "uncertainty": f"grey H2 CI {ci_rows['grey']['ci_kgCO2e_per_kgH2']['low']:.1f}-{ci_rows['grey']['ci_kgCO2e_per_kgH2']['high']:.1f} kg/kg, always above unabated SMR 10-12",
        "envelope": "cracked H2 at the PSA outlet vs fossil H2 comparators, GWP100, sourced EF ranges",
        "threshold": {"breakeven_gate_ef_vs_smr_unabated_max": max(be_smr.values()), "grey_gate_ef_min": ci_rows["grey"]["gate_ef_kgCO2e_per_kgNH3"]["low"]},
        "reason": "Break-even gate EF vs unabated SMR is {:.2f}-{:.2f}; the lowest sourced grey value 2.0 is above, so low-carbon NH3 is necessary. Blue v1 central (1.16) is only just below and its range (0.77-1.92) straddles; against SMR+CCS (break-even {:.2f}-{:.2f}) grey fails; green passes only below {:.2f}-{:.2f} (its high value fails the lowest-CCS case).".format(min(be_smr.values()), max(be_smr.values()), min(be_ccs.values()), max(be_ccs.values()), min(be_ccs.values()), max(be_ccs.values())),
    },
    "H2-e_mode_A_actual_policy": {
        "proposed_verdict": "CONTRADICTED",
        "numbers": {"carbon_tax_USD_per_kg_all_routes": 0.0, "direct_tCO2e_per_yr_self_firing": 0.0,
                    "n2o_needed_for_threshold_kg_per_h": tt["n2o_needed_kg_per_h"], "fraction_of_fuel_N_to_N2O_needed": tt["fraction_of_fuel_N_to_N2O_needed"],
                    "n2o_ppmv_needed": tt["n2o_ppmv_needed_in_flue"], "ng_heat_direct_tCO2e_per_yr": ng["direct_tCO2e_per_yr"],
                    "ng_heat_capacity_scale_to_threshold": ng_scale, "lcoh_by_route_USD_per_kg": lc0},
        "assumptions": ["Carbon Pricing Act 2018 text as at 23 Nov 2026 (rate 45 from 2026, threshold 25,000 tCO2e, direct emissions only)", "single-site facility, no other emitters on site", "NH3 self-firing (no CO2)"],
        "uncertainty": "N2O factor not sourced; the threshold needs about 5 % of the fuel nitrogen to leave as N2O (about 1500 ppmv), far above the 0.15 ppmv simulated for an NH3 turbine. EITE allowances and future amendments not read.",
        "envelope": "current Singapore law; any plant size for the ammonia-route question (upstream emissions are outside the Act at every size)",
        "threshold": {"n2o_ppmv_needed": tt["n2o_ppmv_needed_in_flue"], "ng_heat_capacity_scale": ng_scale},
        "reason": "The tax charges no upstream emission, so the carbon cost is the same (zero) for grey, blue and green NH3, while low-carbon NH3 raises LCOH (blue +{:.3f}, green current +{:.2f} USD/kg). Low carbon intensity is not rewarded under actual policy. This follows from the statute, not from a model assumption.".format(lc0["blue"] - lc0["grey"], lc0["green_current"] - lc0["grey"]),
    },
    "H2-e_mode_B_hypothetical_conditional": {
        "proposed_verdict": "INCONCLUSIVE",
        "conditional_on": "HYPOTHETICAL life-cycle carbon price applied to the full CI of the hydrogen (not Singapore law)",
        "numbers": {"blue_over_grey": {"central": t_bg["threshold_central_SGD_per_tCO2e"], "range": t_bg["threshold_range_from_ci_ranges_SGD_per_tCO2e"], "mc": mc_thr["blue_over_grey"]},
                    "green_current_over_grey": {"central": t_gcg["threshold_central_SGD_per_tCO2e"], "range": t_gcg["threshold_range_from_ci_ranges_SGD_per_tCO2e"]},
                    "green_2030_over_grey": {"central": t_g30g["threshold_central_SGD_per_tCO2e"], "range": t_g30g["threshold_range_from_ci_ranges_SGD_per_tCO2e"]},
                    "green_current_over_blue": {"central": t_gcb["threshold_central_SGD_per_tCO2e"], "range": t_gcb["threshold_range_from_ci_ranges_SGD_per_tCO2e"]},
                    "green_2030_over_blue": {"central": t_g30b["threshold_central_SGD_per_tCO2e"], "range": t_g30b["threshold_range_from_ci_ranges_SGD_per_tCO2e"]},
                    "reference_prices": thresholds["reference_prices_SGD_per_tCO2e"]},
        "assumptions": ["life-cycle price on the full CI (no such instrument exists in Singapore)", "NH3 price scenarios (central)", "CI gate-factor ranges (lca.route_spec), 5000 km"],
        "uncertainty": "threshold ranges from CI ranges and a joint Monte Carlo with NH3 price ranges (thresholds.json)",
        "envelope": "conditional on the hypothetical price only",
        "threshold": {"blue_over_grey_central": t_bg["threshold_central_SGD_per_tCO2e"], "green_current_over_grey_central": t_gcg["threshold_central_SGD_per_tCO2e"]},
        "reason": "Blue overtakes grey near {:.0f} SGD/t centrally but the CI ranges give {:.0f} to {}, straddling 45, 50-80 and the EU ETS level ({:.0f}). Green at current prices needs {:.0f} SGD/t (range {:.0f}-{}) to beat grey and {:.0f} to beat blue: above every reference price. Green 2030 needs {:.0f}. So the reward exists only for blue at moderate prices and is uncertain; green current ammonia is not cheapest at any reference price.".format(
            t_bg["threshold_central_SGD_per_tCO2e"], t_bg["threshold_range_from_ci_ranges_SGD_per_tCO2e"][0],
            "unbounded" if t_bg["upper_unbounded"] else f"{t_bg['threshold_range_from_ci_ranges_SGD_per_tCO2e'][1]:.0f}", EU_ETS,
            t_gcg["threshold_central_SGD_per_tCO2e"], t_gcg["threshold_range_from_ci_ranges_SGD_per_tCO2e"][0],
            "unbounded" if t_gcg["upper_unbounded"] else f"{t_gcg['threshold_range_from_ci_ranges_SGD_per_tCO2e'][1]:.0f}",
            t_gcb["threshold_central_SGD_per_tCO2e"], t_g30g["threshold_central_SGD_per_tCO2e"]),
    },
}
wj(OUT / "row_evidence.json", {"provenance": prov("derived from the files in results/research/carbon_pricing"), "row_evidence": row_evidence,
                               "note": "Proposed verdicts only; the evidence matrix sets the verdicts by its coded rules. Mode B evidence is conditional on a hypothetical price and cannot change a row about actual policy."})

# ===================================================================== 6. site summary + test vectors
site = {
    "schema": "amcrax.carbon_pricing.site/1", "generated_utc": NOW, "reference_scenario": provenance_stamp(),
    "fx_SGD_per_USD": FX, "default_mode": "actual_sg",
    "labels": {"actual_sg": cp.ACTUAL_LABEL, "hypothetical_lca": cp.HYPOTHETICAL_LABEL},
    "policy": {"rate_SGD_2026_onward": SG_RATE, "aim_2030_not_law": list(AIM), "threshold_tCO2e": cp.POLICY["threshold_tCO2e_per_yr"],
               "n2o_gwp": cp.POLICY["gwp"]["N2O"], "eu_ets_SGD_context": round(EU_ETS, 2)},
    "routes": {r: {"nh3_USD_per_t": SD[r]["value"], "lcoh_USD_per_kg": round(lc0[r], 4), "lcoh_SGD_per_kg": round(lc0[r] * FX, 4),
                   "ci_kgCO2e_per_kgH2": {lv: round(ci_of(r, lv), 3) for lv in ("central", "low", "high")}} for r in ROUTES},
    "mode_a": {"carbon_tax_USD_per_kg": 0.0, "n2o_ppmv_for_threshold": round(tt["n2o_ppmv_needed_in_flue"], 0), "upstream_taxed": False},
    "thresholds_SGD_per_tCO2e": {f"{t['route']}_over_{t['overtakes']}": {"central": None if t["threshold_central_SGD_per_tCO2e"] is None else round(t["threshold_central_SGD_per_tCO2e"], 1),
                                 "low": None if t["threshold_range_from_ci_ranges_SGD_per_tCO2e"][0] is None else round(t["threshold_range_from_ci_ranges_SGD_per_tCO2e"][0], 1),
                                 "high": None if t["threshold_range_from_ci_ranges_SGD_per_tCO2e"][1] is None else round(t["threshold_range_from_ci_ranges_SGD_per_tCO2e"][1], 1)} for t in thr_rows},
    "feed": {"share": round(shares["ammonia_feed"], 4), "breakeven_nh3_vs_smr_USD_per_t": round(be_hi["ne_asia_smr_production_cost"]["breakeven_nh3_USD_per_t"], 1),
             "capex_multiple_capital_overtakes_feed": round(m450["capital_plus_fixed_opex_equals_feed"], 2), "nh3_price_feed_share_50pct": round(p_share50, 1)},
    "sweep_step_SGD": 5, "sweep_max_SGD": 500,
    "note": "LCOH under Mode B = Mode A LCOH - actual tax + price x CI / 1000 / fx. Mode B is hypothetical, not Singapore law.",
}
wj(OUT / "site_summary.json", site)

vectors = []
fac = cp.ci_factors()
for i, (route, heating, dist) in enumerate([("grey", "self_firing", None), ("blue", "self_firing", None), ("green", "self_firing", None),
                                             ("grey", "natural_gas", None), ("grey", "electric", None), ("blue", "self_firing", 12000.0)]):
    ef = lca.route_spec(route).ef
    out = cp.carbon_intensity_h2(CI_IN, ef, heating, dist)
    vectors.append({"id": f"CI{i+1:02d}", "function": "carbonIntensity", "python": "carbon_pricing.carbon_intensity_h2",
                    "inputs": {"x": CI_IN, "nh3_ef_kg_per_kg": ef, "heating": heating, "distance_km": dist if dist is not None else fac.distance_km,
                               "factors": fac.__dict__}, "expected": out})
cost_cases = [("grey", "actual_sg", 0.0, {}), ("grey", "hypothetical_lca", 45.0, {}), ("blue", "hypothetical_lca", 80.0, {}),
              ("green_current", "hypothetical_lca", 500.0, {}), ("green_2030", "hypothetical_lca", EU_ETS, {}),
              ("grey", "hypothetical_lca", 0.0, {}), ("grey", "actual_sg", 0.0, {"heat_fuel": "natural_gas", "apply_threshold": False}),
              ("grey", "hypothetical_lca", 100.0, {"heat_fuel": "natural_gas", "apply_threshold": False}),
              ("green_2050", "hypothetical_lca", 250.0, {})]
for j, (route, mode, P, ov) in enumerate(cost_cases):
    econ = singapore.evaluate(BASE, route, ov or None)
    heating = "natural_gas" if ov.get("heat_fuel") == "natural_gas" else "self_firing"
    ci = cp.carbon_intensity_h2(CI_IN, cp.route_gate_ef(route)["central"], heating)
    out = cp.carbon_cost(econ, ci["total_kgCO2e_per_kgH2"], mode, P)
    vectors.append({"id": f"CC{j+1:02d}", "function": "carbonCost", "python": "carbon_pricing.carbon_cost",
                    "inputs": {"econ": {"lcoh_USD_per_kg": econ["lcoh_USD_per_kg"], "lcoh_SGD_per_kg": econ["lcoh_SGD_per_kg"],
                                        "breakdown_USD_per_kg": {"carbon_tax": econ["breakdown_USD_per_kg"]["carbon_tax"]}, "fx_SGD_per_USD": econ["fx_SGD_per_USD"]},
                               "ci_total_kgCO2e_per_kgH2": ci["total_kgCO2e_per_kgH2"], "mode": mode, "ts_mode": "actual" if mode == "actual_sg" else "hypothetical",
                               "price_SGD_per_t": P, "evaluate_overrides": ov, "route": route},
                    "expected": {k: v for k, v in out.items() if k != "label"} | {"label_contains": "HYPOTHETICAL" if mode != "actual_sg" else "actual boundary"}})
for k, (a, b) in enumerate(pairs[:3]):
    t = next(x for x in thr_rows if x["route"] == a and x["overtakes"] == b)
    vectors.append({"id": f"XO{k+1:02d}", "function": "crossoverPrice", "python": "carbon_pricing.crossover_price",
                    "inputs": {"lcoh_a": lc0[a], "ci_a": ci_of(a), "lcoh_b": lc0[b], "ci_b": ci_of(b), "fx": FX},
                    "expected": t["threshold_central_SGD_per_tCO2e"]})
wj(OUT / "test_vectors.json", {"provenance": prov("inputs and outputs of the Python functions for a TypeScript port check (frontend/src/sim/carbon.ts)"),
                               "tolerance_relative": 1e-9,
                               "mapping": {"actual_sg": "carbonCost mode 'actual'", "hypothetical_lca": "carbonCost mode 'hypothetical'",
                                           "factors": "m.carbon.accounting: ship_ef_kg_per_tkm, distance_km, electricity[grid], natural_gas_kg_per_TJ, fired_heater_efficiency_lhv, electric_heater_efficiency"},
                               "vectors": vectors})

# ===================================================================== 7. validation
items = []
def V(id_, desc, kind, obs, exp, tol, unit, status=None, note=""):
    st = status or ("pass" if (exp is not None and obs is not None and abs(obs - exp) <= tol) else "fail")
    items.append({"id": id_, "description": desc, "evidence_kind": kind, "observed": obs, "expected": exp, "tolerance": tol, "unit": unit, "status": st, "note": note})
refb = json.loads((ROOT / "results" / "research" / "reference_scenario" / "baseline.json").read_text(encoding="utf-8"))
V("CP01", "Frozen basis: singapore.evaluate default LCOH equals the stored reference baseline", "numerical_verification", L, refb["lcoh_USD_per_kg"], 1e-9, "USD/kg H2")
V("CP02", "Mode A LCOH equals singapore.evaluate for every route (carbon_cost actual)", "numerical_verification",
  max(abs(c["lcoh_USD_per_kg"] - lc0[c["route"]]) for c in cases if c["mode"] == "actual_sg"), 0.0, 1e-12, "USD/kg H2")
V("CP03", "Mode B at P = 0 equals Mode A LCOH minus the actual tax (no double counting)", "numerical_verification",
  max(abs(c["lcoh_USD_per_kg"] - lc0[c["route"]]) for c in cases if c["mode"] == "hypothetical_lca" and c["carbon_price_SGD_per_tCO2e"] == 0.0), 0.0, 1e-12, "USD/kg H2")
eng = singapore.evaluate(BASE, "grey", {"heat_fuel": "natural_gas", "apply_threshold": False})
cin = cp.carbon_intensity_h2(CI_IN, cp.route_gate_ef("grey")["central"], "natural_gas")
cb = cp.carbon_cost(eng, cin["total_kgCO2e_per_kgH2"], "hypothetical_lca", 100.0)
V("CP04", "Replacement, not addition: with a non-zero actual tax (natural-gas heat, threshold off) Mode B LCOH = LCOH - tax + P*CI/1000/fx", "numerical_verification",
  cb["lcoh_USD_per_kg"], eng["lcoh_USD_per_kg"] - eng["breakdown_USD_per_kg"]["carbon_tax"] + 100.0 * cin["total_kgCO2e_per_kgH2"] / 1000.0 / FX, 1e-12, "USD/kg H2",
  note=f"actual tax term in that case {eng['breakdown_USD_per_kg']['carbon_tax']:.5f} USD/kg")
for r in ("grey", "blue", "green", "green_lee"):
    V(f"CP05-{r}", f"Carbon intensity ({r}) reproduces results/research/lca/lca_results.json H2_kgCO2e_per_kg (two Python paths)", "numerical_verification",
      ci_rows[r]["ci_kgCO2e_per_kgH2"]["central"], lca_by[r]["H2_kgCO2e_per_kg"], 1e-6, "kg CO2e/kg H2")
V("CP06", "Crossover blue over grey equals the analytic Delta p x fx / Delta EF (CAPEX independent)", "numerical_verification",
  t_bg["threshold_central_SGD_per_tCO2e"], t_bg["analytic_dp_fx_over_def_SGD_per_tCO2e"], 1e-6 * t_bg["threshold_central_SGD_per_tCO2e"], "SGD/tCO2e")
xs = np.array([r["price_SGD_per_tCO2e"] for r in sweep_rows]); gap = np.array([r["lcoh_blue_central_USD_per_kg"] - r["lcoh_grey_central_USD_per_kg"] for r in sweep_rows])
idx = int(np.argmax(gap <= 0)); xo = xs[idx - 1] + (0 - gap[idx - 1]) * (xs[idx] - xs[idx - 1]) / (gap[idx] - gap[idx - 1])
V("CP07", "Crossover blue over grey from the 0-500 sweep (linear interpolation) equals the closed form", "numerical_verification", float(xo), t_bg["threshold_central_SGD_per_tCO2e"], 1e-6, "SGD/tCO2e")
V("CP08", "Mode A tax liability is zero for the self-fired reference plant (direct CO2 0, N2O 0 by default)", "numerical_verification", ab["carbon_tax_USD_per_kg"], 0.0, 0.0, "USD/kg H2")
V("CP09", "N2O GWP used for the Singapore tax equals the CPA First Schedule value", "literature_comparison", cp.POLICY["gwp"]["N2O"], 265.0, 0.0, "-",
  note="research/data/carbon_policy_sg.json gases_covered; amcrax.environmental.lca uses AR6 273 for the CI (not for the tax)")
V("CP10", "Legislated rate for 2026 and every later year equals the CPA Third Schedule value", "literature_comparison", cp.legislated_rate_SGD(2030), 45.0, 0.0, "SGD/tCO2e")
be_chk = cp.route_case(BASE, "grey", "actual_sg")["breakeven_nh3_USD_per_t"]
V("CP11", "Break-even NH3 vs NE Asia SMR (route_case) equals results/research/singapore/breakeven_ammonia_price.json", "numerical_verification", be_chk,
  be_hi["ne_asia_smr_production_cost"]["breakeven_nh3_USD_per_t"], 1e-6, "USD/t")
npv_chk = cp.route_case(BASE, "grey", "actual_sg")["npv_USD"]
V("CP12", "Mode A NPV equals singapore.evaluate npv_USD", "numerical_verification", npv_chk, E["npv_USD"], 1e-6, "USD")
cmc = singapore.evaluate(BASE, "grey", {"capex_multiplier": m450["capital_plus_fixed_opex_equals_feed"]})["breakdown_USD_per_kg"]
V("CP13", "At the computed CAPEX multiple, capital + fixed opex equal the feed cost", "numerical_verification", cmc["capex"] + cmc["fixed_opex"], cmc["ammonia_feed"], 1e-9, "USD/kg H2")
V("CP14", "Feed share at the computed 50 % NH3 price equals 0.5", "numerical_verification",
  (lambda e: e["breakdown_USD_per_kg"]["ammonia_feed"] / e["lcoh_USD_per_kg"])(singapore.evaluate(BASE, p_share50)), 0.5, 1e-9, "-")
V("CP15", "EU ETS context price conversion (EUR 90 x 1.0990 x 1.288444)", "numerical_verification", EU_ETS, 90.0 * 1.0990 * 1.288444, 1e-9, "SGD/tCO2e",
  note="EUR 90 is a secondary press report; context only")
for vv in vectors:
    if vv["function"] == "carbonCost":
        econ = vv["inputs"]["econ"]
        o = cp.carbon_cost(econ, vv["inputs"]["ci_total_kgCO2e_per_kgH2"], vv["inputs"]["mode"], vv["inputs"]["price_SGD_per_t"])
        V(f"CP16-{vv['id']}", "Test vector round trip (carbon_cost)", "numerical_verification", o["lcoh_USD_per_kg"], vv["expected"]["lcoh_USD_per_kg"], 1e-12, "USD/kg H2")
V("CP17", "Experimental validation of the carbon-pricing results", "experimental_validation", None, None, None, "-", status="not_available",
  note="AmCraX has no independent experimental validation; none is claimed.")
n_pass = sum(1 for i in items if i["status"] == "pass"); n_fail = sum(1 for i in items if i["status"] == "fail")
wj(VAL / "carbon_pricing.json", {"provenance": prov("validation of the carbon_pricing workstream"), "summary": {"pass": n_pass, "fail": n_fail, "other": len(items) - n_pass - n_fail}, "items": items})

# ===================================================================== 8. figures
plt.rcParams.update({"font.size": 8, "axes.edgecolor": INK2, "axes.labelcolor": INK, "xtick.color": INK2, "ytick.color": INK2})
NAMES = {"grey": "Grey NH3", "blue": "Blue NH3", "green_current": "Green NH3 (current price)", "green_2030": "Green NH3 (2030 price)", "green_2050": "Green NH3 (2050 price)"}
# (a) sweep
fig, ax = plt.subplots(figsize=(8, 4.8))
ax.axvspan(AIM[0], AIM[1], color="#e9e8e4", lw=0)
for x, t in ((SG_RATE, "SG Act 45"), (EU_ETS, f"EU ETS ~{EU_ETS:.0f} (context)")):
    ax.axvline(x, color=INK2, lw=0.8, ls="--")
    ax.text(x + 3, 11.9, t, fontsize=7, color=INK2, va="top")
ax.text(AIM[0] + 1, 11.4, "SG 2030 aim\n50-80 (not law)", fontsize=6.5, color=INK2, va="top")
for r in ROUTES:
    y = [row[f"lcoh_{r}_central_USD_per_kg"] for row in sweep_rows]
    ax.fill_between(xs, [row[f"lcoh_{r}_low_USD_per_kg"] for row in sweep_rows], [row[f"lcoh_{r}_high_USD_per_kg"] for row in sweep_rows], color=COLORS[r], alpha=0.12, lw=0)
    ax.plot(xs, y, color=COLORS[r], lw=2, label=NAMES[r])
    ax.text(503, y[-1], NAMES[r], fontsize=6.5, color=INK, va="center")
ax.plot(xs, [row["benchmark_smr_carbon_adjusted_USD_per_kg"] for row in sweep_rows], color=INK2, lw=1.2, ls=":", label="NE Asia SMR 3.06 + its own carbon cost (CI 11)")
ax.set_xlim(0, 500); ax.set_ylim(2.5, 12.0)
ax.set_xlabel("HYPOTHETICAL life-cycle carbon price (SGD/tCO2e) - not Singapore law")
ax.set_ylabel("LCOH (USD/kg H2)")
ax.set_title("Mode B: LCOH by ammonia route vs a hypothetical life-cycle carbon price (bands: CI ranges)", fontsize=9, color=INK)
ax.legend(fontsize=6.5, loc="upper left", bbox_to_anchor=(0.30, 0.99), frameon=False)
ax.grid(axis="y", color="#e9e8e4", lw=0.6); ax.spines[["top", "right"]].set_visible(False)
fig.subplots_adjust(right=0.80, bottom=0.14)
foot(fig, "AmCraX C3 | Mode A (actual Singapore boundary) gives 0 carbon cost for every route | reference scenario LCOH | CI: simplified accounting, lca.route_spec ranges")
fig.savefig(FIG / "carbon_price_sweep.png", dpi=150); plt.close(fig)
# (b) CI by route with ranges
fig, ax = plt.subplots(figsize=(7, 3.8))
keys = ["grey", "blue", "blue_v2", "green", "green_lee"]
for i, k in enumerate(keys):
    v = ci_rows[k]["ci_kgCO2e_per_kgH2"]
    ax.barh(i, v["central"], color="#2a78d6", height=0.5, zorder=2)
    ax.plot([v["low"], v["high"]], [i, i], color=INK, lw=1.2, zorder=3)
    ax.text(v["high"] + 0.4, i, f"{v['central']:.1f} ({v['low']:.1f}-{v['high']:.1f})", va="center", fontsize=7, color=INK)
ax.axvspan(SMR_CI[0], SMR_CI[1], color="#e9e8e4", lw=0, zorder=0); ax.text(SMR_CI[0], -0.55, "SMR unabated 10-12", fontsize=6.5, color=INK2)
ax.set_yticks(range(len(keys))); ax.set_yticklabels(["Grey", "Blue (Lee v1)", "Blue (Lee v2)", "Green (incl. embedded)", "Green (Lee boundary 0)"], fontsize=7)
ax.set_xlabel("kg CO2e per kg H2 (cradle to PSA outlet, simplified accounting)")
ax.set_title("Carbon intensity of cracked H2 by ammonia route (kept apart from cost)", fontsize=9, color=INK)
ax.spines[["top", "right"]].set_visible(False); ax.set_xlim(0, 42)
ax.set_ylim(len(keys) - 0.5, -0.9); fig.subplots_adjust(left=0.22, bottom=0.16); foot(fig)
fig.savefig(FIG / "carbon_intensity_routes.png", dpi=150); plt.close(fig)
# (c) feed dominance: feed vs capital+fixed against CAPEX multiplier at 300/450/610
fig, ax = plt.subplots(figsize=(7, 3.8))
mm = np.linspace(0.25, 6, 60)
cap = [(lambda b: b["capex"] + b["fixed_opex"])(at_price_and_mult(450.0, m)) for m in mm]
ax.plot(mm, cap, color="#2a78d6", lw=2, label="capital charge + fixed opex")
for p, ls in ((300.0, ":"), (450.0, "-"), (610.0, "--")):
    ax.axhline(feed_per * p, color="#eb6834", lw=1.4, ls=ls)
    ax.text(5.05, feed_per * p + 0.05, f"NH3 feed at {p:.0f} USD/t", fontsize=6.5, color=INK)
ax.axvspan(m_ind[0], 1.5, color="#e9e8e4", lw=0); ax.text(0.55, 0.15, "sourced CAPEX\nmultiplier 0.41-1.5", fontsize=6.5, color=INK2)
ax.set_xlabel("CAPEX multiplier on the reference CAPEX (7.67 MUSD)"); ax.set_ylabel("USD/kg H2")
ax.set_title("Where capital would overtake ammonia feed (grey basis)", fontsize=9, color=INK)
ax.legend(fontsize=7, frameon=False, loc="lower right"); ax.spines[["top", "right"]].set_visible(False)
fig.subplots_adjust(bottom=0.16); foot(fig)
fig.savefig(FIG / "carbon_feed_dominance.png", dpi=150); plt.close(fig)

print(json.dumps({"lcoh": L, "feed_share": shares["ammonia_feed"], "p50": p_share50, "mult450": m450, "mult300": m300, "scale": scale_star,
                  "mc": mc_feed, "be_env": be_env, "thr": [(t["route"], t["overtakes"], t["threshold_central_SGD_per_tCO2e"], t["threshold_range_from_ci_ranges_SGD_per_tCO2e"]) for t in thr_rows],
                  "mc_thr": {k: (v["p5_p50_p95_SGD_per_tCO2e"], v["P_below_or_at_SG_45"], v["P_below_or_at_EU_ETS"]) for k, v in mc_thr.items()},
                  "changes": changes, "pw_be": [pw_min, pw_max], "be_smr": be_smr, "be_ccs": be_ccs, "tt": tt, "ng_scale": ng_scale,
                  "val": (n_pass, n_fail)}, indent=1, default=float))
