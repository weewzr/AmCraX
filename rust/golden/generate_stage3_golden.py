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
    (OUT / "MANIFEST.json").write_bytes((json.dumps(MANIFEST, indent=1, sort_keys=True) + "\n").encode("utf-8"))


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


# ======================================================================================================== carbon
def carbon() -> None:
    from amcrax.economics import carbon_pricing as cp
    from amcrax.environmental import lca

    S = summaries()
    base_res = load("results/simulations/baseline.json")
    # ---- lca.py
    lc = {"route_spec": {r: _try(lambda: lca.route_spec(r).__dict__) for r in (*lca.ROUTES, "green_lee", "purple")},
          "blue_nh3_ef": [{"args": a, "value": _try(lambda: lca.blue_nh3_ef(*a))}
                          for a in ((1.0, 0.0), (1.0, 1.0), (0.9, 0.0, 0.03), (0.95, 0.0, 0.015), (0.5, 0.25, 0.01, 28.0),
                                    (0.0, 0.0), (1.2, 0.0), (0.5, -0.1), (0.5, 0.5, -0.01))],
          "green_nh3_ef": {k: _try(lambda: lca.green_nh3_ef(k)) for k in ("lee", "low", "mid", "high", "other")},
          "ship_kg_per_kg_nh3": [{"distance_km": dk, "ef": e, "value": lca.ship_kg_per_kg_nh3(dk, e)}
                                 for dk in (0.0, 2000.0, 5000.0, 12000.0) for e in (None, 0.02)],
          "delivered_nh3_ef": [{"ef_gate": g, "distance_km": dk, "boil_off": bo, "value": _try(lambda: lca.delivered_nh3_ef(g, dk, bo))}
                               for g in (0.0, 1.16, 2.6) for dk in (2000.0, 5000.0) for bo in (None, 0.0, 0.02, 1.0, -0.1)],
          "n2o_noX_per_MWh": lca.n2o_noX_per_MWh(),
          "ccgt_ci_kg_per_MWh": [{"eff": e, "leak": lk, "value": lca.ccgt_ci_kg_per_MWh(e, lk)}
                                 for e in (None, 0.5, 0.6) for lk in (0.0, 0.002, 0.015, 0.03)],
          "smr_h2_ci": {"ccs": lca.smr_h2_ci(True), "unabated": lca.smr_h2_ci(False)},
          "KG_H2_PER_KG_NH3": lca.KG_H2_PER_KG_NH3}
    # ---- carbon_pricing.py
    ci_in = {"baseline": cp.ci_inputs_from_result(base_res),
             "baseline_no_hi": cp.ci_inputs_from_result(load("results/simulations/baseline_no_hi.json")),
             "surplus": dict(cp.ci_inputs_from_result(base_res), heat_deficit_kW=-50.0)}
    grids = {g: cp.ci_factors(g).__dict__ for g in ("singapore_2024", "eu_average", "low_carbon_nuclear")}
    ci = []
    for name, x in ci_in.items():
        for ef in (0.0, 0.2752157829839704, 1.16, 2.6, 4.6):
            for heating in ("self_firing", "natural_gas", "electric", "coal"):
                for dist in (None, 2000.0, 12000.0):
                    for g in grids:
                        ci.append({"inputs": name, "nh3_ef": ef, "heating": heating, "distance_km": dist, "grid": g,
                                   "value": _try(lambda: cp.carbon_intensity_h2(x, ef, heating, dist, cp.ci_factors(g)))})
    econs = {"grey": SG.evaluate(S["baseline"], "grey"), "blue": SG.evaluate(S["baseline"], "blue"),
             "ng_liable": SG.evaluate(S["baseline"], "grey", {"heat_fuel": "natural_gas", "apply_threshold": False}),
             "green_current": SG.evaluate(S["baseline"], "green_current")}
    cc = []
    for en, e in econs.items():
        for mode in ("actual_sg", "hypothetical_lca", "other"):
            for price in (0.0, 45.0, 127.43999603999998, 500.0, -1.0, float("inf")):
                for ci_t in (2.43, 19.5):
                    cc.append({"econ": en, "mode": mode, "price": price, "ci": ci_t,
                               "value": _try(lambda: cp.carbon_cost(e, ci_t, mode, price))})
    ab = []
    for name in ("baseline", "baseline_no_hi"):
        for sc in ("grey", "green_current"):
            for year in (2023, 2024, 2025, 2026, 2030):
                for n2o in (0.0, 1.0, 12.0):
                    for o in ({}, {"heat_fuel": "natural_gas"}, {"heat_fuel": "natural_gas", "capacity_scale": 25.0},
                              {"operating_hours_h_per_yr": 7000.0, "n2o_tCO2e_per_yr": 100.0}, {"carbon_tax_SGD_per_t": 80.0}):
                        v = _try(lambda: cp.actual_boundary(S[name], sc, year=year, n2o_kg_per_h=n2o, overrides=o))
                        ab.append({"summary": name, "scenario": sc, "year": year, "n2o_kg_per_h": n2o, "overrides": o, "value": v})
    rcases = []
    for route in ("grey", "blue", "green_current", "green_2030", "green_2050", "blue_v2"):
        for mode, price in (("actual_sg", 0.0), ("hypothetical_lca", 0.0), ("hypothetical_lca", 45.0),
                            ("hypothetical_lca", 127.43999603999998), ("hypothetical_lca", 500.0)):
            for kw in ({}, {"ci_level": "low"}, {"ci_level": "high"}, {"nh3_ef_kg_per_kg": 1.0},
                       {"benchmark_USD_per_kg": 5.0, "benchmark_ci_kgCO2e_per_kgH2": 3.5},
                       {"overrides": {"heat_fuel": "natural_gas", "apply_threshold": False}},
                       {"overrides": {"discount_rate": 0.0}}):
                v = _try(lambda: cp.route_case(S["baseline"], route, mode, price, **kw))
                rcases.append({"summary": "baseline", "route": route, "mode": mode, "price": price, "kwargs": kw, "value": v})
    xo = [{"args": a, "value": cp.crossover_price(*a)}
          for a in ((4.29, 8.9, 4.02, 19.5, 1.288444), (4.0, 8.9, 4.02, 19.5, 1.288444), (4.02, 8.9, 4.02, 19.5, 1.288444),
                    (4.29, 19.5, 4.02, 8.9, 1.288444), (4.29, 19.5, 4.02, 19.5, 1.288444), (8.06, 2.43, 4.02, 19.52, 1.3))]
    e_grey = SG.evaluate(base_res)
    tt = cp.n2o_threshold_test(base_res, e_grey)
    nt = {"threshold_test": tt, "at_ppmv": [cp.n2o_at_ppmv(p, tt, h) for p in (0.15, 1.0, 50.0) for h in (8000.0, 7000.0)]}
    pairs = [("blue", "grey"), ("green_current", "grey"), ("green_2030", "grey"), ("green_2050", "grey"),
             ("green_current", "blue"), ("green_2030", "blue"), ("green_2050", "blue")]
    misc = {"legislated_rate_SGD": {str(y): cp.legislated_rate_SGD(y) for y in (2019, 2023, 2024, 2025, 2026, 2031)},
            "eu_ets_SGD_per_t": cp.eu_ets_SGD_per_t(), "ci_factors": grids,
            "route_gate_ef": {r: _try(lambda: cp.route_gate_ef(r)) for r in ("grey", "blue", "blue_v2", "green_current",
                                                                             "green_2030", "green_2050", "coal", "purple")}}
    # Python reproduces the stored carbon-pricing results (checked here; the Rust verifier compares with the files)
    stored_ok = {}
    sc_file = load("results/research/carbon_pricing/scenarios.json")
    bench_ci = sc_file["benchmark_ci_smr_kgCO2e_per_kgH2"]
    ok = True
    for c in sc_file["cases"]:
        hyp = c["mode"] == "hypothetical_lca"
        v = cp.route_case(base_res, c["route"], c["mode"], c["carbon_price_SGD_per_tCO2e"] if hyp else 0.0,
                          benchmark_ci_kgCO2e_per_kgH2=bench_ci if hyp else 11.0)
        ok &= json.dumps(enc(v), sort_keys=True) == json.dumps(enc(c), sort_keys=True)
    stored_ok["scenarios.json cases"] = ok
    th = load("results/research/carbon_pricing/thresholds.json")["pairwise"]
    stored_ok["thresholds.json pairwise (pairs)"] = [[t["route"], t["overtakes"]] for t in th] == [list(p) for p in pairs]
    tv = load("results/research/carbon_pricing/test_vectors.json")
    ok = True
    for v in tv["vectors"]:
        i = v["inputs"]
        if v["function"] == "carbonIntensity":
            got = cp.carbon_intensity_h2(i["x"], i["nh3_ef_kg_per_kg"], i["heating"], i["distance_km"], cp.CIFactors(**i["factors"]))
        elif v["function"] == "carbonCost":
            got = cp.carbon_cost(i["econ"], i["ci_total_kgCO2e_per_kgH2"], i["mode"], i["price_SGD_per_t"])
        else:
            got = cp.crossover_price(i["lcoh_a"], i["ci_a"], i["lcoh_b"], i["ci_b"], i["fx"])
        exp = v["expected"]
        if isinstance(exp, dict) and "label_contains" in exp:
            exp = dict(exp)
            ok &= exp.pop("label_contains") in got["label"]
            got = {k: x for k, x in got.items() if k != "label"}
        ok &= json.dumps(enc(got), sort_keys=True) == json.dumps(enc(exp), sort_keys=True)
    stored_ok["test_vectors.json (18)"] = ok
    cij = load("results/research/carbon_pricing/carbon_intensity.json")
    ng = cij["power_comparators_kgCO2e_per_MWh"]["ng_ccgt"]
    stored_ok["carbon_intensity.json ng_ccgt"] = (
        ng["central"] == lca.ccgt_ci_kg_per_MWh() and ng["low_eff_0.50"] == lca.ccgt_ci_kg_per_MWh(0.5)
        and ng["high_eff_0.60"] == lca.ccgt_ci_kg_per_MWh(0.6)
        and all(ng[f"leak_{lk:g}"] == lca.ccgt_ci_kg_per_MWh(None, lk) for lk in (0.002, 0.015, 0.03)))
    ci_base = cp.ci_inputs_from_result(base_res)
    ok = True
    for r, row in cij["routes"].items():
        s_ = lca.route_spec(r)
        ok &= row["gate_ef_kgCO2e_per_kgNH3"] == {"central": s_.ef, "low": s_.low, "high": s_.high}
        ok &= row["ci_kgCO2e_per_kgH2"]["central"] == cp.carbon_intensity_h2(ci_base, s_.ef)["total_kgCO2e_per_kgH2"]
    stored_ok["carbon_intensity.json routes"] = ok
    print("python reproduces stored carbon results:", stored_ok)
    body = {"summaries": S, "lca": lc, "ci_inputs": ci_in, "carbon_intensity": ci, "econs": econs, "carbon_cost": cc,
            "actual_boundary": ab, "route_case": rcases, "crossover_price": xo, "n2o": nt, "pairs": pairs, "misc": misc,
            "python_reproduces_stored": stored_ok}
    write_table("carbon", body, len(ci) + len(cc) + len(ab) + len(rcases) + len(xo) + 40)


# ======================================================================================================== uq
def uq() -> None:
    import importlib.util
    import time
    from scipy import special, stats as sst
    from amcrax.uq import SEED
    from amcrax.uq import sobol as sb

    def sha(a):
        return hashlib.sha256(np.ascontiguousarray(a, dtype="<f8").tobytes()).hexdigest()

    # ---- fixed output matrices for the estimators
    est = []
    A, B = sb.sobol_base(1024, 3, SEED)
    to = lambda U: -math.pi + 2 * math.pi * U  # noqa: E731
    fA, fB = sb.ishigami(to(A)), sb.ishigami(to(B))
    fAB = np.stack([sb.ishigami(to(sb.ab_matrix(A, B, [i]))) for i in range(3)])
    est.append(("ishigami_N1024", fA, fB, fAB, 200, SEED))
    r = np.random.default_rng(7)
    fA2 = r.normal(size=500)
    fB2 = r.normal(size=500)
    fAB2 = np.stack([0.3 * fA2 + 0.7 * r.normal(size=500) for _ in range(4)])
    est.append(("random_N500_k4", fA2, fB2, fAB2, 300, 11))
    c = np.full(64, 2.5)
    est.append(("constant_N64", c, c.copy(), np.stack([c, c]), 20, 3))
    estimators = []
    for name, a_, b_, ab_, nb, seed in est:
        S, ST, V = sb.indices_from_outputs(a_, b_, ab_)
        ciS, ciT = sb.bootstrap_ci(a_, b_, ab_, nb, seed)
        g = np.random.default_rng(seed)
        idx = [g.integers(0, a_.size, a_.size).tolist() for _ in range(2)]
        estimators.append({"name": name, "fA": a_, "fB": b_, "fAB": ab_, "n_boot": nb, "seed": seed,
                           "S": S, "ST": ST, "V": V, "S_ci": ciS, "ST_ci": ciT, "first_bootstrap_idx": idx})
    # ---- Sobol' base samples of the studies
    bases = []
    for n, d in ((8192, 10), (8192, 11), (8192, 3), (8192, 4), (1024, 3)):
        a_, b_ = sb.sobol_base(n, d, SEED)
        ab = np.hstack([a_, b_])
        bases.append({"n": n, "d": d, "sha256_le_f8": sha(ab), "first_rows": ab[:3], "last_row": ab[-1]})
    # ---- distributions
    g = np.random.default_rng(99)
    u = np.concatenate([g.random(3000), [1e-12, 1 - 1e-12, 0.5, 0.05, 0.95, 0.25, 1e-300, 0.999999]])
    tri = []
    for lo, md, hi in ((0.5, 1.0, 1.5), (300.0, 450.0, 610.0), (16.7, 33.4, 66.8), (0.0, 0.0, 1.0), (0.0, 1.0, 1.0)):
        cc = (md - lo) / (hi - lo)
        tri.append({"lo": lo, "mode": md, "hi": hi, "values": sst.triang.ppf(u, cc, loc=lo, scale=hi - lo)})
    lgn = [{"s": s_, "values": sst.lognorm.ppf(u, s_, scale=1.0)} for s_ in (0.3, 0.2433)]
    nd = {"u": u, "ndtri": special.ndtri(u), "norm_ppf": sst.norm.ppf(u)}
    # ---- the GSA script's module constants and one reproduced case
    spec = importlib.util.spec_from_file_location("uq_gsa_sobol", REPO / "scripts/research/uq_gsa_sobol.py")
    gm = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(gm)
    S_HI = SG.extract_summary(load("results/simulations/baseline.json"))
    t0 = time.perf_counter()
    case = gm.analyse(S_HI, "grey")
    t_case = time.perf_counter() - t0
    stored = load("results/research/uq/gsa_sobol.json")
    same_case = json.dumps(enc(case), sort_keys=True) == json.dumps(enc(stored["cases"]["grey|heat_integration_on"]), sort_keys=True)
    print(f"GSA grey|HI on recomputed in {t_case:.1f} s; identical to stored: {same_case}")
    # ---- Monte Carlo of economics_singapore.py (section 6 replicated; the script itself writes results/)
    t0 = time.perf_counter()
    SD = SG.load_singapore_data()
    REF = R.load_reference_scenario()
    ELEC_LO, ELEC_HI = REF.sens("electricity_USD_per_kWh")
    DR_LO, DR_HI = REF.sens("discount_rate")
    PL_LO, PL_HI = REF.sens("plant_life_yr")
    OH_LO, OH_HI = REF.sens("operating_hours_h_per_yr")
    N = 5000
    rng = np.random.default_rng(SEED)
    draws = {"elec": rng.uniform(ELEC_LO, ELEC_HI, N), "cat": rng.triangular(16.7, 33.4, 66.8, N), "life": rng.uniform(1, 4, N),
             "capx": rng.triangular(0.5, 1.0, 1.5, N), "dr": rng.uniform(DR_LO, DR_HI, N), "oh": rng.uniform(OH_LO, OH_HI, N),
             "pl": rng.uniform(PL_LO, PL_HI, N)}
    u_nh3 = rng.random(N)
    mc = {}
    for sc in ("grey", "blue", "green_current", "green_2030"):
        d_ = SD["nh3_price_scenarios_USD_per_t"][sc]
        lo, md, hi = d_["low"], d_["value"], d_["high"]
        fc = (md - lo) / (hi - lo)
        pr = np.where(u_nh3 < fc, lo + np.sqrt(u_nh3 * (hi - lo) * (md - lo)), hi - np.sqrt((1 - u_nh3) * (hi - lo) * (hi - md)))
        L_ = []
        for i in range(N):
            e = SG.evaluate(S_HI, float(pr[i]), {"electricity_price_USD_per_kWh": draws["elec"][i], "catalyst_price_USD_per_kg": draws["cat"][i],
                                                "catalyst_lifetime_yr": draws["life"][i], "capex_multiplier": draws["capx"][i],
                                                "discount_rate": draws["dr"][i], "operating_hours_h_per_yr": draws["oh"][i],
                                                "plant_life_yr": draws["pl"][i]})
            L_.append(e["lcoh_USD_per_kg"])
        mc[sc] = float(np.mean(L_))
    t_mc = time.perf_counter() - t0
    smc = load("results/research/singapore/monte_carlo.json")["results"]
    same_mc = all(mc[k] == smc[k]["lcoh_mean"] for k in mc)
    print(f"Monte Carlo recomputed in {t_mc:.1f} s; lcoh_mean identical to stored: {same_mc}")
    body = {"estimators": estimators, "sobol_base": bases, "triang_ppf": tri, "lognorm_ppf": lgn, "normal": nd,
            "gsa_module": {"SIG_LN": gm.SIG_LN, "W_TRI": gm.W_TRI, "CAT_PRICE": gm.CAT_PRICE, "N": gm.N, "N_BOOT": gm.N_BOOT,
                           "SEED": SEED},
            "python_reproduces_stored": {"gsa_sobol.json cases grey|heat_integration_on": same_case,
                                         "monte_carlo.json lcoh_mean (4 scenarios)": same_mc},
            "python_timing_s": {"gsa_one_case_of_17": t_case, "monte_carlo_4x5000": t_mc,
                                "note": "generator machine (Windows, loaded); not the benchmark (see rust/verification/benchmark_stage3.json)"}}
    write_table("uq", body, len(estimators) + len(bases) + 3000 * 8)


# ======================================================================================================== stiff
def stiff() -> None:
    """High-temperature plug-flow cases (stiff for an explicit method) with the Python LSODA reference."""
    import time
    import scipy.integrate as si
    from amcrax.reactor import pfr as P

    rec = {}
    orig = si.solve_ivp

    def solve_rec(*a, **k):
        r = orig(*a, **k)
        rec.update(nfev=int(r.nfev), njev=int(getattr(r, "njev", 0)), nlu=int(getattr(r, "nlu", 0)))
        return r

    P.solve_ivp = solve_rec
    cases = []
    cats = ["ru_kum_temkin_pyzhev", "nire_ceo2_5ni1ru_lucentini_lhhw", "nire_ceo2_2p5ni0p5ru_lucentini_lhhw",
            "ni_takahashi_microkinetic", "ru_takahashi_microkinetic"]
    bed = {"eps_b": 0.36, "rho_particle_kg_m3": 1651.8}
    for cid in cats:
        for T in (750.0, 850.0, 900.0):
            for Pb in (1.01325, 20.0):
                for W in (100.0, 1000.0):
                    kw = dict(W_kg=W, T_in_C=T, P_in_bar=Pb, feed_kmol_h={"NH3": 100.0}, mode="isothermal",
                              pressure_drop=False, n_points=3, **bed)
                    cases.append((cid, kw))
    cases.append(("ru_kum_temkin_pyzhev", dict(W_kg=1000.0, T_in_C=900.0, P_in_bar=1.01325, n_points=3)))
    cases.append(("nire_ceo2_5ni1ru_lucentini_lhhw", dict(W_kg=1000.0, T_in_C=900.0, P_in_bar=1.01325, feed_kmol_h={"NH3": 100.0},
                                                          mode="isothermal", pressure_drop=False, n_points=3,
                                                          **bed)))
    for T in (700.0, 800.0):
        cases.append(("ru_takahashi_microkinetic", dict(W_kg=500.0, T_in_C=T, P_in_bar=20.0, mode="adiabatic", n_tubes=50, n_points=3)))
    out = []
    for cid, kw in cases:
        rec.clear()
        t0 = time.perf_counter()
        try:
            r = P.simulate_pfr(cid, **kw)
            v = {"conversion": r.outlet["conversion"], "T_C": r.outlet["T_C"], "P_bar": r.outlet["P_bar"],
                 "X_profile": list(r.conversion), "T_K_profile": list(r.T_K), "W_profile": list(r.W_kg),
                 "hydraulic_limit": bool(r.outlet["hydraulic_limit"])}
        except Exception as e:  # noqa: BLE001
            v = err(e)
        out.append({"catalyst_id": cid, "kwargs": kw, "result": v, "lsoda": dict(rec),
                    "python_seconds": time.perf_counter() - t0})
    P.solve_ivp = orig
    write_table("stiff", {"cases": out, "note": "Python simulate_pfr (LSODA rtol 1e-8, atol 1e-12) at high temperature"}, len(out))


TABLES = {"economics": economics, "carbon": carbon, "uq": uq, "stiff": stiff}

if __name__ == "__main__":
    names = sys.argv[1:] or list(TABLES)
    for n in names:
        TABLES[n]()
    save_manifest()
