"""Export the data of the browser-side process simulator (frontend/src/sim) from the Python registries and stored results.

Writes (deterministic: no timestamps, sorted keys, fixed rounding of nothing - values are written as Python floats):
    results/research/simulator/model.json         every parameter the browser model needs (single source of parameters)
    results/research/simulator/aspen_anchors.json  stored Aspen Plus V15 results the simulator can show as 'aspen'
    results/research/simulator/test_vectors.json   cases computed by the PYTHON models, used by the vitest suite

The TypeScript code contains no scientific parameter values of its own; it reads model.json.
Economics are read through the public Python objects of amcrax.economics (singapore.evaluate, reference.py) on the unified
reference scenario backend/amcrax/data/reference_scenario.yaml (capex_mode 'reference', method cho2026_itemised_v1).
Catalyst prices come from research/data/catalyst_prices.json (derived from metal content, not quotations).

Run:  python scripts/research/export_simulator_data.py
Check that the stored files are current:  python scripts/research/export_simulator_data.py --check
"""
from __future__ import annotations

import argparse
import csv
import json
import math
import sys
from dataclasses import fields
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))

import yaml  # noqa: E402

from amcrax.economics import singapore as sg  # noqa: E402
from amcrax.economics.lcoh import EconomicAssumptions  # noqa: E402
from amcrax.environmental import carbon_intensity, load_factors  # noqa: E402
from amcrax.environmental import lca  # noqa: E402
from amcrax.kinetics import rate_mol_per_kgcat_s  # noqa: E402
from amcrax.kinetics import rate_laws  # noqa: E402
from amcrax.process_model import flowsheet as fs  # noqa: E402
from amcrax.reactor import pfr  # noqa: E402
from amcrax.schemas import LHV_KJ_PER_MOL, MOLAR_MASS, CaseInputs  # noqa: E402
from amcrax.thermodynamics import nasa7 as n7  # noqa: E402

OUT = ROOT / "results" / "research" / "simulator"
KIN = ROOT / "backend" / "amcrax" / "data" / "kinetics.yaml"
VALIDITY = ROOT / "results" / "research" / "kinetics" / "validity_classification.json"
ASPEN_KIN = ROOT / "results" / "research" / "aspen_kinetic"
SIM = ROOT / "results" / "simulations"
EQ_GRID = ROOT / "results" / "validation" / "equilibrium_aspen_grid.csv"
SCHEMA = "amcrax.simulator/1"

# Tolerances of the browser port against the Python model. Fixed BEFORE any comparison was run (task S1 targets).
TOLERANCES = {
    "conversion_abs": 1e-3,
    "temperature_K_abs": 0.5,
    "pressure_bar_abs": 1e-3,
    "duty_rel": 5e-3,
    "cost_rel": 5e-3,
    "carbon_rel": 5e-3,
    "rate_rel": 5e-3,
    "note": "fixed before the comparison; a mismatch is a bug in the port, not a reason to widen a tolerance",
}

LAW_SHORT = {"ni_takahashi_microkinetic": "tni", "ru_takahashi_microkinetic": "tru", "ru_kum_temkin_pyzhev": "kum",
             "nire_ceo2_5ni1ru_lucentini_lhhw": "luc5", "nire_ceo2_2p5ni0p5ru_lucentini_lhhw": "luc25"}


def rel(p: Path) -> str:
    return p.relative_to(ROOT).as_posix()


def finite(x):
    """JSON-safe: nan/inf -> None (recursively)."""
    if isinstance(x, float):
        return x if math.isfinite(x) else None
    if isinstance(x, dict):
        return {str(k): finite(v) for k, v in x.items()}
    if isinstance(x, (list, tuple)):
        return [finite(v) for v in x]
    return x


# ------------------------------------------------------------------------------------------------ model.json blocks
def thermo_block() -> dict:
    d = n7._data()
    return {
        "R_J_molK": n7.R_J_molK,
        "standard_pressure_bar": n7.P_STD_BAR,
        "species": {s: {"Tmin": v["Tmin"], "Tmid": v["Tmid"], "Tmax": v["Tmax"], "low": [float(a) for a in v["low"]],
                        "high": [float(a) for a in v["high"]], "ds_R": v["ds_R"], "composition": v["composition"]}
                    for s, v in d.items()},
        "argon_cp_J_molK": 20.786,
        "molar_mass_g_mol": dict(MOLAR_MASS),
        "lhv_kJ_per_mol": dict(LHV_KJ_PER_MOL),
        "source": "backend/amcrax/data/nasa7.json via amcrax.thermodynamics.nasa7 (GRI-Mech 3.0 NASA-7); amcrax.schemas",
    }


def kinetics_block() -> dict:
    reg = yaml.safe_load(KIN.read_text(encoding="utf-8"))
    validity = None
    if VALIDITY.exists():
        try:
            validity = json.loads(VALIDITY.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            validity = None

    def vclass(cid: str):
        if validity is None:
            return None

        def find(o):
            if isinstance(o, dict):
                if cid in o and isinstance(o[cid], (dict, str)):
                    return o[cid]
                for v in o.values():
                    r = find(v)
                    if r is not None:
                        return r
            if isinstance(o, list):
                for v in o:
                    if isinstance(v, dict) and (v.get("catalyst_id") == cid or v.get("id") == cid or v.get("law_id") == cid):
                        return v
                    r = find(v)
                    if r is not None:
                        return r
            return None
        return find(validity)

    laws = {}
    for section in ("catalysts", "research_catalysts"):
        for cid, d in (reg.get(section) or {}).items():
            cat = rate_laws.get_catalyst(cid)
            laws[cid] = {
                "id": cid, "short": LAW_SHORT.get(cid, cid), "registry_section": section, "label": d["label"],
                "metal": d["metal"], "composition": d["composition"], "form": d["form"], "usable": bool(d["usable"]),
                "rate_law_text": d["rate_law_text"].strip(), "rate_unit_published": d["rate_unit"],
                "rate_unit_model": cat.rate_unit_amcrax, "pressure_basis": d["pressure_basis"],
                "parameters": d["parameters"], "validity": d["validity"],
                "irreversible_published": bool(d["irreversible_published"]),
                "reversibility_treatment": (
                    "published reversible driving force (Keq basis selectable; PFR default amcrax_thermo)"
                    if not d["irreversible_published"] else
                    "irreversible as published; AmCraX approach factor (1 - Q/Kp) applied, default ON (assumption)"),
                "equilibrium_constant": d.get("equilibrium_constant"), "bed_properties": d.get("bed_properties"),
                "limitations": d["limitations"], "source": d["source"], "citekey": d["source"]["citekey"],
                "amcrax_extensions": cat.amcrax_extensions,
                "validity_classification": vclass(cid),
            }
    return {"unit_conversions": reg["unit_conversions"], "equilibrium_approach_factor": reg["equilibrium_approach_factor"],
            "laws": laws, "law_ids": list(laws),
            "validity_classification_file": rel(VALIDITY) if validity is not None else None,
            "validity_classification_status": "read" if validity is not None else "absent when exported (another workstream writes it)",
            "takahashi_root_bracket_ln_theta_s": [-300.0, 0.0],
            "source": rel(KIN)}


def viscosity_table() -> dict:
    """Cantera mixture-averaged viscosity of the baseline-feed cracked gas against T and conversion X (P independent)."""
    T = [380.0 + 20.0 * i for i in range(47)]       # 380 .. 1300 K
    X = [0.05 * i for i in range(21)]
    feed = pfr.BASELINE_FEED_kmol_h
    F0 = feed["NH3"]
    mu = []
    for t in T:
        row = []
        for x in X:
            n = {"NH3": F0 * (1 - x), "H2O": feed["H2O"], "N2": 0.5 * F0 * x, "H2": 1.5 * F0 * x}
            tot = sum(n.values())
            row.append(pfr.gas_viscosity_Pa_s(t, 10.0, {k: v / tot for k, v in n.items()}))
        mu.append(row)
    return {"T_K": T, "X": X, "mu_Pa_s": mu, "feed_kmol_h": dict(feed),
            "source": "Cantera gri30.yaml mixture-averaged viscosity (amcrax.reactor.pfr.gas_viscosity_Pa_s), evaluated at 10 bar",
            "reduction": "browser interpolates bilinearly in (T, X); valid for the baseline feed composition only"}


def reactor_block() -> dict:
    return {"default_bed": dict(pfr.DEFAULT_BED), "default_bed_source": pfr.DEFAULT_BED_SOURCE,
            "baseline_feed_kmol_h": dict(pfr.BASELINE_FEED_kmol_h), "molar_mass_kg_mol": dict(pfr.MOLAR_MASS_kg_mol),
            "normal_T_K": pfr.NORMAL_T_K, "normal_P_Pa": pfr.NORMAL_P_Pa, "x_seed_temkin": 1e-6,
            "hydraulic_stop_fraction_of_inlet_pressure": 0.05, "ergun": {"viscous": 150.0, "inertial": 1.75},
            "default_n_tubes": 50, "default_keq_basis": "amcrax_thermo",
            "viscosity": viscosity_table(), "source": "amcrax.reactor.pfr (simulate_pfr)"}


PROC_T = [400.0 + 25.0 * i for i in range(17)]          # 400 .. 800 degC
PROC_P = [3.0, 5.0, 10.0, 15.0, 20.0, 25.0, 30.0, 40.0, 50.0]


def _case(T, P, hi, **kw):
    ci = CaseInputs(case_id="sim", reactor_temperature_C=T, reactor_pressure_bar=P, heat_integration=hi, **kw)
    return fs.run_python_case(ci)


def process_block() -> dict:
    d = CaseInputs()
    grid = {}
    for hi in (True, False):
        rows = []
        for T in PROC_T:
            row = []
            for P in PROC_P:
                try:
                    k = _case(T, P, hi).kpis
                    F = d.feed_total_kmol_h
                    row.append({"vaporiser_kW": k.vaporiser_duty_kW / F, "pump_kW": k.pump_power_kW / F,
                                "preheat_kW": k.preheat_duty_kW / F, "recovered_kW": k.recovered_heat_kW / F,
                                "cooling_kW": k.cooling_duty_kW / F,
                                "combustion_over_lhv": k.tailgas_combustion_heat_kW / k.tailgas_lhv_kW})
                except fs.FlowsheetSpecError:
                    row.append(None)
            rows.append(row)
        grid["hi" if hi else "nohi"] = rows
    return {"inputs_defaults": d.model_dump(), "pump_efficiency": fs.PUMP_EFFICIENCY,
            "vaporiser_superheat_K": fs.VAPORIZER_SUPERHEAT_K, "feed_pressure_bar": fs.FEED_PRESSURE_BAR,
            "min_flowsheet_pressure_bar": fs.MIN_FLOWSHEET_PRESSURE_BAR,
            "air": {"T_C": fs.AIR_T_C, "O2": fs.AIR_O2, "N2": fs.AIR_N2},
            "burner": "adiabatic complete combustion H2 + 0.5 O2 -> H2O, NH3 + 0.75 O2 -> 0.5 N2 + 1.5 H2O; air = (1 + excess) x stoichiometric",
"pressure_profile": {k: list(v) for k, v in fs.pressure_profile().items()},
            "grid": {"T_C": PROC_T, "P_bar": PROC_P, "per_kmol_h_total_feed": grid,
                     "fields": ["vaporiser_kW", "pump_kW", "preheat_kW", "recovered_kW", "cooling_kW", "combustion_over_lhv"],
                     "generated_by": "amcrax.process_model.flowsheet.run_python_case (eos='ideal', CaseInputs defaults otherwise)",
                     "null": "specification infeasible in the Python flowsheet (FlowsheetSpecError)"},
            "reduction": ("Pump, vaporiser, preheater, feed-effluent exchanger and cooler duties and the burner "
                          "combustion/LHV ratio are bilinear interpolations of this Python grid (scaled linearly with feed "
                          "flow, at equilibrium conversion). Cracker duty, H2 production and tail-gas LHV are computed in "
                          "the browser (ideal gas, NASA-7), from equilibrium or from the kinetic reactor outlet."),
            "source": "amcrax.process_model.flowsheet; config/flowsheet.json"}


def purification_block() -> dict:
    d = CaseInputs()
    return {"psa_h2_recovery_default": d.psa_h2_recovery, "psa_n2_slip_default": d.psa_n2_slip,
            "psa_feed_temperature_C_default": d.psa_feed_temperature_C,
            "model": ("reduced-order PSA component splitter as amcrax.process_model.flowsheet: H2 recovery and N2 slip are "
                      "assumed inputs; NH3, H2O, O2 go to the tail gas"),
            "purity_label": "assumption (follows from assumed recovery and N2 slip; no adsorption model)",
            "membrane": "not ported to the browser (Python Sieverts model in amcrax.separation.membrane); known gap",
            "stored_comparison": stored_purification_comparison(),
            "source": "amcrax.schemas.CaseInputs; amcrax.process_model.flowsheet"}


PURIFICATION_COMPARISON = ROOT / "results" / "research" / "purification" / "phase2_comparison.json"
_PUR_FIELDS = ("h2_recovery", "h2_purity_mole_frac", "n2_ppm", "nh3_ppm", "meets_spec_within_model_scope", "membrane_area_m2",
               "capital_USD", "membrane_module_cost_USD", "replacement_USD_per_yr", "purification_only_usd_per_kg",
               "lcoh_usd_per_kg_usable", "lcoh_sgd_per_kg_usable")


def stored_purification_comparison():
    """PSA against Pd-Ag membrane at the reference conditions (Python results of scripts/research/purification_phase2.py).
    Stored values only: the browser has no membrane model, so these numbers do not respond to the simulator controls."""
    if not PURIFICATION_COMPARISON.exists():
        return None
    src = json.loads(PURIFICATION_COMPARISON.read_text(encoding="utf-8"))
    specs = {}
    for sid, sp in (src.get("specs") or {}).items():
        confs = {}
        for cid, c in (sp.get("configurations") or {}).items():
            row = {k: c.get(k) for k in _PUR_FIELDS}
            rd = c.get("readiness") or {}
            row["readiness"] = {k: rd.get(k) for k in ("configuration", "trl", "polishing_bed", "source") if rd.get(k) is not None}
            rs = c.get("recovery_source")
            if rs:
                row["recovery_source"] = {k: rs.get(k) for k in ("source_type", "source", "note") if rs.get(k) is not None}
            confs[cid] = row
        specs[sid] = {"label": sp.get("label"), "configurations": confs}
    basis = src.get("basis") or {}
    return {"file": rel(PURIFICATION_COMPARISON), "script": (src.get("provenance") or {}).get("script"),
            "source_type": "python",
            "statement": ("Stored Python results at the reference conditions (plant gate, reference scenario). They do not respond "
                          "to the simulator controls; the browser has no membrane model."),
            "basis": {k: basis.get(k) for k in ("economics", "baseline_lcoh_usd", "baseline_lcoh_sgd", "baseline_note") if k in basis},
            "specs": specs}


CARBON_PRICING_VECTORS = ROOT / "results" / "research" / "carbon_pricing" / "test_vectors.json"


def carbon_pricing_vectors() -> dict:
    """The Python carbon-pricing test vectors (scripts/research/carbon_pricing_run.py), copied without the generation time so
    that the export stays deterministic. Used by frontend/src/sim/carbon.test.ts (relative tolerance as stored)."""
    src = json.loads(CARBON_PRICING_VECTORS.read_text(encoding="utf-8"))
    prov = {k: v for k, v in (src.get("provenance") or {}).items() if k != "generated_utc"}
    return {"schema": SCHEMA, "source_file": rel(CARBON_PRICING_VECTORS), "provenance": prov,
            "tolerance_relative": src["tolerance_relative"], "mapping": src.get("mapping"),
            "n_vectors": len(src["vectors"]), "vectors": src["vectors"]}


ECON_CAPEX_MODE = "reference"   # unified reference CAPEX (cho2026_itemised_v1), the default of singapore.evaluate
CATALYST_PRICES = ROOT / "research" / "data" / "catalyst_prices.json"
#: rate law -> formulation key of research/data/catalyst_prices.json (the supports of the two Takahashi laws are as in the
#: laws' own composition strings; the Ni-Ru laws match the two CeO2 formulations by name)
CATALYST_PRICE_KEY = {"ni_takahashi_microkinetic": "Ni/MgO", "ru_takahashi_microkinetic": "Ru/MgO", "ru_kum_temkin_pyzhev": "Ru/Al2O3",
                      "nire_ceo2_5ni1ru_lucentini_lhhw": "5Ni1Ru/CeO2", "nire_ceo2_2p5ni0p5ru_lucentini_lhhw": "2.5Ni0.5Ru/CeO2"}


def _reference():
    from amcrax.economics.reference import load_reference_scenario
    return load_reference_scenario()


def catalyst_price_block() -> dict:
    """Metal-content catalyst prices (research/data/catalyst_prices.json). Original currency is USD; SGD is computed in the
    browser with the reference scenario's one exchange rate (the 1.2801 stored in that file is superseded and not exported)."""
    d = json.loads(CATALYST_PRICES.read_text(encoding="utf-8"))
    sc = d["scenarios_usd_per_kg_finished_catalyst"]
    by_law = {}
    for cid, key in CATALYST_PRICE_KEY.items():
        s = sc[key]
        by_law[cid] = {"formulation": key, "loading_wt_pct": s["loading_wt_pct"], "grade": s["grade"],
                       "loading_basis": s["loading_basis"],
                       **{lvl: {"usd_per_kg": s[lvl]["usd_per_kg"], "P_Ni_usd_per_kg": s[lvl]["P_Ni_usd_per_kg"],
                                "P_Ru_usd_per_kg": s[lvl]["P_Ru_usd_per_kg"], "N_usd_per_kg": s[lvl]["N_usd_per_kg"]}
                          for lvl in ("low", "central", "high")}}
    return {"by_law": by_law, "currency": "USD", "formula": "price = wNi*P_Ni + wRu*P_Ru + N (per kg finished catalyst)",
            "inputs": d["inputs"], "caveats": d["scenario_caveats"], "file": rel(CATALYST_PRICES),
            "statement": ("derived from metal content (metal price times loading plus a non-metal term taken from one published TEA "
                          "price), NOT supplier quotations; no quotation or published commercial price exists for any "
                          "ammonia-cracking catalyst in the file"),
            "levels": ["central", "low", "high"], "default_level": "central",
            "phase1_tea_note": ("Phase 1 published TEA price: Ni 33.4 USD/kg (8 wt% Ni/Al2O3, Cho 2026) and Ru 542 USD/kg (Ru-K/CaO), "
                                "selectable; the Ru value is below the Ru metal floor"),
            "fx_not_used": "the file's own SGD values (1.2801 SGD/USD, Fed G.5 2026-10) are superseded by the reference scenario rate"}


def economics_block() -> dict:
    """Economic parameters as amcrax.economics.singapore.evaluate RESOLVES them (its returned 'assumptions') with the
    unified reference CAPEX (capex_mode 'reference', method cho2026_itemised_v1; backend/amcrax/economics/reference.py)."""
    from amcrax.economics import reference as rf
    data = sg.load_singapore_data()
    probe = sg.evaluate(sg.extract_summary(_case(600.0, 20.0, True)), "grey", {"capex_mode": ECON_CAPEX_MODE})
    a_eff = dict(probe["assumptions"]["economic"])
    p_eff = {k: v for k, v in dict(probe["assumptions"]["singapore"]).items() if isinstance(v, (int, float, str, bool, type(None)))}
    prices = {}
    for c in ("Ni", "Ru"):
        prices[c] = EconomicAssumptions(**{**a_eff, "catalyst": c, "catalyst_price_USD_per_kg": None}).resolved_catalyst_price_USD_per_kg()
    ref = _reference()
    cx = ref.raw["capex"]
    items = rf.reference_item_costs()
    return {
        "basis": f"reference_scenario {ref.id} v{ref.version} ({ref.capex_method})",
        "basis_short": f"unified reference scenario {ref.id} v{ref.version}",
        "basis_note": (f"CAPEX: unified reference method {ref.capex_method} (capex_mode='{ECON_CAPEX_MODE}'), cost year {cx['cost_year']['value']} USD. "
                       "Every other parameter exactly as evaluate() resolves it from backend/amcrax/data/reference_scenario.yaml."),
        "capex_mode": ECON_CAPEX_MODE,
        "reference_scenario": {"id": ref.id, "version": ref.version, "sha256": ref.sha256},
        "source_files": ["backend/amcrax/data/reference_scenario.yaml", "backend/amcrax/data/singapore.yaml",
                         "backend/amcrax/data/economics.yaml (via EconomicAssumptions)", rel(CATALYST_PRICES)],
        "source_functions": ["amcrax.economics.singapore.evaluate", "amcrax.economics.reference.reference_capex",
                             "amcrax.economics.lcoh.EconomicAssumptions"],
        "economic_assumptions": a_eff,
        "sg_params": p_eff,
        "catalyst_price_USD_per_kg": prices,
        "catalyst_price_phase1_note": "Phase 1 published TEA price (EconomicAssumptions): Ni 8 wt% Ni/Al2O3 (Cho 2026), Ru Ru-K/CaO",
        "catalyst_prices": catalyst_price_block(),
        "catalyst_metal_map": {"Ni": "Ni", "Ru": "Ru", "Ni-Ru": "Ru"},
        "catalyst_metal_map_note": ("assumption (Phase 1 TEA price only): EconomicAssumptions prices only Ni and Ru; a Ru-containing Ni-Ru "
                                    "catalyst is priced as Ru. The metal-content prices price each of the five formulations separately."),
        "nh3_price_scenarios_USD_per_t": {k: sg.scenario_price(k) for k in sg.SCENARIOS},
        "capex_reference": {
            "method": ref.capex_method, "cost_year": cx["cost_year"]["value"], "price_year_label": ref.raw["price_year_label"],
            "installed_ISBL_USD_reference_plant": {k: v for k, v in items["installed_USD"].items() if k != "compressor"},
            "excluded_items": ["compressor"], "indirect_factor": items["indirect_factor"],
            "reference_nh3_feed_kmol_h": items["reference_nh3_feed_kmol_h"], "scaling_exponent": ref.capex_scaling_exponent,
            "location_factor": cx["location_factor_singapore"]["value"],
            "size_driver": dict(cx["size_driver"]["value"]),
            "formula": "TCI = sum_i(I_i,ref (S/S_ref)^n x location_factor) x capex_multiplier x indirect_factor; S = NH3 feed (all items)",
            "source": "backend/amcrax/economics/reference.py (reference_capex); backend/amcrax/data/reference_scenario.yaml"},
        "carbon_tax": {"rate_2026_SGD_per_tCO2e": p_eff["carbon_tax_SGD_per_t"], "threshold_tCO2e_per_yr": ref.carbon_threshold_tCO2e_per_yr},
        "natural_gas_co2_factor_kg_per_GJ": data["gas_and_fuel"]["natural_gas_co2_factor_kg_per_GJ"]["value"],
        "cost_basis": ref.raw["price_year_label"],
        "h2_selling_price_USD_per_kg": ref.h2_selling_price_USD_per_kg,
    }


def fx_block() -> dict:
    """The one USD->SGD rate, where the Python economics takes it from (reference scenario if present)."""
    ref = _reference()
    if ref is not None:
        raw = ((getattr(ref, "raw", None) or {}).get("economics") or {}).get("fx_SGD_per_USD") or {}
        if not raw:
            def find(o):
                if isinstance(o, dict):
                    if "fx_SGD_per_USD" in o and isinstance(o["fx_SGD_per_USD"], dict):
                        return o["fx_SGD_per_USD"]
                    for v in o.values():
                        r = find(v)
                        if r:
                            return r
                return None
            raw = find(getattr(ref, "raw", None) or {}) or {}
        return {"SGD_per_USD": ref.fx_SGD_per_USD, "date": getattr(ref, "fx_date", None) or raw.get("date"),
                "access_date": raw.get("access_date"), "source": raw.get("source") or raw.get("note"), "url": raw.get("url"),
                "stored_in": "backend/amcrax/data/reference_scenario.yaml (via amcrax.economics.reference)"}
    fx = sg.load_singapore_data()["fx_SGD_per_USD"]
    return {"SGD_per_USD": fx["value"], "date": fx.get("year"), "access_date": fx.get("access_date"),
            "source": fx.get("source"), "url": fx.get("url"), "stored_in": "backend/amcrax/data/singapore.yaml"}


def carbon_block() -> dict:
    f = load_factors()
    routes = {}
    for r in ("grey", "blue", "blue_v2", "green", "green_lee"):
        s = lca.route_spec(r)
        routes[r] = {"ef_kg_per_kg_nh3": s.ef, "low": s.low, "high": s.high, "label": s.label, "source_type": s.source_type}
    return {
        "accounting": {"upstream_ammonia": {k: v["value"] for k, v in f["upstream_ammonia"].items()},
                       "electricity": {k: v["value"] for k, v in f["electricity"].items()},
                       "ship_ef_kg_per_tkm": f["transport"]["ship_ef"]["value"],
                       "distance_km": f["transport"]["distance_km"]["value"],
                       "natural_gas_kg_per_TJ": f["heating"]["natural_gas_combustion"]["value"],
                       "fired_heater_efficiency_lhv": f["heating"]["fired_heater_efficiency_lhv"]["value"],
                       "electric_heater_efficiency": f["heating"]["electric_heater_efficiency"]["value"],
                       "source": "backend/amcrax/data/environmental.yaml via amcrax.environmental.carbon_intensity",
                       "statement": "simplified carbon-intensity accounting, not a life-cycle assessment"},
        "lca_routes": routes,
        "lca_source": "amcrax.environmental.lca.route_spec (research life-cycle factors, kg CO2e per kg NH3 at the producer gate)",
        "actual_boundary": ("Singapore carbon tax on direct (Scope 1) facility CO2e only, only above the facility threshold, as "
                            "amcrax.economics.singapore.evaluate applies it; upstream and overseas emissions are not taxed"),
        "hypothetical_boundary": ("HYPOTHETICAL, not Singapore law: a user carbon price in SGD per tCO2e times the life-cycle "
                                  "carbon intensity per kg H2; it replaces the actual tax term so that no emission is charged twice"),
    }


def build_model() -> dict:
    return {
        "schema": SCHEMA,
        "statement": "Parameters of the browser-side simulator. Generated from the Python registries; not an Aspen result.",
        "thermo": thermo_block(), "kinetics": kinetics_block(), "reactor": reactor_block(),
        "process": process_block(), "purification": purification_block(), "economics": economics_block(),
        "fx": fx_block(), "carbon": carbon_block(), "tolerances": TOLERANCES,
        "provenance": {"script": "scripts/research/export_simulator_data.py", "source_type": "python",
                       "inputs": [rel(KIN), "backend/amcrax/data/nasa7.json", "backend/amcrax/data/singapore.yaml",
                                  "backend/amcrax/data/reference_scenario.yaml", rel(CATALYST_PRICES),
                                  "backend/amcrax/data/environmental.yaml", "config/flowsheet.json"]},
    }


# ------------------------------------------------------------------------------------------------ anchors
def _kin_case(d: dict) -> dict:
    a = d.get("aspen") or {}
    rp = a.get("rplug") or {}
    inp = (d.get("inputs") or {}).get("reactor") or {}
    prof = rp.get("profiles") or {}
    out = a.get("product") or a.get("cracker_outlet") or {}
    inl = a.get("feed") or a.get("cracker_inlet") or {}
    fsr = a.get("flowsheet_result") or {}
    nh3_in = (inl.get("flows_kmol_h") or {}).get("NH3")
    y = prof.get("y") or {}
    conv_prof = None
    if y.get("NH3") and nh3_in:
        # conversion of reactor-inlet NH3 from the mole-fraction profile (N balance with constant H2O flow)
        h2o = (inl.get("flows_kmol_h") or {}).get("H2O", 0.0)
        tot_in = sum((inl.get("flows_kmol_h") or {}).values())
        conv_prof = []
        for i, yn in enumerate(y["NH3"]):
            yw = y.get("H2O", [None] * len(y["NH3"]))[i]
            if yw and h2o:
                ntot = h2o / yw
                conv_prof.append(1.0 - yn * ntot / nh3_in)
            else:
                conv_prof.append(None)
        del tot_in
    return finite({
        "case_id": d.get("case_id"), "configuration": d.get("configuration"), "catalyst_id": inp.get("catalyst_id"),
        "T_C": inp.get("temperature_C"), "P_bar": inp.get("pressure_bar"), "catalyst_mass_kg": inp.get("catalyst_mass_kg"),
        "thermal_mode": inp.get("thermal_mode"), "coolant_temperature_C": inp.get("coolant_temperature_C"),
        "U_W_m2K": inp.get("U_W_m2K"), "pressure_drop": inp.get("pressure_drop"), "n_tubes": inp.get("n_tubes"),
        "tube_diameter_m": inp.get("tube_diameter_m"), "feed_kmol_h": inp.get("feed_kmol_h"),
        "h2_seed_conversion": inp.get("h2_seed_conversion"),
        "heat_integration": ((d.get("inputs") or {}).get("flowsheet") or {}).get("heat_integration"),
        "conversion": a.get("conversion_of_reactor_inlet_NH3"), "conversion_of_fresh_NH3": a.get("conversion_of_fresh_NH3"),
        "duty_kW": rp.get("duty"), "reactor_length_m": rp.get("reactor_length"), "residence_time_s": rp.get("residence_time_s"),
        "inlet": inl, "outlet": out,
        "profiles": {"length_m": prof.get("length_m"), "T_C": prof.get("T_C"), "P_bar": prof.get("P_bar"),
                     "y": y, "conversion": conv_prof,
                     "catalyst_mass_kg": ([L / prof["length_m"][-1] * inp["catalyst_mass_kg"] for L in prof["length_m"]]
                                          if prof.get("length_m") and prof["length_m"][-1] and inp.get("catalyst_mass_kg") else None),
                     "catalyst_mass_note": "uniform bed: W(z) = W_total z / L (derived)"},
        "equilibrium_reference": (a.get("equilibrium_reference") or {}) and {
            "conversion": a["equilibrium_reference"].get("conversion_of_reactor_inlet_NH3"),
            "duty_kW": a["equilibrium_reference"].get("duty_kW")},
        "flowsheet_kpis": fsr.get("kpis"), "model_file": d.get("model_inp"), "run_status": d.get("run_status"),
        "python_pfr_outlet": (d.get("python_pfr") or {}).get("outlet"),
        "source": "aspen", "engine": ((d.get("provenance") or {}).get("model_versions") or {}).get("aspen"),
    })


def build_anchors() -> dict:
    kin = []
    for p in sorted(ASPEN_KIN.glob("*.json")):
        try:
            d = json.loads(p.read_text(encoding="utf-8"))
        except ValueError:
            continue
        if not isinstance(d, dict) or "aspen" not in d or d.get("run_status") != "ok":
            continue
        c = _kin_case(d)
        c["file"] = rel(p)
        kin.append(c)
    core = []
    for name in ("baseline", "baseline_no_hi", "scn_fuel_cell_grade", "scn_high_pressure", "scn_high_recovery",
                 "scn_high_temperature", "scn_low_pressure", "scn_low_recovery", "scn_low_temperature", "scn_tight_fehe"):
        p = SIM / f"{name}.json"
        if not p.exists():
            continue
        d = json.loads(p.read_text(encoding="utf-8"))
        core.append(finite({"case_id": d.get("case_id"), "source": d.get("source"), "inputs": d.get("inputs"),
                            "kpis": d.get("kpis"), "file": rel(p), "model_file": d.get("model_file")}))
    grid = []
    with open(EQ_GRID, encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            grid.append({"T_C": float(r["T_C"]), "P_bar": float(r["P_bar"]), "conversion": float(r["nh3_conversion"]),
                         "heat_duty_kJ_per_mol_NH3_fed": float(r["heat_duty_kJ_per_mol_NH3_fed"]),
                         "property_method": r["property_method"]})
    Ts = sorted({g["T_C"] for g in grid})
    Ps = sorted({g["P_bar"] for g in grid})
    return {"schema": SCHEMA, "statement": "Stored Aspen Plus V15 results (no new Aspen run). 'aspen' values only.",
            "kinetic_cases": kin, "core_cases": core,
            "equilibrium_grid": {"T_C": Ts, "P_bar": Ps, "points": grid, "n_points": len(grid), "file": rel(EQ_GRID),
                                 "block": "RGibbs, PENG-ROB, pure NH3 feed"},
            "provenance": {"script": "scripts/research/export_simulator_data.py", "source_type": "aspen",
                           "inputs": [rel(ASPEN_KIN), rel(SIM), rel(EQ_GRID)]}}


# ------------------------------------------------------------------------------------------------ test vectors
def _pfr_vec(cid, T, P, W, mode, **kw):
    r = pfr.simulate_pfr(cid, W, T_in_C=T, P_in_bar=P, mode=mode, n_points=11, **kw)
    o = r.outlet
    return {"kind": "pfr", "id": f"pfr_{LAW_SHORT[cid]}_{mode}_T{T:g}_P{P:g}_W{W:g}" + ("_dp" if kw.get("pressure_drop", True) else "")
            + (f"_nt{kw['n_tubes']}" if "n_tubes" in kw else ""),
            "inputs": {"catalyst_id": cid, "T_in_C": T, "P_in_bar": P, "W_kg": W, "mode": mode,
                       "pressure_drop": kw.get("pressure_drop", True), "n_tubes": kw.get("n_tubes", 1),
                       "T_wall_C": kw.get("T_wall_C"), "U_W_m2K": kw.get("U_W_m2K")},
            "python": {"W_kg": r.W_kg, "conversion": r.conversion, "T_K": r.T_K, "P_bar": r.P_bar,
                       "outlet": {k: o[k] for k in ("conversion", "T_C", "P_bar", "X_eq_outlet", "heat_input_kW",
                                                    "residence_time_s", "hydraulic_limit")},
                       "rate_inlet": r.rate_mol_per_kgcat_s[0]}}


def pfr_vectors() -> list[dict]:
    v = []
    for cid in LAW_SHORT:
        v.append(_pfr_vec(cid, 500.0, 1.01325, 20.0, "isothermal", pressure_drop=False))
        v.append(_pfr_vec(cid, 450.0, 20.0, 100.0, "isothermal", pressure_drop=False))
        v.append(_pfr_vec(cid, 600.0, 20.0, 50.0, "isothermal", n_tubes=50))
        v.append(_pfr_vec(cid, 550.0, 10.0, 5.0, "isothermal", n_tubes=50))
        v.append(_pfr_vec(cid, 650.0, 20.0, 100.0, "adiabatic", n_tubes=50))
        v.append(_pfr_vec(cid, 450.0, 5.0, 100.0, "external", n_tubes=50, T_wall_C=650.0, U_W_m2K=100.0))
        v.append(_pfr_vec(cid, 700.0, 40.0, 200.0, "isothermal", pressure_drop=False))
    return v


def rate_vectors() -> list[dict]:
    v = []
    for cid in LAW_SHORT:
        for T, p in ((723.15, {"NH3": 0.9, "H2": 0.075, "N2": 0.025}), (873.15, {"NH3": 10.0, "H2": 7.5, "N2": 2.5}),
                     (773.15, {"NH3": 1.0, "H2": 9.0, "N2": 3.0, "H2O": 0.02})):
            v.append({"kind": "rate", "id": f"rate_{LAW_SHORT[cid]}_T{T:g}_P{sum(p.values()):g}",
                      "inputs": {"catalyst_id": cid, "T_K": T, "p_bar": p},
                      "python": {"rate": rate_mol_per_kgcat_s(cid, T, p, keq_basis="amcrax_thermo")}})
    return v


def _summary_python(res) -> dict:
    k = res.kpis
    return {"h2_product_kg_h": k.h2_product_kg_h, "h2_in_cracked_gas_kmol_h": k.h2_in_cracked_gas_kmol_h,
            "nh3_conversion": k.nh3_conversion, "reactor_duty_kW": k.reactor_duty_kW, "preheat_duty_kW": k.preheat_duty_kW,
            "vaporiser_duty_kW": k.vaporiser_duty_kW, "recovered_heat_kW": k.recovered_heat_kW,
            "total_external_heating_kW": k.total_external_heating_kW, "cooling_duty_kW": k.cooling_duty_kW,
            "pump_power_kW": k.pump_power_kW, "tailgas_combustion_heat_kW": k.tailgas_combustion_heat_kW,
            "tailgas_lhv_kW": k.tailgas_lhv_kW, "net_fuel_heat_deficit_kW": k.net_fuel_heat_deficit_kW,
            "h2_purity_mole_frac": k.h2_purity_mole_frac}


PROC_CASES = [  # (T, P, hi, feed, recovery, on_grid)
    (600.0, 20.0, True, 100.0, 0.85), (600.0, 20.0, False, 100.0, 0.85), (500.0, 10.0, True, 100.0, 0.85),
    (700.0, 30.0, True, 150.0, 0.90), (450.0, 5.0, False, 80.0, 0.80), (650.0, 40.0, True, 100.0, 0.95),
    (550.0, 15.0, False, 120.0, 0.85),
    # off-grid points: the interpolated parts are compared as data (reported, not asserted)
    (612.0, 18.0, True, 100.0, 0.85), (537.0, 12.0, False, 100.0, 0.85), (681.0, 27.0, True, 100.0, 0.88),
]


def process_vectors() -> list[dict]:
    v = []
    for T, P, hi, F, R in PROC_CASES:
        res = _case(T, P, hi, feed_total_kmol_h=F, psa_h2_recovery=R)
        on = T in PROC_T and P in PROC_P
        v.append({"kind": "process", "id": f"proc_T{T:g}_P{P:g}_{'hi' if hi else 'nohi'}_F{F:g}_R{R:g}",
                  "inputs": {"T_C": T, "P_bar": P, "heat_integration": hi, "feed_total_kmol_h": F, "psa_h2_recovery": R},
                  "on_grid": on, "python": _summary_python(res)})
    return v


def purification_vectors() -> list[dict]:
    v = []
    for R, slip in ((0.85, 0.001), (0.70, 0.001), (0.95, 0.0), (0.90, 0.01)):
        res = _case(600.0, 20.0, True, psa_h2_recovery=R, psa_n2_slip=slip)
        v.append({"kind": "purification", "id": f"psa_R{R:g}_slip{slip:g}",
                  "inputs": {"T_C": 600.0, "P_bar": 20.0, "heat_integration": True, "psa_h2_recovery": R, "psa_n2_slip": slip},
                  "python": _summary_python(res)})
    return v


def econ_vectors() -> list[dict]:
    v = []
    base = _case(600.0, 20.0, True)
    nohi = _case(600.0, 20.0, False)
    combos = [
        ("base_grey", base, "grey", {}),
        ("base_blue", base, "blue", {}),
        ("base_green", base, "green_current", {}),
        ("nohi_grey", nohi, "grey", {}),
        ("base_ru_100kg", base, "grey", {"catalyst": "Ru", "catalyst_mass_kg": 100.0}),
        ("base_ni_500kg", base, "grey", {"catalyst": "Ni", "catalyst_mass_kg": 500.0}),
        ("base_price600", base, 600.0, {}),
        ("base_ng_heat", base, "grey", {"heat_fuel": "natural_gas"}),
        ("base_ng_nothreshold", base, "grey", {"heat_fuel": "natural_gas", "apply_threshold": False}),
        ("base_scale5", base, "grey", {"capacity_scale": 5.0}),
        ("base_ru_derived_price", base, "grey", {"catalyst": "Ru", "catalyst_mass_kg": 100.0, "catalyst_price_USD_per_kg": 3006.14}),
        ("base_price_h2_high", base, "grey", {"h2_price_USD_per_kg": 6.0}),
        ("stored_baseline", json.loads((SIM / "baseline.json").read_text(encoding="utf-8")), "grey", {}),
    ]
    for name, res, scen, ov in combos:
        summ = sg.extract_summary(res)
        ov = {"capex_mode": ECON_CAPEX_MODE, **ov}
        out = sg.evaluate(summ, scen, ov)
        v.append({"kind": "economics", "id": f"econ_{name}",
                  "inputs": {"summary": finite(summ), "scenario": scen, "overrides": ov},
                  "python": finite({"lcoh_USD_per_kg": out["lcoh_USD_per_kg"], "rec_USD_per_kg": out["rec_USD_per_kg"],
                                    "breakdown_USD_per_kg": out["breakdown_USD_per_kg"], "catalyst_mass_kg": out["catalyst_mass_kg"],
                                    "direct_emissions_tCO2e_per_yr": out["direct_emissions_tCO2e_per_yr"],
                                    "carbon_tax_liable": out["carbon_tax_liable"], "npv_USD": out["npv_USD"], "payback_yr": out["payback_yr"],
                                    "lcoh_SGD_per_kg": out["lcoh_SGD_per_kg"],
                                    "capex_total_USD": out["capex"]["total_capex_USD"]})})
    return v


def carbon_vectors() -> list[dict]:
    v = []
    base = _case(600.0, 20.0, True)
    nohi = _case(600.0, 20.0, False)
    for name, res in (("base", base), ("nohi", nohi)):
        for scen in ("grey/natural_gas", "blue/self_firing", "green/self_firing", "grey/electric"):
            r = carbon_intensity(res, scen)
            k = res.kpis
            v.append({"kind": "carbon", "id": f"ci_{name}_{scen.replace('/', '_')}",
                      "inputs": {"scenario": scen, "h2_kg_h": k.h2_product_kg_h,
                                 "nh3_feed_kg_h": r.nh3_feed_kg_h, "heat_deficit_kW": r.heat_deficit_kW,
                                 "pump_kW": k.pump_power_kW},
                      "python": {"total": r.total_kgCO2e_per_kgH2, "breakdown": r.breakdown_kgCO2e_per_kgH2.model_dump(),
                                 "nh3_fuel_kg_h": r.nh3_fuel_kg_h}})
    return v


def build_vectors() -> dict:
    vec = rate_vectors() + pfr_vectors() + process_vectors() + purification_vectors() + econ_vectors() + carbon_vectors()
    return {"schema": SCHEMA, "statement": "Outputs of the PYTHON models (amcrax), used to test the browser port.",
            "tolerances": TOLERANCES, "n_vectors": len(vec), "vectors": finite(vec),
            "provenance": {"script": "scripts/research/export_simulator_data.py", "source_type": "python",
                           "models": ["amcrax.kinetics.rate_mol_per_kgcat_s", "amcrax.reactor.pfr.simulate_pfr",
                                      "amcrax.process_model.flowsheet.run_python_case", "amcrax.economics.singapore.evaluate",
                                      "amcrax.environmental.carbon_intensity"]}}


def dumps(obj) -> str:
    return json.dumps(obj, indent=1, sort_keys=True, allow_nan=False, ensure_ascii=True) + "\n"


def build_all() -> dict[str, str]:
    return {"model.json": dumps(build_model()), "aspen_anchors.json": dumps(build_anchors()),
            "test_vectors.json": dumps(build_vectors()), "carbon_pricing_vectors.json": dumps(carbon_pricing_vectors())}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true", help="exit 1 if a stored file differs from a fresh export")
    a = ap.parse_args(argv)
    files = build_all()
    if a.check:
        bad = [n for n, t in files.items() if not (OUT / n).exists() or (OUT / n).read_text(encoding="utf-8") != t]
        print("stale:" if bad else "current", *bad)
        return 1 if bad else 0
    OUT.mkdir(parents=True, exist_ok=True)
    for n, t in files.items():
        (OUT / n).write_text(t, encoding="utf-8", newline="\n")
        print(f"wrote {rel(OUT / n)} ({len(t)} bytes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
