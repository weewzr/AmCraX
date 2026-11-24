"""Generate the stage 3 golden reference tables (economics, carbon pricing, uncertainty quantification) for the Rust engine.

Produced ONCE by the Python reference (the ``amcrax`` package of this repository, imported from ``backend/``, at the
tagged Phase 2 baseline amcrax-phase2-reviewed-2026-11-24) and committed; never regenerated from Rust. Run from the
repository root with the project venv, naming the tables to (re)write (the others keep their MANIFEST entries):

    python rust/golden/generate_stage3_golden.py economics
    python rust/golden/generate_stage3_golden.py carbon
    python rust/golden/generate_stage3_golden.py uq

Floats are written with repr() (shortest round trip); non-finite values as "nan", "inf", "-inf". Python exceptions are
recorded as {"error": <class>, "message": ...} with the class normalised to its builtin base (pydantic's
ValidationError is a ValueError).

Stored-result checks ("stored" entries) give a RECIPE (which public function, which inputs) for every number of a
stored results/ file; the generator recomputes each recipe with Python and records whether it reproduces the stored
value, and the Rust verifier recomputes the recipe and compares with the stored file itself (read at run time).
"""

from __future__ import annotations

import hashlib
import json
import math
import os
import platform
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
RUST_DIR = HERE.parent
REPO = RUST_DIR.parent
os.environ["AMCRAX_ROOT"] = str(REPO)
sys.path.insert(0, str(REPO / "backend"))

import numpy as np  # noqa: E402
import pydantic  # noqa: E402
import scipy  # noqa: E402
import yaml  # noqa: E402

import amcrax  # noqa: E402

if Path(amcrax.__file__).resolve().parents[1] != (REPO / "backend").resolve():
    raise SystemExit(f"amcrax imported from {amcrax.__file__}, not from {REPO / 'backend'}")

from amcrax.economics import lcoh as L  # noqa: E402
from amcrax.economics import reference as R  # noqa: E402
from amcrax.economics import singapore as SG  # noqa: E402
from amcrax.schemas import SimulationResult  # noqa: E402

OUT = HERE / "stage3"
GENERATOR = "rust/golden/generate_stage3_golden.py"


def _git(*args: str) -> str:
    try:
        return subprocess.run(["git", *args], cwd=REPO, capture_output=True, text=True, check=True).stdout.strip()
    except Exception:  # noqa: BLE001
        return "unknown"


META = {"generator": GENERATOR, "python": platform.python_version(), "numpy": np.__version__,
        "scipy": scipy.__version__, "pydantic": pydantic.VERSION, "pyyaml": yaml.__version__,
        "platform": f"{platform.system()} {platform.machine()}", "amcrax_source": "backend/amcrax (this repository)",
        "git_head_at_generation": _git("rev-parse", "HEAD"),
        "python_reference_tag": "amcrax-phase2-reviewed-2026-11-24",
        "science_diff_vs_tag": _git("diff", "--stat", "amcrax-phase2-reviewed-2026-11-24", "--", "backend/amcrax",
                                    ":!backend/amcrax/api") or "none"}


def enc(o):
    if isinstance(o, dict):
        return {str(k): enc(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [enc(v) for v in o]
    if isinstance(o, np.ndarray):
        return enc(o.tolist())
    if isinstance(o, (bool, np.bool_)):
        return bool(o)
    if isinstance(o, (int, np.integer)):
        return int(o)
    if isinstance(o, (float, np.floating)):
        f = float(o)
        if math.isnan(f):
            return "nan"
        if math.isinf(f):
            return "inf" if f > 0 else "-inf"
        return f
    if o is None or isinstance(o, str):
        return o
    if hasattr(o, "model_dump"):
        return enc(o.model_dump(mode="json"))
    return str(o)


def err(e: BaseException) -> dict:
    if isinstance(e, KeyError):
        cls = "KeyError"
    elif isinstance(e, ZeroDivisionError):
        cls = "ZeroDivisionError"
    elif isinstance(e, ValueError):
        cls = "ValueError"
    elif isinstance(e, TypeError):
        cls = "TypeError"
    else:
        cls = type(e).__name__
    return {"error": cls, "message": str(e)[:300]}


def manifest() -> dict:
    p = OUT / "MANIFEST.json"
    if p.exists():
        m = json.loads(p.read_text(encoding="utf-8"))
        m["meta"] = META
        return m
    return {"meta": META, "files": {}}


MANIFEST = manifest()


def write_table(name: str, body: dict, n_cases: int) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    text = json.dumps(enc({"meta": dict(META, table=name), **body}), separators=(",", ":"), allow_nan=False) + "\n"
    data = text.encode("utf-8")
    (OUT / f"{name}.json").write_bytes(data)
    MANIFEST["files"][f"{name}.json"] = {"sha256": hashlib.sha256(data).hexdigest(), "bytes": len(data),
                                         "cases": n_cases}
    print(f"wrote rust/golden/stage3/{name}.json ({len(data)} bytes, {n_cases} cases)")


def save_manifest() -> None:
    (OUT / "MANIFEST.json").write_text(json.dumps(MANIFEST, indent=1, sort_keys=True) + "\n", encoding="utf-8")


def load(rel: str):
    return json.loads((REPO / rel).read_text(encoding="utf-8"))


def get_path(d, path):
    for k in path:
        d = d[k]
    return d


# ======================================================================================================== economics
def summaries() -> dict:
    hi = SG.extract_summary(load("results/simulations/baseline.json"))
    tv = [v for v in load("results/research/simulator/test_vectors.json")["vectors"] if v["kind"] == "economics"]
    return {
        "baseline": hi,
        "baseline_no_hi": SG.extract_summary(load("results/simulations/baseline_no_hi.json")),
        "python_baseline": SG.extract_summary(load("results/simulations/python_baseline.json")),
        "tv_python_model": dict(tv[0]["inputs"]["summary"]),
        "surplus": dict(hi, heat_deficit_kW=-150.0),
        "no_psa_info": dict(hi, psa_recovery=None, h2_cracked_kmol_h=None),
        "no_tailgas_lhv": dict(hi, tailgas_lhv_kW=None),
    }


OVERRIDE_SETS = [
    {}, {"capex_mode": "reference"}, {"capex_mode": "equipment"}, {"capex_mode": "legacy"},
    {"capex_mode": "legacy", "capex_method": "chopra2026_point"},
    {"capex_mode": "legacy", "capex_method": "farokhi2025_point", "capacity_exponent": 0.6},
    {"capex_mode": "legacy", "capex_method": "fixed", "capex_fixed_USD": 5e6},
    {"capex_mode": "legacy", "capex_method": "fixed"},
    {"capex_mode": "legacy", "capex_method": "chopra2026_point", "chopra_exclude_compressor": False,
     "chopra_remove_location_factor": False},
    {"capex_mode": "legacy", "discount_rate": 0.085, "electricity_price_USD_per_kWh": 0.084},
    {"capex_scaling_exponent": 0.6},
    {"capex_mode": "equipment", "capex_scaling_exponent": 0.7451, "capex_multiplier": 1.3},
    {"reactor_size_driver": "catalyst_mass"},
    {"reactor_size_driver": "catalyst_mass", "catalyst_mass_kg": 800.0},
    {"item_size_ratio": {"heat_exchangers": 0.7, "reactor": 1.3, "unknown_item": 2.0}},
    {"capex_multiplier": 0.5},
    {"heat_fuel": "natural_gas"},
    {"heat_fuel": "natural_gas", "apply_threshold": False, "carbon_tax_SGD_per_t": 80.0},
    {"heat_fuel": "natural_gas", "gas_heat_price_USD_per_kJ": 9e-6, "fuel_efficiency": 0.9},
    {"heat_fuel": "natural_gas", "capacity_scale": 20.0},
    {"heat_fuel": "natural_gas", "capacity_scale": 25.0},
    {"fuel_efficiency": 0.85}, {"fuel_efficiency": 0.9225},
    {"psa_recovery": 0.756}, {"psa_recovery": 0.95},
    {"capacity_scale": 0.25}, {"capacity_scale": 4.0, "labour_scales_with_capacity": True},
    {"n2o_tCO2e_per_yr": 30000.0}, {"n2o_tCO2e_per_yr": 2000.0, "other_facility_emissions_tCO2e": 24000.0},
    {"n2o_tCO2e_per_yr": 2000.0},
    {"transport_USD_per_kg_H2": 0.5}, {"h2_price_USD_per_kg": 10.0},
    {"h2_price_USD_per_kg": 6.0, "discount_rate": 0.0}, {"discount_rate": 0.0},
    {"plant_life_yr": 22.5}, {"plant_life_yr": 23.5},
    {"catalyst_mass_kg": 500.0}, {"catalyst": "Ru"},
    {"catalyst_price_USD_per_kg": 100.0, "catalyst_lifetime_yr": 4.0},
    {"operating_hours_h_per_yr": 7000.0, "electricity_price_USD_per_kWh": 0.084},
    {"maintenance_frac_capex_per_yr": 0.05, "insurance_frac_capex_per_yr": 0.01, "labour_USD_per_yr": 200000.0,
     "plant_overhead_frac_labour_maint": 0.3, "g_and_a_frac_fixed_opex": 0.1},
    {"cooling_water_price_USD_per_kJ": 1e-6}, {"ammonia_fuel_heat_efficiency": 0.8},
    {"nh3_price_USD_per_t": 333.0},
    {"electricity_price_USD_per_kWh": 0.15, "capex_multiplier": 1.2, "capex_scaling_exponent": 0.7,
     "catalyst_price_USD_per_kg": 40.0, "catalyst_lifetime_yr": 2.5, "discount_rate": 0.09,
     "operating_hours_h_per_yr": 7500.0, "plant_life_yr": 21.3, "psa_recovery": 0.8},
    # errors
    {"bogus_key": 1.0}, {"capex_mode": "bogus"}, {"heat_fuel": "coal"}, {"discount_rate": -0.1},
    {"operating_hours_h_per_yr": 9000.0}, {"catalyst": "Pt"}, {"fuel_efficiency": 0.0}, {"capacity_scale": 0.0},
]
SCENARIOS_GRID = ["grey", "blue", "green_current", "green_2030", "green_2050", 0.0, 1000.0, 333.3]


def run_eval(s, sc, o):
    try:
        return SG.evaluate(s, sc, o)
    except Exception as e:  # noqa: BLE001
        return err(e)


def economics() -> None:
    S = summaries()
    cases = []
    for sc in SCENARIOS_GRID:
        for o in OVERRIDE_SETS:
            cases.append({"summary": "baseline", "scenario": sc, "overrides": o,
                          "output": run_eval(S["baseline"], sc, o)})
    cases.append({"summary": "baseline", "scenario": "purple", "overrides": {},
                  "output": run_eval(S["baseline"], "purple", {})})
    cases.append({"summary": "baseline", "scenario": "purple", "overrides": {"nh3_price_USD_per_t": 500.0},
                  "output": run_eval(S["baseline"], "purple", {"nh3_price_USD_per_t": 500.0})})
    sub = [o for o in OVERRIDE_SETS if not any(k in o for k in ("bogus_key",))][:30]
    for name in S:
        if name == "baseline":
            continue
        for sc in ("grey", 1000.0):
            for o in sub:
                cases.append({"summary": name, "scenario": sc, "overrides": o, "output": run_eval(S[name], sc, o)})
    # extract_summary on every stored SimulationResult
    extract = []
    for p in sorted((REPO / "results/simulations").glob("*.json")):
        d = json.loads(p.read_text(encoding="utf-8"))
        if not isinstance(d, dict) or "kpis" not in d:
            continue
        rel = p.relative_to(REPO).as_posix()
        try:
            extract.append({"file": rel, "summary": SG.extract_summary(d)})
        except Exception as e:  # noqa: BLE001
            extract.append({"file": rel, "summary": err(e)})
    # break-even NH3 price
    be = []
    for name in ("baseline", "baseline_no_hi", "tv_python_model"):
        for target in (0.5, 3.0, 3.06, 6.0, 10.0):
            for o in ({}, {"fuel_efficiency": 0.85}, {"capex_mode": "equipment"}, {"capacity_scale": 5.0}):
                for metric in ("lcoh_USD_per_kg", "rec_USD_per_kg"):
                    try:
                        v = SG.breakeven_nh3_price(S[name], target, o, metric)
                    except Exception as e:  # noqa: BLE001
                        v = err(e)
                    be.append({"summary": name, "target": target, "overrides": o, "metric": metric, "value": v})
    be.append({"summary": "baseline", "target": 3.06, "overrides": {"nh3_price_USD_per_t": 400.0},
               "metric": "lcoh_USD_per_kg",
               "value": (lambda: _try(lambda: SG.breakeven_nh3_price(S["baseline"], 3.06, {"nh3_price_USD_per_t": 400.0})))()})
    # reference CAPEX
    rc = []
    kw_sets = [{}, {"exponent": 0.6}, {"capex_multiplier": 1.5}, {"location_factor": 1.2}, {"exclude": ["psa"]},
               {"exclude": ["psa", "adsorber", "other_isbl"]},
               {"reactor_size_driver": "catalyst_mass", "catalyst_mass_kg": 300.0},
               {"reactor_size_driver": "catalyst_mass"},
               {"item_size_ratio": {"boiler": 0.5, "psa": 2.0}},
               {"reactor_size_driver": "", "catalyst_mass_kg": 10.0}]
    for feed in (10.0, 36.9914, 99.8, 400.0):
        for kw in kw_sets:
            k2 = dict(kw)
            if "exclude" in k2:
                k2["exclude"] = tuple(k2["exclude"])
            rc.append({"nh3_feed_kmol_h": feed, "kwargs": kw, "output": _try(lambda: R.reference_capex(feed, **k2))})
    # equipment CAPEX
    ec = []
    a0 = L.EconomicAssumptions()
    for feed in (25.0, 99.8, 500.0):
        for lf, ex, mult in ((None, None, 1.0), (1.1, None, 1.0), (None, 0.6, 1.0), (None, None, 1.4)):
            a = a0.model_copy(update={"capex_multiplier": mult})
            ec.append({"nh3_feed_kmol_h": feed, "location_factor": lf, "exponent": ex, "capex_multiplier": mult,
                       "output": SG.equipment_capex(feed, a, location_factor=lf, exponent=ex)})
    # legacy correlation (lcoh.py) on stored SimulationResults
    legacy = []
    a_sets = [{}, {"capex_method": "chopra2026_point"}, {"capex_method": "farokhi2025_point"},
              {"capex_method": "fixed", "capex_fixed_USD": 4e6}, {"capex_method": "fixed"},
              {"credit_heat_surplus": True}, {"heat_import_mode": "fired_heat"},
              {"nh3_price_USD_per_t": 600.0, "catalyst": "Ru", "compression_power_kW": 50.0},
              {"discount_rate": 0.0}, {"catalyst_mass_kg": 120.0, "capacity_exponent": 0.9}]
    files = ["results/simulations/baseline.json", "results/simulations/baseline_no_hi.json",
             "results/simulations/python_baseline.json", "results/simulations/scn_high_pressure.json",
             "results/simulations/opt_opt_lcoh.json"]
    for rel in files:
        res = SimulationResult.model_validate(load(rel))
        for kw in a_sets:
            def one():
                r = L.compute_lcoh(res, L.EconomicAssumptions(**kw))
                d = r.model_dump(mode="json")
                return {k: d[k] for k in ("case_id", "lcoh_USD_per_kg", "breakdown_USD_per_kg", "annual_costs_USD_per_yr",
                                          "annual_h2_kg", "h2_product_kg_h", "crf", "kg_nh3_feed_per_kg_h2",
                                          "kg_nh3_fuel_per_kg_h2", "stoichiometric_floor_kg_nh3_per_kg_h2",
                                          "reconversion_cost_USD_per_kg")} | {"capex": {
                    "method": d["capex"]["method"], "capacity_kg_H2_h": d["capex"]["capacity_kg_H2_h"],
                    "total_capex_USD": d["capex"]["total_capex_USD"], "capex_multiplier": d["capex"]["capex_multiplier"],
                    "selected": {k: d["capex"]["selected"][k] for k in ("method", "reference_capacity_kg_H2_h",
                                                                         "reference_capex_USD", "scaled_capex_USD", "exponent")},
                    "alternatives": [{k: x[k] for k in ("method", "reference_capacity_kg_H2_h", "reference_capex_USD",
                                                        "scaled_capex_USD", "exponent")} for x in d["capex"]["alternatives"]],
                    "equipment_breakdown_USD": d["capex"]["equipment_breakdown_USD"]}}
            out = _try(one)
            legacy.append({"file": rel, "assumptions": kw, "output": out,
                           "breakeven": {str(t): _try(lambda: L.breakeven_ammonia_price(res, L.EconomicAssumptions(**kw), t))
                                         for t in (3.0, 5.0, 0.1)} if "error" not in (out or {}) else None})
    body = {"summaries": S, "extract_summary": extract, "evaluate": cases, "breakeven": be,
            "reference_capex": rc, "reference_item_costs": R.reference_item_costs(),
            "reference_catalyst_mass_kg": R.reference_catalyst_mass_kg(), "equipment_capex": ec,
            "default_electricity_USD_per_kWh": SG.default_electricity_USD_per_kWh(),
            "crf": [{"i": i, "n": n, "lcoh_crf": _try(lambda: L.crf(i, n)), "reference_crf": _try(lambda: R._crf(i, n))}
                    for i in (0.0, 0.05, 0.085, 0.1, 0.25) for n in (1.0, 20.0, 25, 30.5)]
                   + [{"i": 0.1, "n": 0.0, "lcoh_crf": _try(lambda: L.crf(0.1, 0.0)), "reference_crf": None}],
            "irr": [{"capex": c, "net": n_, "n": k, "value": SG._irr(c, n_, k)}
                    for c in (1e6, 7.6e6) for n_ in (-1.0, 1e5, 9e5, 3e6) for k in (10, 25)],
            "legacy": legacy, "stored": stored_recipes(S)}
    n = len(cases) + len(extract) + len(be) + len(rc) + len(ec) + len(legacy) + len(body["stored"])
    write_table("economics", body, n)


def _try(f):
    try:
        return f()
    except Exception as e:  # noqa: BLE001
        return err(e)


# ---------------------------------------------------------------------------------------- stored-result recipes
def recipe_value(S, r):
    k = r["kind"]
    if k == "evaluate":
        return get_path(SG.evaluate(S[r["summary"]], r["scenario"], r["overrides"]), r["output"])
    if k == "breakeven":
        return SG.breakeven_nh3_price(S[r["summary"]], r["target"], r["overrides"], r.get("metric", "lcoh_USD_per_kg"))
    if k == "diff":
        return recipe_value(S, r["a"]) - recipe_value(S, r["b"])
    if k == "legacy":
        res = SimulationResult.model_validate(load(r["file"]))
        return get_path(L.compute_lcoh(res, L.EconomicAssumptions(**r["assumptions"])).model_dump(mode="json"), r["output"])
    raise ValueError(k)


def stored_recipes(S) -> list:
    out = []

    def add(file, path, recipe):
        stored = get_path(load(file), path)
        try:
            v = recipe_value(S, recipe)
        except Exception as e:  # noqa: BLE001
            v = err(e)
        same = (v == stored) or (isinstance(v, float) and isinstance(stored, (int, float)) and abs(v - stored) <= 1e-12 * abs(stored))
        out.append({"file": file, "path": path, "recipe": recipe, "python_recomputed": v,
                    "python_reproduces_stored": bool(same)})

    def ev(summary, scenario, overrides, output):
        return {"kind": "evaluate", "summary": summary, "scenario": scenario, "overrides": overrides, "output": output}

    def leaves(d, prefix=()):
        if isinstance(d, dict):
            for k, v in d.items():
                yield from leaves(v, prefix + (k,))
        elif isinstance(d, (int, float)) and not isinstance(d, bool):
            yield prefix

    f = "results/research/reference_scenario/baseline.json"
    b = load(f)
    direct = ["h2_product_kg_h", "annual_h2_kg", "nh3_price_USD_per_t", "lcoh_USD_per_kg", "lcoh_SGD_per_kg",
              "rec_USD_per_kg", "rec_SGD_per_kg", "npv_USD", "npv_SGD", "crf", "purification_memo_USD_per_kg",
              "kg_nh3_feed_per_kg_h2", "kg_nh3_fuel_per_kg_h2", "catalyst_mass_kg", "direct_emissions_tCO2e_per_yr",
              "capex_total_SGD"]
    for k in direct:
        add(f, [k], ev("baseline", "grey", {}, [k]))
    for k in ("breakdown_USD_per_kg", "breakdown_SGD_per_kg", "annual_USD_per_yr", "fixed_opex_detail_USD_per_yr"):
        for p in leaves(b[k]):
            add(f, [k, *p], ev("baseline", "grey", {}, [k, *p]))
    add(f, ["capex_total_USD"], ev("baseline", "grey", {}, ["capex", "total_capex_USD"]))
    add(f, ["capex_indirects_USD"], ev("baseline", "grey", {}, ["capex", "indirects_USD"]))
    for src, dst in (("capex_isbl_by_item_USD", "isbl_USD"), ("capex_tci_by_item_USD", "tci_by_item_USD"),
                     ("capex_size_ratio", "size_ratio")):
        for p in leaves(b[src]):
            add(f, [src, *p], ev("baseline", "grey", {}, ["capex", dst, *p]))
    for p in leaves(b["heat_integration_off"]):
        add(f, ["heat_integration_off", *p], ev("baseline_no_hi", "grey", {}, list(p)))
    for sc, v in b["nh3_scenarios"].items():
        for k in v:
            add(f, ["nh3_scenarios", sc, k], ev("baseline", sc, {}, [k]))
    leg = {"capex_mode": "legacy", "electricity_price_USD_per_kWh": 0.084}
    add(f, ["superseded_bases", "legacy_v1_correlation", "lcoh_USD_per_kg"], ev("baseline", 450.0, leg, ["lcoh_USD_per_kg"]))
    add(f, ["superseded_bases", "legacy_v1_correlation", "capex_total_USD"], ev("baseline", 450.0, leg, ["capex", "total_capex_USD"]))
    add(f, ["superseded_bases", "legacy_v1_correlation", "stored_lcoh_USD_per_kg"],
        {"kind": "legacy", "file": "results/simulations/baseline.json", "assumptions": {}, "output": ["lcoh_USD_per_kg"]})
    add(f, ["superseded_bases", "phase1_equipment", "lcoh_USD_per_kg"], ev("baseline", "grey", {"capex_mode": "equipment"}, ["lcoh_USD_per_kg"]))
    add(f, ["superseded_bases", "phase1_equipment", "capex_total_USD"], ev("baseline", "grey", {"capex_mode": "equipment"}, ["capex", "total_capex_USD"]))
    fe = b["fuel_efficiency_sensitivity"]
    for i, c in enumerate(fe["cases"]):
        o = {"fuel_efficiency": c["fuel_efficiency"]}
        pre = ["fuel_efficiency_sensitivity", "cases", i]
        add(f, pre + ["lcoh_USD_per_kg"], ev("baseline", "grey", o, ["lcoh_USD_per_kg"]))
        add(f, pre + ["lcoh_SGD_per_kg"], ev("baseline", "grey", o, ["lcoh_SGD_per_kg"]))
        add(f, pre + ["heat_fuel_USD_per_kg"], ev("baseline", "grey", o, ["breakdown_USD_per_kg", "heat_fuel"]))
        add(f, pre + ["npv_USD"], ev("baseline", "grey", o, ["npv_USD"]))
        add(f, pre + ["breakeven_nh3_USD_per_t_vs_marker"], {"kind": "breakeven", "summary": "baseline", "target": 3.06, "overrides": o})
        add(f, pre + ["lcoh_heat_integration_off_USD_per_kg"], ev("baseline_no_hi", "grey", o, ["lcoh_USD_per_kg"]))
        add(f, pre + ["heat_integration_gross_saving_USD_per_kg"],
            {"kind": "diff", "a": ev("baseline_no_hi", "grey", o, ["lcoh_USD_per_kg"]), "b": ev("baseline", "grey", o, ["lcoh_USD_per_kg"])})
    add(f, ["fuel_efficiency_sensitivity", "envelope_lcoh_USD_per_kg", 0], ev("baseline", "grey", {"fuel_efficiency": 1.0}, ["lcoh_USD_per_kg"]))
    add(f, ["fuel_efficiency_sensitivity", "envelope_lcoh_USD_per_kg", 1], ev("baseline", "grey", {"fuel_efficiency": 0.85}, ["lcoh_USD_per_kg"]))

    f = "results/research/reference_scenario/capex_audit.json"
    m = ["methods_on_amcrax_baseline"]
    for key, o in (("reference_cho2026_itemised_v1", {}), ("phase1_equipment_farokhi", {"capex_mode": "equipment"}),
                   ("legacy_ahmad_correlation", None)):
        sc, oo = ("grey", o) if o is not None else (450.0, leg)
        add(f, m + [key, "capex_total_USD"], ev("baseline", sc, oo, ["capex", "total_capex_USD"]))
        add(f, m + [key, "lcoh_USD_per_kg"], ev("baseline", sc, oo, ["lcoh_USD_per_kg"]))

    f = "results/research/singapore/scenario_results.json"
    sr = load(f)
    for key, v in sr["results"].items():
        sc, hn = key.split("|")
        sname = "baseline" if hn == "heat_integration_on" else "baseline_no_hi"
        for k, x in v.items():
            if isinstance(x, dict):
                if k == "capex_by_item_USD":
                    for kk in x:
                        add(f, ["results", key, k, kk], ev(sname, sc, {}, ["capex", "tci_by_item_USD", kk]))
                else:
                    for kk in x:
                        add(f, ["results", key, k, kk], ev(sname, sc, {}, [k, kk]))
            elif isinstance(x, (int, float)) and not isinstance(x, bool) or x is None:
                if k == "capex_total_USD":
                    add(f, ["results", key, k], ev(sname, sc, {}, ["capex", "total_capex_USD"]))
                elif k == "fx_SGD_per_USD":
                    add(f, ["results", key, k], ev(sname, sc, {}, ["fx_SGD_per_USD"]))
                else:
                    add(f, ["results", key, k], ev(sname, sc, {}, [k]))
    for key in sr["phase1_equipment_basis_lcoh_USD_per_kg"]:
        sc, hn = key.split("|")
        sname = "baseline" if hn == "heat_integration_on" else "baseline_no_hi"
        add(f, ["phase1_equipment_basis_lcoh_USD_per_kg", key], ev(sname, sc, {"capex_mode": "equipment"}, ["lcoh_USD_per_kg"]))

    f = "results/research/singapore/tornado.json"
    t = load(f)
    add(f, ["lcoh_base_USD_per_kg"], ev("baseline", "grey", {}, ["lcoh_USD_per_kg"]))
    for i, bar in enumerate(t["bars"]):
        if bar["parameter"] == "heat_integration":
            add(f, ["bars", i, "lcoh_at_high_input"], ev("baseline_no_hi", "grey", {}, ["lcoh_USD_per_kg"]))
            continue
        add(f, ["bars", i, "lcoh_at_low_input"], ev("baseline", "grey", {bar["parameter"]: bar["low_input"]}, ["lcoh_USD_per_kg"]))
        add(f, ["bars", i, "lcoh_at_high_input"], ev("baseline", "grey", {bar["parameter"]: bar["high_input"]}, ["lcoh_USD_per_kg"]))

    f = "results/research/singapore/breakeven_ammonia_price.json"
    bk = load(f)
    for hn, v in bk["results"].items():
        sname = "baseline" if hn == "heat_integration_on" else "baseline_no_hi"
        for name, x in v.items():
            add(f, ["results", hn, name, "breakeven_nh3_USD_per_t"],
                {"kind": "breakeven", "summary": sname, "target": x["h2_price_USD_per_kg"], "overrides": {}})

    for f, src in (("results/simulations/economics_baseline.json", "results/simulations/baseline.json"),
                   ("results/simulations/economics_baseline_no_hi.json", "results/simulations/baseline_no_hi.json")):
        e = load(f)
        add(f, ["lcoh_USD_per_kg"], {"kind": "legacy", "file": src, "assumptions": {}, "output": ["lcoh_USD_per_kg"]})
        for k in e["breakdown_USD_per_kg"]:
            add(f, ["breakdown_USD_per_kg", k], {"kind": "legacy", "file": src, "assumptions": {}, "output": ["breakdown_USD_per_kg", k]})
        for k in e["annual_costs_USD_per_yr"]:
            add(f, ["annual_costs_USD_per_yr", k], {"kind": "legacy", "file": src, "assumptions": {}, "output": ["annual_costs_USD_per_yr", k]})
        add(f, ["capex", "total_capex_USD"], {"kind": "legacy", "file": src, "assumptions": {}, "output": ["capex", "total_capex_USD"]})
        add(f, ["reconversion_cost_USD_per_kg"], {"kind": "legacy", "file": src, "assumptions": {}, "output": ["reconversion_cost_USD_per_kg"]})
    bad = [x for x in out if not x["python_reproduces_stored"]]
    print(f"stored recipes: {len(out)}, not reproduced by the current Python: {len(bad)}")
    for x in bad[:20]:
        print("  ", x["file"], x["path"], x["python_recomputed"])
    return out


TABLES = {"economics": economics}

if __name__ == "__main__":
    names = sys.argv[1:] or list(TABLES)
    for n in names:
        TABLES[n]()
    save_manifest()
