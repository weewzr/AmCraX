"""Phase 2 task D2: H4 purification, PSA against Pd-Ag membrane on ONE basis.

Run:  python scripts/research/purification_phase2.py   (after scripts/research/purification_study.py)
Reuses the configuration and cost functions of purification_study.py (unified reference scenario through
amcrax.economics.singapore.evaluate; same plant, same boundaries, same cost basis for every configuration).
Outputs (new keys / files only; Phase 1 files are not changed by this script):
  results/research/purification/phase2_comparison.json, phase2_comparison.csv,
  results/research/purification/phase2_psa_recovery_sensitivity.csv, phase2_tradeoff_psa.csv, phase2_tradeoff_membrane.csv,
  results/figures/research/purification_phase2_*.png,
  results/research/validation/purification.json (P2-* items appended, existing items kept).
Every low / central / high input names its source and source type. Deterministic.
"""
from __future__ import annotations

import itertools
import json
import math
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import purification_study as ps  # noqa: E402  (module import computes the reference-scenario economics only)

from amcrax.plotstyle import C_AMBER, C_GREY, C_HEAT, C_N2, C_PRIMARY, add_provenance, apply_style, plt  # noqa: E402
from amcrax.separation.purification import psa_recovery_at_purity, psa_tail_h2_fraction_from_point, required_selectivity  # noqa: E402
from scipy.optimize import brentq  # noqa: E402

ROOT = ps.ROOT
OUT, FIG, VAL = ps.OUT, ps.FIG, ps.VAL
SCRIPT = "scripts/research/purification_phase2.py"
REF = ps._REF
FX = REF.fx_SGD_per_USD
USD_PER_EUR = REF.usd_per_eur
LIT = json.loads((ROOT / "research/data/purification_literature.json").read_text(encoding="utf-8"))
TRL = json.loads((ROOT / "research/data/membrane_trl.json").read_text(encoding="utf-8"))

SPECS = {
    "industrial_99.9": {"grade": "B", "label": "Industrial 99.9 % (ISO 14687 grade B index), delivered at 30 bar",
                        "psa_purity": 0.9991, "membrane_polish": False},
    "fuel_cell_grade_D": {"grade": "D", "label": "ISO 14687:2019 Grade D, delivered at 350 bar",
                          "psa_purity": 0.99975, "membrane_polish": True},
}
N2_LIMIT_PPM = {"industrial_99.9": 1000.0, "fuel_cell_grade_D": 300.0}


# ------------------------------------------------------------------------------------------ sourced inputs
def yanez_recovery(purity: float) -> float:
    """Linear interpolation through the two Yanez 2020 points (purge-gas feed, NOT cracked ammonia)."""
    (p1, r1), (p2, r2) = (0.9925, 0.753), (0.9997, 0.555)
    return r1 + (r2 - r1) * (purity - p1) / (p2 - p1)


_feed20 = ps.load_cases()["20bar_baseline"]["feed"]
_cho = next(p for p in ps.params()["psa"]["operating_points"] if p["id"] == "cho2026_5A")
_yt = psa_tail_h2_fraction_from_point(_feed20, _cho["recovery"], _cho["purity"])
SEL_PRINTED = 1.5e-6 / 3.7e-11   # cechetto2021fpt p. 4: printed double-sealed N2 permeance 3.7e-11 -> about 40,500


def inp(value, unit, source_type, source, note=""):
    return {"value": value, "unit": unit, "source_type": source_type, "source": source, "note": note}


INPUTS = {
    "psa_recovery": {
        "industrial_99.9": {
            "low": inp(yanez_recovery(0.9991), "-", "literature (derived)",
                       "yanez2020 (S01/S02 in purification_literature.json): linear interpolation between 75.3 % at "
                       "99.25 % and 55.5 % at 99.97 % at the modelled purity 99.91 %",
                       "PESSIMISTIC CASE, DIFFERENT FEED: ammonia-plant purge gas (58 % H2, 25 % N2, 15 % CH4, 2 % Ar), "
                       "9 bar, 5A; not cracked ammonia"),
            "central": inp(psa_recovery_at_purity(_feed20, 0.9991, _yt), "-", "assumption",
                           "mass-balance relation, tail-gas H2 fraction held at the Cho 2026 point (Phase 1 PSA_B_MB)",
                           "no sourced recovery at 99.9 % for cracked ammonia; flat by construction (optimistic)"),
            "high": inp(0.85, "-", "assumption", "AmCraX Aspen splitter assumption F4 (PSA_AMCRAX, 99.96 %)",
                        "not supported by a source at this purity"),
        },
        "fuel_cell_grade_D": {
            "low": inp(0.555, "-", "literature", "yanez2020 (S01): 55.5 % at 99.97 %",
                       "PESSIMISTIC CASE, DIFFERENT FEED (purge gas, see above); applied at the modelled 99.975 %"),
            "central": inp(psa_recovery_at_purity(_feed20, 0.99975, _yt), "-", "assumption",
                           "mass-balance relation, Cho anchor (Phase 1 PSA_D_MB)", "optimistic, flat by construction"),
            "high": inp(0.81, "-", "literature (low confidence)", "mehr2026highcapacity (S06): 81 % at 99.96 %",
                        "paper internally inconsistent; LOW confidence"),
        },
    },
    "psa_capex_basis": {"note": "spread between the two sourced PSA/TSA CAPEX bases; no other sourced range",
                        "options": {"amcrax_split": "reference scenario item (Cho 2026 itemised, T/PSA split 26:4)",
                                    "cho": "Cho 2026 T/PSA unit CAPEX 0.084 USD/kg at 82 kg/h, exponent 0.6 (assumption)"}},
    "electricity_USD_per_kWh": {
        "low": inp(REF.sens("electricity_USD_per_kWh")[0], "USD/kWh", "literature", "reference scenario sensitivity_ranges (Cho 2026)"),
        "central": inp(REF.electricity_USD_per_kWh, "USD/kWh", "derived", "reference scenario (Singapore USEP 2025 + network + fees)"),
        "high": inp(REF.sens("electricity_USD_per_kWh")[1], "USD/kWh", "derived", "reference scenario sensitivity_ranges (SP Group tariff Q4 2026)"),
    },
    "membrane_cost_USD_per_m2": {
        "low": inp(6800.0 * USD_PER_EUR, "USD/m2", "literature (derived)",
                   f"dimarcoberardino2019 (M03): 6,800 EUR/m2 (ceramic, 2017 cost data) x {USD_PER_EUR} USD/EUR (ECB 20 Nov 2026)",
                   "original value 6,800 EUR/m2; no escalation"),
        "central": inp(10000.0, "USD/m2", "literature", "sweeney2023 (M01): model value, midpoint of 5,000-15,000 USD/m2"),
        "high": inp(15000.0, "USD/m2", "literature", "sweeney2023 (M01): upper end"),
        "phase1_point": inp(6000.0 * USD_PER_EUR, "USD/m2", "literature", "richard2024technoeconomic (M05): 6,000 EUR/m2",
                            "Phase 1 value, below the sourced low end; kept in purification_study.json"),
    },
    "membrane_life_yr": {
        "low_cost": inp(5.0, "yr", "assumption (literature)", "dimarcoberardino2019 (L03) / DOE target (L04)"),
        "central": inp(3.0, "yr", "assumption (literature)", "sweeney2023 (L02); richard2024technoeconomic"),
        "high_cost": inp(2.0, "yr", "assumption (literature)", "sweeney2023 (L01) lower end",
                         "measured only 600 h (lab, NH3) and 2,068 h (Ammogen system)"),
    },
    "membrane_selectivity_H2_N2": {
        "low": inp(SEL_PRINTED, "-", "literature (derived)",
                   "cechetto2021fpt Sec. 3.1 p. 4: H2 permeance > 1.5e-6 over the PRINTED double-sealed N2 permeance 3.7e-11",
                   "the paper states 'above 400,000' for the same membrane; the printed numbers give 40,500 (internal inconsistency)"),
        "central": inp(400000.0, "-", "literature", "cechetto2021fpt Sec. 3.1 p. 4 (double sealed, stated)"),
        "high": inp(500000.0, "-", "literature", "cechetto2021fpt Sec. 3.1 p. 4 (dead end; 1.5e-6 / 3e-12)"),
        "caveats": "ideal (single gas) values; NEW membrane; one research group; measured at 450 degC (model runs at 400 degC); "
                   "membrane reactor with trace NH3 only; mixed-gas selectivity and its change with time NOT found; all are lower bounds",
        "secondary_not_used": "6,000 (P13, DOE OSTI 1460402, pure Pd, secondary excerpt) is a stress test only",
    },
    "membrane_flux_multiplier": {
        "low": inp(0.60 / 0.74, "-", "literature (derived)", "purification_literature.json P11: Cechetto lower-bound flux "
                   "0.60 against Richard-fit flux 0.74 mol m-2 s-1 at 5/1 bar, 450 degC", "uses n = 1 for the Cechetto value"),
        "central": inp(1.0, "-", "literature", "richard2024technoeconomic Table 2 Sieverts fit (P09)"),
        "high": inp(1.0, "-", "literature", "no higher sourced value; Cechetto value is a lower bound"),
    },
    "membrane_recovery": {
        "low": inp(0.86, "-", "vendor claim", "aea_h2site2024 (P24): more than 86 % (membrane reactor)"),
        "central": inp(0.90, "-", "assumption", "Phase 1 design value"),
        "high": inp(0.905, "-", "literature", "cechetto2023membrane Table 8 (P08): 90.5 % at 5 bar, lab reactor"),
        "note": "a separator's recovery is a design choice (area); the sourced values are reactor results. Ammogen's >97 % KPI was not met.",
    },
}


def readiness(kind: str, polish: bool) -> dict:
    a = TRL["assessments"]
    if kind == "psa":
        return {"configuration": a[0]["configuration"], "trl": a[0]["assessed_trl"], "source": "research/data/membrane_trl.json"}
    out = {"configuration": a[1]["configuration"], "trl": a[1]["assessed_trl"], "source": "research/data/membrane_trl.json"}
    if polish:
        out["polishing_bed"] = ("clinoptilolite NH3 polishing bed: laboratory bed (cechetto2023membrane p. 14, Sitar 2022); "
                                "TRL not assessed")
    return out


# ------------------------------------------------------------------------------------------ evaluation
CASE = ps.load_cases()["20bar_baseline"]
FEED = CASE["feed"]
_mem_cache: dict = {}


def psa_cfg(spec: str, R: float):
    return ps.cfg_psa(FEED, CASE, f"PSA_{spec}", "PSA+TSA", R, SPECS[spec]["psa_purity"], "phase2")


def mem_cfg(spec: str, R: float, alpha: float, flux: float):
    key = (spec, round(R, 6), alpha, round(flux, 6))
    if key not in _mem_cache:
        pol = SPECS[spec]["membrane_polish"]
        _mem_cache[key] = ps.cfg_membrane(FEED, CASE, f"MEM_{spec}", "Pd-Ag", R, 1.0, alpha, 0.025 if pol else 2.9,
                                          "polish bed bound" if pol else "measured permeate NH3 2.9 ppm", pol, flux)
    return _mem_cache[key]


def cost(cfg, spec, **kw):
    return ps.usable_cost(cfg, CASE, spec, **kw)


def mem_kw(cost_usd, life, elec):
    return dict(mem_cost_mult=cost_usd / (ps.MEM_EUR_PER_M2 * ps.EURUSD_PARITY), mem_life=life, elec=elec)


def describe(cfg, c, spec, inputs):
    kg_h = cfg["product_h2_kg_h"]
    capex = 0.0
    if cfg["kind"] == "psa":
        capex = (ps.PSA_CAPEX + ps.ADS_CAPEX) if inputs.get("psa_capex_basis", "amcrax_split") == "amcrax_split" else \
            c["annual_named_items_USD"]["purification_capex_and_maintenance"] / (ps.CRF + ps.MAINT_INS)
    elif cfg.get("nh3_polishing_adsorber"):
        capex = ps.ADS_CAPEX
    return {
        "inputs": inputs,
        "h2_purity_mole_frac": cfg["product_purity_h2_mole_frac"], "n2_ppm": cfg["product_ppm"]["N2"],
        "nh3_ppm": cfg["product_ppm"]["NH3"], "h2_recovery": cfg["h2_recovery"],
        "meets_spec_within_model_scope": c["meets_spec_within_model_scope"],
        "energy": {"compression_kWh_per_kg_h2": c["compression_kWh_per_kg_h2"],
                   "imported_heat_kWh_per_kg_h2": cfg["net_heat_deficit_kW"] / kg_h,
                   "tail_heat_to_furnace_kW": cfg["tail_heat_to_furnace_kW"], "net_heat_deficit_kW": cfg["net_heat_deficit_kW"],
                   "surplus_heat_not_credited_kW": cfg["surplus_heat_kW_not_credited"],
                   "psa_own_power": "not modelled (no verified source, purification_literature.json S08)" if cfg["kind"] == "psa" else None},
        "capital_USD": capex, "membrane_area_m2": cfg["area_m2"],
        "membrane_module_cost_USD": cfg["area_m2"] * inputs.get("membrane_cost_USD_per_m2", 0.0),
        "replacement_USD_per_yr": c["annual_named_items_USD"]["membrane_replacement"],
        "purification_only_usd_per_kg": c["purification_only_usd_per_kg"],
        "lcoh_usd_per_kg_usable": c["usd_per_kg_product_h2"] if c["meets_spec_within_model_scope"] else None,
        "lcoh_sgd_per_kg_usable": c["sgd_per_kg_product_h2"] if c["meets_spec_within_model_scope"] else None,
        "lcoh_usd_per_kg_product_ignoring_spec": c["usd_per_kg_product_h2"],
    }


def central_vals():
    I = INPUTS
    return {"elec": I["electricity_USD_per_kWh"]["central"]["value"],
            "mcost": I["membrane_cost_USD_per_m2"]["central"]["value"], "life": I["membrane_life_yr"]["central"]["value"],
            "alpha": I["membrane_selectivity_H2_N2"]["central"]["value"], "flux": 1.0,
            "Rm": I["membrane_recovery"]["central"]["value"]}


def run_factorial(spec):
    I = INPUTS
    elecs = [I["electricity_USD_per_kWh"][k]["value"] for k in ("low", "central", "high")]
    psa_rows, mem_rows = [], []
    for lvl in ("low", "central", "high"):
        R = I["psa_recovery"][spec][lvl]["value"]
        cfg = psa_cfg(spec, R)
        for basis in ("amcrax_split", "cho"):
            for e in elecs:
                c = cost(cfg, spec, elec=e, psa_capex_basis=basis)
                psa_rows.append({"recovery_level": lvl, "recovery": R, "psa_capex_basis": basis, "elec": e,
                                 "lcoh": c["usd_per_kg_product_h2"] if c["meets_spec_within_model_scope"] else None,
                                 "meets": c["meets_spec_within_model_scope"]})
    Rs = sorted({I["membrane_recovery"][k]["value"] for k in ("low", "central", "high")})
    alphas = [I["membrane_selectivity_H2_N2"][k]["value"] for k in ("low", "central", "high")]
    fluxes = sorted({I["membrane_flux_multiplier"][k]["value"] for k in ("low", "central")})
    costs_m = [I["membrane_cost_USD_per_m2"][k]["value"] for k in ("low", "central", "high")]
    lives = [I["membrane_life_yr"][k]["value"] for k in ("low_cost", "central", "high_cost")]
    for R, a, f in itertools.product(Rs, alphas, fluxes):
        cfg = mem_cfg(spec, R, a, f)
        if cfg is None:
            continue
        for mc, life, e in itertools.product(costs_m, lives, elecs):
            c = cost(cfg, spec, **mem_kw(mc, life, e))
            mem_rows.append({"recovery": R, "alpha": a, "flux_mult": f, "mem_cost": mc, "life": life, "elec": e,
                             "lcoh": c["usd_per_kg_product_h2"] if c["meets_spec_within_model_scope"] else None,
                             "meets": c["meets_spec_within_model_scope"]})
    return psa_rows, mem_rows


def lcoh_mem(spec, mc, life, elec, R=0.90, alpha=400000.0, flux=1.0):
    cfg = mem_cfg(spec, R, alpha, flux)
    return cost(cfg, spec, **mem_kw(mc, life, elec))["usd_per_kg_product_h2"]


def lcoh_psa(spec, R, elec, basis="amcrax_split"):
    return cost(psa_cfg(spec, R), spec, elec=elec, psa_capex_basis=basis)["usd_per_kg_product_h2"]


def thresholds(spec):
    cv = central_vals()
    out = {}
    for lvl in ("low", "central", "high"):
        Rp = INPUTS["psa_recovery"][spec][lvl]["value"]
        target = lcoh_psa(spec, Rp, cv["elec"])
        # membrane cost (linear) at which LCOH_mem = LCOH_PSA, central life
        a0 = lcoh_mem(spec, 0.0, cv["life"], cv["elec"])
        a1 = lcoh_mem(spec, 10000.0, cv["life"], cv["elec"])
        slope = (a1 - a0) / 10000.0
        c_star = (target - a0) / slope
        # membrane life at which equal, central cost: LCOH = A + B / life
        b = (lcoh_mem(spec, cv["mcost"], 1.0, cv["elec"]) - lcoh_mem(spec, cv["mcost"], 2.0, cv["elec"])) * 2.0
        A = lcoh_mem(spec, cv["mcost"], 1.0, cv["elec"]) - b
        life_star = b / (target - A) if target > A else None
        out[lvl] = {"psa_recovery": Rp, "psa_lcoh_usd": target,
                    "membrane_cost_USD_per_m2_at_parity": c_star,
                    "membrane_cost_EUR_per_m2_at_parity": c_star / USD_PER_EUR,
                    "membrane_life_yr_at_parity": life_star,
                    "note": "membrane cheaper below the parity cost / above the parity life (other inputs central)"}
    # PSA recovery at which PSA equals the central membrane
    m_c = lcoh_mem(spec, cv["mcost"], cv["life"], cv["elec"])
    try:
        R_star = brentq(lambda R: lcoh_psa(spec, R, cv["elec"]) - m_c, 0.40, 0.999)
    except ValueError:
        R_star = None
    m_hi = lcoh_mem(spec, 15000.0, 2.0, cv["elec"], R=0.86, alpha=SEL_PRINTED, flux=0.60 / 0.74)
    try:
        R_star_hi = brentq(lambda R: lcoh_psa(spec, R, cv["elec"]) - m_hi, 0.40, 0.999)
    except ValueError:
        R_star_hi = None
    # selectivity: spec-feasibility threshold (cost changes negligibly with selectivity)
    cfg = mem_cfg(spec, cv["Rm"], math.inf, 1.0)
    req = required_selectivity(FEED, cfg["area_m2"], CASE["P_bar"], 1.0, ps.MEM_T_K, N2_LIMIT_PPM[spec])
    req_lo = required_selectivity(FEED, mem_cfg(spec, 0.905, math.inf, 0.60 / 0.74)["area_m2"], CASE["P_bar"], 1.0,
                                  ps.MEM_T_K, N2_LIMIT_PPM[spec], flux_multiplier=0.60 / 0.74)
    out["psa_recovery_at_parity_with_central_membrane"] = R_star
    out["psa_recovery_at_parity_with_high_cost_membrane"] = {"value": R_star_hi, "membrane_case":
                                                             "15,000 USD/m2, 2 yr, R 0.86, alpha 40,500, flux x0.81"}
    out["selectivity"] = {
        "required_alpha_H2_N2": req, "required_alpha_H2_N2_worst_area_case": req_lo,
        "n2_limit_ppm": N2_LIMIT_PPM[spec], "limit_basis": "Grade D N2 300 ppm" if spec == "fuel_cell_grade_D" else
        "grade B total non-H2 1000 ppm (N2 dominant)",
        "sourced_low": SEL_PRINTED, "sourced_central": 400000.0, "sourced_high": 500000.0,
        "margin_low": SEL_PRINTED / req, "margin_central": 400000.0 / req,
        "secondary_stress_value_6000_meets": 6000.0 >= req,
        "reading": "below the required value the membrane product fails the specification and the membrane drops out of the "
                   "ranking; every sourced (ideal, new-membrane) value lies above it"}
    return out


def summarise(spec, psa_rows, mem_rows):
    cv = central_vals()
    pc = [r for r in psa_rows if r["recovery_level"] == "central" and r["psa_capex_basis"] == "amcrax_split" and r["elec"] == cv["elec"]][0]
    mc = [r for r in mem_rows if r["recovery"] == cv["Rm"] and r["alpha"] == cv["alpha"] and r["flux_mult"] == 1.0
          and r["mem_cost"] == cv["mcost"] and r["life"] == cv["life"] and r["elec"] == cv["elec"]][0]
    pv = [r["lcoh"] for r in psa_rows if r["lcoh"] is not None]
    mv = [r["lcoh"] for r in mem_rows if r["lcoh"] is not None]
    # paired comparison with a shared electricity price
    n = wins = 0
    gaps = []
    for e in sorted({r["elec"] for r in psa_rows}):
        P = [r["lcoh"] for r in psa_rows if r["elec"] == e and r["lcoh"] is not None]
        M = [r["lcoh"] for r in mem_rows if r["elec"] == e and r["lcoh"] is not None]
        for p, m in itertools.product(P, M):
            n += 1
            wins += int(bool(m < p))
            gaps.append(p - m)
    return {"central": {"psa": pc["lcoh"], "membrane": mc["lcoh"], "membrane_minus_psa": mc["lcoh"] - pc["lcoh"],
                        "cheaper": "membrane" if mc["lcoh"] < pc["lcoh"] else "psa"},
            "psa_range": [min(pv), max(pv)], "membrane_range": [min(mv), max(mv)],
            "psa_range_sgd": [min(pv) * FX, max(pv) * FX], "membrane_range_sgd": [min(mv) * FX, max(mv) * FX],
            "membrane_infeasible_combinations": sum(1 for r in mem_rows if r["lcoh"] is None),
            "pairs": n, "pairs_membrane_cheaper": wins, "share_membrane_cheaper": wins / n if n else None,
            "psa_minus_membrane_range_usd": [min(gaps), max(gaps)],
            "ranking_robust": wins in (0, n),
            "ranking_reading": ("robust: same order in every pair" if wins in (0, n) else
                                f"NOT robust: membrane cheaper in {wins} of {n} input pairs (shared electricity price)")}


def oat(spec):
    """One-at-a-time low/high around the central membrane and PSA (USD/kg usable H2)."""
    cv = central_vals()
    rows = []
    base_m = lcoh_mem(spec, cv["mcost"], cv["life"], cv["elec"])
    base_p = lcoh_psa(spec, INPUTS["psa_recovery"][spec]["central"]["value"], cv["elec"])
    I = INPUTS
    for k in ("low", "high"):
        rows.append({"tech": "membrane", "input": "membrane cost", "level": k, "value": I["membrane_cost_USD_per_m2"][k]["value"],
                     "lcoh": lcoh_mem(spec, I["membrane_cost_USD_per_m2"][k]["value"], cv["life"], cv["elec"])})
    for k in ("low_cost", "high_cost"):
        rows.append({"tech": "membrane", "input": "membrane life", "level": k, "value": I["membrane_life_yr"][k]["value"],
                     "lcoh": lcoh_mem(spec, cv["mcost"], I["membrane_life_yr"][k]["value"], cv["elec"])})
    for k in ("low", "high"):
        a = I["membrane_selectivity_H2_N2"][k]["value"]
        cfg = mem_cfg(spec, cv["Rm"], a, 1.0)
        c = cost(cfg, spec, **mem_kw(cv["mcost"], cv["life"], cv["elec"]))
        rows.append({"tech": "membrane", "input": "selectivity", "level": k, "value": a, "lcoh": c["usd_per_kg_product_h2"],
                     "n2_ppm": cfg["product_ppm"]["N2"], "meets": c["meets_spec_within_model_scope"]})
    rows.append({"tech": "membrane", "input": "flux multiplier", "level": "low", "value": 0.60 / 0.74,
                 "lcoh": lcoh_mem(spec, cv["mcost"], cv["life"], cv["elec"], flux=0.60 / 0.74)})
    for k in ("low", "high"):
        R = I["membrane_recovery"][k]["value"]
        rows.append({"tech": "membrane", "input": "membrane recovery", "level": k, "value": R,
                     "lcoh": lcoh_mem(spec, cv["mcost"], cv["life"], cv["elec"], R=R)})
    for k in ("low", "high"):
        e = I["electricity_USD_per_kWh"][k]["value"]
        rows.append({"tech": "membrane", "input": "electricity", "level": k, "value": e, "lcoh": lcoh_mem(spec, cv["mcost"], cv["life"], e)})
        rows.append({"tech": "psa", "input": "electricity", "level": k, "value": e,
                     "lcoh": lcoh_psa(spec, I["psa_recovery"][spec]["central"]["value"], e)})
    for k in ("low", "high"):
        R = I["psa_recovery"][spec][k]["value"]
        rows.append({"tech": "psa", "input": "psa recovery", "level": k, "value": R, "lcoh": lcoh_psa(spec, R, cv["elec"])})
    rows.append({"tech": "psa", "input": "psa capex basis", "level": "cho", "value": "cho",
                 "lcoh": lcoh_psa(spec, I["psa_recovery"][spec]["central"]["value"], cv["elec"], basis="cho")})
    for r in rows:
        r["delta_vs_central"] = r["lcoh"] - (base_m if r["tech"] == "membrane" else base_p)
    return {"central_membrane": base_m, "central_psa": base_p, "rows": rows}


# ------------------------------------------------------------------------------------------ PSA recovery sensitivity
def psa_recovery_sensitivity():
    cv = central_vals()
    rows = []
    for spec in SPECS:
        for R in np.round(np.arange(0.50, 0.9001, 0.01), 4):
            cfg = psa_cfg(spec, float(R))
            c = cost(cfg, spec, elec=cv["elec"])
            rows.append({"spec": spec, "recovery": float(R), "lcoh_usd": c["usd_per_kg_product_h2"],
                         "lcoh_sgd": c["sgd_per_kg_product_h2"], "net_heat_deficit_kW": cfg["net_heat_deficit_kW"],
                         "surplus_heat_not_credited_kW": cfg["surplus_heat_kW_not_credited"]})
    pts = {}
    for spec in SPECS:
        base = lcoh_psa(spec, 0.85, cv["elec"])
        pts[spec] = {"assumption_0.85": {"recovery": 0.85, "lcoh_usd": base, "label": "AmCraX assumption F4"}}
        for name, R, lab in (("yanez_pessimistic", INPUTS["psa_recovery"][spec]["low"]["value"],
                              "Yanez 2020, PESSIMISTIC, DIFFERENT FEED (ammonia purge gas)"),
                             ("mass_balance_central", INPUTS["psa_recovery"][spec]["central"]["value"], "assumption (Cho anchor)"),
                             ("hansen_0.71", 0.71, "Hansen/Cha 2021 at 99 %, applied out of range"),
                             ("mehr_0.81", 0.81, "Mehr 2026, low confidence")):
            v = lcoh_psa(spec, R, cv["elec"])
            pts[spec][name] = {"recovery": R, "lcoh_usd": v, "lcoh_sgd": v * FX, "delta_vs_0.85_usd": v - base, "label": lab}
    return rows, pts


# ------------------------------------------------------------------------------------------ trade-off curves (H4-B)
def tradeoffs():
    cv = central_vals()
    psa_rows = []
    for p in np.round(np.linspace(0.990, 0.9998, 50), 6):
        for rel, R in (("mass_balance_relation_assumption", psa_recovery_at_purity(FEED, float(p), _yt)),
                       ("yanez2020_linear_different_feed", yanez_recovery(float(p)))):
            cfg = ps.cfg_psa(FEED, CASE, "PSA_t", "", R, float(p), rel)
            c30 = ps.purification_cost(cfg, CASE, 30.0, elec=cv["elec"])
            psa_rows.append({"purity": float(p), "relation": rel, "recovery": R,
                             "inside_yanez_range": 0.9925 <= p <= 0.9997 if rel.startswith("yanez") else None,
                             "n2_ppm": cfg["product_ppm"]["N2"], "compression_kWh_per_kg_30bar": c30["compression_kWh_per_kg_h2"],
                             "tail_heat_to_furnace_kW": cfg["tail_heat_to_furnace_kW"],
                             "net_heat_deficit_kW": cfg["net_heat_deficit_kW"],
                             "surplus_heat_not_credited_kW": cfg["surplus_heat_kW_not_credited"],
                             "cost_usd_per_kg_30bar": c30["usd_per_kg_product_h2"]})
    mem_rows = []
    for a in (SEL_PRINTED, 400000.0):
        for R in np.round(np.linspace(0.50, 0.95, 19), 4):
            cfg = mem_cfg("industrial_99.9", float(R), a, 1.0)
            if cfg is None:
                continue
            c30 = ps.purification_cost(cfg, CASE, 30.0, **mem_kw(cv["mcost"], cv["life"], cv["elec"]))
            mem_rows.append({"alpha": a, "recovery": float(R), "area_m2": cfg["area_m2"], "n2_ppm": cfg["product_ppm"]["N2"],
                             "purity": cfg["product_purity_h2_mole_frac"],
                             "compression_kWh_per_kg_30bar": c30["compression_kWh_per_kg_h2"],
                             "tail_heat_to_furnace_kW": cfg["tail_heat_to_furnace_kW"],
                             "net_heat_deficit_kW": cfg["net_heat_deficit_kW"],
                             "surplus_heat_not_credited_kW": cfg["surplus_heat_kW_not_credited"],
                             "cost_usd_per_kg_30bar": c30["usd_per_kg_product_h2"]})
    # computed threshold: PSA recovery at which tail gas covers the furnace demand (H4-e)
    def deficit(R):
        cfg = ps.cfg_psa(FEED, CASE, "x", "", R, 0.99975, "")
        return cfg["tail_heat_to_furnace_kW"] - CASE["furnace_demand_kW"]
    R_zero = brentq(deficit, 0.5, 0.99)
    def mdef(R):
        cfg = mem_cfg("industrial_99.9", R, 400000.0, 1.0)
        return cfg["tail_heat_to_furnace_kW"] - CASE["furnace_demand_kW"]
    try:
        Rm_zero = brentq(mdef, 0.5, 0.95)
    except ValueError:
        Rm_zero = None
    return psa_rows, mem_rows, {"psa_recovery_where_tail_heat_equals_furnace_demand": R_zero,
                                "membrane_recovery_where_retentate_heat_equals_furnace_demand": Rm_zero,
                                "furnace_demand_kW": CASE["furnace_demand_kW"]}


# ------------------------------------------------------------------------------------------ H4-b check and row evidence
def h4b_check(fact):
    """Cheapest compliant route per specification at each shared electricity price, over every sourced input
    combination; plus the purity-only increment at equal (30 bar) delivery."""
    raw = next(c for c in json.loads((OUT / "purification_study.json").read_text(encoding="utf-8"))["cases"]["20bar_baseline"]["configs"]
               if c["id"] == "RAW")
    raw_cfg = ps.cfg_raw(FEED, CASE)
    by_e = []
    for e in sorted({r["elec"] for r in fact["industrial_99.9"][0]}):
        mins = {}
        maxs = {}
        for spec in SPECS:
            v = [r["lcoh"] for r in fact[spec][0] + fact[spec][1] if r["elec"] == e and r["lcoh"] is not None]
            mins[spec], maxs[spec] = min(v), max(v)
        rawc = ps.usable_cost(raw_cfg, CASE, "turbine_blend", elec=e)["usd_per_kg_product_h2"]
        by_e.append({"electricity": e, "raw_turbine_blend": rawc, "cheapest_industrial": mins["industrial_99.9"],
                     "cheapest_grade_D": mins["fuel_cell_grade_D"],
                     "order_raw_lt_industrial_lt_gradeD": rawc < mins["industrial_99.9"] < mins["fuel_cell_grade_D"]})
    cv = central_vals()
    # purity-only increment at equal delivery (30 bar), same inputs
    eq = {}
    for lvl, (Rb, Rd) in {"yanez_different_feed": (INPUTS["psa_recovery"]["industrial_99.9"]["low"]["value"], 0.555),
                          "mass_balance_assumption": (INPUTS["psa_recovery"]["industrial_99.9"]["central"]["value"],
                                                      INPUTS["psa_recovery"]["fuel_cell_grade_D"]["central"]["value"])}.items():
        b = ps.purification_cost(psa_cfg("industrial_99.9", Rb), CASE, 30.0, elec=cv["elec"])["usd_per_kg_product_h2"]
        d = ps.purification_cost(psa_cfg("fuel_cell_grade_D", Rd), CASE, 30.0, elec=cv["elec"])["usd_per_kg_product_h2"]
        eq[f"psa_{lvl}"] = {"industrial": b, "grade_D_at_30bar": d, "increment": d - b}
    b = ps.purification_cost(mem_cfg("industrial_99.9", cv["Rm"], cv["alpha"], 1.0), CASE, 30.0,
                             **mem_kw(cv["mcost"], cv["life"], cv["elec"]))["usd_per_kg_product_h2"]
    d = ps.purification_cost(mem_cfg("fuel_cell_grade_D", cv["Rm"], cv["alpha"], 1.0), CASE, 30.0,
                             **mem_kw(cv["mcost"], cv["life"], cv["elec"]))["usd_per_kg_product_h2"]
    eq["membrane_central"] = {"industrial": b, "grade_D_at_30bar": d, "increment": d - b,
                              "cause": "NH3 polishing bed (measured permeate NH3 2.9 ppm > 0.1 ppm limit); bed cost is a proxy"}
    return {"by_electricity": by_e, "order_holds_everywhere": all(r["order_raw_lt_industrial_lt_gradeD"] for r in by_e),
            "equal_delivery_increment": eq, "raw_turbine_blend_stored": raw["costs"]["turbine_blend"]["usd_per_kg_usable_h2"]}


def row_evidence(comp):
    D, B = comp["specs"]["fuel_cell_grade_D"], comp["specs"]["industrial_99.9"]
    tD, tB = D["thresholds"], B["thresholds"]
    h4b = comp["h4b_purity_cost_check"]
    to = comp["tradeoff"]
    return {
        "H4-a": {"proposed_verdict": "INCONCLUSIVE",
                 "numbers": {"yanez2020_recovery_99.25": 0.753, "yanez2020_recovery_99.97": 0.555,
                             "mass_balance_recovery_99.91": INPUTS["psa_recovery"]["industrial_99.9"]["central"]["value"],
                             "mass_balance_recovery_99.975": INPUTS["psa_recovery"]["fuel_cell_grade_D"]["central"]["value"]},
                 "assumptions": "AmCraX has no adsorption-cycle model; the PSA recovery at any purity is an input",
                 "uncertainty": "Grade D recovery 0.555 (Yanez, different feed) to 0.81 (Mehr, low confidence); no cracked-ammonia value",
                 "envelope": "none (not computed)",
                 "threshold": None,
                 "reason": "the direction is shown by one literature source for a different feed (literature_comparison), not "
                           "computed; the model relation is flat by construction. Computed for the membrane instead: at a fixed "
                           "sourced selectivity, permeate N2 rises with recovery (P2-MEM-1), but this row is about PSA"},
        "H4-b": {"proposed_verdict": "SUPPORTED (direction), narrow envelope; orchestrator to decide",
                 "numbers": {"by_electricity": h4b["by_electricity"], "equal_delivery_increment": h4b["equal_delivery_increment"]},
                 "assumptions": "PSA recoveries are inputs; polishing-bed cost is a proxy (adsorber share); delivery 30 / 350 bar",
                 "uncertainty": "factorial over all sourced inputs (PSA recovery, CAPEX basis, electricity, membrane cost, life, "
                                "selectivity, flux, recovery)",
                 "envelope": "20 bar baseline cracked gas, grey NH3 450 USD/t, electricity 0.084-0.222 USD/kWh, unified basis",
                 "threshold": "none needed for the sign: the Grade D increment of the cheapest route is positive in every input "
                              "combination; its purity-only part at equal delivery is small (membrane: polishing bed; PSA: "
                              "about zero under the flat relation, positive under Yanez)",
                 "reason": "ordering raw < cheapest industrial < cheapest Grade D holds at every electricity price and every "
                           "sourced input combination (order_holds_everywhere = %s). Caveat: raw < industrial is structural "
                           "(raw skips purification) and most of the Grade D increment is 350 bar delivery, not purity; "
                           "the orchestrator may judge the purity-only part too small or too proxy-dependent and keep "
                           "INCONCLUSIVE" % h4b["order_holds_everywhere"]},
        "H4-c": {"proposed_verdict": "CONTRADICTED (unchanged)",
                 "numbers": {"cho_recovery": 0.756, "cho_purity": 0.9911, "n2_ppm": 8900.0},
                 "assumptions": "NH3 at the TSA design limit", "uncertainty": "none for the specification check",
                 "envelope": "ISO 14687:2019 grades B and D, modelled species NH3, N2, H2O", "threshold": None,
                 "reason": "published composition fails the 99.9 % index and Grade D (secondary row, does not vote)"},
        "H4-d": {"proposed_verdict": "INCONCLUSIVE",
                 "numbers": {"central_membrane_usd": D["factorial_summary"]["central"]["membrane"],
                             "central_psa_usd": D["factorial_summary"]["central"]["psa"],
                             "membrane_range_usd": D["factorial_summary"]["membrane_range"],
                             "psa_range_usd": D["factorial_summary"]["psa_range"],
                             "share_pairs_membrane_cheaper": D["factorial_summary"]["share_membrane_cheaper"],
                             "psa_recovery_at_parity_central_membrane": tD["psa_recovery_at_parity_with_central_membrane"],
                             "psa_recovery_at_parity_high_cost_membrane": tD["psa_recovery_at_parity_with_high_cost_membrane"]["value"],
                             "membrane_cost_at_parity_vs_central_psa_USD_m2": tD["central"]["membrane_cost_USD_per_m2_at_parity"],
                             "membrane_life_at_parity_vs_central_psa_yr": tD["central"]["membrane_life_yr_at_parity"],
                             "membrane_cost_at_parity_vs_psa_0.81_USD_m2": tD["high"]["membrane_cost_USD_per_m2_at_parity"],
                             "required_selectivity": tD["selectivity"]["required_alpha_H2_N2"],
                             "sourced_selectivity": [tD["selectivity"]["sourced_low"], 400000.0, 500000.0],
                             "industrial_share_pairs_membrane_cheaper": B["factorial_summary"]["share_membrane_cheaper"],
                             "industrial_psa_recovery_at_parity": tB["psa_recovery_at_parity_with_central_membrane"]},
                 "assumptions": "membrane housing, skid and heating CAPEX not modelled (favours the membrane); PSA own power and "
                                "TSA heat not modelled (favours PSA); permeate at 1 bar",
                 "uncertainty": "factorial over sourced inputs; ranking reverses inside it",
                 "envelope": "membrane cheaper only if PSA Grade D recovery is below about %.3f (central membrane) or %.3f "
                             "(high-cost membrane)" % (tD["psa_recovery_at_parity_with_central_membrane"],
                                                       tD["psa_recovery_at_parity_with_high_cost_membrane"]["value"]),
                 "threshold": "PSA recovery at parity about 0.75-0.79 (Grade D) and 0.75-0.80 (industrial); sourced PSA values "
                              "straddle it (0.555 Yanez, different feed, below; 0.81 Mehr, low confidence, above). Membrane "
                              "cost (parity about 34,800 USD/m2) and life (parity about 0.9 yr) are outside the sourced ranges, "
                              "so they do not decide the ranking; selectivity requirement 12,919 is below all sourced ideal values",
                 "reason": "the ranking is decided by an unsourced PSA recovery; readiness also differs: Pd-Ag downstream "
                           "separator TRL 4 to 5 against PSA unit 9 / integrated chain 6 to 7; Ammogen did not meet its "
                           "recovery KPI. Secondary row, does not vote"},
        "H4-e": {"proposed_verdict": "SUPPORTED",
                 "numbers": {"furnace_demand_kW": to["furnace_demand_kW"],
                             "recovery_where_tail_heat_equals_demand": to["psa_recovery_where_tail_heat_equals_furnace_demand"],
                             "psa_0.85_net_deficit_kW": B["configurations"]["PSA_high_recovery"]["energy"]["net_heat_deficit_kW"],
                             "membrane_0.90_imported_heat_kWh_per_kg": D["configurations"]["MEM_central"]["energy"]["imported_heat_kWh_per_kg_h2"]},
                 "assumptions": "tail gas or retentate burned in the cracker furnace with the baseline furnace model; surplus not credited",
                 "uncertainty": "computed for recoveries 0.50-0.95 (PSA and membrane trade-off grids)",
                 "envelope": "20 bar baseline; above recovery %.3f the tail gas does not cover the furnace and NH3 is burned; "
                             "below it the lost H2 has no use in this flowsheet" % to["psa_recovery_where_tail_heat_equals_furnace_demand"],
                 "threshold": to["psa_recovery_where_tail_heat_equals_furnace_demand"],
                 "reason": "computed energy balance; holds for both technologies (same threshold, since it depends only on the "
                           "H2 sent to the furnace)"},
    }


# ------------------------------------------------------------------------------------------ main
def main():
    apply_style()
    cv = central_vals()
    comp = {"provenance": {**ps.prov("python", "Phase 2 D2: PSA against Pd-Ag membrane on the unified reference basis; "
                                     "low/central/high from sourced inputs (purification_literature.json)"), "script": SCRIPT},
            "basis": {"economics": "amcrax.economics.singapore.evaluate on results/simulations/baseline.json (reference "
                                   "scenario, capex_mode reference), through scripts/research/purification_study.py cost functions",
                      "baseline_lcoh_usd": ps.ECON["lcoh_USD_per_kg"],
                      "baseline_lcoh_sgd": ps.ECON["lcoh_SGD_per_kg"],
                      "baseline_note": "plant gate, 19.5 bar, PSA at the 0.85 assumption; the purification LCOH values add "
                                       "delivery compression and recompute imported heat for each configuration",
                      "fx_SGD_per_USD": FX, "fx_date": REF.fx_date, "usd_per_eur": USD_PER_EUR,
                      "nh3_price_USD_per_t": ps.NH3_PRICE,
                      "boundary": "same plant (20 bar Aspen baseline cracked gas), same furnace, same delivery pressure per "
                                  "specification (30 bar industrial, 350 bar Grade D); purification CAPEX + maintenance, membrane "
                                  "replacement, product compression electricity and imported heat change per configuration",
                      "lcoh_definition": "USD per kg of usable H2 (product meets the specification within model scope)",
                      "not_modelled": ["TSA regeneration heat", "PSA own power (no verified source)", "compression CAPEX",
                                       "membrane housing, skid and heating CAPEX", "NH3 inhibition and ageing of Pd-Ag",
                                       "concentration polarisation (stress test only)", "heat-integration effect of a hot membrane"],
                      "lower_bound_note": "unmodelled items add cost mainly to the membrane (housing, skid) and to PSA (TSA heat)"},
            "inputs": INPUTS, "specs": {}}
    flat = []
    fact = {}
    for spec, S in SPECS.items():
        psa_rows, mem_rows = run_factorial(spec)
        fact[spec] = (psa_rows, mem_rows)
        entry = {"label": S["label"], "configurations": {}}
        for lvl in ("low", "central", "high"):
            R = INPUTS["psa_recovery"][spec][lvl]["value"]
            cfg = psa_cfg(spec, R)
            c = cost(cfg, spec, elec=cv["elec"])
            d = describe(cfg, c, spec, {"psa_recovery": R, "psa_capex_basis": "amcrax_split", "electricity": cv["elec"]})
            d["readiness"] = readiness("psa", False)
            d["recovery_source"] = INPUTS["psa_recovery"][spec][lvl]
            entry["configurations"][f"PSA_{lvl}_recovery"] = d
        for lvl, mc, life, a, f, R in (
                ("cost_low", INPUTS["membrane_cost_USD_per_m2"]["low"]["value"], 5.0, 500000.0, 1.0, 0.90),
                ("central", cv["mcost"], cv["life"], cv["alpha"], 1.0, cv["Rm"]),
                ("cost_high", 15000.0, 2.0, SEL_PRINTED, 0.60 / 0.74, 0.86)):
            cfg = mem_cfg(spec, R, a, f)
            c = cost(cfg, spec, **mem_kw(mc, life, cv["elec"]))
            d = describe(cfg, c, spec, {"membrane_cost_USD_per_m2": mc, "membrane_life_yr": life, "alpha_H2_N2": a,
                                        "flux_multiplier": f, "recovery": R, "permeate_bar": 1.0, "electricity": cv["elec"],
                                        "nh3_polishing_bed": S["membrane_polish"]})
            d["readiness"] = readiness("membrane", S["membrane_polish"])
            entry["configurations"][f"MEM_{lvl}"] = d
        for k, d in entry["configurations"].items():
            flat.append({"spec": spec, "config": k, "purity": d["h2_purity_mole_frac"], "n2_ppm": d["n2_ppm"],
                         "recovery": d["h2_recovery"], "compression_kWh_per_kg": d["energy"]["compression_kWh_per_kg_h2"],
                         "imported_heat_kWh_per_kg": d["energy"]["imported_heat_kWh_per_kg_h2"], "capital_USD": d["capital_USD"],
                         "membrane_area_m2": d["membrane_area_m2"], "replacement_USD_per_yr": d["replacement_USD_per_yr"],
                         "lcoh_usd": d["lcoh_usd_per_kg_usable"], "lcoh_sgd": d["lcoh_sgd_per_kg_usable"],
                         "trl": d["readiness"]["trl"]})
        entry["factorial_summary"] = summarise(spec, psa_rows, mem_rows)
        entry["one_at_a_time"] = oat(spec)
        entry["thresholds"] = thresholds(spec)
        entry["factorial_counts"] = {"psa": len(psa_rows), "membrane": len(mem_rows)}
        comp["specs"][spec] = entry
    sens_rows, sens_pts = psa_recovery_sensitivity()
    comp["psa_recovery_sensitivity"] = {"points": sens_pts, "csv": "results/research/purification/phase2_psa_recovery_sensitivity.csv"}
    psa_t, mem_t, h4e = tradeoffs()
    comp["tradeoff"] = {"psa_csv": "results/research/purification/phase2_tradeoff_psa.csv",
                        "membrane_csv": "results/research/purification/phase2_tradeoff_membrane.csv", **h4e,
                        "computed": ["energy (compression, tail-gas heat, net heat deficit) and cost for a GIVEN recovery and purity",
                                     "membrane recovery-area-N2 leakage-purity at a sourced ideal selectivity (Sieverts model)",
                                     "recovery at which tail-gas heat covers the furnace demand"],
                        "assumed": ["PSA recovery as a function of purity (mass-balance relation flat by construction; Yanez "
                                    "line is literature for a different feed, extrapolated outside 99.25-99.97 %)",
                                    "membrane permeability fit (Richard 2024), isothermal, no NH3 inhibition, no ageing",
                                    "tail gas burned in the cracker furnace; surplus heat not credited"]}
    comp["selectivity_statement"] = {
        "phase1": "the base model assumes infinite selectivity and no numeric selectivity is available in the library",
        "phase2": ("Required ideal H2/N2 selectivity for Grade D (N2 300 ppm, R 0.90, 1 bar permeate, 400 degC): "
                   f"{comp['specs']['fuel_cell_grade_D']['thresholds']['selectivity']['required_alpha_H2_N2']:.0f}. "
                   "Sourced: Cechetto et al. 2021 state above 400,000 (double sealed) and above 500,000 (dead end) at 450 degC; "
                   f"the printed double-sealed N2 permeance gives about {SEL_PRINTED:,.0f}. The requirement is met by every "
                   "sourced value, but only as ideal (single-gas) values of NEW membranes from one group, at 450 degC, with "
                   "trace NH3 only; mixed-gas and aged selectivity were not found (a review excerpt reporting decay 6000 -> 4300 "
                   "and 4300 -> 1000 in about 1000 h could not be opened and is not used)."),
        "nus_researchers": ("NUS has strong membrane-science groups (Zhang Sui, Zhao Dan) whose published gas-separation work is "
                            "on non-metallic membranes at low temperature and does not address cracked-ammonia purification. "
                            "No number from their work is used in AmCraX and no specific work is attributed to them here "
                            "(research/notes/nus_membrane_researchers.md)")}
    comp["h4b_purity_cost_check"] = h4b_check(fact)
    comp["row_evidence"] = row_evidence(comp)
    json.dump(ps._clean(comp), open(OUT / "phase2_comparison.json", "w", encoding="utf-8"), indent=1,
              default=lambda o: o.item() if hasattr(o, "item") else str(o))
    ps._csv(OUT / "phase2_comparison.csv", flat)
    ps._csv(OUT / "phase2_psa_recovery_sensitivity.csv", sens_rows)
    ps._csv(OUT / "phase2_tradeoff_psa.csv", psa_t)
    ps._csv(OUT / "phase2_tradeoff_membrane.csv", mem_t)
    figures(comp, sens_rows, sens_pts, psa_t, mem_t)
    validation(comp, mem_t)
    print(json.dumps({s: comp["specs"][s]["factorial_summary"] for s in SPECS}, indent=1, default=str))
    print(json.dumps({s: comp["specs"][s]["thresholds"] for s in SPECS}, indent=1, default=str))
    print(json.dumps(comp["psa_recovery_sensitivity"]["points"], indent=1, default=str))
    print(json.dumps(h4e, indent=1))


# ------------------------------------------------------------------------------------------ figures
def figures(comp, sens_rows, sens_pts, psa_t, mem_t):
    foot = "python reduced-order models on Aspen Plus V15 cracked gas; unified reference scenario"
    # 1 comparison: central with low-high envelope
    fig, axs = plt.subplots(1, 2, figsize=(10, 4.4), sharey=False)
    for ax, (spec, e) in zip(axs, comp["specs"].items()):
        fs = e["factorial_summary"]
        names = ["PSA + TSA", "Pd-Ag membrane" + (" + NH3 polish" if SPECS[spec]["membrane_polish"] else "")]
        cen = [fs["central"]["psa"], fs["central"]["membrane"]]
        lo = [fs["psa_range"][0], fs["membrane_range"][0]]
        hi = [fs["psa_range"][1], fs["membrane_range"][1]]
        y = np.arange(2)
        for i, col in enumerate((C_PRIMARY, C_HEAT)):
            ax.plot([lo[i], hi[i]], [y[i], y[i]], color=col, lw=6, alpha=0.35, solid_capstyle="round")
            ax.plot(cen[i], y[i], "o", color=col, ms=9)
            ax.text(hi[i] + 0.02, y[i], f"{cen[i]:.2f} ({lo[i]:.2f}-{hi[i]:.2f})", va="center", fontsize=7.5)
        trl = ["TRL " + e["configurations"]["PSA_central_recovery"]["readiness"]["trl"].split(";")[0].replace("PSA unit operation ", "unit "),
               "TRL " + e["configurations"]["MEM_central"]["readiness"]["trl"]]
        ax.set_yticks(y)
        ax.set_yticklabels([f"{n}\n{t}" for n, t in zip(names, trl)], fontsize=7.5)
        ax.set_xlabel("LCOH, USD/kg usable H2 (dot central; bar sourced range)")
        ax.set_title(SPECS[spec]["label"], fontsize=9)
        ax.set_ylim(-0.6, 1.6)
        ax.set_xlim(min(lo) - 0.1, max(hi) + 0.6)
    fig.suptitle("PSA against Pd-Ag membrane on the unified basis (20 bar baseline, grey NH3 450 USD/t)", fontsize=10)
    add_provenance(fig, foot + "; ranges: factorial over sourced inputs; housing/skid, TSA heat not modelled")
    fig.tight_layout(rect=(0, 0.05, 1, 0.95))
    fig.savefig(FIG / "purification_phase2_comparison.png", dpi=200)
    plt.close(fig)
    # 2 PSA recovery sensitivity
    fig, axs = plt.subplots(1, 2, figsize=(10, 4.2))
    for ax, spec in zip(axs, SPECS):
        rr = [r for r in sens_rows if r["spec"] == spec]
        ax.plot([r["recovery"] * 100 for r in rr], [r["lcoh_usd"] for r in rr], color=C_PRIMARY, lw=2, label="PSA + TSA")
        mc = comp["specs"][spec]["factorial_summary"]["central"]["membrane"]
        ax.axhline(mc, color=C_HEAT, lw=1.5, ls="--", label="Pd-Ag membrane, central")
        for name, p in sens_pts[spec].items():
            ax.plot(p["recovery"] * 100, p["lcoh_usd"], "o", ms=8, color=C_AMBER if "yanez" in name else C_GREY)
            ax.annotate(p["label"].split(",")[0] + (" (different feed)" if "yanez" in name else ""),
                        (p["recovery"] * 100, p["lcoh_usd"]), textcoords="offset points", xytext=(4, 5), fontsize=6.5)
        ax.set_xlabel("PSA H2 recovery (%)")
        ax.set_ylabel("LCOH, USD/kg usable H2")
        ax.set_title(SPECS[spec]["label"], fontsize=9)
        ax.legend(fontsize=7, loc="upper right")
    add_provenance(fig, foot + "; recovery is an input (no adsorption-cycle model)")
    fig.tight_layout(rect=(0, 0.05, 1, 1))
    fig.savefig(FIG / "purification_phase2_psa_recovery.png", dpi=200)
    plt.close(fig)
    # 3 trade-off: 2 x 2
    fig, axs = plt.subplots(2, 2, figsize=(10, 7.6))
    for rel, col, ls in (("mass_balance_relation_assumption", C_PRIMARY, "-"), ("yanez2020_linear_different_feed", C_AMBER, "--")):
        rr = [r for r in psa_t if r["relation"] == rel]
        lab = "PSA, mass-balance relation (assumption)" if rel.startswith("mass") else "PSA, Yanez 2020 line (different feed)"
        axs[0, 0].plot([r["purity"] * 100 for r in rr], [r["recovery"] * 100 for r in rr], color=col, ls=ls, label=lab)
        axs[1, 0].plot([r["recovery"] * 100 for r in rr], [r["cost_usd_per_kg_30bar"] for r in rr], color=col, ls=ls, label=lab)
        axs[1, 1].plot([r["recovery"] * 100 for r in rr], [r["net_heat_deficit_kW"] for r in rr], color=col, ls=ls, label=lab)
    for a, col, ls in ((SEL_PRINTED, C_N2, "-"), (400000.0, C_HEAT, "-.")):
        rr = [r for r in mem_t if r["alpha"] == a]
        lab = f"Pd-Ag, ideal H2/N2 {a:,.0f}"
        axs[0, 1].plot([r["recovery"] * 100 for r in rr], [r["n2_ppm"] for r in rr], color=col, ls=ls, label=lab)
        axs[1, 0].plot([r["recovery"] * 100 for r in rr], [r["cost_usd_per_kg_30bar"] for r in rr], color=col, ls=ls, label=lab)
        if a == 400000.0:
            axs[1, 1].plot([r["recovery"] * 100 for r in rr], [r["net_heat_deficit_kW"] for r in rr], color=col, ls=ls, label="Pd-Ag")
    axs[0, 0].axvline(99.9, color=C_GREY, lw=0.7, ls=":")
    axs[0, 0].axvline(99.97, color=C_GREY, lw=0.7, ls=":")
    axs[0, 0].set_xlabel("PSA product purity (mol % H2)")
    axs[0, 0].set_ylabel("H2 recovery (%)")
    axs[0, 0].set_title("Purity vs recovery, PSA (assumed or literature)", fontsize=9)
    axs[0, 1].axhline(300, color=C_GREY, lw=0.7, ls=":")
    axs[0, 1].text(51, 310, "Grade D N2 limit 300 ppm", fontsize=7)
    axs[0, 1].set_xlabel("Membrane H2 recovery (%)")
    axs[0, 1].set_ylabel("N2 in permeate (ppm)")
    axs[0, 1].set_title("Recovery vs purity, Pd-Ag (computed at sourced selectivity)", fontsize=9)
    axs[1, 0].set_xlabel("H2 recovery (%)")
    axs[1, 0].set_ylabel("USD/kg product H2, 30 bar")
    axs[1, 0].set_title("Recovery vs cost (computed for a given recovery)", fontsize=9)
    axs[1, 1].set_xlabel("H2 recovery (%)")
    axs[1, 1].set_ylabel("Imported furnace heat (kW)")
    axs[1, 1].set_title("Recovery vs energy: tail gas offsets furnace fuel (computed)", fontsize=9)
    for ax in axs.flat:
        ax.legend(fontsize=6.5)
    fig.suptitle("H4-B trade-offs: purity, recovery, energy, cost (20 bar baseline)", fontsize=10)
    add_provenance(fig, foot + "; PSA purity-recovery relation is NOT computed")
    fig.tight_layout(rect=(0, 0.03, 1, 0.96))
    fig.savefig(FIG / "purification_phase2_tradeoff.png", dpi=200)
    plt.close(fig)


# ------------------------------------------------------------------------------------------ validation
def validation(comp, mem_t):
    items = []

    def add(id_, desc, method, ref, obs, exp, tol, unit, status, kind, files):
        items.append({"id": id_, "description": desc, "method": method, "reference_source": ref, "observed": obs,
                      "expected": exp, "tolerance": tol, "unit": unit, "status": status, "evidence_kind": kind,
                      "source_files": files})

    SF = ["results/research/purification/phase2_comparison.json"]
    # 1 SGD = USD x FX for every configuration
    worst = 0.0
    for e in comp["specs"].values():
        for d in e["configurations"].values():
            if d["lcoh_usd_per_kg_usable"] is not None:
                worst = max(worst, abs(d["lcoh_sgd_per_kg_usable"] - d["lcoh_usd_per_kg_usable"] * FX))
    add("P2-FX-1", "SGD LCOH equals USD LCOH x 1.288444 for every Phase 2 configuration", "max absolute difference",
        "reference scenario fx_SGD_per_USD", worst, 0.0, 1e-9, "SGD/kg", "pass" if worst <= 1e-9 else "fail",
        "numerical_verification", SF)
    # 2 reproduction of the Phase 1 configurations on the same basis (same functions, same inputs)
    st = json.loads((OUT / "purification_study.json").read_text(encoding="utf-8"))
    p1 = {c["id"]: c for c in st["cases"]["20bar_baseline"]["configs"]}
    cv = central_vals()
    mem_p1 = lcoh_mem("fuel_cell_grade_D", ps.MEM_EUR_PER_M2 * ps.EURUSD_PARITY, 3.0, cv["elec"], alpha=math.inf)
    ref = p1["MEM_1bar_polish"]["costs"]["fuel_cell_grade_D"]["usd_per_kg_usable_h2"]
    add("P2-REP-1", "Phase 2 code path reproduces the stored MEM_1bar_polish Grade D LCOH when given the Phase 1 inputs "
        "(6000 EUR/m2, 3 yr, infinite selectivity)", "recompute through purification_phase2 helpers",
        "results/research/purification/purification_study.json", mem_p1, ref, 1e-9, "USD/kg",
        "pass" if abs(mem_p1 - ref) <= 1e-9 else "fail", "numerical_verification", SF)
    psa_p1 = lcoh_psa("fuel_cell_grade_D", p1["PSA_D_MB"]["h2_recovery"], cv["elec"])
    ref2 = p1["PSA_D_MB"]["costs"]["fuel_cell_grade_D"]["usd_per_kg_usable_h2"]
    add("P2-REP-2", "Phase 2 code path reproduces the stored PSA_D_MB Grade D LCOH", "recompute",
        "purification_study.json", psa_p1, ref2, 1e-9, "USD/kg", "pass" if abs(psa_p1 - ref2) <= 1e-9 else "fail",
        "numerical_verification", SF)
    # 3 linearity of membrane cost (parity threshold method)
    th = comp["specs"]["fuel_cell_grade_D"]["thresholds"]["central"]
    chk = lcoh_mem("fuel_cell_grade_D", th["membrane_cost_USD_per_m2_at_parity"], cv["life"], cv["elec"])
    add("P2-THR-1", "Membrane cost at parity (Grade D, PSA central recovery) gives LCOH equal to the PSA LCOH",
        "re-evaluate at the solved cost", "internal consistency", chk, th["psa_lcoh_usd"], 1e-9, "USD/kg",
        "pass" if abs(chk - th["psa_lcoh_usd"]) <= 1e-9 else "fail", "numerical_verification", SF)
    # 4 N2 leakage monotone in recovery at fixed selectivity
    rr = sorted([r for r in mem_t if r["alpha"] == 400000.0], key=lambda r: r["recovery"])
    mono = all(b["n2_ppm"] >= a["n2_ppm"] for a, b in zip(rr, rr[1:]))
    add("P2-MEM-1", "At fixed ideal selectivity, permeate N2 rises with recovery (more area, lower H2 driving force)",
        "monotonicity over the trade-off grid", "physical expectation (python)", mono, True, None, "-",
        "pass" if mono else "fail", "numerical_verification", ["results/research/purification/phase2_tradeoff_membrane.csv"])
    # 5 sourced selectivity vs requirement (literature comparison)
    s = comp["specs"]["fuel_cell_grade_D"]["thresholds"]["selectivity"]
    add("P2-SEL-1", "Required ideal H2/N2 for Grade D N2 300 ppm against the sourced Cechetto 2021 values",
        "required value from required_selectivity at R 0.90, 1 bar, 400 degC; sourced: 40,500 (printed permeances), "
        "400,000 (stated), 500,000 (dead end); ideal, new membrane, 450 degC", "cechetto2021fpt Sec. 3.1 p. 4",
        s["required_alpha_H2_N2"], [s["sourced_low"], s["sourced_central"], s["sourced_high"]], None, "-",
        "informational", "literature_comparison", SF)
    # 6 Cechetto internal consistency (dead end): 1.5e-6 / 3e-12 = 5e5
    add("P2-SEL-2", "Cechetto 2021 dead-end ratio of printed permeances reproduces the stated selectivity above 500,000",
        "1.5e-6 / 3e-12", "cechetto2021fpt Sec. 3.1 p. 4", 1.5e-6 / 3e-12, 500000.0, 1e-6 * 500000.0, "-",
        "pass" if abs(1.5e-6 / 3e-12 - 5e5) <= 0.5 else "fail", "literature_comparison", [])
    add("P2-SEL-3", "Cechetto 2021 double-sealed ratio of printed permeances against the stated selectivity above 400,000",
        "1.5e-6 / 3.7e-11 (printed exponent -11)", "cechetto2021fpt Sec. 3.1 p. 4", SEL_PRINTED, 400000.0, None, "-",
        "informational", "literature_comparison", [])
    # 7 PSA against Yanez: no AmCraX PSA model to compare (stated, not passed)
    add("P2-PSA-1", "PSA recovery at Grade D against Yanez 2020 (55.5 % at 99.97 %)",
        "not a validation: AmCraX has no adsorption-cycle model; the Yanez point is a different feed (purge gas). Reported "
        "as a pessimistic input case only", "yanez2020", INPUTS["psa_recovery"]["fuel_cell_grade_D"]["central"]["value"],
        0.555, None, "-", "informational", "literature_comparison", [])
    f = VAL / "purification.json"
    old = json.loads(f.read_text(encoding="utf-8")) if f.exists() else []
    old = [i for i in old if not str(i.get("id", "")).startswith("P2-")]
    json.dump(ps._clean(old + items), open(f, "w", encoding="utf-8"), indent=1)


if __name__ == "__main__":
    main()
