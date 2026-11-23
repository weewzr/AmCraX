"""Workstream H: heat integration coupled to catalyst performance; catalyst cost comparison (hypothesis H3).

Deterministic; run from the project root:  python scripts/research/catalyst_comparison.py
Writes results/research/catalyst_comparison/*.json/.csv, results/figures/research/catalyst_*.png and
results/research/validation/catalyst_comparison.json. Method: backend/amcrax/research/catalyst_comparison.py.
"""
from __future__ import annotations

import csv
import json
import math
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))

import matplotlib  # noqa: E402

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
from scipy.optimize import brentq  # noqa: E402

from amcrax.heat_integration import analyse  # noqa: E402
from amcrax.plotstyle import C_GREY, PALETTE, apply_style  # noqa: E402
from amcrax.research import catalyst_comparison as cc  # noqa: E402
from amcrax.economics.reference import load_reference_scenario, provenance_stamp  # noqa: E402
REF = load_reference_scenario()   # Phase 2 unified reference scenario (cost inputs, named reproduction fields)
from amcrax.schemas import SimulationResult  # noqa: E402

SCRIPT = "scripts/research/catalyst_comparison.py"
OUT = ROOT / "results" / "research" / "catalyst_comparison"
FIG = ROOT / "results" / "figures" / "research"
VAL = ROOT / "results" / "research" / "validation"
ASP = ROOT / "results" / "research" / "aspen_kinetic"
for d in (OUT, FIG, VAL):
    d.mkdir(parents=True, exist_ok=True)
NOW = datetime.now(timezone.utc).isoformat(timespec="seconds")
CATS = list(cc.CATALYSTS)
T_GRID = [float(t) for t in range(470, 761, 5)]
BASE = dict(P_bar=20.0, X=0.95, hi=True, dT=20.0, psa=0.85, feff=cc.FURNACE_EFFICIENCY, scenario="grey")
ASPEN_CASES = {"ru_kum_temkin_pyzhev": "kum_T499", "nire_ceo2_5ni1ru_lucentini_lhhw": "luc5_T572",
               "nire_ceo2_2p5ni0p5ru_lucentini_lhhw": "luc25_T576", "ni_takahashi_microkinetic": "tni_T594",
               "ru_takahashi_microkinetic": "tru_T522"}
FOOT = ("AmCraX workstream H | kinetics: python PFR (amcrax.reactor.pfr), flowsheet: python at kinetic X, "
        "Aspen Plus V15 where marked | economics: amcrax.economics.singapore | furnace eff. 0.85 (assumption)")


def prov(source_type: str, summary: str) -> dict:
    return {"generated_utc": NOW, "script": SCRIPT, "source_type": source_type, "inputs_summary": summary,
            "reference_scenario": provenance_stamp(),
            "model_versions": {"kinetics": "backend/amcrax/data/kinetics.yaml via amcrax.reactor.pfr",
                               "flowsheet": "amcrax.process_model.run_python_case (cracker at kinetic conversion)",
                               "heat_integration": "amcrax.heat_integration.analyse (problem table)",
                               "economics": "amcrax.economics.singapore.evaluate (Phase 2 reference scenario, CAPEX cho2026_itemised_v1)",
                               "lca": "amcrax.enduse.pathways.carbon_intensity + amcrax.environmental.lca",
                               "aspen": "results/research/aspen_kinetic/ci_*.json (Aspen Plus V15, PENG-ROB)"}}


def clean(o):
    if isinstance(o, dict):
        return {str(k): clean(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [clean(v) for v in o]
    if hasattr(o, "model_dump"):
        return clean(o.model_dump(mode="json"))
    if hasattr(o, "item") and not isinstance(o, (str, bytes)):
        o = o.item()
    if isinstance(o, float) and (o != o or o in (float("inf"), float("-inf"))):
        return None
    return o


def dump(name: str, obj) -> None:
    (OUT / name).write_text(json.dumps(clean(obj), indent=2, allow_nan=False), encoding="utf-8")


def write_csv(path: Path, rows: list[dict]) -> None:
    if not rows:
        return
    keys: list[str] = []
    for r in rows:
        for k in r:
            if k not in keys:
                keys.append(k)
    with open(path, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=keys)
        w.writeheader()
        for r in rows:
            w.writerow({k: (json.dumps(clean(v)) if isinstance(v, (dict, list)) else clean(v)) for k, v in r.items()})


def footer(fig, text=FOOT):
    fig.text(0.01, 0.003, text, fontsize=6.0, color=C_GREY, ha="left", va="bottom")


def flat(d: dict, keys=None) -> dict:
    out = {}
    for k, v in d.items():
        if isinstance(v, dict):
            for k2, v2 in v.items():
                if not isinstance(v2, (dict, list)):
                    out[f"{k}.{k2}"] = v2
        elif not isinstance(v, list):
            out[k] = v
    return out


def curve(cid, **kw):
    a = dict(BASE)
    a.update(kw)
    return cc.lcoh_curve(cid, T_GRID, P_bar=a["P_bar"], X=a["X"], hi=a["hi"], dT=a["dT"], psa=a["psa"], feff=a["feff"],
                         scenario=a["scenario"], price=a.get("price"), lifetime=a.get("lifetime", cc.CATALYST_LIFETIME_YR),
                         kinetic_factor=a.get("kinetic_factor", 1.0), capex_volume_scaling=a.get("capex_volume_scaling", False),
                         econ_overrides=a.get("econ_overrides"))


def main() -> None:
    apply_style()
    val: list[dict] = []

    def add(id_, desc, method, ref, obs, exp, tol, unit, status, files):
        val.append({"id": id_, "description": desc, "method": method, "reference_source": ref, "observed": obs,
                    "expected": exp, "tolerance": tol, "unit": unit, "status": status, "source_files": files})

    # ---------------------------------------------------------------- 0. pinch check against the baseline value
    base = SimulationResult.model_validate(json.loads((ROOT / "results/simulations/baseline.json").read_text(encoding="utf-8")))
    hb = cc.heat_accounting(base, 20.0)
    add("HCAT-PINCH-BASELINE", "Heat import after FEHE and tail-gas firing (config c) for the stored Aspen baseline, dT_min 20 K",
        "cc.heat_accounting(results/simulations/baseline.json, 20)", "docs/internal/fact_sheet.md F7 (752.6 kW)",
        round(hb["external_heat_import_kW"], 2), 752.6, 0.1, "kW",
        "pass" if abs(hb["external_heat_import_kW"] - 752.6) <= 0.1 else "fail", ["results/simulations/baseline.json"])

    # ---------------------------------------------------------------- 1. kinetic design curves and cost-optimal T
    curves, optima, details = {}, {}, {}
    for hi in (True, False):
        for cid in CATS:
            c = curve(cid, hi=hi)
            curves[(cid, hi)] = c
            oc = cc.optimum(c)
            # local refinement on a 1 K grid around the 5 K optimum
            loc = cc.lcoh_curve(cid, [oc["T_C"] + k for k in range(-5, 6)], P_bar=BASE["P_bar"], X=BASE["X"], hi=hi,
                                dT=BASE["dT"], psa=BASE["psa"], feff=BASE["feff"], scenario=BASE["scenario"])
            o = cc.optimum(loc)
            eq_limited = bool(o["T_C"] <= min(r["T_C"] for r in loc)
                              and cc.eq_conversion(o["T_C"] - 1.0, BASE["P_bar"]) <= BASE["X"] + 1e-4)
            o["equilibrium_limited"] = eq_limited
            o["at_grid_bound"] = bool((o["at_grid_bound"] and not eq_limited) or oc["T_C"] >= max(T_GRID))
            lmin = o["lcoh_USD_per_kg"]
            near = [r["T_C"] for r in c if r["lcoh_USD_per_kg"] <= lmin + 0.001]
            o["T_range_within_0.001USD_kg_C"] = [min(near + [o["T_C"]]), max(near + [o["T_C"]])]
            optima[(cid, hi)] = o
            d = cc.design_point(cid, o["T_C"], BASE["P_bar"], BASE["X"], heat_integration=hi, W_kg=o["W_kg"])
            d["source_type"] = "python"
            d["at_grid_bound"] = o["at_grid_bound"]
            d["equilibrium_limited_optimum"] = o["equilibrium_limited"]
            d["T_range_within_0.001USD_kg_C"] = o["T_range_within_0.001USD_kg_C"]
            details[(cid, hi)] = d
            full = d["lcoh_USD_per_kg"]
            add(f"HCAT-ECON-ADD-{cc.CATALYSTS[cid]['short']}-{'HI' if hi else 'noHI'}",
                "Catalyst cost added analytically on the T grid equals a full evaluate() call at the optimum",
                "lcoh_curve vs design_point at T_opt", "amcrax.economics.singapore.evaluate", o["lcoh_USD_per_kg"], full,
                1e-9, "USD/kg H2", "pass" if abs(o["lcoh_USD_per_kg"] - full) <= 1e-9 else "fail",
                ["backend/amcrax/research/catalyst_comparison.py"])
            add(f"HCAT-OPT-INTERIOR-{cc.CATALYSTS[cid]['short']}-{'HI' if hi else 'noHI'}",
                "Cost-optimal temperature lies inside the temperature grid, or at the equilibrium-limited lowest feasible "
                "temperature (then reported as informational: the optimum is bounded by equilibrium, not by the grid)",
                "argmin over 5 K grid, refined on 1 K", "-", o["T_C"], "interior of feasible grid", None, "degC",
                "informational" if o["equilibrium_limited"] else ("pass" if not o["at_grid_bound"] else "fail"),
                ["results/research/catalyst_comparison/catalyst_design_curves.csv"])
    rows_curves = [{"catalyst_id": cid, "heat_integration": hi, **r, "source_type": "python"}
                   for (cid, hi), c in curves.items() for r in c]
    write_csv(OUT / "catalyst_design_curves.csv", rows_curves)

    # energy balance of every python configuration at the optimum
    for (cid, hi), d in details.items():
        res = cc.kinetic_flowsheet(d["T_C"], BASE["P_bar"], BASE["X"], hi)
        b = res.balances
        ok = abs(b.energy_closure_rel) < 1e-6 and abs(b.mass_closure_rel) < 1e-5 and abs(d["heat_pinch_energy_balance_residual_kW"]) < 1e-6
        add(f"HCAT-EB-PY-{cc.CATALYSTS[cid]['short']}-{'HI' if hi else 'noHI'}",
            f"Energy and mass balance closure, python flowsheet at T_opt {d['T_C']:.0f} degC, X {BASE['X']}",
            "flowsheet balances + problem-table residual", "-",
            {"energy_closure_rel": b.energy_closure_rel, "mass_closure_rel": b.mass_closure_rel,
             "pinch_residual_kW": d["heat_pinch_energy_balance_residual_kW"]}, 0.0, "1e-6 rel / 1e-5 mass / 1e-6 kW", "-",
            "pass" if ok else "fail", ["backend/amcrax/research/catalyst_comparison.py"])

    # ---------------------------------------------------------------- 2. Aspen operating points (T_op from kinetics)
    aspen_rows, dT_rows = [], []
    for cid, tag in ASPEN_CASES.items():
        for hi in (True, False):
            fn = f"ci_{tag}_P20_W100_{'hi' if hi else 'nohi'}.json"
            j = json.loads((ASP / fn).read_text(encoding="utf-8"))
            res = SimulationResult.model_validate(j["aspen"]["flowsheet_result"])
            T = res.inputs.reactor_temperature_C
            X = res.kpis.nh3_conversion
            d = cc.design_point(cid, T, 20.0, round(X, 6), heat_integration=hi, W_kg=100.0, result=res)
            d["source_type"] = "aspen"
            d["economics_source_type"] = "python (amcrax.economics.singapore on Aspen duties)"
            d["lca_source_type"] = "python (amcrax.enduse.pathways on Aspen activity data)"
            d["source_files"] = [f"results/research/aspen_kinetic/{fn}"]
            b = res.balances
            add(f"HCAT-EB-ASPEN-{cc.CATALYSTS[cid]['short']}-{'HI' if hi else 'noHI'}",
                f"Energy balance closure of the Aspen integrated case {fn}", "SimulationResult.balances (stored Aspen run)",
                "Aspen Plus V15", b.energy_closure_rel, 0.0, 1e-3, "relative",
                "pass" if b.energy_closure_rel is not None and abs(b.energy_closure_rel) <= 1e-3 else "fail",
                [f"results/research/aspen_kinetic/{fn}"])
            # python at the same T and X
            py = cc.design_point(cid, T, 20.0, X, heat_integration=hi, W_kg=100.0)
            d["python_same_T_X"] = {k: py[k] for k in ("heat_kpi_total_external_heating_kW", "heat_external_heat_import_kW",
                                                         "heat_recovered_heat_kW", "heat_kpi_tailgas_combustion_heat_kW",
                                                         "lcoh_USD_per_kg", "rec_USD_per_kg", "supplementary_nh3_kg_h")}
            for key, lab in (("heat_kpi_total_external_heating_kW", "total external heating (KPI)"),
                             ("heat_kpi_tailgas_combustion_heat_kW", "tail-gas combustion heat"),
                             ("heat_recovered_heat_kW", "recovered heat (FEHE)")):
                a_, p_ = d[key], py[key]
                if not hi and key == "heat_recovered_heat_kW":
                    continue
                rel = (p_ - a_) / abs(a_) if a_ else None
                add(f"HCAT-ASPY-{cc.CATALYSTS[cid]['short']}-{'HI' if hi else 'noHI'}-{key.split('_')[2]}",
                    f"Python flowsheet vs Aspen, {lab}, {cc.CATALYSTS[cid]['label']} at {T:.0f} degC, X {X:.4f}",
                    "python kinetic_flowsheet at Aspen T and X vs stored Aspen run", "Aspen Plus V15 (PENG-ROB)",
                    p_, a_, 0.03, "relative", "pass" if rel is not None and abs(rel) <= 0.03 else "fail",
                    [f"results/research/aspen_kinetic/{fn}"])
            aspen_rows.append(d)
            for dT in (10.0, 20.0, 30.0, 40.0, 50.0):
                h = cc.heat_accounting(res, dT)
                dT_rows.append({"catalyst_id": cid, "heat_integration": hi, "T_C": T, "dT_min_K": dT,
                                "external_heat_import_kW": h["external_heat_import_kW"],
                                "pinch_min_hot_utility_with_flue_kW": h["pinch_min_hot_utility_with_flue_kW"],
                                "pinch_min_hot_utility_process_only_kW": h["pinch_min_hot_utility_process_only_kW"],
                                "source_type": "aspen (duties) + python (pinch)"})
    for dT in (10.0, 20.0, 30.0, 40.0, 50.0):
        h = cc.heat_accounting(base, dT)
        dT_rows.append({"catalyst_id": "baseline_rgibbs_600C", "heat_integration": True, "T_C": 600.0, "dT_min_K": dT,
                        "external_heat_import_kW": h["external_heat_import_kW"],
                        "pinch_min_hot_utility_with_flue_kW": h["pinch_min_hot_utility_with_flue_kW"],
                        "pinch_min_hot_utility_process_only_kW": h["pinch_min_hot_utility_process_only_kW"],
                        "source_type": "aspen (duties) + python (pinch)"})
    write_csv(OUT / "catalyst_pinch_dTmin.csv", dT_rows)

    # ---------------------------------------------------------------- 3. break-even catalyst price
    ref = optima[(cc.REFERENCE_NI, True)]
    be_rows = []
    for cid in CATS:
        if cid == cc.REFERENCE_NI:
            continue

        def f(p, cid=cid, ref_l=ref["lcoh_USD_per_kg"]):
            return cc.optimum(curve(cid, price=p))["lcoh_USD_per_kg"] - ref_l
        lo, hi_ = 0.0, 1e6
        pbe = brentq(f, lo, hi_, xtol=0.01) if f(lo) < 0 < f(hi_) else (None if f(lo) >= 0 else float("inf"))
        o_be = cc.optimum(curve(cid, price=pbe)) if pbe not in (None, float("inf")) else None
        be_rows.append({"catalyst_id": cid, "catalyst": cc.CATALYSTS[cid]["label"],
                        "reference": cc.CATALYSTS[cc.REFERENCE_NI]["label"] + " at its cost-optimal T",
                        "reference_lcoh_USD_per_kg": ref["lcoh_USD_per_kg"], "reference_T_C": ref["T_C"],
                        "breakeven_price_USD_per_kg": pbe, "assumed_price_USD_per_kg": cc.CATALYSTS[cid]["price"],
                        "ratio_breakeven_to_Cho_Ru_price": (pbe / cc.CHO_PRICE["Ru"]) if pbe not in (None, float("inf")) else None,
                        "T_opt_at_breakeven_C": o_be["T_C"] if o_be else None, "W_at_breakeven_kg": o_be["W_kg"] if o_be else None,
                        "lcoh_at_zero_price_minus_ref_USD_per_kg": f(0.0), "source_type": "python",
                        "basis": "grey 450 USD/t, 20 bar, X 0.95, HI on, catalyst T re-optimised at each price"})
    # break-even versus Ni operated at a conventional high temperature (fixed design, not optimised)
    ni_fixed = {}
    for Tn in (700.0, 735.0):
        cN = [r for r in curve(cc.REFERENCE_NI) if abs(r["T_C"] - Tn) < 1e-9][0]
        ni_fixed[Tn] = cN
        for cid in CATS:
            if cid == cc.REFERENCE_NI:
                continue

            def g(p, cid=cid, l=cN["lcoh_USD_per_kg"]):
                return cc.optimum(curve(cid, price=p))["lcoh_USD_per_kg"] - l
            pbe = brentq(g, 0.0, 1e6, xtol=0.01) if g(0.0) < 0 < g(1e6) else None
            be_rows.append({"catalyst_id": cid, "catalyst": cc.CATALYSTS[cid]["label"],
                            "reference": f"Ni/MgO fixed at {Tn:.0f} degC", "reference_lcoh_USD_per_kg": cN["lcoh_USD_per_kg"],
                            "reference_T_C": Tn, "breakeven_price_USD_per_kg": pbe,
                            "assumed_price_USD_per_kg": cc.CATALYSTS[cid]["price"],
                            "ratio_breakeven_to_Cho_Ru_price": pbe / cc.CHO_PRICE["Ru"] if pbe else None,
                            "lcoh_at_zero_price_minus_ref_USD_per_kg": g(0.0), "source_type": "python",
                            "basis": "grey 450 USD/t, 20 bar, X 0.95, HI on"})
    dump("catalyst_breakeven_price.json", {"provenance": prov("python", "break-even catalyst price vs Ni reference"), "rows": be_rows})
    write_csv(OUT / "catalyst_breakeven_price.csv", be_rows)

    # ---------------------------------------------------------------- 4. sensitivities and ranking robustness
    ru_like = [c for c in CATS if cc.CATALYSTS[c]["family"] != "Ni"]
    cases = [("base", {}, None, None)]
    for m in (0.5, 2.0, 4.0, 8.0):
        cases.append((f"Ru_price_x{m:g}", {}, {c: cc.CHO_PRICE["Ru"] * m for c in ru_like}, None))
    for p in (16.7, 66.8):
        cases.append((f"Ni_price_{p:g}", {}, {cc.REFERENCE_NI: p}, None))
    for lt in (1.0, 4.0):
        cases.append((f"lifetime_{lt:g}yr", {"lifetime": lt}, None, None))
    for pr in (300.0, 610.0, 1000.0):
        cases.append((f"NH3_{pr:g}USD_t", {"scenario": pr}, None, None))
    for el in REF.sens("electricity_USD_per_kWh"):
        cases.append((f"electricity_{el:g}", {"econ_overrides": {"electricity_price_USD_per_kWh": el}}, None, None))
    for P in (10.0, 30.0):
        cases.append((f"P_{P:g}bar", {"P_bar": P}, None, None))
    for dT in (10.0, 30.0, 50.0):
        cases.append((f"dTmin_{dT:g}K", {"dT": dT}, None, None))
    for fe in cc.FURNACE_EFFICIENCY_RANGE:
        cases.append((f"furnace_eff_{fe:g}", {"feff": fe}, None, None))
    for X in (0.90, 0.97, 0.99):
        cases.append((f"X_{X:g}", {"X": X}, None, None))
    cases.append(("no_heat_integration", {"hi": False}, None, None))
    cases.append(("psa_recovery_0.756", {"psa": 0.756}, None, None))
    cases.append(("cracker_capex_scales_with_bed_volume", {"capex_volume_scaling": True}, None, None))
    for kf in (0.2, 5.0):
        cases.append((f"all_rates_x{kf:g}", {}, None, {c: kf for c in CATS}))
    # adverse to the low-temperature catalysts: their rates /5 (Lucentini Ek CI gives about x3-5 at 572 degC),
    # Ni nominal; and the reverse
    cases.append(("Ru_NiRu_rates_div5_Ni_nominal", {}, None, {c: 0.2 for c in ru_like}))
    cases.append(("Ni_rate_div5_others_nominal", {}, None, {cc.REFERENCE_NI: 0.2}))
    cases.append(("Ru_price_x4_and_rates_div5", {}, {c: cc.CHO_PRICE["Ru"] * 4 for c in ru_like}, {c: 0.2 for c in ru_like}))

    rank_rows, rob = [], []
    base_rank = None
    for name, kw, pmap, kmap in cases:
        res = {}
        for cid in CATS:
            k = dict(kw)
            if pmap and cid in pmap:
                k["price"] = pmap[cid]
            if kmap and cid in kmap:
                k["kinetic_factor"] = kmap[cid]
            o = cc.optimum(curve(cid, **k))
            res[cid] = o
        order = sorted(CATS, key=lambda c: res[c]["lcoh_USD_per_kg"] if res[c] else 1e9)
        if name == "base":
            base_rank = order
        refl = res[cc.REFERENCE_NI]["lcoh_USD_per_kg"]
        for cid in CATS:
            o = res[cid]
            rank_rows.append({"case": name, "catalyst_id": cid, "catalyst": cc.CATALYSTS[cid]["label"],
                              "rank": order.index(cid) + 1, "T_opt_C": o["T_C"], "W_kg": o["W_kg"],
                              "lcoh_USD_per_kg": o["lcoh_USD_per_kg"], "rec_USD_per_kg": o["rec_USD_per_kg"],
                              "delta_vs_Ni_USD_per_kg": o["lcoh_USD_per_kg"] - refl,
                              "external_heat_import_kW": o["external_heat_import_kW"],
                              "supplementary_nh3_kg_h": o["supplementary_nh3_kg_h"], "at_grid_bound": o["at_grid_bound"],
                              "source_type": "python"})
        spread = max(r["lcoh_USD_per_kg"] for r in res.values()) - min(r["lcoh_USD_per_kg"] for r in res.values())
        rob.append({"case": name, "ranking": [cc.CATALYSTS[c]["short"] for c in order], "best": cc.CATALYSTS[order[0]]["label"],
                    "same_ranking_as_base": order == base_rank, "same_best_as_base": order[0] == base_rank[0],
                    "best_low_T_minus_Ni_USD_per_kg": min(res[c]["lcoh_USD_per_kg"] for c in ru_like) - refl,
                    "spread_USD_per_kg": spread, "source_type": "python"})
    write_csv(OUT / "catalyst_sensitivity_ranking.csv", rank_rows)
    dump("catalyst_ranking_robustness.json", {"provenance": prov("python", "re-optimised T per catalyst per case"),
                                              "cases": rob, "rows": rank_rows})

    # ---------------------------------------------------------------- 5. Cho et al. (2026) reference designs
    cho_rows = []
    cho_ov = REF.reproduction("cho2026")   # named field: Cho 2026 Table 4 basis, used only for this reconstruction
    m_cho = cc.FEED_NH3_KMOL_H * 1000.0 * 22.414 * 1000.0 / 9000.0 / 1000.0  # GHSV 9000 mL/(g h), cho2026nickel Table 3
    designs = [("Ni_735.52C_24.34bar", cc.REFERENCE_NI, 735.52, 24.34), ("RuAl2O3_566.69C_10bar", "ru_kum_temkin_pyzhev", 566.69, 10.0),
               ("RuMgO_566.69C_10bar", "ru_takahashi_microkinetic", 566.69, 10.0),
               ("Ni_swap_566.69C_10bar", cc.REFERENCE_NI, 566.69, 10.0)]
    for psa in (0.85, 0.756):
        for inv in ("cho_ghsv_9000", "kinetic_minimum"):
            for name, cid, T, P in designs:
                Wk = cc.required_mass_kg(cid, T, P, 0.97)
                W = m_cho if inv == "cho_ghsv_9000" else Wk
                d = cc.design_point(cid, T, P, 0.97, W_kg=W, psa_recovery=psa, econ_overrides=cho_ov)
                cho_rows.append({"design": name, "psa_recovery": psa, "inventory_basis": inv, "catalyst": d["catalyst"],
                                 "T_C": T, "P_bar": P, "X": 0.97, "W_kg": W, "W_kinetic_min_kg": Wk,
                                 "X_cho_basis_at_W": None, "external_heat_import_kW": d["heat_external_heat_import_kW"],
                                 "fired_process_duty_kW": d["fired_process_duty_kW"],
                                 "supplementary_nh3_kg_h": d["supplementary_nh3_kg_h"],
                                 "supplementary_fuel_needed": d["supplementary_fuel_needed"],
                                 "first_law_deficit_kW": d["heat_kpi_net_fuel_heat_deficit_kW_first_law"],
                                 "tailgas_heat_kW": d["heat_kpi_tailgas_combustion_heat_kW"],
                                 "h2_product_kg_h": d["h2_product_kg_h"], "lcoh_USD_per_kg": d["lcoh_USD_per_kg"],
                                 "rec_USD_per_kg": d["rec_USD_per_kg"], "catalyst_USD_per_kg": d["breakdown_USD_per_kg"]["catalyst"],
                                 "kg_nh3_total_per_kg_h2": d["carbon"]["kg_nh3_total_per_kg_h2"], "source_type": "python"})
    cho_summary = []
    for psa in (0.85, 0.756):
        for inv in ("cho_ghsv_9000", "kinetic_minimum"):
            g = {r["design"]: r for r in cho_rows if r["psa_recovery"] == psa and r["inventory_basis"] == inv}
            ni, ru = g["Ni_735.52C_24.34bar"], g["RuAl2O3_566.69C_10bar"]
            cho_summary.append({"psa_recovery": psa, "inventory_basis": inv,
                                "rec_Ni": ni["rec_USD_per_kg"], "rec_Ru": ru["rec_USD_per_kg"],
                                "rec_Ru_lower_by_pct": 100 * (1 - ru["rec_USD_per_kg"] / ni["rec_USD_per_kg"]),
                                "lcoh_Ru_lower_by_pct": 100 * (1 - ru["lcoh_USD_per_kg"] / ni["lcoh_USD_per_kg"]),
                                "Ni_needs_supplementary_fuel": ni["supplementary_fuel_needed"],
                                "Ru_needs_supplementary_fuel": ru["supplementary_fuel_needed"],
                                "Ni_supp_nh3_kg_h": ni["supplementary_nh3_kg_h"], "Ru_supp_nh3_kg_h": ru["supplementary_nh3_kg_h"],
                                "cho_values": {"rec_Ni": 1.995, "rec_Ru": 1.856, "rec_Ru_lower_by_pct": 7.0, "lcoh_Ru_lower_by_pct": 2.7,
                                               "Ni_fuel_kmol_h": 1.736, "Ru_fuel_kmol_h": 0.0,
                                               "source": "research/notes/cho2026nickel.md (Table 7 p. 13, p. 14-15)",
                                               "source_type": "literature"}})
    dump("catalyst_cho_comparison.json", {"provenance": prov("python", "Cho et al. 2026 reference designs on AmCraX boundaries"),
                                          "boundary_differences": [
                                              "AmCraX has no product compression to 180 bar, no H2 recycle, no TSA, no expander, no NOx SCR cost.",
                                              "Kinetics are proxies: Ni/MgO and Ru/Al2O3, Ru/MgO laws; Cho uses Ni/Al2O3 (Collins 1993) and Ru-K/CaO (Sayas 2020), both in an unavailable SI.",
                                              "Cho optimises T, P and reactor jointly with the Aspen boiler; here T and P are fixed to Cho's optima.",
                                              "Economic overrides: discount 8.5 %, electricity 0.084 USD/kWh, 25 yr (cho2026nickel Table 4); CAPEX from amcrax.economics.singapore (does not respond to T or P)."],
                                          "designs": cho_rows, "summary": cho_summary})
    write_csv(OUT / "catalyst_cho_comparison.csv", cho_rows)
    for s in cho_summary:
        add(f"HCAT-CHO-DIR-psa{s['psa_recovery']}-{s['inventory_basis']}",
            "Direction and size of the Ru vs Ni REC difference compared with Cho et al. (2026)",
            "AmCraX Ni 735.52 degC/24.34 bar vs Ru/Al2O3 566.69 degC/10 bar, X 0.97", "cho2026nickel Table 7 (7.0 % lower)",
            s["rec_Ru_lower_by_pct"], 7.0, None, "%", "informational", ["results/research/catalyst_comparison/catalyst_cho_comparison.json"])

    # ---------------------------------------------------------------- 6. summary table
    table = []
    for d in aspen_rows:
        table.append({"row_id": f"aspen_Top_{cc.CATALYSTS[d['catalyst_id']]['short']}_{'HI' if d['heat_integration'] else 'noHI'}",
                      "design_basis": "kinetic operating temperature (100 kg, 95 % conversion, 20 bar; workstreams K/A)", **d})
    for (cid, hi), d in details.items():
        table.append({"row_id": f"python_Topt_{cc.CATALYSTS[cid]['short']}_{'HI' if hi else 'noHI'}",
                      "design_basis": "cost-optimal temperature (min LCOH over T with W(T) for X 0.95, 20 bar)",
                      "source_files": ["results/research/catalyst_comparison/catalyst_design_curves.csv"], **d})
    for Tn, cN in ni_fixed.items():
        d = cc.design_point(cc.REFERENCE_NI, Tn, 20.0, 0.95, W_kg=cN["W_kg"])
        d["source_type"] = "python"
        table.append({"row_id": f"python_fixed_Ni_{Tn:.0f}C_HI", "design_basis": f"fixed reference design: Ni at {Tn:.0f} degC",
                      "source_files": ["results/research/catalyst_comparison/catalyst_design_curves.csv"], **d})
    summary_obj = {
        "provenance": prov("mixed (per row)", "Aspen integrated ci_* runs at the kinetic T_op; python flowsheet at kinetic X elsewhere"),
        "basis": {"feed": "100 kmol/h liquid NH3 (0.2 mol% H2O), 20 bar, 95 % NH3 conversion for every catalyst, PSA recovery 0.85",
                  "operating_temperature": "from kinetics: W(T) for the conversion target; T_opt = argmin LCOH over 470-760 degC (5 K)",
                  "heat_import": "temperature-feasible import after FEHE and tail-gas firing (amcrax.heat_integration config (c); "
                                 "without FEHE: problem table of feed + reaction vs flue gas), dT_min 20 K",
                  "furnace": f"supplementary NH3 at furnace efficiency {cc.FURNACE_EFFICIENCY} plus {cc.THERMAL_LOSS_FRACTION:.0%} "
                             "thermal loss of reactor + trim heater duty (assumptions)",
                  "economics": "amcrax.economics.singapore.evaluate, grey 450 USD/t, catalyst W*price/lifetime (2 yr)",
                  "lca": "GWP100, 5000 km ship, routes grey/blue/green (amcrax.environmental.lca)"},
        "rows": table}
    asp = {(d["catalyst_id"], d["heat_integration"]): d for d in aspen_rows}
    ni_a, ru_a = asp[(cc.REFERENCE_NI, True)], asp[("ru_kum_temkin_pyzhev", True)]
    ni_an, ru_an = asp[(cc.REFERENCE_NI, False)], asp[("ru_kum_temkin_pyzhev", False)]
    summary_obj["findings"] = {
        "fixed_inventory_100kg_aspen": {
            "fired_duty_HI_kW": {lab_: asp[(c, True)]["fired_process_duty_kW"] for c, lab_ in ((c, cc.CATALYSTS[c]["short"]) for c in CATS)},
            "fired_duty_noHI_kW": {cc.CATALYSTS[c]["short"]: asp[(c, False)]["fired_process_duty_kW"] for c in CATS},
            "lcoh_HI_USD_per_kg": {cc.CATALYSTS[c]["short"]: asp[(c, True)]["lcoh_USD_per_kg"] for c in CATS},
            "lcoh_noHI_USD_per_kg": {cc.CATALYSTS[c]["short"]: asp[(c, False)]["lcoh_USD_per_kg"] for c in CATS},
            "Ru_Al2O3_vs_Ni_fired_duty_reduction_HI": 1 - ru_a["fired_process_duty_kW"] / ni_a["fired_process_duty_kW"],
            "Ru_Al2O3_vs_Ni_fired_duty_reduction_noHI": 1 - ru_an["fired_process_duty_kW"] / ni_an["fired_process_duty_kW"],
            "Ru_Al2O3_minus_Ni_lcoh_HI": ru_a["lcoh_USD_per_kg"] - ni_a["lcoh_USD_per_kg"],
            "Ru_Al2O3_minus_Ni_lcoh_noHI": ru_an["lcoh_USD_per_kg"] - ni_an["lcoh_USD_per_kg"],
            "source_type": "aspen (duties) + python (economics)"},
        "cost_optimal_python": {
            cc.CATALYSTS[c]["short"]: {f"{'HI' if hi else 'noHI'}": {
                "T_opt_C": details[(c, hi)]["T_C"], "W_kg": details[(c, hi)]["W_kg"],
                "bed_volume_m3": details[(c, hi)]["bed_volume_m3"],
                "T_range_within_0.001USD_kg_C": details[(c, hi)]["T_range_within_0.001USD_kg_C"],
                "fired_duty_kW": details[(c, hi)]["fired_process_duty_kW"],
                "lcoh_USD_per_kg": details[(c, hi)]["lcoh_USD_per_kg"], "rec_USD_per_kg": details[(c, hi)]["rec_USD_per_kg"],
                "grey_kgCO2e_per_kgH2": details[(c, hi)]["carbon"]["grey_kgCO2e_per_kgH2"],
                "green_kgCO2e_per_kgH2": details[(c, hi)]["carbon"]["green_kgCO2e_per_kgH2"]} for hi in (True, False)}
            for c in CATS},
        "ranking_robustness": {"n_cases": len(rob), "n_same_best_as_base": sum(r["same_best_as_base"] for r in rob),
                               "cases_where_a_low_T_catalyst_beats_Ni": [r["case"] for r in rob if r["best_low_T_minus_Ni_USD_per_kg"] < 0],
                               "max_abs_best_low_T_minus_Ni_USD_per_kg": max(abs(r["best_low_T_minus_Ni_USD_per_kg"]) for r in rob)},
        "breakeven_price": [{k: r[k] for k in ("catalyst", "reference", "breakeven_price_USD_per_kg")} for r in be_rows],
    }
    dump("catalyst_comparison.json", summary_obj)
    write_csv(OUT / "catalyst_comparison.csv", [flat(r) for r in table])
    assum = list(cc.ASSUMPTIONS) + [dict(name=f"price_{c}", value=v["price"], unit="USD/kg", source_type=v["price_source_type"],
                                         source=cc.CHO_PRICE_SOURCE, applicability_note=v["price_note"]) for c, v in cc.CATALYSTS.items()]
    (OUT / "assumptions.json").write_text(json.dumps(assum, indent=2), encoding="utf-8")

    # kinetics consistency: W at the K/A operating temperature
    for cid, tag in ASPEN_CASES.items():
        Ttop = float(tag.split("_T")[1])
        W = cc.required_mass_kg(cid, Ttop, 20.0, 0.95)
        add(f"HCAT-W-TOP-{cc.CATALYSTS[cid]['short']}", "Catalyst mass for 95 % at the K/A operating temperature (rounded up 1 K, 100 kmol/h basis there)",
            "cc.required_mass_kg (99.8 kmol/h NH3)", "results/research/aspen_kinetic/catalyst_comparison.json", W, "90-100", None, "kg",
            "pass" if 90.0 <= W <= 100.0 else "fail", ["results/research/kinetics/study_temperature_for_target_conversion.json"])

    VAL.joinpath("catalyst_comparison.json").write_text(json.dumps(clean(val), indent=2), encoding="utf-8")

    # ---------------------------------------------------------------- 7. figures
    lab = {c: cc.CATALYSTS[c]["short"] for c in CATS}
    col = {c: PALETTE[i % len(PALETTE)] for i, c in enumerate(CATS)}
    # 7a heat duty vs catalyst
    fig, ax = plt.subplots(1, 2, figsize=(11, 4.3))
    asp = {(d["catalyst_id"], d["heat_integration"]): d for d in aspen_rows}
    x = np.arange(len(CATS))
    for k, hi in enumerate((True, False)):
        ax[0].bar(x + (k - 0.5) * 0.38, [asp[(c, hi)]["fired_process_duty_kW"] for c in CATS], 0.38,
                  color=PALETTE[k], label=f"fired duty, {'with' if hi else 'without'} FEHE")
    ax[0].plot(x - 0.19, [asp[(c, True)]["heat_kpi_tailgas_combustion_heat_kW"] for c in CATS], "k_", ms=18, label="tail-gas combustion heat")
    ax[0].set_xticks(x, [f"{lab[c]}\n{asp[(c, True)]['T_C']:.0f} C" for c in CATS], fontsize=7)
    ax[0].set_ylabel("kW")
    ax[0].set_title("At kinetic T_op (Aspen duties, 95 % conv., 20 bar)", fontsize=9)
    ax[0].legend(fontsize=7)
    Ts = sorted({r["T_C"] for r in curves[(CATS[0], True)]})
    for hi, ls in ((True, "-"), (False, "--")):
        cN = curves[(cc.REFERENCE_NI, hi)]
        ax[1].plot([r["T_C"] for r in cN], [r["fired_process_duty_kW"] for r in cN], ls, color=C_GREY,
                   label=f"fired duty, {'with' if hi else 'without'} FEHE (python)")
    for c in CATS:
        o = optima[(c, True)]
        ax[1].plot(o["T_C"], o["fired_process_duty_kW"], "o", color=col[c], label=f"{lab[c]} T_opt")
    ax[1].set_xlabel("reactor temperature (degC)")
    ax[1].set_ylabel("kW")
    ax[1].set_title("Fired duty vs temperature at fixed 95 % conversion", fontsize=9)
    ax[1].legend(fontsize=6.5)
    footer(fig)
    fig.tight_layout(rect=(0, 0.03, 1, 1))
    fig.savefig(FIG / "catalyst_heat_duty.png", dpi=150)
    plt.close(fig)
    write_csv(OUT / "catalyst_heat_duty_plotdata.csv",
              [{"catalyst_id": d["catalyst_id"], "heat_integration": d["heat_integration"], "T_C": d["T_C"],
                "fired_process_duty_kW": d["fired_process_duty_kW"], "tailgas_kW": d["heat_kpi_tailgas_combustion_heat_kW"],
                "source_type": "aspen"} for d in aspen_rows])

    # 7b cost breakdown (REC components) at the cost-optimal T
    comps = ["capex", "fixed_opex", "heat_fuel", "electricity", "cooling_water", "catalyst"]
    fig, ax = plt.subplots(figsize=(8, 4.3))
    bottom = np.zeros(len(CATS))
    bd_rows = []
    for i, comp in enumerate(comps):
        v = np.array([details[(c, True)]["breakdown_USD_per_kg"][comp] for c in CATS])
        ax.bar(x, v, 0.6, bottom=bottom, color=(PALETTE + [C_GREY])[i % 7], label=comp)
        bottom += v
    for c in CATS:
        bd_rows.append({"catalyst_id": c, "T_opt_C": details[(c, True)]["T_C"], "W_kg": details[(c, True)]["W_kg"],
                        **details[(c, True)]["breakdown_USD_per_kg"], "lcoh": details[(c, True)]["lcoh_USD_per_kg"], "source_type": "python"})
    ax.set_xticks(x, [f"{lab[c]}\n{details[(c, True)]['T_C']:.0f} C, {details[(c, True)]['W_kg']:.0f} kg" for c in CATS], fontsize=7)
    ax.set_ylabel("USD/kg H2 (excluding feed NH3, about 3.04)")
    ax.set_title("Cost breakdown at each catalyst's cost-optimal T (grey 450 USD/t, HI on)", fontsize=9)
    ax.legend(fontsize=7, ncol=3)
    footer(fig)
    fig.tight_layout(rect=(0, 0.03, 1, 1))
    fig.savefig(FIG / "catalyst_cost_breakdown.png", dpi=150)
    plt.close(fig)
    write_csv(OUT / "catalyst_cost_breakdown_plotdata.csv", bd_rows)

    # 7c break-even price
    fig, ax = plt.subplots(figsize=(8, 4.3))
    bb = [r for r in be_rows if r["reference"].endswith("cost-optimal T")]
    vals = [r["breakeven_price_USD_per_kg"] if r["breakeven_price_USD_per_kg"] not in (None, float("inf")) else 0 for r in bb]
    ax.bar(range(len(bb)), vals, 0.6, color=PALETTE[0], label="break-even vs Ni/MgO at its optimum")
    bb2 = [r for r in be_rows if r["reference"].startswith("Ni/MgO fixed at 735")]
    ax.plot(range(len(bb2)), [r["breakeven_price_USD_per_kg"] or 0 for r in bb2], "s", color=PALETTE[1], label="break-even vs Ni fixed at 735 degC")
    ax.axhline(cc.CHO_PRICE["Ru"], color=C_GREY, ls="--", label="Cho Ru catalyst price 542 USD/kg")
    ax.set_yscale("log")
    ax.set_xticks(range(len(bb)), [cc.CATALYSTS[r["catalyst_id"]]["short"] for r in bb], fontsize=8)
    ax.set_ylabel("catalyst price (USD/kg)")
    ax.set_title("Break-even catalyst price (equal LCOH with the Ni reference)", fontsize=9)
    ax.legend(fontsize=7)
    footer(fig)
    fig.tight_layout(rect=(0, 0.03, 1, 1))
    fig.savefig(FIG / "catalyst_breakeven_price.png", dpi=150)
    plt.close(fig)

    # 7d ranking robustness
    fig, ax = plt.subplots(figsize=(9, 7))
    names = [r["case"] for r in rob]
    for c in CATS:
        if c == cc.REFERENCE_NI:
            continue
        v = [next(rr["delta_vs_Ni_USD_per_kg"] for rr in rank_rows if rr["case"] == n and rr["catalyst_id"] == c) for n in names]
        ax.plot(v, range(len(names)), "o", color=col[c], label=lab[c], ms=4)
    ax.axvline(0, color=C_GREY, lw=0.8)
    ax.set_yticks(range(len(names)), names, fontsize=6.5)
    ax.invert_yaxis()
    ax.set_xlabel("LCOH minus Ni/MgO LCOH, each at its own cost-optimal T (USD/kg H2); < 0 = cheaper than Ni")
    ax.set_title("Ranking robustness of the catalyst comparison", fontsize=9)
    ax.legend(fontsize=7)
    footer(fig)
    fig.tight_layout(rect=(0, 0.03, 1, 1))
    fig.savefig(FIG / "catalyst_ranking_robustness.png", dpi=150)
    plt.close(fig)

    # console summary
    print("pinch baseline", round(hb["external_heat_import_kW"], 2))
    for (cid, hi), d in details.items():
        print("OPT", lab[cid], hi, d["T_C"], round(d["W_kg"], 1), round(d["fired_process_duty_kW"], 1),
              round(d["lcoh_USD_per_kg"], 4), round(d["rec_USD_per_kg"], 4), round(d["carbon"]["grey_kgCO2e_per_kgH2"], 3))
    for d in aspen_rows:
        print("ASP", lab[d["catalyst_id"]], d["heat_integration"], d["T_C"], round(d["fired_process_duty_kW"], 1),
              round(d["lcoh_USD_per_kg"], 4), round(d["rec_USD_per_kg"], 4))
    for r in be_rows:
        print("BE", r["catalyst"], r["reference"], r["breakeven_price_USD_per_kg"])
    for r in rob:
        print("ROB", r["case"], r["ranking"], round(r["best_low_T_minus_Ni_USD_per_kg"], 4), round(r["spread_USD_per_kg"], 4))
    for s in cho_summary:
        print("CHO", s)
    print("validation", {s: sum(1 for v in val if v["status"] == s) for s in ("pass", "fail", "informational")},
          [v["id"] for v in val if v["status"] == "fail"])


if __name__ == "__main__":
    main()
