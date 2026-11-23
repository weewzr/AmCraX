"""Catalyst economics for hypothesis H3 (Phase 2, task C2).

Question: can the energy and heat-integration savings of a lower-temperature catalyst design outweigh its higher
catalyst cost, on the unified techno-economic basis (amcrax.economics.singapore.evaluate, reference scenario)?

Inputs
  * Catalyst prices: research/data/catalyst_prices.json. Every scenario price is DERIVED
        price = (wNi/100) P_Ni + (wRu/100) P_Ru + N        (USD/kg finished catalyst)
    No supplier quotation exists. 'low' has N = 0 and is a metal-content FLOOR, not a market price. Published TEA
    prices (Cho 2026 and others) are a separate, labelled case: the Ru ones lie below the Ru metal floor.
    SGD values are recomputed at the ONE reference exchange rate (reference_scenario.yaml); EUR prices are converted
    at the reference USD/EUR rate. The 1.2801 SGD/USD of the price file is superseded for conversion.
  * Lifetimes (LIFETIMES_YR): 1, 2, 4 and 5 yr, each with its source (all are TEA assumptions or a
    steam-reforming analogue; none is a measured cracking-catalyst life).
  * Kinetics, flowsheet, heat accounting: amcrax.research.catalyst_comparison (W(T) from the PFR laws, Python
    flowsheet at the kinetic conversion, temperature-feasible fired duty with the furnace assumptions).
  * Exchanger: amcrax.heat_integration.exchanger (task X1), FEHE area from the segmented UA, Turton cost, TCI
    equivalent. It is passed to the reference CAPEX through ``item_size_ratio['heat_exchangers']`` so that the
    item equals the reference item PLUS the FEHE TCI (incremental convention of task X1: the reference item is
    taken not to contain the FEHE; designs without heat integration add nothing).
  * Reactor: optionally sized by catalyst mass (``reactor_size_driver='catalyst_mass'`` of the reference CAPEX).

Economic modes (MODES) -- the frozen default of singapore.evaluate is not changed; these are optional arguments:
  'reference'               CAPEX by NH3 feed (as catalyst_comparison and the frozen baseline)
  'exchanger'               + FEHE cost from its area (U case 'central' unless stated)
  'exchanger_reactor_mass'  + reactor item scaled by catalyst mass (ratio to the Cho inventory, exponent 0.8)

Decision quantities (all USD per kg H2 unless named otherwise; 'low' = low-temperature catalyst design,
'ref' = Ni reference design; delta = low - ref, so a negative net delta favours the low-temperature catalyst)
  catalyst cost        c = W p / (L H)                          H = annual H2 (kg/yr)
  break-even price     p* = (LCOH_ref - A_low) L H / W_low      A_low = LCOH_low - c_low (design held fixed)
  break-even lifetime  L* = W_low p_low / ((LCOH_ref - A_low) H) (none if A_low >= LCOH_ref)
  incremental investment I0 = dTCI + (W_low p_low - W_ref p_ref)   (first catalyst charge counted as capital)
  annual operating saving S = -(d fuel + d utilities + d fixed opex) (USD/yr, catalyst and capital charge excluded)
  NPV (choosing low)   = -I0 + S a(i,n) - sum_k dCharge (1+i)^-(k L)   for k L < n   (a = annuity factor)
  NPV (smoothed)       = -dLCOH H / CRF  (singapore.evaluate convention: catalyst smoothed as W p / L per year)
  simple payback       = I0 / (S - dCharge / L)
"""
from __future__ import annotations

import math
from functools import lru_cache
from typing import Any, Optional

import numpy as np

from amcrax.economics.reference import load_reference_scenario, reference_capex
from amcrax.economics.singapore import evaluate
from amcrax.heat_integration import analyse
from amcrax.heat_integration.exchanger import U_CASES, size_and_cost
from amcrax.research import catalyst_comparison as cc
from amcrax.schemas import SimulationResult

REF = load_reference_scenario()
FX = REF.fx_SGD_per_USD
USD_PER_EUR = REF.usd_per_eur

MODELLED = {cid: c["price_key"] for cid, c in cc.CATALYSTS.items()}
UNMODELLED = ("Ni/CeO2", "Ru/CeO2", "Ru-K/CaO")
LOW_T = [c for c in cc.CATALYSTS if c != cc.REFERENCE_NI]
MODES = ("reference", "exchanger", "exchanger_reactor_mass")

LIFETIMES_YR = {
    1.0: {"source_type": "literature (assumption in the source)",
          "source": "cho2026nickel Table 4 p. 7: lifetime sensitivity 1-4 yr (lower bound)", "measured": False},
    2.0: {"source_type": "literature (assumption in the source)",
          "source": "cho2026nickel Table 4 p. 7: 'Catalyst lifetime 2 years Assumed' (base value)", "measured": False},
    4.0: {"source_type": "literature (assumption in the source; vendor analogue)",
          "source": "cho2026nickel Table 4 sensitivity upper bound; Shah (Johnson Matthey), Refining India Sept 2025 "
                    "p. 25: steam-reforming Ni changeout cycle 4-6 yr (comparable service, not cracking)",
          "measured": False},
    5.0: {"source_type": "literature (assumption in the source)",
          "source": "richard2024 Table 5: 'Catalyst lifetime 5 years' (assumed)", "measured": False},
}
BASE_LIFETIME = cc.CATALYST_LIFETIME_YR

T_GRID = [float(t) for t in range(470, 761, 5)]
P_BAR, X_TARGET = 20.0, 0.95


# ------------------------------------------------------------------------------------------ prices
def _scen(name: str) -> dict:
    return cc.load_price_data()["scenarios_usd_per_kg_finished_catalyst"][name]


def price_from_components(name: str, P_Ni: float, P_Ru: float, N: float) -> float:
    w = _scen(name)["loading_wt_pct"]
    return w["Ni"] / 100.0 * P_Ni + w["Ru"] / 100.0 * P_Ru + N


def price(name: str, scenario: str = "central") -> float:
    """Derived price, USD/kg (scenario 'low' | 'central' | 'high') recomputed from its components."""
    e = _scen(name)[scenario]
    return price_from_components(name, e["P_Ni_usd_per_kg"], e["P_Ru_usd_per_kg"], e["N_usd_per_kg"])


def ru_metal_floor(wt_pct_ru: float, P_Ru: Optional[float] = None) -> float:
    """Ru metal content of 1 kg catalyst at the low (USGS 2025 average) Ru price, USD/kg."""
    if P_Ru is None:
        P_Ru = _scen("Ru/MgO")["low"]["P_Ru_usd_per_kg"]
    return wt_pct_ru / 100.0 * P_Ru


def price_table() -> list[dict]:
    rows = []
    for name in list(MODELLED.values()) + list(UNMODELLED):
        s = _scen(name)
        cid = next((k for k, v in MODELLED.items() if v == name), None)
        r = {"catalyst": name, "catalyst_id": cid, "modelled": cid is not None,
             "loading_wt_pct": s["loading_wt_pct"], "loading_basis": s["loading_basis"], "formula": s["formula"],
             "grade": s["grade"], "quoted_or_derived": "derived (no supplier quotation exists)",
             "performance": "modelled (rate law in kinetics.yaml)" if cid else "unmodelled: price only, no performance "
                            "(no published rate law; results/research/kinetics/validity_classification.json)"}
        for sc in cc.PRICE_SCENARIOS:
            e = s[sc]
            usd = price(name, sc)
            r[sc] = {"USD_per_kg": usd, "SGD_per_kg": usd * FX, "P_Ni_USD_per_kg": e["P_Ni_usd_per_kg"],
                     "P_Ru_USD_per_kg": e["P_Ru_usd_per_kg"], "N_USD_per_kg": e["N_usd_per_kg"],
                     "price_file_USD_per_kg": e["usd_per_kg"], "price_file_SGD_per_kg_superseded_fx": e["sgd_per_kg"]}
        r["low"]["label"] = "metal-content floor (non-metal part N = 0): NOT a market price"
        r["central"]["label"] = "derived central: metal at Nov 2026 spot (JM Ru base, LME Ni) + N 32.2 USD/kg (Cho Ni/Al2O3 minus Ni metal)"
        r["high"]["label"] = "derived high: Ni at the 2022 USGS average; Ru = central (no sourced higher Ru price)"
        if cid:
            r["published_TEA_case_USD_per_kg"] = cc.PUBLISHED_TEA_PRICE[cid]
            r["published_TEA_case_SGD_per_kg"] = cc.PUBLISHED_TEA_PRICE[cid] * FX
            r["published_TEA_case_label"] = ("Cho 2026 Table 4 Ni/Al2O3 8 wt% (33.4 USD/kg), published TEA price, not a current price"
                                             if cc.CATALYSTS[cid]["family"] == "Ni" else
                                             "Cho 2026 Table 4 Ru-K/CaO 3 wt% (542 USD/kg), published TEA price, NOT a current price; "
                                             "below the Ru metal floor of the catalyst it is applied to")
            r["published_TEA_case_below_Ru_metal_floor"] = bool(cc.PUBLISHED_TEA_PRICE[cid] < ru_metal_floor(s["loading_wt_pct"]["Ru"]))
        rows.append(r)
    return rows


def published_tea_prices() -> list[dict]:
    """Published TEA catalyst prices, kept in their original currency; recomputed USD and SGD at the reference rates."""
    out = []
    for e in cc.load_price_data()["entries"]:
        if e.get("kind") != "tea_price":
            continue
        cur = e["currency"]
        usd = e["price_value"] if cur == "USD" else e["price_value"] * USD_PER_EUR if cur == "EUR" else None
        wru = (e.get("loading_wt_pct") or {}).get("Ru")
        floor = ru_metal_floor(wru) if wru else None
        out.append({"id": e["id"], "material": e["material"], "price_value": e["price_value"], "currency": cur,
                    "unit": e["unit"], "price_date": e["price_date"], "publication": e["supplier_or_publication"],
                    "url": e["url"], "grade": e["grade"], "USD_per_kg": usd, "SGD_per_kg": None if usd is None else usd * FX,
                    "fx_used": ("none (USD)" if cur == "USD" else f"USD/EUR {USD_PER_EUR} (reference scenario, ECB 20 Nov 2026)"),
                    "Ru_wt_pct": wru, "Ru_metal_floor_USD_per_kg_USGS2025": floor,
                    "below_Ru_metal_floor": (usd < floor) if (usd is not None and floor) else None,
                    "label": "published TEA price: shown as a separate case, NOT a current price"})
    return out


# ------------------------------------------------------------------------------------------ cost per kg H2
def catalyst_cost(W_kg: float, price_USD_per_kg: float, lifetime_yr: float, annual_h2_kg: float) -> dict:
    yr = W_kg * price_USD_per_kg / lifetime_yr
    return {"W_kg": W_kg, "price_USD_per_kg": price_USD_per_kg, "lifetime_yr": lifetime_yr,
            "charge_USD": W_kg * price_USD_per_kg, "charge_SGD": W_kg * price_USD_per_kg * FX,
            "annual_USD_per_yr": yr, "annual_SGD_per_yr": yr * FX,
            "USD_per_kg_H2": yr / annual_h2_kg, "SGD_per_kg_H2": yr / annual_h2_kg * FX}


# ------------------------------------------------------------------------------------------ design states
def fehe_geometry(res: SimulationResult) -> Optional[dict]:
    if not res.inputs.heat_integration or "FEHE" not in res.blocks:
        return None
    s = res.streams
    duty = abs(res.blocks["FEHE"].duty_kW or 0.0)
    if duty <= 0:
        return None
    return {"duty_kW": duty, "T_hot_in": s["S5"].temperature_C, "T_hot_out": s["S6"].temperature_C,
            "T_cold_in": s["S2"].temperature_C, "T_cold_out": s["S3"].temperature_C,
            "ua_seg_kW_K": analyse(res).fehe.ua_segmented_kW_K}


def fehe_cost(geo: Optional[dict], U_case: Any = "central") -> dict:
    if geo is None:
        return {"area_m2": 0.0, "tci_equivalent_USD": 0.0, "U_case": U_case}
    r = size_and_cost(geo["duty_kW"], geo["T_hot_in"], geo["T_hot_out"], geo["T_cold_in"], geo["T_cold_out"], U_case,
                      ua_kW_K=geo["ua_seg_kW_K"])
    return {"area_m2": r["area_m2"], "n_shells": r["n_shells"], "U_W_m2K": r["U_W_m2K"], "U_case": U_case,
            "tci_equivalent_USD": r["tci_equivalent_USD"], "tci_equivalent_SGD": r["tci_equivalent_SGD"],
            "installed_USD": r["installed_USD"]}


def state_from_result(res: SimulationResult, dT: float = 20.0, feff: float = cc.FURNACE_EFFICIENCY) -> dict:
    h = cc.heat_accounting(res, dT)
    fd = cc.fired_duty(h, feff)
    s = cc.summary_for_economics(res, fd, h)
    geo = fehe_geometry(res)
    return {"T_C": res.inputs.reactor_temperature_C, "heat": h, "fired": fd, "summary": s, "fehe_geometry": geo,
            "fehe": {u: fehe_cost(geo, u) for u in ("low", "central", "high")}, "source": res.source.value}


@lru_cache(maxsize=4096)
def state(T_C: float, P_bar: float = P_BAR, X: float = X_TARGET, hi: bool = True, psa: float = 0.85,
          feff: float = cc.FURNACE_EFFICIENCY, dT: float = 20.0) -> dict:
    """Catalyst-independent part of a design at (T, P, X, HI): flowsheet, heat, fired duty, FEHE cost."""
    return state_from_result(cc.kinetic_flowsheet(T_C, P_bar, X, hi, psa), dT, feff)


def hx_size_ratio(fehe_tci_USD: float, nh3_feed_kmol_h: float) -> float:
    """Size ratio for item 'heat_exchangers' so that its TCI = reference item TCI + FEHE TCI (exact)."""
    cap = reference_capex(nh3_feed_kmol_h)
    n = cap["scaling_exponent"]
    return cap["size_ratio"]["heat_exchangers"] * (1.0 + fehe_tci_USD / cap["tci_by_item_USD"]["heat_exchangers"]) ** (1.0 / n)


def evaluate_design(st: dict, W_kg: float, price_USD_per_kg: float, lifetime_yr: float = BASE_LIFETIME, *,
                    mode: str = "exchanger", U_case: Any = "central", scenario: Any = "grey",
                    econ_overrides: Optional[dict] = None) -> dict:
    """singapore.evaluate on one design state with the optional CAPEX responses of the chosen mode."""
    if mode not in MODES:
        raise ValueError(f"mode must be one of {MODES}")
    o = {"catalyst_mass_kg": max(W_kg, 0.0), "catalyst_price_USD_per_kg": price_USD_per_kg,
         "catalyst_lifetime_yr": lifetime_yr, "fuel_efficiency": st["fired"]["furnace_efficiency"], "heat_fuel": "ammonia"}
    fe = st["fehe"][U_case] if isinstance(U_case, str) and U_case in st["fehe"] else fehe_cost(st["fehe_geometry"], U_case)
    if mode in ("exchanger", "exchanger_reactor_mass"):
        o["item_size_ratio"] = {"heat_exchangers": hx_size_ratio(fe["tci_equivalent_USD"], st["summary"]["nh3_feed_kmol_h"])}
    if mode == "exchanger_reactor_mass":
        o["reactor_size_driver"] = "catalyst_mass"
    o.update(econ_overrides or {})
    e = evaluate(st["summary"], scenario, o)
    a = e["assumptions"]["economic"]
    fac = e["crf"] + (a["maintenance_frac_capex_per_yr"] * (1.0 + a["plant_overhead_frac_labour_maint"])
                      + a["insurance_frac_capex_per_yr"]) * (1.0 + a["g_and_a_frac_fixed_opex"])
    items = e["capex"]["tci_by_item_USD"]
    item_annual = {k: v * fac / e["annual_h2_kg"] for k, v in items.items()}
    return {"lcoh_USD_per_kg": e["lcoh_USD_per_kg"], "lcoh_SGD_per_kg": e["lcoh_SGD_per_kg"],
            "rec_USD_per_kg": e["rec_USD_per_kg"], "breakdown_USD_per_kg": e["breakdown_USD_per_kg"],
            "annual_USD_per_yr": e["annual_USD_per_yr"], "annual_h2_kg": e["annual_h2_kg"], "crf": e["crf"],
            "capex_total_USD": e["capex"]["total_capex_USD"], "tci_by_item_USD": items,
            "item_annual_charge_factor": fac, "item_annualised_USD_per_kg": item_annual,
            "fehe": fe, "mode": mode, "U_case": U_case, "discount_rate": a["discount_rate"],
            "plant_life_yr": a["plant_life_yr"], "nh3_price_USD_per_t": e["nh3_price_USD_per_t"],
            "npv_USD_evaluate": e["npv_USD"]}


@lru_cache(maxsize=4096)
def _eqc(T_C: float) -> float:
    return cc.eq_conversion(T_C, P_BAR)


def design(cid: str, T_C: float, price_USD_per_kg: float, lifetime_yr: float = BASE_LIFETIME, *, W_kg: Optional[float] = None,
           kinetic_factor: float = 1.0, hi: bool = True, mode: str = "exchanger", U_case: Any = "central",
           scenario: Any = "grey", econ_overrides: Optional[dict] = None, st: Optional[dict] = None) -> Optional[dict]:
    if W_kg is None:
        if _eqc(float(T_C)) <= X_TARGET + 1e-4:
            return None
        W_kg = cc.required_mass_kg(cid, float(T_C), P_BAR, X_TARGET)
        if not math.isfinite(W_kg):
            return None
        W_kg /= kinetic_factor
    st = st if st is not None else state(float(T_C), P_BAR, X_TARGET, bool(hi))
    ev = evaluate_design(st, W_kg, price_USD_per_kg, lifetime_yr, mode=mode, U_case=U_case, scenario=scenario,
                         econ_overrides=econ_overrides)
    return {"catalyst_id": cid, "catalyst": cc.CATALYSTS[cid]["short"], "T_C": float(T_C), "W_kg": W_kg,
            "heat_integration": bool(hi), "fired_process_duty_kW": st["fired"]["fired_process_duty_kW"],
            "supplementary_nh3_kg_h": st["fired"]["supplementary_nh3_kg_h"],
            "first_law_deficit_kW": st["heat"]["kpi_net_fuel_heat_deficit_kW_first_law"],
            "total_external_heating_kW": st["heat"]["kpi_total_external_heating_kW"],
            "h2_product_kg_h": st["summary"]["h2_kg_h"], "flowsheet_source": st["source"],
            **ev, "catalyst_cost": catalyst_cost(W_kg, price_USD_per_kg, lifetime_yr, ev["annual_h2_kg"]),
            **cc.kinetic_validity(cid, P_BAR, float(T_C))}


def optimise(cid: str, price_USD_per_kg: float, lifetime_yr: float = BASE_LIFETIME, *, refine: bool = True,
             grid=None, **kw) -> Optional[dict]:
    """Cost-optimal temperature (min LCOH) on the 5 K grid, refined on 1 K."""
    grid = T_GRID if grid is None else grid
    rows = [d for d in (design(cid, T, price_USD_per_kg, lifetime_yr, **kw) for T in grid) if d is not None]
    if not rows:
        return None
    best = min(rows, key=lambda d: d["lcoh_USD_per_kg"])
    if refine:
        loc = [d for d in (design(cid, best["T_C"] + k, price_USD_per_kg, lifetime_yr, **kw) for k in range(-4, 5))
               if d is not None]
        best = min(loc + [best], key=lambda d: d["lcoh_USD_per_kg"])
    best = dict(best)
    best["at_grid_bound"] = best["T_C"] >= max(grid) or best["T_C"] <= min(r["T_C"] for r in rows)
    return best


# ------------------------------------------------------------------------------------------ comparison
def item(d: dict, k: str) -> float:
    return d["item_annualised_USD_per_kg"].get(k, 0.0)


def compare(low: dict, ref: dict) -> dict:
    """Decomposition of LCOH(low) - LCOH(ref) and the investment view of choosing the low-temperature design."""
    bl, br = low["breakdown_USD_per_kg"], ref["breakdown_USD_per_kg"]
    d = {k: bl[k] - br[k] for k in bl}
    hx = item(low, "heat_exchangers") - item(ref, "heat_exchangers")
    rx = item(low, "reactor") - item(ref, "reactor")
    cap_fixed = d["capex"] + d["fixed_opex"]
    dec = {"energy_heat_fuel": d["heat_fuel"], "utilities_cooling_electricity": d["cooling_water"] + d["electricity"],
           "exchanger_capital_and_fixed": hx, "reactor_capital_and_fixed": rx,
           "other_capital_and_fixed": cap_fixed - hx - rx, "catalyst": d["catalyst"], "carbon_tax": d["carbon_tax"],
           "ammonia_feed": d["ammonia_feed"]}
    net = low["lcoh_USD_per_kg"] - ref["lcoh_USD_per_kg"]
    H = low["annual_h2_kg"]
    # break-even quantities, low-temperature design held fixed (T, W)
    A_low = low["lcoh_USD_per_kg"] - bl["catalyst"]
    margin = ref["lcoh_USD_per_kg"] - A_low          # USD/kg available to pay for the low-T catalyst
    W, p, L = low["W_kg"], low["catalyst_cost"]["price_USD_per_kg"], low["catalyst_cost"]["lifetime_yr"]
    p_be = margin * L * H / W if (margin > 0 and W > 0) else (None if W > 0 else float("inf"))
    L_be = (W * p / (margin * H)) if margin > 0 else None
    inv = investment(low, ref)
    return {"low": low["catalyst"], "ref": ref["catalyst"], "low_T_C": low["T_C"], "ref_T_C": ref["T_C"],
            "low_W_kg": W, "ref_W_kg": ref["W_kg"],
            "net_lcoh_delta_USD_per_kg": net, "net_lcoh_delta_SGD_per_kg": net * FX,
            "low_cheaper": net < 0, "decomposition_USD_per_kg": dec,
            "decomposition_sum_check_USD_per_kg": sum(dec.values()) - net,
            "energy_saving_USD_per_kg": -d["heat_fuel"],
            "energy_saving_fired_duty_kW": ref["fired_process_duty_kW"] - low["fired_process_duty_kW"],
            "energy_saving_supplementary_nh3_kg_h": ref["supplementary_nh3_kg_h"] - low["supplementary_nh3_kg_h"],
            "energy_saving_first_law_deficit_kW": ref["first_law_deficit_kW"] - low["first_law_deficit_kW"],
            "catalyst_cost_increase_USD_per_kg": d["catalyst"],
            "savings_minus_catalyst_increase_USD_per_kg": -(net),
            "breakeven_price_fixed_design_USD_per_kg": p_be,
            "breakeven_price_fixed_design_SGD_per_kg": None if p_be in (None, float("inf")) else p_be * FX,
            "breakeven_lifetime_fixed_design_yr": L_be,
            "margin_for_low_T_catalyst_USD_per_kg": margin, **inv}


def investment(low: dict, ref: dict) -> dict:
    al, ar = low["annual_USD_per_yr"], ref["annual_USD_per_yr"]
    ops = ("heat_fuel", "electricity", "cooling_water", "fixed_opex", "carbon_tax", "ammonia_feed")
    S = -sum(al[k] - ar[k] for k in ops)                       # USD/yr saved by choosing low
    dTCI = low["capex_total_USD"] - ref["capex_total_USD"]
    ch_l, ch_r = low["catalyst_cost"]["charge_USD"], ref["catalyst_cost"]["charge_USD"]
    L_l, L_r = low["catalyst_cost"]["lifetime_yr"], ref["catalyst_cost"]["lifetime_yr"]
    I0 = dTCI + ch_l - ch_r
    i, n = low["discount_rate"], int(round(low["plant_life_yr"]))
    a = (1.0 - (1.0 + i) ** -n) / i if i > 0 else float(n)
    repl = _replacements_pv(ch_l, L_l, i, n) - _replacements_pv(ch_r, L_r, i, n)
    npv = -I0 + S * a - repl
    s_net = S - (ch_l / L_l - ch_r / L_r)
    if s_net > 0:
        payback = max(I0, 0.0) / s_net
    else:
        payback = None
    npv_s = -(low["lcoh_USD_per_kg"] - ref["lcoh_USD_per_kg"]) * low["annual_h2_kg"] / low["crf"]
    return {"incremental_TCI_USD": dTCI, "incremental_first_charge_USD": ch_l - ch_r, "incremental_investment_USD": I0,
            "incremental_investment_SGD": I0 * FX, "annual_operating_saving_USD_per_yr": S,
            "annual_saving_net_of_smoothed_replacement_USD_per_yr": s_net,
            "simple_payback_yr": payback, "npv_choose_low_USD": npv, "npv_choose_low_SGD": npv * FX,
            "npv_choose_low_smoothed_USD": npv_s, "npv_discount_rate": i, "npv_life_yr": n}


def _replacements_pv(charge: float, L: float, i: float, n: int) -> float:
    pv, k = 0.0, 1
    while k * L < n - 1e-9:
        pv += charge * (1.0 + i) ** -(k * L)
        k += 1
    return pv


def kinetics_label(*cids: str) -> dict:
    v = [cc.kinetic_validity(c, P_BAR) for c in cids]
    ext = [c for c, x in zip(cids, v) if x["kinetic_validity_class"] == "extrapolated"]
    return {"laws": {cc.CATALYSTS[c]["short"]: x["kinetic_validity_class"] for c, x in zip(cids, v)},
            "rests_on_extrapolated_law": bool(ext),
            "result_label": "extrapolation" if ext else "pressure extrapolation (laws validated against literature at <= 10 bar only)",
            "extrapolated_laws": [cc.CATALYSTS[c]["short"] for c in ext]}
