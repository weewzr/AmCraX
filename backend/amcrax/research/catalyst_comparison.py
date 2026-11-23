"""Heat integration coupled to catalyst performance, and the catalyst cost comparison (workstream H, hypothesis H3).

Logic (no circularity):
  1. Kinetics fix the catalyst mass W(T) that reaches a target NH3 conversion X at pressure P for each catalyst
     (amcrax.reactor.pfr.catalyst_mass_for_conversion, isothermal plug flow, no pressure drop, effectiveness
     factor 1). The operating temperature is NOT assumed.
  2. The flowsheet energy balance at (T, P, X) comes from the independent Python flowsheet
     (amcrax.process_model.run_python_case) with the cracker outlet held at the kinetic conversion X instead of
     equilibrium (``kinetic_flowsheet``; X above equilibrium is refused). Same feed, same P, same X, so every
     catalyst delivers the same hydrogen product: catalysts differ only through T and W.
  3. Temperature-level heat accounting (amcrax.heat_integration): external heating after the feed/effluent
     exchanger and after tail-gas firing where the flue gas is hot enough, pinch targets, FEHE UA and area.
  4. The heat that the tail gas cannot cover is fired with supplementary NH3 in a furnace with a stated
     efficiency and thermal-loss allowance (ASSUMPTIONS, below).
  5. Costs: amcrax.economics.singapore.evaluate (LCOH, REC); catalyst replacement W * price / lifetime.
     Carbon intensity: amcrax.enduse.pathways.carbon_intensity with the factors of amcrax.environmental.lca.
  6. Each catalyst's cost-optimal T minimises LCOH over a temperature grid (W(T) and heating both vary).

Every output names its source_type: 'python' (this model), 'aspen' (stored Aspen Plus V15 runs),
'literature', 'assumption'.
"""
from __future__ import annotations

import dataclasses
import json
import math
import warnings
from functools import lru_cache
from pathlib import Path
from typing import Any, Optional
from unittest import mock

import numpy as np

from amcrax.economics.singapore import evaluate
from amcrax.enduse.pathways import Activity, carbon_intensity
from amcrax.environmental import lca
from amcrax.heat_integration import analyse, problem_table
from amcrax.heat_integration.streams import extract_streams
from amcrax.process_model import flowsheet as _fs
from amcrax.reactor.pfr import _eq_conversion, catalyst_mass_for_conversion
from amcrax.schemas import LHV_KJ_PER_MOL, MOLAR_MASS, CaseInputs, SimulationResult

# ------------------------------------------------------------------------------------------ basis
FEED_TOTAL_KMOL_H = 100.0
FEED_H2O = 0.002
FEED_NH3_KMOL_H = FEED_TOTAL_KMOL_H * (1.0 - FEED_H2O)  # kinetics see the NH3 only (H2O not in any rate law)
LCA_DISTANCE_KM = 5000.0
LCA_ROUTES = ("grey", "blue", "green")

CHO_PRICE = {"Ni": 33.4, "Ru": 542.0}  # USD/kg, cho2026nickel Table 4 p. 7 ("calculated"; method in unavailable SI)
CHO_PRICE_SOURCE = "cho2026nickel Table 4 p. 7 (Ni/Al2O3 8 wt% 33.4, Ru-K/CaO 3 wt% 542 USD/kg)"

#: Phase 2 (task C2): catalyst prices are DERIVED scenario prices (metal content + non-metal part) from
#: research/data/catalyst_prices.json; no supplier quotation exists. The Cho TEA prices above are kept for the Cho
#: reconstruction and as a separately labelled 'published TEA price' case (they lie below the Ru metal floor).
PRICE_FILE = Path(__file__).resolve().parents[3] / "research" / "data" / "catalyst_prices.json"
PRICE_FILE_REL = "research/data/catalyst_prices.json"
PRICE_SCENARIOS = ("low", "central", "high")


@lru_cache(maxsize=1)
def load_price_data() -> dict:
    return json.loads(PRICE_FILE.read_text(encoding="utf-8"))


def derived_price(price_key: str, scenario: str = "central") -> float:
    """Derived catalyst price, USD/kg finished catalyst (research/data/catalyst_prices.json scenario table)."""
    return float(load_price_data()["scenarios_usd_per_kg_finished_catalyst"][price_key][scenario]["usd_per_kg"])


_PRICE_NOTE = ("DERIVED scenario price (central): metal content x metal price + non-metal part 32.2 USD/kg "
               "(research/data/catalyst_prices.json); not a supplier quotation")

#: catalyst registry for the comparison. Bed data as workstream K (scripts/research/kinetics_studies.py BED).
CATALYSTS: dict[str, dict[str, Any]] = {
    "ru_kum_temkin_pyzhev": dict(
        label="Ru/Al2O3 (Kum)", family="Ru", short="Ru/Al2O3", approximation=False, eps_b=0.36, rho_particle=980.0,
        price_key="Ru/Al2O3", price=derived_price("Ru/Al2O3"), price_source_type="derived",
        price_note=_PRICE_NOTE + "; 8 wt% Ru"),
    "ru_takahashi_microkinetic": dict(
        label="Ru/MgO (Takahashi)", family="Ru", short="Ru/MgO", approximation=False, eps_b=0.36, rho_particle=980.0,
        price_key="Ru/MgO", price=derived_price("Ru/MgO"), price_source_type="derived",
        price_note=_PRICE_NOTE + "; 5 wt% Ru"),
    "nire_ceo2_5ni1ru_lucentini_lhhw": dict(
        label="5Ni1Ru/CeO2 (Lucentini)", family="NiRu", short="5Ni1Ru/CeO2", approximation=False, eps_b=0.36,
        rho_particle=1651.8, price_key="5Ni1Ru/CeO2", price=derived_price("5Ni1Ru/CeO2"), price_source_type="derived",
        price_note=_PRICE_NOTE + "; 5 wt% Ni + 1 wt% Ru"),
    "nire_ceo2_2p5ni0p5ru_lucentini_lhhw": dict(
        label="2.5Ni0.5Ru/CeO2 (Lucentini)", family="NiRu", short="2.5Ni0.5Ru/CeO2", approximation=False, eps_b=0.36,
        rho_particle=1651.8, price_key="2.5Ni0.5Ru/CeO2", price=derived_price("2.5Ni0.5Ru/CeO2"),
        price_source_type="derived", price_note=_PRICE_NOTE + "; 2.5 wt% Ni + 0.5 wt% Ru"),
    "ni_takahashi_microkinetic": dict(
        label="Ni/MgO (Takahashi)", family="Ni", short="Ni/MgO", approximation=False, eps_b=0.36, rho_particle=980.0,
        price_key="Ni/MgO", price=derived_price("Ni/MgO"), price_source_type="derived",
        price_note=_PRICE_NOTE + "; 30 wt% Ni"),
}
VALIDITY_FILE = Path(__file__).resolve().parents[3] / "results" / "research" / "kinetics" / "validity_classification.json"
VALIDITY_FILE_REL = "results/research/kinetics/validity_classification.json"


@lru_cache(maxsize=1)
def _validity_data() -> dict:
    return json.loads(VALIDITY_FILE.read_text(encoding="utf-8"))


def kinetic_validity(cid: str, P_bar: float = 20.0, T_C: Optional[float] = None) -> dict:
    """Kinetic validity class (task K1) of the rate law a result rests on, with an extrapolation label."""
    law = next(x for x in _validity_data()["laws"] if x.get("catalyst_id") == cid)
    fr = law["fitted_range"]
    p_out = not (fr["P_bar"][0] - 1e-9 <= P_bar <= fr["P_bar"][1] + 1e-9)
    t_out = None if T_C is None else not (fr["T_C"][0] <= T_C <= fr["T_C"][1])
    cls = law["class"]
    label = ("extrapolation" if cls == "extrapolated" else
             "pressure extrapolation of a law validated against literature" if p_out else cls)
    return {"kinetic_validity_class": cls, "kinetic_result_label": label, "kinetic_pressure_extrapolated": p_out,
            "kinetic_T_outside_fitted_range": t_out, "kinetic_fitted_P_bar": fr["P_bar"], "kinetic_fitted_T_C": fr["T_C"],
            "kinetic_validity_source": VALIDITY_FILE_REL}


#: published TEA price used for each catalyst in the separately labelled 'published TEA' case (not a current price)
PUBLISHED_TEA_PRICE = {cid: (CHO_PRICE["Ni"] if c["family"] == "Ni" else CHO_PRICE["Ru"]) for cid, c in CATALYSTS.items()}
REFERENCE_NI = "ni_takahashi_microkinetic"

#: ASSUMPTIONS for the fired heater (no sourced value in the AmCraX library; labelled, varied in sensitivities)
FURNACE_EFFICIENCY = 0.85          # fraction of supplementary-fuel LHV delivered to the process at temperature
FURNACE_EFFICIENCY_RANGE = (0.65, 1.0)
THERMAL_LOSS_FRACTION = 0.02       # wall/radiation loss, fraction of reactor + trim-heater duty
CATALYST_LIFETIME_YR = 2.0         # cho2026nickel Table 4 (assumed there)

ASSUMPTIONS = [
    dict(name="furnace_efficiency", value=FURNACE_EFFICIENCY, unit="fraction of NH3 LHV", source_type="assumption",
         source="AmCraX workstream H; no sourced fired-heater efficiency in the library (economics.yaml uses 1.0)",
         applicability_note="Applied only to supplementary NH3 fuel; tail-gas heat is credited by the pinch model. Range 0.65-1.0 in sensitivities."),
    dict(name="thermal_loss_fraction", value=THERMAL_LOSS_FRACTION, unit="fraction of reactor + trim heater duty",
         source_type="assumption", source="AmCraX workstream H (allowance; not sourced)",
         applicability_note="Added to the fired duty; the existing KPIs have no losses (fact sheet F7)."),
    dict(name="catalyst_price_Ni_published_TEA", value=CHO_PRICE["Ni"], unit="USD/kg", source_type="literature",
         source=CHO_PRICE_SOURCE,
         applicability_note="Phase 2: used only in the Cho reconstruction and the labelled 'published TEA price' case "
                            "(not a current price). Default prices are the derived central scenario prices."),
    dict(name="catalyst_price_Ru_published_TEA", value=CHO_PRICE["Ru"], unit="USD/kg", source_type="literature",
         source=CHO_PRICE_SOURCE,
         applicability_note="Phase 2: Cho reconstruction and 'published TEA price' case only. 542 USD/kg is below the "
                            "Ru metal-content floor of a 3 wt% Ru catalyst (666 USD/kg at the USGS 2025 average, "
                            "research/data/catalyst_prices.json C2 caution)."),
    dict(name="catalyst_lifetime", value=CATALYST_LIFETIME_YR, unit="yr", source_type="literature",
         source="cho2026nickel Table 4 (an assumption in the source)", applicability_note="Sensitivity 1-4 yr."),
    dict(name="feed_basis", value=FEED_TOTAL_KMOL_H, unit="kmol/h liquid NH3 (0.2 mol% H2O)", source_type="assumption",
         source="AmCraX baseline CaseInputs", applicability_note="Kinetics use the 99.8 kmol/h NH3 only."),
    dict(name="kinetic_reactor", value="isothermal PFR, no pressure drop, effectiveness factor 1", unit="-",
         source_type="assumption", source="as workstreams K and A",
         applicability_note="Powder kinetics applied to an industrial bed; all laws extrapolated to 10-30 bar."),
    dict(name="kinetic_conversion_in_flowsheet", value="cracker outlet conversion fixed at the kinetic target X",
         unit="-", source_type="python", source="amcrax.process_model.run_python_case with solve_equilibrium replaced "
         "by X (never above equilibrium)", applicability_note="Same H-T property basis as the Python flowsheet."),
    dict(name="cracker_capex_scaling", value=0.8, unit="exponent on bed volume", source_type="assumption",
         source="scaling exponent of the Singapore equipment CAPEX (Chopra 2026 Eq. 5) applied to catalyst volume",
         applicability_note="Sensitivity only; in the base case CAPEX does not respond to catalyst volume."),
]


def bed_density(cid: str) -> float:
    c = CATALYSTS[cid]
    return (1.0 - c["eps_b"]) * c["rho_particle"]


# ------------------------------------------------------------------------------------------ kinetics
@lru_cache(maxsize=20000)
def required_mass_kg(cid: str, T_C: float, P_bar: float, X: float) -> float:
    """Catalyst mass (kg) for conversion X at isothermal T, P (python kinetics); nan if not reachable."""
    c = CATALYSTS[cid]
    feed = {"NH3": FEED_NH3_KMOL_H}
    if _eq_conversion(T_C + 273.15, P_bar, feed) <= X + 1e-4:
        return float("nan")
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        w = catalyst_mass_for_conversion(cid, X, T_in_C=T_C, P_in_bar=P_bar, feed_kmol_h=feed, mode="isothermal",
                                         pressure_drop=False, eps_b=c["eps_b"], rho_particle_kg_m3=c["rho_particle"],
                                         W_max_kg=1e5)
    return float(w)


def eq_conversion(T_C: float, P_bar: float) -> float:
    return _eq_conversion(T_C + 273.15, P_bar, {"NH3": FEED_NH3_KMOL_H})


# ------------------------------------------------------------------------------------------ flowsheet at kinetic X
_real_solve = _fs.solve_equilibrium


def kinetic_flowsheet(T_C: float, P_bar: float, X: float, heat_integration: bool = True,
                      psa_recovery: float = 0.85, **inputs) -> SimulationResult:
    """Python flowsheet with the cracker outlet at conversion X (kinetically limited, X <= X_eq)."""

    def solve(T_K, P, n, eos="ideal", **kw):
        eq = _real_solve(T_K, P, n, eos=eos, **kw)
        if X > eq.conversion + 1e-9:
            raise ValueError(f"X = {X} above equilibrium {eq.conversion:.5f} at {T_K - 273.15:.1f} degC, {P} bar")
        n0 = n["NH3"]
        ext = X * n0 / 2.0
        out = dict(n)
        out["NH3"] = n0 * (1.0 - X)
        out["N2"] = n.get("N2", 0.0) + ext
        out["H2"] = n.get("H2", 0.0) + 3.0 * ext
        tot = sum(out.values())
        return dataclasses.replace(eq, conversion=X, extent=ext, n_out=out, y={k: v / tot for k, v in out.items()})

    ci = CaseInputs(case_id="hcat", feed_total_kmol_h=FEED_TOTAL_KMOL_H, feed_h2o_mole_frac=FEED_H2O,
                    reactor_temperature_C=T_C, reactor_pressure_bar=P_bar, heat_integration=heat_integration,
                    psa_h2_recovery=psa_recovery, **inputs)
    with mock.patch.object(_fs, "solve_equilibrium", solve):
        r = _fs.run_python_case(ci)
    r.notes.append(f"workstream H: cracker conversion fixed at the kinetic value X = {X:.4f} (not equilibrium)")
    return r


# ------------------------------------------------------------------------------------------ heat accounting
def heat_accounting(res: SimulationResult, dT_min_K: float = 20.0) -> dict:
    """Temperature-level heat import with tail-gas firing (with or without the FEHE), pinch targets, FEHE area."""
    hi = bool(res.inputs.heat_integration)
    a = analyse(res, dT_min_K)
    rows = {r.id: r for r in a.configurations}
    k = res.kpis
    if hi:
        imp = rows["c"].external_heating_kW
        tg_used = rows["c"].tailgas_heat_used_kW
        recovered = rows["b"].process_heat_recovered_kW
    else:  # no FEHE: all feed heating and the reaction duty against the tail-gas flue gas
        x = extract_streams(res)
        r = problem_table([x["feed"], x["reaction"], x["flue"]], dT_min_K)
        imp = r.hot_utility_kW
        tg_used = x["feed"].duty_kW + x["reaction"].duty_kW - imp
        recovered = 0.0
    fe = a.fehe
    return {
        "heat_integration": hi, "dT_min_K": dT_min_K,
        "external_heat_import_kW": float(imp),
        "tailgas_heat_used_kW": float(tg_used or 0.0),
        "recovered_heat_kW": float(recovered),
        "pinch_min_hot_utility_process_only_kW": a.targets_process.hot_utility_kW,
        "pinch_min_hot_utility_with_flue_kW": a.targets_with_flue.hot_utility_kW if a.targets_with_flue else None,
        "pinch_temperature_C": a.targets_process.pinch_shifted_C,
        "pinch_energy_balance_residual_kW": a.targets_process.energy_balance_residual_kW,
        "fehe_duty_kW": fe.duty_kW if hi else 0.0, "fehe_UA_kW_K": (fe.ua_segmented_kW_K or fe.ua_lmtd_kW_K) if hi else 0.0,
        "fehe_area_m2_at_U50": fe.area_m2 if hi else 0.0, "fehe_area_range_m2": fe.area_range_m2 if hi else [],
        "kpi_total_external_heating_kW": k.total_external_heating_kW, "kpi_recovered_heat_kW": k.recovered_heat_kW,
        "kpi_tailgas_combustion_heat_kW": k.tailgas_combustion_heat_kW,
        "kpi_net_fuel_heat_deficit_kW_first_law": k.net_fuel_heat_deficit_kW,
        "reactor_duty_kW": k.reactor_duty_kW, "preheat_duty_kW": k.preheat_duty_kW, "vaporiser_duty_kW": k.vaporiser_duty_kW,
        "cooling_duty_kW": abs(k.cooling_duty_kW), "pump_power_kW": k.pump_power_kW or 0.0,
        "warnings": list(a.warnings),
    }


def fired_duty(h: dict, furnace_efficiency: float = FURNACE_EFFICIENCY, loss_fraction: float = THERMAL_LOSS_FRACTION) -> dict:
    loss = loss_fraction * (h["reactor_duty_kW"] + (h["preheat_duty_kW"] or 0.0))
    q = h["external_heat_import_kW"] + loss
    fuel_kmol_h = q / (LHV_KJ_PER_MOL["NH3"] * furnace_efficiency) * 3600.0 / 1000.0
    return {"thermal_loss_kW": loss, "fired_process_duty_kW": q, "furnace_efficiency": furnace_efficiency,
            "furnace_fuel_LHV_kW": q / furnace_efficiency, "supplementary_nh3_kg_h": fuel_kmol_h * MOLAR_MASS["NH3"],
            "supplementary_fuel_needed": bool(q > 1e-6)}


# ------------------------------------------------------------------------------------------ economics and LCA
def summary_for_economics(res: SimulationResult, fd: dict, h: dict) -> dict:
    k = res.kpis
    nh3 = res.streams["FEED"].component_mole_flow_kmol_h["NH3"]
    return {"case_id": res.case_id, "source": res.source.value, "heat_integration": res.inputs.heat_integration,
            "h2_kg_h": float(k.h2_product_kg_h), "nh3_feed_kmol_h": float(nh3), "heat_deficit_kW": fd["fired_process_duty_kW"],
            "cooling_kW": h["cooling_duty_kW"], "pump_kW": h["pump_power_kW"], "h2_cracked_kmol_h": k.h2_in_cracked_gas_kmol_h,
            "psa_recovery": res.inputs.psa_h2_recovery, "tailgas_lhv_kW": k.tailgas_lhv_kW,
            "tailgas_heat_kW": k.tailgas_combustion_heat_kW}


def econ(summary: dict, W_kg: float, price: float, scenario: Any = "grey", lifetime: float = CATALYST_LIFETIME_YR,
         furnace_efficiency: float = FURNACE_EFFICIENCY, overrides: Optional[dict] = None) -> dict:
    o = {"catalyst_mass_kg": max(W_kg, 0.0), "catalyst_price_USD_per_kg": price, "catalyst_lifetime_yr": lifetime,
         "fuel_efficiency": furnace_efficiency, "heat_fuel": "ammonia"}
    o.update(overrides or {})
    return evaluate(summary, scenario, o)


def carbon(summary: dict, fuel_nh3_kg_h: float, routes=LCA_ROUTES) -> dict:
    h2 = summary["h2_kg_h"]
    nh3 = (summary["nh3_feed_kmol_h"] * MOLAR_MASS["NH3"] + fuel_nh3_kg_h) / h2
    a = Activity("cat", "catalyst design", "H2", "1 kg H2", nh3, summary["pump_kW"] / h2, 0.0)
    out = {"kg_nh3_total_per_kg_h2": nh3, "distance_km": LCA_DISTANCE_KM, "n2o": "not quantified (0)"}
    for r in routes:
        out[f"{r}_kgCO2e_per_kgH2"] = carbon_intensity(a, lca.route_spec(r).ef, LCA_DISTANCE_KM)["total"]
    return out


# ------------------------------------------------------------------------------------------ one design point
def design_point(cid: str, T_C: float, P_bar: float, X: float, *, heat_integration: bool = True, W_kg: Optional[float] = None,
                 dT_min_K: float = 20.0, scenario: Any = "grey", price: Optional[float] = None,
                 lifetime: float = CATALYST_LIFETIME_YR, furnace_efficiency: float = FURNACE_EFFICIENCY,
                 psa_recovery: float = 0.85, result: Optional[SimulationResult] = None,
                 econ_overrides: Optional[dict] = None) -> dict:
    """All numbers of one (catalyst, T, P, X, HI) configuration. ``result`` = an existing (e.g. Aspen) flowsheet."""
    c = CATALYSTS[cid]
    if W_kg is None:
        W_kg = required_mass_kg(cid, float(T_C), float(P_bar), float(X))
    res = result if result is not None else kinetic_flowsheet(T_C, P_bar, X, heat_integration, psa_recovery)
    h = heat_accounting(res, dT_min_K)
    fd = fired_duty(h, furnace_efficiency)
    s = summary_for_economics(res, fd, h)
    p = c["price"] if price is None else price
    e = econ(s, W_kg, p, scenario, lifetime, furnace_efficiency, econ_overrides)
    rho = bed_density(cid)
    return {
        "catalyst_id": cid, "catalyst": c["label"], "family": c["family"], "T_C": T_C, "P_bar": P_bar,
        "X_target": X, "X_flowsheet": res.kpis.nh3_conversion, "X_eq": eq_conversion(T_C, P_bar),
        "heat_integration": res.inputs.heat_integration, "flowsheet_source": res.source.value,
        "W_kg": W_kg, "bed_volume_m3": W_kg / rho, "bed_density_kg_m3": rho,
        "GHSV_NH3_STP_h-1": FEED_NH3_KMOL_H * 22.414 / (W_kg / rho) if W_kg > 0 else None,
        "h2_product_kg_h": s["h2_kg_h"], **{f"heat_{k}": v for k, v in h.items()}, **fd,
        "catalyst_price_USD_per_kg": p, "catalyst_lifetime_yr": lifetime,
        "lcoh_USD_per_kg": e["lcoh_USD_per_kg"], "rec_USD_per_kg": e["rec_USD_per_kg"],
        "lcoh_SGD_per_kg": e["lcoh_SGD_per_kg"], "rec_SGD_per_kg": e["rec_SGD_per_kg"], "fx_SGD_per_USD": e["fx_SGD_per_USD"],
        "breakdown_USD_per_kg": e["breakdown_USD_per_kg"], "kg_nh3_fuel_per_kg_h2": e["kg_nh3_fuel_per_kg_h2"],
        "annual_h2_kg": e["annual_h2_kg"], "nh3_price_USD_per_t": e["nh3_price_USD_per_t"],
        "carbon": carbon(s, fd["supplementary_nh3_kg_h"]),
    }


# ------------------------------------------------------------------------------------------ temperature optimisation
@lru_cache(maxsize=4096)
def _heat_cost_at(T_C: float, P_bar: float, X: float, hi: bool, dT: float, psa: float, feff: float) -> dict:
    """Catalyst-independent part at (T, P, X): flowsheet + heat + economics with zero catalyst cost."""
    res = kinetic_flowsheet(T_C, P_bar, X, hi, psa)
    h = heat_accounting(res, dT)
    fd = fired_duty(h, feff)
    s = summary_for_economics(res, fd, h)
    return {"res_kpis": res.kpis, "heat": h, "fired": fd, "summary": s}


def lcoh_curve(cid: str, T_grid, *, P_bar: float = 20.0, X: float = 0.95, hi: bool = True, dT: float = 20.0,
               psa: float = 0.85, feff: float = FURNACE_EFFICIENCY, scenario: Any = "grey", price: Optional[float] = None,
               lifetime: float = CATALYST_LIFETIME_YR, kinetic_factor: float = 1.0, capex_volume_scaling: bool = False,
               econ_overrides: Optional[dict] = None) -> list[dict]:
    """LCOH(T) for one catalyst. kinetic_factor multiplies every rate (W scales as 1/factor, exact for isothermal PFR)."""
    p = CATALYSTS[cid]["price"] if price is None else price
    rho = bed_density(cid)
    out = []
    for T in T_grid:
        T = float(T)
        if eq_conversion(T, P_bar) <= X + 1e-4:
            continue
        W = required_mass_kg(cid, T, float(P_bar), float(X))
        if not math.isfinite(W):
            continue
        W = W / kinetic_factor
        hc = _heat_cost_at(T, float(P_bar), float(X), bool(hi), float(dT), float(psa), float(feff))
        e0 = econ(hc["summary"], 0.0, p, scenario, lifetime, feff, econ_overrides)
        cat = W * p / lifetime / e0["annual_h2_kg"]
        cap_extra = 0.0
        if capex_volume_scaling:
            tci_cr = e0["capex"]["tci_by_equipment_USD"]["cracker"]
            V_ref = 248.0 / rho  # inventory of the default economics (cho2026nickel GHSV 9000 mL/(g h))
            cap_extra = tci_cr * ((W / rho / V_ref) ** 0.8 - 1.0) * e0["crf"] / e0["annual_h2_kg"]
        out.append({"T_C": T, "W_kg": W, "bed_volume_m3": W / rho, "lcoh_USD_per_kg": e0["lcoh_USD_per_kg"] + cat + cap_extra,
                    "rec_USD_per_kg": e0["rec_USD_per_kg"] + cat + cap_extra, "catalyst_USD_per_kg": cat,
                    "lcoh_SGD_per_kg": (e0["lcoh_USD_per_kg"] + cat + cap_extra) * e0["fx_SGD_per_USD"],
                    "capex_volume_extra_USD_per_kg": cap_extra, "heat_fuel_USD_per_kg": e0["breakdown_USD_per_kg"]["heat_fuel"],
                    "external_heat_import_kW": hc["heat"]["external_heat_import_kW"],
                    "fired_process_duty_kW": hc["fired"]["fired_process_duty_kW"],
                    "supplementary_nh3_kg_h": hc["fired"]["supplementary_nh3_kg_h"],
                    "h2_product_kg_h": hc["summary"]["h2_kg_h"]})
    return out


def optimum(curve: list[dict]) -> Optional[dict]:
    if not curve:
        return None
    i = int(np.argmin([r["lcoh_USD_per_kg"] for r in curve]))
    best = dict(curve[i])
    best["at_grid_bound"] = i in (0, len(curve) - 1)
    best["grid_index"] = i
    return best
