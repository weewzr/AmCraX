"""Phase 2 task C2: catalyst economics for hypothesis H3 (catalyst cost against energy and heat-integration savings).

Deterministic; run from the project root after scripts/research/catalyst_comparison.py:
    python scripts/research/catalyst_economics.py
Writes results/research/catalyst_economics/*.json/.csv, results/research/validation/catalyst_economics.json and
results/figures/research/catalyst_econ_*.png. Method: backend/amcrax/research/catalyst_economics.py.
"""
from __future__ import annotations

import csv
import json
import math
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))

import matplotlib  # noqa: E402

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from scipy.optimize import brentq  # noqa: E402

from amcrax.economics.reference import provenance_stamp, reference_capex, reference_catalyst_mass_kg, reference_item_costs  # noqa: E402
from amcrax.economics.singapore import evaluate  # noqa: E402
from amcrax.plotstyle import C_GREY, PALETTE, apply_style  # noqa: E402
from amcrax.research import catalyst_comparison as cc  # noqa: E402
from amcrax.research import catalyst_economics as ce  # noqa: E402
from amcrax.schemas import SimulationResult  # noqa: E402

SCRIPT = "scripts/research/catalyst_economics.py"
OUT = ROOT / "results" / "research" / "catalyst_economics"
FIG = ROOT / "results" / "figures" / "research"
VAL = ROOT / "results" / "research" / "validation"
ASP = ROOT / "results" / "research" / "aspen_kinetic"
CMP = ROOT / "results" / "research" / "catalyst_comparison"
for d in (OUT, FIG, VAL):
    d.mkdir(parents=True, exist_ok=True)
NOW = datetime.now(timezone.utc).isoformat(timespec="seconds")
NI = cc.REFERENCE_NI
LOW = ce.LOW_T
SH = {c: cc.CATALYSTS[c]["short"] for c in cc.CATALYSTS}
LIFE = sorted(ce.LIFETIMES_YR)
PRICE_CASES = ("low", "central", "high", "published_TEA")
ASPEN_CASES = {"ru_kum_temkin_pyzhev": "kum_T499", "nire_ceo2_5ni1ru_lucentini_lhhw": "luc5_T572",
               "nire_ceo2_2p5ni0p5ru_lucentini_lhhw": "luc25_T576", "ni_takahashi_microkinetic": "tni_T594",
               "ru_takahashi_microkinetic": "tru_T522"}
VALIDATED = [c for c in cc.CATALYSTS if cc.kinetic_validity(c)["kinetic_validity_class"] == "validated_against_literature"]
FOOT = ("AmCraX Phase 2 task C2 | prices: research/data/catalyst_prices.json (DERIVED, no quotation) | economics: "
        "amcrax.economics.singapore (reference scenario) | kinetics: python PFR, all laws extrapolated to 20 bar")
items: list[dict] = []


def add(id_, desc, kind, observed, expected, tol, unit, status, files, note=""):
    items.append({"id": id_, "description": desc, "evidence_kind": kind, "observed": observed, "expected": expected,
                  "tolerance": tol, "unit": unit, "status": status, "source_files": files, **({"note": note} if note else {})})


def clean(o):
    if isinstance(o, dict):
        return {str(k): clean(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [clean(v) for v in o]
    if hasattr(o, "item") and not isinstance(o, (str, bytes)):
        o = o.item()
    if isinstance(o, float) and (o != o or o in (float("inf"), float("-inf"))):
        return None
    return o


def prov(what: str) -> dict:
    return {"generated_utc": NOW, "script": SCRIPT, "source_type": "python", "inputs_summary": what,
            "reference_scenario": provenance_stamp(),
            "inputs": {"prices": cc.PRICE_FILE_REL, "kinetic_validity": cc.VALIDITY_FILE_REL,
                       "exchanger": "amcrax.heat_integration.exchanger (task X1)",
                       "aspen": "results/research/aspen_kinetic/ci_*_P20_W100_{hi,nohi}.json (Aspen Plus V15, stored)",
                       "cho_rebuild": "results/research/catalyst_comparison/catalyst_cho_comparison.json"},
            "evidence_kind_note": "economic model results; not validation evidence. No experimental validation exists."}


def dump(name, obj):
    (OUT / name).write_text(json.dumps(clean(obj), indent=2, allow_nan=False), encoding="utf-8")


def write_csv(name, rows):
    keys: list[str] = []
    for r in rows:
        for k in r:
            if k not in keys:
                keys.append(k)
    with open(OUT / name, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=keys)
        w.writeheader()
        for r in rows:
            w.writerow({k: (json.dumps(clean(v)) if isinstance(v, (dict, list)) else clean(v)) for k, v in r.items()})


def pc(cid: str, case: str) -> float:
    return cc.PUBLISHED_TEA_PRICE[cid] if case == "published_TEA" else ce.price(cc.CATALYSTS[cid]["price_key"], case)


def slim(d: dict) -> dict:
    keys = ("catalyst", "T_C", "W_kg", "heat_integration", "lcoh_USD_per_kg", "lcoh_SGD_per_kg", "rec_USD_per_kg",
            "fired_process_duty_kW", "supplementary_nh3_kg_h", "first_law_deficit_kW", "flowsheet_source", "mode", "U_case",
            "kinetic_validity_class", "kinetic_result_label", "at_grid_bound")
    o = {k: d.get(k) for k in keys}
    o["fehe_area_m2"] = d["fehe"]["area_m2"]
    o["fehe_tci_USD"] = d["fehe"]["tci_equivalent_USD"]
    o["reactor_tci_USD"] = d["tci_by_item_USD"]["reactor"]
    o["heat_exchangers_item_tci_USD"] = d["tci_by_item_USD"]["heat_exchangers"]
    o["catalyst_USD_per_kg_H2"] = d["catalyst_cost"]["USD_per_kg_H2"]
    o["catalyst_price_USD_per_kg"] = d["catalyst_cost"]["price_USD_per_kg"]
    o["catalyst_lifetime_yr"] = d["catalyst_cost"]["lifetime_yr"]
    o["breakdown_USD_per_kg"] = d["breakdown_USD_per_kg"]
    return o


def load_aspen(cid: str, hi: bool) -> SimulationResult:
    fn = ASP / f"ci_{ASPEN_CASES[cid]}_P20_W100_{'hi' if hi else 'nohi'}.json"
    return SimulationResult.model_validate(json.loads(fn.read_text(encoding="utf-8"))["aspen"]["flowsheet_result"])


def h3a_envelope(fx_hi: dict, fx_no: dict, co_ex: dict, resolution: dict) -> str:
    """H3-a envelope text, computed (fix pass 24 Nov 2026: reviews A M3/m5 and C M2). One temperature value only
    (the smallest resolved difference), both resolution readings, the size on two metrics, the cost-optimal reversal."""
    kpis = json.loads((ROOT / "results/simulations/baseline.json").read_text(encoding="utf-8"))["kpis"]
    ext = kpis["total_external_heating_kW"]
    res_kw, spr_kw = resolution["max_abs_fired_duty_offset_kW"], resolution["spread_of_fired_duty_offset_between_catalysts_kW"]
    res_usd, spr_usd = resolution["max_abs_python_minus_aspen_lcoh_USD_per_kg"], resolution["spread_of_offset_between_catalysts_USD_per_kg"]
    best_k = max(fx_hi, key=lambda k: fx_hi[k]["energy_saving_fired_duty_kW"])
    best = fx_hi[best_k]
    s_max = best["energy_saving_fired_duty_kW"]
    resolved = {k: v for k, v in fx_hi.items() if v["energy_saving_fired_duty_kW"] > res_kw}
    unresolved = {k: v for k, v in fx_hi.items() if v["energy_saving_fired_duty_kW"] <= res_kw}
    dT_min = min(v["ref_T_C"] - v["low_T_C"] for v in resolved.values()) if resolved else None
    res_txt = ", ".join(f"{k} {v['energy_saving_fired_duty_kW']:.1f} kW at {v['low_T_C']:.0f} degC" for k, v in
                        sorted(resolved.items(), key=lambda kv: kv[1]["energy_saving_fired_duty_kW"]))
    unres = [v["energy_saving_fired_duty_kW"] for v in unresolved.values()]
    co_ru = [v["energy_saving_fired_duty_kW"] for k, v in co_ex.items() if k.startswith("Ru")]
    no = [v["energy_saving_fired_duty_kW"] for v in fx_no.values()]
    return (f"20 bar, X 0.95 (equal conversion; Python only, the Aspen runs reach unequal conversion), "
            f"{min(v['low_T_C'] for v in fx_hi.values()):.0f}-{best['ref_T_C']:.0f} degC, with and without FEHE. With FEHE the "
            f"largest saving is {s_max:.1f} kW ({best_k}), which is {100 * s_max / best['ref_fired_process_duty_kW']:.1f} % of the "
            f"supplementary fired duty and {100 * s_max / ext:.1f} % of the {ext:.0f} kW total external heating. On the "
            f"absolute Python-Aspen offset ({res_kw:.1f} kW; {res_usd:.4f} USD/kg), the reading used for the verdicts, the saving "
            f"is resolved only for temperature differences of {dT_min:.0f} K or more ({res_txt}); the NiRu/CeO2 savings "
            f"({min(unres):.1f}-{max(unres):.1f} kW) are not. On the spread of that offset across catalysts ({spr_kw:.1f} kW; "
            f"{spr_usd:.4f} USD/kg) the NiRu savings would also be resolved. Without FEHE {min(no):.0f}-{max(no):.0f} kW. When "
            f"the designs are cost-optimised (exchanger mode, derived central prices) the Ru designs run hotter and use "
            f"{-max(co_ru):.0f}-{-min(co_ru):.0f} kW MORE energy. The direction is kinetics-independent; WHICH catalyst reaches "
            f"which T rests on extrapolated laws (Ru/MgO and the Ni reference).")


def main() -> None:
    t0 = time.time()
    apply_style()
    files_p = [cc.PRICE_FILE_REL]
    # ============================================================ 0. frozen basis check
    base_lcoh = json.loads((ROOT / "results/research/reference_scenario/baseline.json").read_text(encoding="utf-8"))
    stored = base_lcoh.get("lcoh_USD_per_kg") or base_lcoh.get("baseline", {}).get("lcoh_USD_per_kg")
    e0 = evaluate(json.loads((ROOT / "results/simulations/baseline.json").read_text(encoding="utf-8")), "grey")
    add("CE-FROZEN-BASELINE", "Default singapore.evaluate on the stored baseline is unchanged by this task (frozen basis)",
        "numerical_verification", e0["lcoh_USD_per_kg"], stored, 1e-9, "USD/kg H2",
        "pass" if stored is not None and abs(e0["lcoh_USD_per_kg"] - stored) <= 1e-9 else "fail",
        ["results/research/reference_scenario/baseline.json"])
    add("CE-FX", "SGD conversion uses the one reference rate (reference_scenario.yaml), not the 1.2801 of the price file",
        "numerical_verification", ce.FX, 1.288444, 1e-9, "SGD/USD", "pass" if abs(ce.FX - 1.288444) < 1e-9 else "fail",
        ["backend/amcrax/data/reference_scenario.yaml"])

    # ============================================================ 1. prices
    ptab = ce.price_table()
    tea = ce.published_tea_prices()
    for r in ptab:
        for sc in cc.PRICE_SCENARIOS:
            v = r[sc]
            add(f"CE-PRICE-{r['catalyst']}-{sc}", "Derived price recomputed from metal prices, loadings and N equals the price-file value",
                "numerical_verification", v["USD_per_kg"], v["price_file_USD_per_kg"], 0.01, "USD/kg catalyst",
                "pass" if abs(v["USD_per_kg"] - v["price_file_USD_per_kg"]) <= 0.01 else "fail", files_p)
    dump("catalyst_prices_sgd.json", {"provenance": prov("derived catalyst prices recomputed in SGD at the reference FX"),
                                      "fx_SGD_per_USD": ce.FX, "usd_per_eur": ce.USD_PER_EUR,
                                      "fx_note": "Reference scenario rate (ECB 20 Nov 2026). The 1.2801 SGD/USD of "
                                                 "research/data/catalyst_prices.json is superseded for conversion; its "
                                                 "SGD values are kept as price_file_SGD_per_kg_superseded_fx.",
                                      "evidence_grade_note": "No grade A (quotation) or B (catalogue) price exists for any "
                                                             "ammonia-cracking catalyst. Metal part grade E, non-metal part "
                                                             "grade C-derived. 'low' is a metal-content floor.",
                                      "catalysts": ptab, "published_TEA_prices": tea,
                                      "lifetimes_yr": {str(k): v for k, v in ce.LIFETIMES_YR.items()}})

    # ============================================================ 2. catalyst cost per kg H2 and annual expenditure
    asp_state = {(c, hi): ce.state_from_result(load_aspen(c, hi)) for c in cc.CATALYSTS for hi in (True, False)}
    cost_rows = []
    opt_cache = {}
    for cid in cc.CATALYSTS:
        for case in PRICE_CASES:
            p = pc(cid, case)
            for L in LIFE:
                o = ce.optimise(cid, p, L, mode="reference")
                opt_cache[(cid, case, L, "reference")] = o
                fx = ce.design(cid, asp_state[(cid, True)]["T_C"], p, L, W_kg=100.0, mode="reference", st=asp_state[(cid, True)])
                cost_rows.append({
                    "catalyst_id": cid, "catalyst": SH[cid], "price_case": case,
                    "price_label": ("published TEA price (Cho 2026), NOT a current price" if case == "published_TEA" else
                                    "metal-content floor, NOT a market price" if case == "low" else f"derived {case}"),
                    "price_USD_per_kg": p, "price_SGD_per_kg": p * ce.FX, "lifetime_yr": L,
                    "lifetime_source": ce.LIFETIMES_YR[L]["source"],
                    "costopt_T_C": o["T_C"], "costopt_W_kg": o["W_kg"],
                    "costopt_catalyst_USD_per_kg_H2": o["catalyst_cost"]["USD_per_kg_H2"],
                    "costopt_catalyst_SGD_per_kg_H2": o["catalyst_cost"]["SGD_per_kg_H2"],
                    "costopt_annual_catalyst_USD_per_yr": o["catalyst_cost"]["annual_USD_per_yr"],
                    "costopt_annual_catalyst_SGD_per_yr": o["catalyst_cost"]["annual_SGD_per_yr"],
                    "costopt_charge_SGD": o["catalyst_cost"]["charge_SGD"],
                    "costopt_lcoh_USD_per_kg": o["lcoh_USD_per_kg"], "costopt_lcoh_SGD_per_kg": o["lcoh_SGD_per_kg"],
                    "costopt_at_grid_bound": o["at_grid_bound"],
                    "fixed100kg_T_C": fx["T_C"], "fixed100kg_catalyst_USD_per_kg_H2": fx["catalyst_cost"]["USD_per_kg_H2"],
                    "fixed100kg_catalyst_SGD_per_kg_H2": fx["catalyst_cost"]["SGD_per_kg_H2"],
                    "fixed100kg_annual_catalyst_USD_per_yr": fx["catalyst_cost"]["annual_USD_per_yr"],
                    "fixed100kg_annual_catalyst_SGD_per_yr": fx["catalyst_cost"]["annual_SGD_per_yr"],
                    "fixed100kg_lcoh_USD_per_kg": fx["lcoh_USD_per_kg"],
                    "economic_basis": "singapore.evaluate reference mode (frozen basis), grey 450 USD/t, HI on",
                    **ce.kinetics_label(cid)})
                if case == "central" and L == 2.0:
                    hand = 100.0 * p / L / fx["annual_h2_kg"]
                    add(f"CE-CATCOST-HAND-{SH[cid]}", "Catalyst cost per kg H2 = W p / (L H) (hand calculation) equals the "
                        "catalyst item of singapore.evaluate", "numerical_verification", fx["breakdown_USD_per_kg"]["catalyst"],
                        hand, 1e-12, "USD/kg H2", "pass" if abs(fx["breakdown_USD_per_kg"]["catalyst"] - hand) <= 1e-12 else "fail",
                        [SCRIPT])
    write_csv("catalyst_cost_table.csv", cost_rows)
    print("costs done", round(time.time() - t0))

    # ============================================================ 3. design comparisons against the Ni reference
    pcen = {c: pc(c, "central") for c in cc.CATALYSTS}
    comps = []

    def cmp_row(basis, low, ref, extra=None):
        c = ce.compare(low, ref)
        row = {"basis": basis, "low_catalyst_id": low["catalyst_id"], "ref_catalyst_id": ref["catalyst_id"],
               "mode": low["mode"], "U_case": low["U_case"], **c, "low_design": slim(low), "ref_design": slim(ref),
               "kinetics": ce.kinetics_label(low["catalyst_id"], ref["catalyst_id"]), **(extra or {})}
        add(f"CE-DECOMP-{basis}-{SH[low['catalyst_id']]}", "Decomposition of the LCOH difference sums to the net difference",
            "numerical_verification", c["decomposition_sum_check_USD_per_kg"], 0.0, 1e-9, "USD/kg H2",
            "pass" if abs(c["decomposition_sum_check_USD_per_kg"]) <= 1e-9 else "fail", [SCRIPT])
        comps.append(row)
        return row

    # 3a Aspen fixed inventory (100 kg each, each at its kinetic T_op)
    asp_designs = {}
    for mode in ("reference", "exchanger", "exchanger_reactor_mass"):
        for cid in cc.CATALYSTS:
            for hi in (True, False):
                asp_designs[(cid, hi, mode)] = ce.design(cid, asp_state[(cid, hi)]["T_C"], pcen[cid], 2.0, W_kg=100.0,
                                                         hi=hi, mode=mode, st=asp_state[(cid, hi)])
    hi_saving = {}
    for mode in ("reference", "exchanger"):
        for cid in cc.CATALYSTS:
            a, b = asp_designs[(cid, True, mode)], asp_designs[(cid, False, mode)]
            hi_saving[(cid, mode)] = {"catalyst": SH[cid], "mode": mode, "T_C": a["T_C"],
                                      "gross_saving_USD_per_kg": (b["breakdown_USD_per_kg"]["heat_fuel"] + b["breakdown_USD_per_kg"]["cooling_water"])
                                      - (a["breakdown_USD_per_kg"]["heat_fuel"] + a["breakdown_USD_per_kg"]["cooling_water"]),
                                      "net_saving_USD_per_kg": b["lcoh_USD_per_kg"] - a["lcoh_USD_per_kg"],
                                      "fired_duty_saving_kW": b["fired_process_duty_kW"] - a["fired_process_duty_kW"],
                                      "fehe_tci_USD": a["fehe"]["tci_equivalent_USD"], "source_type": "aspen (duties) + python (economics)"}
    for mode in ("reference", "exchanger", "exchanger_reactor_mass"):
        for cid in LOW:
            for hi in (True, False):
                cmp_row(f"aspen_fixed_100kg_{'HI' if hi else 'noHI'}_{mode}", asp_designs[(cid, hi, mode)],
                        asp_designs[(NI, hi, mode)],
                        {"source_type": "aspen (duties) + python (economics)",
                         "hi_saving_low_USD_per_kg": hi_saving.get((cid, mode), {}).get("net_saving_USD_per_kg"),
                         "hi_saving_ref_USD_per_kg": hi_saving.get((NI, mode), {}).get("net_saving_USD_per_kg"),
                         "h2_product_rel_diff": asp_designs[(cid, hi, mode)]["h2_product_kg_h"] / asp_designs[(NI, hi, mode)]["h2_product_kg_h"] - 1.0,
                         "caution": "Aspen runs reach unequal conversion with 100 kg (X 0.9496-0.9589): the per-kg feed and "
                                    "capital terms differ by the H2 output, not by the catalyst. Use the python_Top_X095 basis "
                                    "(equal X 0.95) for the cost comparison; this basis is the Aspen cross-check."})
    # 3a' same kinetic operating temperatures, EQUAL conversion 0.95 (Python flowsheet, W from the kinetics: 90-100 kg)
    py_designs = {}
    for mode in ("reference", "exchanger", "exchanger_reactor_mass"):
        for cid in cc.CATALYSTS:
            Tq = float(asp_state[(cid, True)]["T_C"])
            Wq = cc.required_mass_kg(cid, Tq, 20.0, 0.95)
            for hi in (True, False):
                py_designs[(cid, hi, mode)] = ce.design(cid, Tq, pcen[cid], 2.0, W_kg=Wq, hi=hi, mode=mode)
    for mode in ("reference", "exchanger", "exchanger_reactor_mass"):
        for cid in LOW:
            for hi in (True, False):
                lo, rf = py_designs[(cid, hi, mode)], py_designs[(NI, hi, mode)]
                cmp_row(f"python_Top_X095_{'HI' if hi else 'noHI'}_{mode}", lo, rf,
                        {"source_type": "python (flowsheet at kinetic X 0.95 and the Aspen operating temperatures)",
                         "h2_product_rel_diff": lo["h2_product_kg_h"] / rf["h2_product_kg_h"] - 1.0,
                         "hi_saving_low_USD_per_kg": None if not hi else py_designs[(cid, False, mode)]["lcoh_USD_per_kg"] - lo["lcoh_USD_per_kg"],
                         "hi_saving_ref_USD_per_kg": None if not hi else py_designs[(NI, False, mode)]["lcoh_USD_per_kg"] - rf["lcoh_USD_per_kg"]})
    # Python at the same T and X as the Aspen runs (resolution of the catalyst differences)
    res_rows = []
    for cid in cc.CATALYSTS:
        sa = asp_state[(cid, True)]
        Xa = load_aspen(cid, True).kpis.nh3_conversion
        sp = ce.state(float(sa["T_C"]), 20.0, round(float(Xa), 6), True)
        da = ce.design(cid, sa["T_C"], pcen[cid], 2.0, W_kg=100.0, mode="reference", st=sa)
        dp = ce.design(cid, sa["T_C"], pcen[cid], 2.0, W_kg=100.0, mode="reference", st=sp)
        res_rows.append({"catalyst": SH[cid], "T_C": sa["T_C"], "lcoh_aspen": da["lcoh_USD_per_kg"], "lcoh_python": dp["lcoh_USD_per_kg"],
                         "python_minus_aspen_USD_per_kg": dp["lcoh_USD_per_kg"] - da["lcoh_USD_per_kg"],
                         "fired_aspen_kW": da["fired_process_duty_kW"], "fired_python_kW": dp["fired_process_duty_kW"]})
    offs = [r["python_minus_aspen_USD_per_kg"] for r in res_rows]
    offs_kW = [r["fired_aspen_kW"] - r["fired_python_kW"] for r in res_rows]
    resolution = {"max_abs_python_minus_aspen_lcoh_USD_per_kg": max(abs(x) for x in offs),
                  "spread_of_offset_between_catalysts_USD_per_kg": max(offs) - min(offs),
                  "max_abs_fired_duty_offset_kW": max(abs(x) for x in offs_kW),
                  "spread_of_fired_duty_offset_between_catalysts_kW": max(offs_kW) - min(offs_kW), "rows": res_rows,
                  "rule": "verdict_methodology_v2: a difference smaller than the demonstrated Python-Aspen offset cannot "
                          "support or contradict a row. The absolute offset (conservative) is used as the resolution for the "
                          "verdicts. Both readings are reported (fix pass 24 Nov 2026, review C finding M2): the absolute offset, "
                          "and the spread of that offset across catalysts, which is the demonstrated uncertainty of a difference "
                          "between designs when the offset is common."}
    RES = resolution["max_abs_python_minus_aspen_lcoh_USD_per_kg"]
    add("CE-RESOLUTION", "Python vs Aspen LCOH at the same T, X, 100 kg (all five catalysts): demonstrated model offset",
        "python_vs_aspen", RES, None, None, "USD/kg H2", "informational",
        [f"results/research/aspen_kinetic/ci_{t}_P20_W100_hi.json" for t in ASPEN_CASES.values()],
        note=f"spread between catalysts {resolution['spread_of_offset_between_catalysts_USD_per_kg']:.5f} USD/kg")

    # 3b cost-optimal designs, each mode (both catalysts re-optimised)
    opt = {}
    for mode in ce.MODES:
        for cid in cc.CATALYSTS:
            opt[(cid, mode)] = opt_cache.get((cid, "central", 2.0, mode)) or ce.optimise(cid, pcen[cid], 2.0, mode=mode)
    for mode in ("exchanger_U_low", "exchanger_U_high"):
        u = mode.rsplit("_", 1)[1]
        for cid in cc.CATALYSTS:
            opt[(cid, mode)] = ce.optimise(cid, pcen[cid], 2.0, mode="exchanger", U_case=u)
    for mode in list(ce.MODES) + ["exchanger_U_low", "exchanger_U_high"]:
        for cid in LOW:
            lo, rf = opt[(cid, mode)], opt[(NI, mode)]
            st_l = ce.state(lo["T_C"], hi=False)
            st_r = ce.state(rf["T_C"], hi=False)
            m_ = lo["mode"]
            nl = ce.design(cid, lo["T_C"], pcen[cid], 2.0, W_kg=lo["W_kg"], hi=False, mode=m_, U_case=lo["U_case"], st=st_l)
            nr = ce.design(NI, rf["T_C"], pcen[NI], 2.0, W_kg=rf["W_kg"], hi=False, mode=m_, U_case=rf["U_case"], st=st_r)
            cmp_row(f"cost_optimal_{mode}", lo, rf, {"source_type": "python",
                                                     "low_is_lower_temperature": lo["T_C"] < rf["T_C"],
                                                     "hi_saving_low_USD_per_kg": nl["lcoh_USD_per_kg"] - lo["lcoh_USD_per_kg"],
                                                     "hi_saving_ref_USD_per_kg": nr["lcoh_USD_per_kg"] - rf["lcoh_USD_per_kg"]})
    print("comparisons done", round(time.time() - t0))

    # 3c Ni at fixed conventional / published design temperatures
    ni_fixed_T = {700.0: "conventional screening value (Phase 1 workstream H)", 735.52: "cho2026nickel optimised Ni design (24.34 bar)",
                  760.0: "mehr2026highcapacity Table 6 Ni/Al2O3 reactor outlet"}
    for Tn, src in ni_fixed_T.items():
        rf = ce.design(NI, Tn, pcen[NI], 2.0, mode="exchanger")
        for cid in LOW:
            cmp_row(f"vs_Ni_fixed_{Tn:g}C_exchanger", opt[(cid, "exchanger")], rf,
                    {"source_type": "python", "ni_temperature_source": src})

    # ============================================================ 4. break-even price, lifetime, recovery fraction
    be_rows = []
    for mode in ("reference", "exchanger", "exchanger_reactor_mass"):
        rf = opt[(NI, mode)]
        for cid in LOW:
            lo = opt[(cid, mode)]
            c = ce.compare(lo, rf)
            # hand check of the fixed-design break-even price and lifetime
            if c["breakeven_price_fixed_design_USD_per_kg"] not in (None, float("inf")):
                d2 = ce.design(cid, lo["T_C"], c["breakeven_price_fixed_design_USD_per_kg"], 2.0, W_kg=lo["W_kg"], mode=mode)
                add(f"CE-BE-PRICE-HAND-{mode}-{SH[cid]}", "At the fixed-design break-even price the full evaluate() LCOH equals the reference",
                    "numerical_verification", d2["lcoh_USD_per_kg"], rf["lcoh_USD_per_kg"], 1e-9, "USD/kg H2",
                    "pass" if abs(d2["lcoh_USD_per_kg"] - rf["lcoh_USD_per_kg"]) <= 1e-9 else "fail", [SCRIPT])
            if c["breakeven_lifetime_fixed_design_yr"]:
                d3 = ce.design(cid, lo["T_C"], pcen[cid], c["breakeven_lifetime_fixed_design_yr"], W_kg=lo["W_kg"], mode=mode)
                add(f"CE-BE-LIFE-HAND-{mode}-{SH[cid]}", "At the fixed-design break-even lifetime the full evaluate() LCOH equals the reference",
                    "numerical_verification", d3["lcoh_USD_per_kg"], rf["lcoh_USD_per_kg"], 1e-9, "USD/kg H2",
                    "pass" if abs(d3["lcoh_USD_per_kg"] - rf["lcoh_USD_per_kg"]) <= 1e-9 else "fail", [SCRIPT])

            # re-optimised break-even price (low-T design re-optimised at each price; Ni reference fixed)
            def f(p, cid=cid, mode=mode, l_ref=rf["lcoh_USD_per_kg"]):
                return ce.optimise(cid, p, 2.0, mode=mode)["lcoh_USD_per_kg"] - l_ref
            f0 = f(0.0)
            p_re = brentq(f, 0.0, 2e5, xtol=0.05) if f0 < 0 < f(2e5) else None
            o_re = ce.optimise(cid, p_re, 2.0, mode=mode) if p_re else None

            def g(L, cid=cid, mode=mode, l_ref=rf["lcoh_USD_per_kg"]):
                return ce.optimise(cid, pcen[cid], L, mode=mode)["lcoh_USD_per_kg"] - l_ref
            L_re = brentq(g, 0.05, 200.0, xtol=1e-3) if g(200.0) < 0 < g(0.05) else None
            s = cc.load_price_data()["scenarios_usd_per_kg_finished_catalyst"][cc.CATALYSTS[cid]["price_key"]]["central"]
            w = cc.load_price_data()["scenarios_usd_per_kg_finished_catalyst"][cc.CATALYSTS[cid]["price_key"]]["loading_wt_pct"]
            metal = w["Ni"] / 100 * s["P_Ni_usd_per_kg"] + w["Ru"] / 100 * s["P_Ru_usd_per_kg"]
            pbe = c["breakeven_price_fixed_design_USD_per_kg"]
            rec_frac = ((pcen[cid] - pbe) / metal) if (pbe not in (None, float("inf")) and pbe < pcen[cid]) else (0.0 if pbe and pbe >= pcen[cid] else None)
            be_rows.append({"mode": mode, "catalyst_id": cid, "catalyst": SH[cid], "reference": f"Ni/MgO cost-optimal ({mode})",
                            "low_T_C": lo["T_C"], "low_W_kg": lo["W_kg"], "ref_T_C": rf["T_C"], "ref_W_kg": rf["W_kg"],
                            "central_price_USD_per_kg": pcen[cid], "floor_price_USD_per_kg": pc(cid, "low"),
                            "published_TEA_price_USD_per_kg": cc.PUBLISHED_TEA_PRICE[cid],
                            "breakeven_price_fixed_design_USD_per_kg": pbe,
                            "breakeven_price_fixed_design_SGD_per_kg": c["breakeven_price_fixed_design_SGD_per_kg"],
                            "breakeven_price_reoptimised_USD_per_kg": p_re,
                            "breakeven_price_reoptimised_SGD_per_kg": p_re * ce.FX if p_re else None,
                            "T_at_reoptimised_breakeven_C": o_re["T_C"] if o_re else None,
                            "lcoh_low_at_zero_price_minus_ref_USD_per_kg": f0,
                            "breakeven_lifetime_fixed_design_yr": c["breakeven_lifetime_fixed_design_yr"],
                            "breakeven_lifetime_reoptimised_yr": L_re,
                            "metal_value_central_USD_per_kg": metal,
                            "ru_recovery_fraction_needed_for_breakeven": rec_frac,
                            "recovery_note": "net catalyst price = price - recovered metal value; no refining charge or "
                                             "verified recovery fraction is sourced (catalyst_prices.json L6, L7: snippet-level 85-95 %)",
                            "floor_vs_breakeven": (None if pbe in (None, float("inf")) else
                                                   "break-even below the metal-content floor" if pbe < pc(cid, "low") else
                                                   "break-even between floor and central" if pbe < pcen[cid] else
                                                   "break-even above the central price"),
                            **ce.kinetics_label(cid, NI)})
    # fixed-inventory (Aspen) break-even price and lifetime, HI on, all modes
    for row in comps:
        if row["basis"].startswith(("aspen_fixed_100kg_", "python_Top_X095_")):
            be_rows.append({"mode": row["mode"], "catalyst_id": row["low_catalyst_id"], "catalyst": row["low"],
                            "reference": f"Ni/MgO at 594 degC ({row['basis']})", "basis": row["basis"], "low_T_C": row["low_T_C"],
                            "low_W_kg": row["low_W_kg"], "ref_T_C": row["ref_T_C"], "ref_W_kg": row["ref_W_kg"],
                            "central_price_USD_per_kg": pcen[row["low_catalyst_id"]],
                            "floor_price_USD_per_kg": pc(row["low_catalyst_id"], "low"),
                            "published_TEA_price_USD_per_kg": cc.PUBLISHED_TEA_PRICE[row["low_catalyst_id"]],
                            "breakeven_price_fixed_design_USD_per_kg": row["breakeven_price_fixed_design_USD_per_kg"],
                            "breakeven_price_fixed_design_SGD_per_kg": row["breakeven_price_fixed_design_SGD_per_kg"],
                            "breakeven_lifetime_fixed_design_yr": row["breakeven_lifetime_fixed_design_yr"],
                            "floor_vs_breakeven": (None if row["breakeven_price_fixed_design_USD_per_kg"] in (None, float("inf")) else
                                                   "break-even below the metal-content floor" if row["breakeven_price_fixed_design_USD_per_kg"] < pc(row["low_catalyst_id"], "low") else
                                                   "break-even between floor and central" if row["breakeven_price_fixed_design_USD_per_kg"] < pcen[row["low_catalyst_id"]] else
                                                   "break-even above the central price"),
                            "source_type": row["source_type"], **row["kinetics"]})
    write_csv("catalyst_breakeven.csv", be_rows)
    print("break-even done", round(time.time() - t0))

    # ============================================================ 5. crossover map (price x lifetime) and Ni-temperature threshold
    cross = []
    for basis, getter in (("cost_optimal_exchanger", lambda c: (opt[(c, "exchanger")], opt[(NI, "exchanger")])),
                          ("python_Top_X095_HI_exchanger", lambda c: (py_designs[(c, True, "exchanger")], py_designs[(NI, True, "exchanger")]))):
        for cid in LOW:
            lo0, rf0 = getter(cid)
            for L in LIFE:
                lo = ce.design(cid, lo0["T_C"], pcen[cid], L, W_kg=lo0["W_kg"], hi=lo0["heat_integration"], mode="exchanger")
                rf = ce.design(NI, rf0["T_C"], pcen[NI], L, W_kg=rf0["W_kg"], hi=rf0["heat_integration"], mode="exchanger")
                c = ce.compare(lo, rf)
                cross.append({"basis": basis, "catalyst": SH[cid], "lifetime_yr": L, "low_T_C": lo["T_C"], "ref_T_C": rf["T_C"],
                              "breakeven_price_USD_per_kg": c["breakeven_price_fixed_design_USD_per_kg"],
                              "breakeven_price_SGD_per_kg": c["breakeven_price_fixed_design_SGD_per_kg"],
                              **{f"low_cheaper_at_{k}": (pc(cid, k) < c["breakeven_price_fixed_design_USD_per_kg"])
                                 if c["breakeven_price_fixed_design_USD_per_kg"] not in (None, float("inf")) else False for k in PRICE_CASES},
                              "breakeven_lifetime_at_central_yr": c["breakeven_lifetime_fixed_design_yr"],
                              **{f"breakeven_lifetime_at_{k}_yr": ce.compare(
                                  ce.design(cid, lo0["T_C"], pc(cid, k), L, W_kg=lo0["W_kg"], hi=lo0["heat_integration"], mode="exchanger",
                                            st=(asp_state[(cid, True)] if basis.startswith("aspen") else None)), rf)["breakeven_lifetime_fixed_design_yr"]
                                 for k in ("low", "published_TEA")},
                              "rule": "design held fixed; ranking reverses where price < break-even price (or lifetime > break-even lifetime)",
                              **ce.kinetics_label(cid, NI)})
    write_csv("catalyst_crossover.csv", cross)
    # Ni temperature above which the low-T catalyst (cost-optimal, central price, 2 yr) is cheaper.
    # kinetics-free variant: Ni catalyst mass and cost set to zero (only the T-dependence of the flowsheet remains)
    thr = []
    T_scan = [float(t) for t in range(500, 761, 5)]   # cached 5 K grid states; threshold by linear interpolation
    for cid in LOW:
        lo = opt[(cid, "exchanger")]
        for variant in ("Ni_kinetics_Takahashi_extrapolated", "Ni_catalyst_free_kinetics_independent"):
            Tstar, prev, status = None, None, "low-T design never cheaper up to 760 degC"
            start = opt[(NI, "exchanger")]["T_C"] if variant.startswith("Ni_kinetics") else 0.0
            for T in T_scan:
                if T < start or ce._eqc(T) <= ce.X_TARGET + 1e-4:
                    continue
                d = (ce.design(NI, T, pcen[NI], 2.0, mode="exchanger") if variant.startswith("Ni_kinetics")
                     else ce.design(NI, T, 0.0, 2.0, W_kg=0.0, mode="exchanger"))
                if d is None:
                    continue
                gap = d["lcoh_USD_per_kg"] - lo["lcoh_USD_per_kg"]   # > 0: the Ni design is dearer
                if gap > 0:
                    if prev is None:
                        Tstar, status = T, "low-T design cheaper already at the first scanned Ni temperature"
                    else:
                        Tstar = prev[0] + (T - prev[0]) * (-prev[1]) / (gap - prev[1])
                        status = "crossing (linear interpolation on the 5 K grid)"
                    break
                prev = (T, gap)
            thr.append({"catalyst": SH[cid], "variant": variant, "low_T_C": lo["T_C"], "low_W_kg": lo["W_kg"],
                        "low_lcoh_USD_per_kg": lo["lcoh_USD_per_kg"], "Ni_threshold_T_C": Tstar,
                        "threshold_status": status, "scan_start_C": start,
                        "sourced_Ni_design_T_C": {"cho2026nickel": 735.52, "mehr2026highcapacity_outlet": 760.0},
                        "sourced_values_above_threshold": (Tstar is not None and Tstar < 735.52),
                        "AmCraX_Ni_costopt_T_C_extrapolated": opt[(NI, "exchanger")]["T_C"],
                        "interpretation": "the low-T catalyst design is cheaper than a Ni design operated above Ni_threshold_T_C",
                        **(ce.kinetics_label(cid) if variant.endswith("independent") else ce.kinetics_label(cid, NI))})
    print("crossover done", round(time.time() - t0))

    # ============================================================ 6. sensitivities (cost-optimal, exchanger mode, both re-optimised)
    ru_like = LOW
    sens_cases = [("base", {}, {}, {}),
                  ("price_low_metal_floor", {c: pc(c, "low") for c in cc.CATALYSTS}, {}, {}),
                  ("price_high", {c: pc(c, "high") for c in cc.CATALYSTS}, {}, {}),
                  ("published_TEA_prices_not_current", {c: pc(c, "published_TEA") for c in cc.CATALYSTS}, {}, {}),
                  ("Ru_price_USGS_2025_average", {c: ce.price_from_components(cc.CATALYSTS[c]["price_key"], 15.31, 22184.0, 32.2) for c in ru_like}, {}, {})]
    for L in (1.0, 4.0, 5.0):
        sens_cases.append((f"lifetime_{L:g}yr", {}, {"lifetime": L}, {}))
    for p in (300.0, 610.0, 1000.0):
        sens_cases.append((f"NH3_{p:g}USD_t", {}, {"scenario": p}, {}))
    sens_cases.append(("heat_fuel_natural_gas", {}, {"econ": {"heat_fuel": "natural_gas"}}, {}))
    for el in ce.REF.sens("electricity_USD_per_kWh"):
        sens_cases.append((f"electricity_{el:g}", {}, {"econ": {"electricity_price_USD_per_kWh": el}}, {}))
    sens_cases.append(("discount_0.085", {}, {"econ": {"discount_rate": 0.085}}, {}))
    sens_cases.append(("operating_hours_7000", {}, {"econ": {"operating_hours_h_per_yr": 7000.0}}, {}))
    sens_cases.append(("U_low_35", {}, {"U": "low"}, {}))
    sens_cases.append(("U_high_150", {}, {"U": "high"}, {}))
    sens_cases.append(("reactor_by_catalyst_mass", {}, {"mode": "exchanger_reactor_mass"}, {}))
    sens_cases.append(("frozen_reference_capex", {}, {"mode": "reference"}, {}))
    sens_cases.append(("low_T_rates_div5", {}, {}, {c: 0.2 for c in ru_like}))
    sens_cases.append(("Ni_rate_div5", {}, {}, {NI: 0.2}))
    sens = []
    for name, pmap, kw, kmap in sens_cases:
        res = {}
        for cid in cc.CATALYSTS:
            econ = dict(kw.get("econ", {}))
            res[cid] = ce.optimise(cid, pmap.get(cid, pcen[cid]), kw.get("lifetime", 2.0), mode=kw.get("mode", "exchanger"),
                                   U_case=kw.get("U", "central"), scenario=kw.get("scenario", "grey"),
                                   econ_overrides=econ or None, kinetic_factor=kmap.get(cid, 1.0))
        for cid in LOW:
            c = ce.compare(res[cid], res[NI])
            sens.append({"case": name, "catalyst": SH[cid], "low_T_C": res[cid]["T_C"], "ref_T_C": res[NI]["T_C"],
                         "low_W_kg": res[cid]["W_kg"], "ref_W_kg": res[NI]["W_kg"],
                         "net_lcoh_delta_USD_per_kg": c["net_lcoh_delta_USD_per_kg"],
                         "net_lcoh_delta_SGD_per_kg": c["net_lcoh_delta_SGD_per_kg"],
                         "energy_saving_USD_per_kg": c["energy_saving_USD_per_kg"],
                         "catalyst_cost_increase_USD_per_kg": c["catalyst_cost_increase_USD_per_kg"],
                         "exchanger_delta_USD_per_kg": c["decomposition_USD_per_kg"]["exchanger_capital_and_fixed"],
                         "reactor_delta_USD_per_kg": c["decomposition_USD_per_kg"]["reactor_capital_and_fixed"],
                         "npv_choose_low_USD": c["npv_choose_low_USD"], "simple_payback_yr": c["simple_payback_yr"],
                         "low_is_lower_temperature": res[cid]["T_C"] < res[NI]["T_C"],
                         "low_cheaper": c["low_cheaper"], "below_resolution": abs(c["net_lcoh_delta_USD_per_kg"]) < RES,
                         **ce.kinetics_label(cid, NI)})
    # fuel price alone (feed held at 450 USD/t): heat-fuel term is linear in the fuel price (fixed designs, analytic)
    for p in (300.0, 610.0, 1000.0):
        for cid in LOW:
            c = ce.compare(opt[(cid, "exchanger")], opt[(NI, "exchanger")])
            dfuel = c["decomposition_USD_per_kg"]["energy_heat_fuel"] * (p / 450.0)
            net = c["net_lcoh_delta_USD_per_kg"] - c["decomposition_USD_per_kg"]["energy_heat_fuel"] + dfuel
            sens.append({"case": f"fuel_NH3_only_{p:g}USD_t_fixed_designs", "catalyst": SH[cid],
                         "low_T_C": opt[(cid, "exchanger")]["T_C"], "ref_T_C": opt[(NI, "exchanger")]["T_C"],
                         "net_lcoh_delta_USD_per_kg": net, "net_lcoh_delta_SGD_per_kg": net * ce.FX,
                         "energy_saving_USD_per_kg": -dfuel, "low_cheaper": net < 0, "below_resolution": abs(net) < RES,
                         "note": "supplementary-fuel price varied alone, designs fixed (analytic: heat-fuel term linear in price)",
                         **ce.kinetics_label(cid, NI)})
    write_csv("catalyst_econ_sensitivity.csv", sens)
    print("sensitivities done", round(time.time() - t0))

    # ============================================================ 7. CAPEX response checks (hand calculations)
    st = ce.state(560.0)
    fe = st["fehe"]["central"]["tci_equivalent_USD"]
    d_ref = ce.design(NI, 560.0, pcen[NI], 2.0, W_kg=200.0, mode="reference", st=st)
    d_hx = ce.design(NI, 560.0, pcen[NI], 2.0, W_kg=200.0, mode="exchanger", st=st)
    add("CE-HX-RATIO", "FEHE passed through the reference CAPEX size ratio: total CAPEX = reference CAPEX + FEHE TCI-equivalent",
        "numerical_verification", d_hx["capex_total_USD"] - d_ref["capex_total_USD"], fe, 1e-6 * fe, "USD",
        "pass" if abs(d_hx["capex_total_USD"] - d_ref["capex_total_USD"] - fe) <= 1e-6 * fe else "fail",
        ["backend/amcrax/heat_integration/exchanger.py", "backend/amcrax/economics/reference.py"])
    d_rm = ce.design(NI, 560.0, pcen[NI], 2.0, W_kg=200.0, mode="exchanger_reactor_mass", st=st)
    base_items = reference_item_costs()
    hand_rx = base_items["installed_USD"]["reactor"] * (200.0 / reference_catalyst_mass_kg()) ** 0.8 * base_items["indirect_factor"]
    add("CE-REACTOR-MASS", "Reactor item by catalyst mass = Cho reactor installed cost x (W / Cho inventory)^0.8 x indirect factor (hand calculation)",
        "numerical_verification", d_rm["tci_by_item_USD"]["reactor"], hand_rx, 1e-6 * hand_rx, "USD",
        "pass" if abs(d_rm["tci_by_item_USD"]["reactor"] - hand_rx) <= 1e-6 * hand_rx else "fail",
        ["backend/amcrax/economics/reference.py"])
    lo_, rf_ = opt[(LOW[0], "exchanger")], opt[(NI, "exchanger")]
    cchk = ce.compare(lo_, rf_)
    npv_eval = lo_["npv_USD_evaluate"] - rf_["npv_USD_evaluate"]
    add("CE-NPV-SMOOTHED", "NPV of choosing the low-T design (smoothed catalyst) equals the difference of singapore.evaluate NPVs",
        "numerical_verification", cchk["npv_choose_low_smoothed_USD"], npv_eval, 1e-6 * max(1.0, abs(npv_eval)), "USD",
        "pass" if abs(cchk["npv_choose_low_smoothed_USD"] - npv_eval) <= 1e-6 * max(1.0, abs(npv_eval)) else "fail", [SCRIPT])
    for cid in cc.CATALYSTS:
        for mode in ce.MODES:
            o = opt[(cid, mode)]
            add(f"CE-OPT-INTERIOR-{mode}-{SH[cid]}", "Cost-optimal temperature lies inside the 470-760 degC grid",
                "numerical_verification", o["T_C"], "interior", None, "degC", "fail" if o["at_grid_bound"] else "pass", [SCRIPT])

    # ============================================================ 8. Cho rebuild with prices (H3-e, H3-f)
    cho = json.loads((CMP / "catalyst_cho_comparison.json").read_text(encoding="utf-8"))
    hours = ce.REF.operating_hours_h_per_yr
    cho_rows = []
    pr = {"published_TEA_Cho": {"Ni": 33.4, "Ru": 542.0},
          # Cho's Ni catalyst is 8 wt% Ni/Al2O3: same formula (central P_Ni 15.31 + N 32.2; floor P_Ni 15.0, N 0)
          "derived_central": {"Ni": 0.08 * 15.31 + 32.2, "Ru": ce.price("Ru-K/CaO", "central")},
          "derived_floor": {"Ni": 0.08 * 15.0, "Ru": ce.price("Ru-K/CaO", "low")}}
    for s in cho["summary"]:
        g = {r["design"]: r for r in cho["designs"] if r["psa_recovery"] == s["psa_recovery"] and r["inventory_basis"] == s["inventory_basis"]}
        ni, ru = g["Ni_735.52C_24.34bar"], g["RuAl2O3_566.69C_10bar"]
        for k, v in pr.items():
            def rec(r, pnew):
                return r["rec_USD_per_kg"] + r["W_kg"] * (pnew - (33.4 if "Ni" in r["design"].split("_")[0] else 542.0)) / 2.0 / (r["h2_product_kg_h"] * hours)
            rn, rr = rec(ni, v["Ni"]), rec(ru, v["Ru"])
            cho_rows.append({"psa_recovery": s["psa_recovery"], "inventory_basis": s["inventory_basis"], "price_case": k,
                             "price_Ni_USD_per_kg": v["Ni"], "price_Ru_USD_per_kg": v["Ru"],
                             "rec_Ni_USD_per_kg": rn, "rec_Ru_USD_per_kg": rr, "rec_Ru_lower_by_pct": 100 * (1 - rr / rn),
                             "cho_value_pct": 7.0, "W_Ni_kg": ni["W_kg"], "W_Ru_kg": ru["W_kg"],
                             "Ni_supp_nh3_kg_h": ni["supplementary_nh3_kg_h"], "Ru_supp_nh3_kg_h": ru["supplementary_nh3_kg_h"],
                             "note": "Cho reconstruction rows (catalyst_cho_comparison.json, Cho economic basis) with the catalyst "
                                     "term re-priced analytically; Ru kinetics are the Ru/Al2O3 proxy (Cho's Ru-K/CaO law unmodelled), "
                                     "Ru-K/CaO priced as 3 wt% Ru", **ce.kinetics_label("ru_kum_temkin_pyzhev", NI)})
    # PSA recovery at which each Cho design stops needing supplementary fuel (process heat import = 0)
    psa_thr = {}
    for name, cid, T, P in (("Ni_735.52C_24.34bar", NI, 735.52, 24.34), ("RuAl2O3_566.69C_10bar", "ru_kum_temkin_pyzhev", 566.69, 10.0)):
        def imp(r, cid=cid, T=T, P=P):
            return cc.heat_accounting(cc.kinetic_flowsheet(T, P, 0.97, True, r), 20.0)["external_heat_import_kW"]
        lo_r, hi_r = 0.70, 0.95
        i_lo, i_hi = imp(lo_r), imp(hi_r)
        thr_r = None
        if i_lo <= 1e-6 < i_hi:
            for _ in range(14):
                mid = 0.5 * (lo_r + hi_r)
                if imp(mid) > 1e-6:
                    hi_r = mid
                else:
                    lo_r = mid
            thr_r = 0.5 * (lo_r + hi_r)
        psa_thr[name] = {"psa_recovery_threshold": thr_r, "import_kW_at_0.70": i_lo, "import_kW_at_0.95": i_hi,
                         "import_kW_at_0.756": imp(0.756), "import_kW_at_0.85": imp(0.85)}
    print("cho done", round(time.time() - t0))

    # ============================================================ 9. findings and row evidence
    def C(basis, cid):
        return next(r for r in comps if r["basis"] == basis and r["low_catalyst_id"] == cid)

    fx_hi = {SH[c]: C("python_Top_X095_HI_exchanger", c) for c in LOW}        # equal conversion: the cost basis
    fx_no = {SH[c]: C("python_Top_X095_noHI_exchanger", c) for c in LOW}
    fx_asp = {SH[c]: C("aspen_fixed_100kg_HI_exchanger", c) for c in LOW}      # Aspen cross-check (unequal X)
    fx_asp_no = {SH[c]: C("aspen_fixed_100kg_noHI_exchanger", c) for c in LOW}
    co = {m: {SH[c]: C(f"cost_optimal_{m}", c) for c in LOW} for m in list(ce.MODES) + ["exchanger_U_low", "exchanger_U_high"]}
    sens_by = {}
    for r in sens:
        sens_by.setdefault(r["case"], {})[r["catalyst"]] = r
    n_low_cheaper = sum(1 for r in sens if r["low_cheaper"] and not r["below_resolution"])
    n_low_lowerT = sum(1 for r in sens if r.get("low_is_lower_temperature"))
    resolved = [r for r in sens if not r["below_resolution"]]
    ess = {
        "fixed_inventory_aspen_HI_exchanger": {k: {"energy_saving_kW": v["energy_saving_fired_duty_kW"],
                                                   "energy_saving_USD_per_kg": v["energy_saving_USD_per_kg"],
                                                   "catalyst_increase_USD_per_kg": v["catalyst_cost_increase_USD_per_kg"],
                                                   "exchanger_delta_USD_per_kg": v["decomposition_USD_per_kg"]["exchanger_capital_and_fixed"],
                                                   "net_lcoh_delta_USD_per_kg": v["net_lcoh_delta_USD_per_kg"],
                                                   "breakeven_price_USD_per_kg": v["breakeven_price_fixed_design_USD_per_kg"],
                                                   "floor_price_USD_per_kg": pc(cc.CATALYSTS and next(c for c in LOW if SH[c] == k), "low"),
                                                   "central_price_USD_per_kg": pcen[next(c for c in LOW if SH[c] == k)],
                                                   "breakeven_lifetime_yr": v["breakeven_lifetime_fixed_design_yr"],
                                                   "npv_choose_low_USD": v["npv_choose_low_USD"], "simple_payback_yr": v["simple_payback_yr"],
                                                   "kinetics": v["kinetics"]} for k, v in fx_hi.items()},
        "fixed_inventory_aspen_noHI_exchanger": {k: {"net_lcoh_delta_USD_per_kg": v["net_lcoh_delta_USD_per_kg"],
                                                     "energy_saving_kW": v["energy_saving_fired_duty_kW"],
                                                     "breakeven_price_USD_per_kg": v["breakeven_price_fixed_design_USD_per_kg"]} for k, v in fx_no.items()},
        "cost_optimal": {m: {k: {"low_T_C": v["low_T_C"], "ref_T_C": v["ref_T_C"], "low_W_kg": v["low_W_kg"], "ref_W_kg": v["ref_W_kg"],
                                 "low_is_lower_temperature": v["low_is_lower_temperature"],
                                 "net_lcoh_delta_USD_per_kg": v["net_lcoh_delta_USD_per_kg"],
                                 "net_lcoh_delta_SGD_per_kg": v["net_lcoh_delta_SGD_per_kg"],
                                 "energy_saving_USD_per_kg": v["energy_saving_USD_per_kg"],
                                 "energy_saving_kW": v["energy_saving_fired_duty_kW"],
                                 "catalyst_increase_USD_per_kg": v["catalyst_cost_increase_USD_per_kg"],
                                 "decomposition_USD_per_kg": v["decomposition_USD_per_kg"],
                                 "hi_saving_low_USD_per_kg": v["hi_saving_low_USD_per_kg"], "hi_saving_ref_USD_per_kg": v["hi_saving_ref_USD_per_kg"],
                                 "npv_choose_low_USD": v["npv_choose_low_USD"], "npv_choose_low_SGD": v["npv_choose_low_SGD"],
                                 "simple_payback_yr": v["simple_payback_yr"], "below_resolution": abs(v["net_lcoh_delta_USD_per_kg"]) < RES,
                                 "kinetics": v["kinetics"]} for k, v in d.items()} for m, d in co.items()},
        "fixed_inventory_aspen_cross_check_HI_exchanger": {k: {"net_lcoh_delta_USD_per_kg": v["net_lcoh_delta_USD_per_kg"],
                                                               "energy_saving_kW": v["energy_saving_fired_duty_kW"],
                                                               "h2_product_rel_diff": v["h2_product_rel_diff"],
                                                               "feed_term_from_unequal_X_USD_per_kg": v["decomposition_USD_per_kg"]["ammonia_feed"],
                                                               "caution": v["caution"]} for k, v in fx_asp.items()},
        "key_descriptions": {
            "fixed_inventory_aspen_HI_exchanger": "MIS-NAMED KEY, kept for readers (fix pass 24 Nov 2026, review A m10): it holds "
                                                  "the PYTHON equal-conversion values (python_Top_X095_HI_exchanger: each catalyst "
                                                  "at the temperature where its law reaches X 0.95, with FEHE, exchanger mode), not "
                                                  "Aspen fixed-inventory values. The Aspen fixed 100 kg cross-check is "
                                                  "fixed_inventory_aspen_cross_check_HI_exchanger.",
            "fixed_inventory_aspen_noHI_exchanger": "MIS-NAMED KEY, kept: Python equal-conversion values without FEHE "
                                                    "(python_Top_X095_noHI_exchanger), not Aspen values."},
        "hi_saving_aspen_fixed_inventory": [v for v in hi_saving.values()],
        "resolution_USD_per_kg": RES,
        "resolution_readings": {k: v for k, v in resolution.items() if k != "rows"},
        "sensitivity_counts": {"n_rows": len(sens), "n_low_cheaper_resolved": n_low_cheaper,
                               "n_rows_resolved": len(resolved), "n_low_design_at_lower_T_than_Ni": n_low_lowerT,
                               "cases_where_some_low_T_catalyst_cheaper_resolved": sorted({r["case"] for r in sens if r["low_cheaper"] and not r["below_resolution"]})},
        "ni_temperature_threshold": thr, "cho_psa_fuel_threshold": psa_thr,
    }
    # validated-only subset (no Ni law is validated): comparisons among the validated laws, and the kinetics-free Ni threshold
    val_only = {"validated_laws": [SH[c] for c in VALIDATED],
                "note": "No Ni rate law is validated against literature (Ni/MgO Takahashi is 'extrapolated'); every comparison "
                        "with Ni/MgO and every Ru/MgO result rests on an extrapolated law. All laws are pressure-extrapolated at 20 bar.",
                "cost_optimal_exchanger": {SH[c]: {"T_C": opt[(c, "exchanger")]["T_C"], "W_kg": opt[(c, "exchanger")]["W_kg"],
                                                   "lcoh_USD_per_kg": opt[(c, "exchanger")]["lcoh_USD_per_kg"]} for c in VALIDATED},
                "ni_threshold_kinetics_free": [t for t in thr if t["variant"].endswith("independent") and t["catalyst"] in [SH[c] for c in VALIDATED]],
                "energy_vs_temperature": "kinetics-independent: fired duty at fixed X and T comes from the flowsheet only"}
    findings = {"energy_and_cost": ess, "validated_laws_only": val_only}

    # ---------------- row evidence
    ru_al = "Ru/Al2O3"
    fx_all_negative_energy = all(v["energy_saving_fired_duty_kW"] > 0 for v in fx_hi.values())
    co_ex = co["exchanger"]
    row_evidence = {
        "H3-a": {
            "proposed_verdict": "SUPPORTED",
            "numbers": {"aspen_fixed_100kg_fired_duty_saving_kW_HI": {k: v["energy_saving_fired_duty_kW"] for k, v in fx_asp.items()},
                        "aspen_fixed_100kg_fired_duty_saving_kW_noHI": {k: v["energy_saving_fired_duty_kW"] for k, v in fx_asp_no.items()},
                        "aspen_fixed_100kg_conversion_note": "Aspen runs reach X 0.9496-0.9589 (Ni highest), so Ni absorbs slightly more reaction heat",
                        "python_Top_X095_fired_duty_saving_kW_HI": {k: v["energy_saving_fired_duty_kW"] for k, v in fx_hi.items()},
                        "python_Top_X095_fired_duty_saving_kW_noHI": {k: v["energy_saving_fired_duty_kW"] for k, v in fx_no.items()},
                        "python_Top_X095_fuel_saving_USD_per_kg_HI": {k: v["energy_saving_USD_per_kg"] for k, v in fx_hi.items()},
                        "cost_optimal_exchanger_energy_saving_kW": {k: v["energy_saving_fired_duty_kW"] for k, v in co_ex.items()},
                        "resolution_USD_per_kg": RES},
            "assumptions": ["fixed 95 % conversion, 20 bar, PSA 0.85", "furnace efficiency 0.85 and 2 % loss (assumptions)",
                            "fired duty = temperature-feasible import after FEHE and tail-gas firing"],
            "uncertainty": "Python fired duty is 13.8-15.2 kW below Aspen at the same T and X for all five catalysts (spread 1.4 kW, so the "
                           "T-dependence is reproduced within 1.4 kW over 95 K); FEHE duty offset +20.8 kW (model form, task X1).",
            "envelope": h3a_envelope(fx_hi, fx_no, co_ex, resolution),
            "threshold": None,
            "reason": "Computed (Python, cross-checked against Aspen at the same T and X); the reduction at equal conversion is not a "
                      "built-in assumption. CORRECTION to Phase 1: the Aspen fixed-inventory runs reach unequal conversion (Ni 0.9589 "
                      "against Ru/Al2O3 0.9496); most of the 102 kW (17 %) Aspen difference comes from that conversion difference (less "
                      "unconverted NH3 burnt in the tail gas), not from temperature. At equal conversion the saving is 25 kW with FEHE. "
                      "When each design is cost-optimised at derived central prices the Ru-containing designs move to HIGHER temperatures "
                      "than Ni and the saving disappears or reverses (H3-c): the energy claim holds for low-T operating points, not for "
                      "cost-optimal designs."},
        "H3-b": {
            "proposed_verdict": "INCONCLUSIVE",
            "numbers": {"aspen_T_op_100kg_C": {SH[c]: asp_state[(c, True)]["T_C"] for c in cc.CATALYSTS},
                        "cost_optimal_T_C_exchanger_central": {SH[c]: opt[(c, "exchanger")]["T_C"] for c in cc.CATALYSTS},
                        "kinetic_classes": {SH[c]: cc.kinetic_validity(c)["kinetic_validity_class"] for c in cc.CATALYSTS}},
            "assumptions": ["isothermal PFR, effectiveness factor 1, no pressure drop", "1 atm (Takahashi, Lucentini) or 1-10 bar (Kum) laws used at 20 bar",
                            "AmCraX reversibility factor for Takahashi and Lucentini (not in the papers)"],
            "uncertainty": "no law validated at 20 bar; Ni/MgO and Ru/MgO laws fail their literature comparison at 1 atm (KIN-NI-PRED, KIN-RU-PRED)",
            "envelope": "20 bar, X 0.95, 100 kg per 100 kmol/h NH3; equilibrium limits X 0.95 to about 485 degC and above",
            "threshold": None,
            "reason": "The temperature ordering at fixed inventory (Ru/Al2O3 499 < Ru/MgO 522 < NiRu 572-576 < Ni/MgO 594 degC) rests on "
                      "laws extrapolated to 20 bar, and the Ni reference law is in class 'extrapolated'. Among laws validated against "
                      "literature only (Ru/Al2O3, NiRu/CeO2; pressure-extrapolated) the Ru/Al2O3 law reaches the target about 73-77 K "
                      "lower than the NiRu laws, but no validated Ni law exists to compare with. This task adds no kinetic evidence."},
        "H3-c": {
            "proposed_verdict": None,  # filled below
            "numbers": {"fixed_inventory_aspen_HI_exchanger": ess["fixed_inventory_aspen_HI_exchanger"],
                        "cost_optimal": ess["cost_optimal"], "breakeven": [r for r in be_rows if r["mode"] == "exchanger"],
                        "ni_temperature_threshold": thr, "resolution_USD_per_kg": RES,
                        "sensitivity_counts": ess["sensitivity_counts"]},
            "assumptions": ["catalyst prices DERIVED from metal content + 32.2 USD/kg non-metal part (no quotation exists)",
                            "lifetime 2 yr (Cho, assumed), varied 1-5 yr", "FEHE U central 72.5 W/(m2 K) (derived), varied 35-150",
                            "reactor CAPEX by NH3 feed (frozen basis) or by catalyst mass (sensitivity)",
                            "no Ru recovery credit (no sourced refining charge or recovery fraction)"],
            "uncertainty": "Ru price (USGS 2025 average to Nov 2026 JM spot), lifetime 1-5 yr, NH3 300-1000 USD/t, fuel price, natural-gas heat, "
                           "electricity 0.084-0.222 USD/kWh, discount 0.085-0.10, 7000-8000 h, U 35-150, reactor cost driver, rates /5. "
                           "The FEHE cost is a step function of temperature (4 -> 5 shells in series between 537 and 538 degC at U central, "
                           "+0.235 MUSD TCI, about +0.023 USD/kg): in the 'exchanger' mode it pins several optima at 537 degC and is of the "
                           "same size as the catalyst differences; the 'reference' mode (no exchanger response) is reported beside it.",
            "envelope": "20 bar, X 0.95, PSA 0.85, grey 450 USD/t base; Python flowsheet (cost-optimal) or Aspen duties (fixed 100 kg)",
            "threshold": {"breakeven_price": "catalyst_breakeven.csv (fixed and re-optimised); compared with the metal-content floor and the central price",
                          "breakeven_lifetime": "catalyst_breakeven.csv", "Ni_temperature_threshold_C": {t["catalyst"] + "|" + t["variant"]: t["Ni_threshold_T_C"] for t in thr},
                          "ru_recovery_fraction_needed": {r["catalyst"] + "|" + r["mode"]: r.get("ru_recovery_fraction_needed_for_breakeven") for r in be_rows if "ru_recovery_fraction_needed_for_breakeven" in r}},
            "reason": None},
        "H3-e": {
            "proposed_verdict": "INCONCLUSIVE",
            "numbers": {"psa_recovery_threshold_for_zero_supplementary_fuel": psa_thr,
                        "cho_rows": [r for r in cho_rows if r["price_case"] == "published_TEA_Cho"]},
            "assumptions": ["Cho operating points rebuilt on AmCraX boundaries (no compression, recycle, TSA, expander)",
                            "supplementary fuel needed when the temperature-feasible process heat import after tail-gas firing is > 0"],
            "uncertainty": "PSA recovery 0.70-0.95; boundary differences to Cho; Python only at Cho's points",
            "envelope": "X 0.97; Ni 735.52 degC / 24.34 bar; Ru 566.69 degC / 10 bar",
            "threshold": {k: v["psa_recovery_threshold"] for k, v in psa_thr.items()},
            "reason": "The fuel need at fixed T, P and X is kinetics-independent. Whether Ru needs no supplementary fuel while Ni does "
                      "depends on PSA recovery: Cho's pattern appears only for recoveries between the two thresholds. At Cho's own 0.756 "
                      "neither design needs process heat import on AmCraX boundaries; at the AmCraX 0.85 both do. The source value 0.756 "
                      "lies outside the window, so on AmCraX boundaries the claim is not reproduced; because the boundaries differ "
                      "(Cho's extra units), this is a reproduction finding, not a contradiction of Cho's own flowsheet. Secondary row."},
        "H3-f": {
            "proposed_verdict": "INCONCLUSIVE",
            "numbers": {"rec_Ru_lower_by_pct": {f"{r['price_case']}|psa{r['psa_recovery']}|{r['inventory_basis']}": r["rec_Ru_lower_by_pct"] for r in cho_rows},
                        "cho_value_pct": 7.0},
            "assumptions": ["Cho economic basis (8.5 %, 0.084 USD/kWh, 25 yr)", "Ru/Al2O3 kinetics as a proxy for Cho's Ru-K/CaO",
                            "Ru-K/CaO priced as 3 wt% Ru (derived) or at Cho's 542 USD/kg (published TEA, below the Ru floor)"],
            "uncertainty": "inventory basis (kinetic minimum or Cho GHSV 9000), PSA recovery, catalyst price case",
            "envelope": "Cho operating points on AmCraX boundaries",
            "threshold": None,
            "reason": "The sign of the REC difference changes with the inventory basis at Cho's prices; at derived prices of a 3 wt% Ru "
                      "catalyst the Ru REC advantage shrinks or reverses. Cho's 7 % is not reproduced; the AmCraX CAPEX does not respond "
                      "to T and P as Cho's does. Secondary row."},
    }
    # ---- H3-c verdict from computed numbers (rule: thresholds vs sourced values; resolution)
    fixed_be = {k: (v["breakeven_price_fixed_design_USD_per_kg"], pc(next(c for c in LOW if SH[c] == k), "low"), pcen[next(c for c in LOW if SH[c] == k)])
                for k, v in fx_hi.items()}
    be_below_floor = [k for k, (b, fl, ce_) in fixed_be.items() if b is None or b < fl]
    be_above_central = [k for k, (b, fl, ce_) in fixed_be.items() if b is not None and b > ce_]
    co_cheaper = [k for k, v in co_ex.items() if v["net_lcoh_delta_USD_per_kg"] < -RES]
    co_lowT = [k for k, v in co_ex.items() if v["low_is_lower_temperature"]]
    thr_ki = {t["catalyst"]: t["Ni_threshold_T_C"] for t in thr if t["variant"].endswith("independent")}
    thr_below_sourced = [k for k, v in thr_ki.items() if v is not None and v < 735.52]
    robust = [k for k in set(co_cheaper) & set(co_lowT)
              if all(r["low_cheaper"] and not r["below_resolution"] and r.get("low_is_lower_temperature", True)
                     for r in sens if r["catalyst"] == k)]
    if robust:
        verdict = "SUPPORTED"
    elif not be_above_central and not co_cheaper and not thr_below_sourced:
        verdict = "CONTRADICTED"
    else:
        verdict = "INCONCLUSIVE"
    row_evidence["H3-c"]["proposed_verdict"] = verdict
    row_evidence["H3-c"]["reason"] = (
        f"(1) Kinetic operating temperatures at equal conversion 0.95 (90-100 kg, Python flowsheet, FEHE costed): break-even prices "
        + ", ".join(f"{k} {b:.0f}" if b is not None else f"{k} none" for k, (b, fl, ce_) in fixed_be.items())
        + " USD/kg against floors " + ", ".join(f"{fl:.0f}" for (b, fl, ce_) in fixed_be.values())
        + " and central " + ", ".join(f"{ce_:.0f}" for (b, fl, ce_) in fixed_be.values())
        + f"; break-even below the metal floor for {be_below_floor or 'none'}, above the central price for {be_above_central or 'none'}. "
        f"(2) Cost-optimal designs (both re-optimised, exchanger mode): low-T catalyst cheaper beyond the resolution {RES:.4f} USD/kg for "
        f"{co_cheaper or 'none'}; Ru-containing designs at a LOWER temperature than Ni for {co_lowT or 'none'}: at derived prices the "
        f"economic optimum of an expensive catalyst is a small charge at high temperature, so the energy saving that the claim rests on is "
        f"not chosen. (3) Against Ni at sourced design temperatures (Cho 735.52, Mehr 760 degC), the kinetics-free Ni threshold "
        f"temperatures are {thr_ki}; the low-T designs win against those Ni designs but lose against the AmCraX Ni/MgO optimum "
        f"({opt[(NI, 'exchanger')]['T_C']:.0f} degC, extrapolated law). The Ni design temperature therefore decides the ranking, sourced "
        f"values and the extrapolated model straddle the threshold, and every LCOH difference is below 1 % of LCOH. "
        f"Resolved low-T wins in {n_low_cheaper} of {len(sens)} sensitivity rows.")
    findings["row_evidence_summary"] = {k: v["proposed_verdict"] for k, v in row_evidence.items()}

    dump("catalyst_economics.json", {"provenance": prov("catalyst economics for H3 on the unified basis"),
                                     "basis": {"economics": "amcrax.economics.singapore.evaluate (reference scenario v1.0.0; default "
                                                            "output unchanged); modes " + ", ".join(ce.MODES),
                                               "modes": {"reference": "CAPEX by NH3 feed (frozen basis)",
                                                         "exchanger": "reference + FEHE TCI-equivalent from its area (task X1), passed "
                                                                      "through item_size_ratio['heat_exchangers'] (incremental convention)",
                                                         "exchanger_reactor_mass": "exchanger + reactor item scaled by catalyst mass (exponent 0.8)"},
                                               "design": "100 kmol/h NH3, 20 bar, X 0.95, PSA 0.85, grey 450 USD/t, furnace 0.85 + 2 % loss",
                                               "fx_SGD_per_USD": ce.FX, "lifetimes_yr": LIFE,
                                               "sign": "delta = low-T design minus Ni reference; negative favours the low-T catalyst"},
                                     "findings": findings, "resolution": resolution, "row_evidence": row_evidence,
                                     "comparisons": comps, "breakeven": be_rows, "crossover": cross,
                                     "cho_rebuild_priced": cho_rows, "sensitivity": sens,
                                     "unmodelled_catalysts": [r for r in ptab if not r["modelled"]]})
    write_csv("catalyst_comparisons_flat.csv", [{k: v for k, v in r.items() if k not in ("low_design", "ref_design", "decomposition_USD_per_kg", "kinetics")}
                                                | {f"dec_{k}": v for k, v in r["decomposition_USD_per_kg"].items()}
                                                | {"kinetic_label": r["kinetics"]["result_label"]} for r in comps])
    VAL.joinpath("catalyst_economics.json").write_text(json.dumps(clean(items), indent=2), encoding="utf-8")

    # ============================================================ 10. figures
    figures(cost_rows, be_rows, sens, cross, RES)
    print("validation", {s: sum(1 for v in items if v["status"] == s) for s in ("pass", "fail", "informational")},
          [v["id"] for v in items if v["status"] == "fail"])
    print("H3", findings["row_evidence_summary"])
    print("elapsed", round(time.time() - t0))


def footer(fig):
    fig.text(0.01, 0.003, FOOT, fontsize=5.8, color=C_GREY, ha="left", va="bottom")


def figures(cost_rows, be_rows, sens, cross, RES):
    cats = list(cc.CATALYSTS)
    # (a) catalyst cost per kg H2 at the cost-optimal design: price case x lifetime
    fig, ax = plt.subplots(1, 2, figsize=(11.5, 4.4))
    for i, cid in enumerate(cats):
        for j, case in enumerate(("low", "central", "published_TEA")):
            rr = [r for r in cost_rows if r["catalyst_id"] == cid and r["price_case"] == case]
            ax[0].plot([r["lifetime_yr"] for r in rr], [r["costopt_catalyst_SGD_per_kg_H2"] for r in rr],
                       ["-", "--", ":"][j], marker="o", ms=3, color=PALETTE[i % len(PALETTE)],
                       label=f"{SH[cid]} ({case})" if j == 1 else None)
            rr2 = [r for r in cost_rows if r["catalyst_id"] == cid and r["price_case"] == case]
            ax[1].plot([r["lifetime_yr"] for r in rr2], [r["fixed100kg_catalyst_SGD_per_kg_H2"] for r in rr2],
                       ["-", "--", ":"][j], marker="o", ms=3, color=PALETTE[i % len(PALETTE)])
    ax[0].set_yscale("log")
    ax[1].set_yscale("log")
    ax[0].set_title("Cost-optimal design (T and W re-optimised)", fontsize=9)
    ax[1].set_title("Fixed 100 kg at the kinetic operating T", fontsize=9)
    for a in ax:
        a.set_xlabel("catalyst lifetime (yr)")
        a.set_ylabel("catalyst cost (SGD/kg H2)")
    ax[0].legend(fontsize=6.5, title="solid: floor, dashed: central, dotted: published TEA", title_fontsize=6.5)
    footer(fig)
    fig.tight_layout(rect=(0, 0.03, 1, 1))
    fig.savefig(FIG / "catalyst_econ_cost_per_kg.png", dpi=150)
    plt.close(fig)
    # (b) break-even price vs floor and central (fixed 100 kg, exchanger; cost-optimal, exchanger)
    fig, ax = plt.subplots(figsize=(9, 4.4))
    low = [c for c in cats if c != NI]
    x = range(len(low))
    sel1 = [next((r for r in be_rows if r["catalyst_id"] == c and r["mode"] == "exchanger" and "python_Top_X095_HI_exchanger" in r["reference"]), None) for c in low]
    sel2 = [next((r for r in be_rows if r["catalyst_id"] == c and r["mode"] == "exchanger" and r["reference"].startswith("Ni/MgO cost-optimal")), None) for c in low]
    ax.plot(x, [r["breakeven_price_fixed_design_USD_per_kg"] or float("nan") for r in sel1], "s", color=PALETTE[0], label="break-even, kinetic T_op at X 0.95 vs Ni 594 degC")
    ax.plot(x, [r["breakeven_price_reoptimised_USD_per_kg"] or float("nan") for r in sel2], "o", color=PALETTE[1], label="break-even, cost-optimal vs Ni optimum (re-optimised)")
    ax.plot(x, [pc(c, "low") for c in low], "_", ms=22, color="k", label="metal-content floor (derived low)")
    ax.plot(x, [pc(c, "central") for c in low], "_", ms=22, color=PALETTE[3], label="derived central price")
    ax.plot(x, [cc.PUBLISHED_TEA_PRICE[c] for c in low], "x", color=C_GREY, label="published TEA price (not current)")
    ax.set_yscale("log")
    ax.set_xticks(list(x), [SH[c] for c in low], fontsize=8)
    ax.set_ylabel("catalyst price (USD/kg)")
    ax.set_title("Break-even catalyst price against the Ni/MgO reference (FEHE costed, lifetime 2 yr); all laws extrapolated to 20 bar", fontsize=8.5)
    ax.legend(fontsize=6.5)
    footer(fig)
    fig.tight_layout(rect=(0, 0.03, 1, 1))
    fig.savefig(FIG / "catalyst_econ_breakeven.png", dpi=150)
    plt.close(fig)
    # (c) sensitivity of the net LCOH difference (cost-optimal, exchanger mode)
    cases = []
    for r in sens:
        if r["case"] not in cases:
            cases.append(r["case"])
    fig, ax = plt.subplots(figsize=(9, 7.5))
    for i, cid in enumerate(low):
        v = [next((r["net_lcoh_delta_USD_per_kg"] for r in sens if r["case"] == n and r["catalyst"] == SH[cid]), float("nan")) for n in cases]
        ax.plot(v, range(len(cases)), "o", ms=4, color=PALETTE[i % len(PALETTE)], label=SH[cid])
    ax.axvspan(-RES, RES, color=C_GREY, alpha=0.2, label=f"below resolution (+/-{RES:.4f})")
    ax.axvline(0, color=C_GREY, lw=0.8)
    ax.set_yticks(range(len(cases)), cases, fontsize=6.5)
    ax.invert_yaxis()
    ax.set_xlabel("LCOH(low-T catalyst design) - LCOH(Ni/MgO design), USD/kg H2; < 0 favours the low-T catalyst")
    ax.set_title("Sensitivity of the catalyst choice (each design re-optimised; FEHE costed)", fontsize=9)
    ax.legend(fontsize=7)
    footer(fig)
    fig.tight_layout(rect=(0, 0.03, 1, 1))
    fig.savefig(FIG / "catalyst_econ_sensitivity.png", dpi=150)
    plt.close(fig)


if __name__ == "__main__":
    main()
