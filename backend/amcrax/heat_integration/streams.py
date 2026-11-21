"""Extraction of heat-integration streams (H-T curves) from a SimulationResult.

Only fields of :class:`amcrax.schemas.SimulationResult` (stream T, P, component flows; block
duties) are used. Enthalpy-temperature curves are computed independently:

* ammonia feed (S1 -> S4): NH3 by CoolProp (reference EOS for ammonia, Gao et al. 2020 as
  implemented in CoolProp 8) from the pressurised liquid through saturation up to the
  switch temperature ``T_sw`` (vaporiser outlet S2, i.e. saturated vapour + superheat);
  above ``T_sw`` NASA-7 ideal-gas enthalpies (amcrax.thermodynamics, GRI-Mech 3.0 data)
  plus the Peng-Robinson enthalpy departure (amcrax.thermodynamics.peng_robinson).
* cracker reaction heat: isothermal cold duty at the reactor temperature, value = CRACKER
  block duty from the result (fallback: KPI, then independent calculation).
* cracked gas (S5 -> S7) and flue gas (FLUE -> STACK): NASA-7 ideal gas + PR departure.

Assumptions (labelled, see ASSUMPTIONS): the 0.2 mol% water in the feed is treated as ideal-gas
sensible heat only (its vaporisation enthalpy, ~0.3 % of the feed duty, is neglected); no
condensation in the cracked gas or flue gas is checked by a dew-point test (warning issued).
"""
from __future__ import annotations

import math

import numpy as np

from ..schemas import SimulationResult, StreamResult
from ..thermodynamics import isothermal_reactor_duty_kW, species_enthalpy_kJ_mol
from ..thermodynamics.peng_robinson import enthalpy_departure_J_mol
from .pinch import Curve, make_curve

N_POINTS = 40  # discretisation points per curve segment

ASSUMPTIONS = [
    "Feed water (0.2 mol%) contributes ideal-gas sensible heat only; its latent heat (<0.4 % of feed duty) is neglected.",
    "Gas-phase enthalpies: NASA-7 ideal gas (GRI-Mech 3.0 via amcrax.thermodynamics) + Peng-Robinson departure (kij = 0).",
    "Liquid/two-phase NH3: CoolProp reference EOS for pure ammonia at the vaporiser outlet pressure (pressure drop along the train neglected for the H-T curve).",
    "Isothermal duties (pure NH3 boiling, isothermal cracker) are represented as linear segments of 0.01 K width (numerical device).",
    "Each stream is taken at a single representative pressure (its inlet pressure); pressure drops in the exchangers are neglected for enthalpy.",
]


def _T_K(s: StreamResult | None) -> float | None:
    return None if s is None or s.temperature_C is None else s.temperature_C + 273.15


def _flows(s: StreamResult) -> dict[str, float]:
    f = {k: v for k, v in (s.component_mole_flow_kmol_h or {}).items() if v and v > 0}
    if not f and s.mole_flow_kmol_h and s.mole_frac:
        f = {k: s.mole_flow_kmol_h * y for k, y in s.mole_frac.items() if y > 0}
    if not f:
        raise ValueError(f"stream {s.id}: no component flows")
    return f


def gas_enthalpy_kW(n_kmol_h: dict[str, float], T_K: float, P_bar: float | None) -> float:
    """Ideal-gas (NASA-7) + PR departure enthalpy flow, kW (formation-enthalpy reference)."""
    h = sum(n * species_enthalpy_kJ_mol(sp, T_K) for sp, n in n_kmol_h.items()) / 3.6
    if P_bar is not None and P_bar > 1.5:
        tot = sum(n_kmol_h.values())
        y = {k: v / tot for k, v in n_kmol_h.items()}
        h += tot * enthalpy_departure_J_mol(y, T_K, P_bar) / 3600.0
    return h


def gas_curve(id: str, kind: str, n: dict[str, float], T_a_K: float, T_b_K: float, P_bar: float | None,
              name: str = "") -> Curve:
    lo, hi = sorted((T_a_K, T_b_K))
    T = np.linspace(lo, hi, N_POINTS)
    H = np.array([gas_enthalpy_kW(n, t, P_bar) for t in T])
    return make_curve(id, kind, T, H - H[0], name)


def feed_curve(n: dict[str, float], T_in_K: float, T_out_K: float, P_bar: float, T_switch_K: float | None,
               name: str = "Ammonia feed S1->S4") -> tuple[Curve, dict]:
    """Cold ammonia feed: CoolProp (liquid, boiling, vapour to T_switch) then ideal gas + PR departure."""
    import CoolProp.CoolProp as CP

    n_nh3 = n.get("NH3", 0.0)
    others = {k: v for k, v in n.items() if k != "NH3"}
    P_Pa = P_bar * 1e5
    Tsat = CP.PropsSI("T", "P", P_Pa, "Q", 0, "Ammonia")
    if T_switch_K is None or T_switch_K <= Tsat:
        T_switch_K = Tsat + 10.0  # flowsheet.json: vaporiser superheats by 10 K
    T_switch_K = min(T_switch_K, T_out_K)

    def h_other(T):  # ideal-gas sensible heat of minor components (water), kW
        return sum(v * species_enthalpy_kJ_mol(k, T) for k, v in others.items()) / 3.6

    pts_T: list[float] = []
    pts_H: list[float] = []
    if T_in_K < Tsat < T_switch_K:
        TL = np.linspace(T_in_K, Tsat - 1e-3, N_POINTS // 2)
        hl = [CP.PropsSI("Hmolar", "T", t, "P", P_Pa, "Ammonia") for t in TL[:-1]]
        hl.append(CP.PropsSI("Hmolar", "P", P_Pa, "Q", 0, "Ammonia"))
        TV = np.linspace(Tsat + 1e-3, T_switch_K, N_POINTS // 2)
        hv = [CP.PropsSI("Hmolar", "P", P_Pa, "Q", 1, "Ammonia")]
        hv += [CP.PropsSI("Hmolar", "T", t, "P", P_Pa, "Ammonia") for t in TV[1:]]
        TL[-1] = Tsat
        TV[0] = Tsat
        for t, h in list(zip(TL, hl)) + list(zip(TV, hv)):
            pts_T.append(float(t))
            pts_H.append(n_nh3 * h / 3600.0 + h_other(t))
    else:
        T0 = np.linspace(T_in_K, T_switch_K, N_POINTS)
        for t in T0:
            pts_T.append(float(t))
            pts_H.append(n_nh3 * CP.PropsSI("Hmolar", "T", t, "P", P_Pa, "Ammonia") / 3600.0 + h_other(t))
    # gas segment, continuous at T_switch
    if T_out_K > T_switch_K:
        H_sw = pts_H[-1]
        g0 = gas_enthalpy_kW(n, T_switch_K, P_bar)
        for t in np.linspace(T_switch_K, T_out_K, N_POINTS)[1:]:
            pts_T.append(float(t))
            pts_H.append(H_sw + gas_enthalpy_kW(n, t, P_bar) - g0)
    H = np.array(pts_H)
    c = make_curve("FEED", "cold", pts_T, H - H[0], name)
    latent_kW = n_nh3 * (CP.PropsSI("Hmolar", "P", P_Pa, "Q", 1, "Ammonia")
                         - CP.PropsSI("Hmolar", "P", P_Pa, "Q", 0, "Ammonia")) / 3600.0
    return c, {"T_sat_K": Tsat, "T_switch_K": T_switch_K, "latent_heat_kW": latent_kW}


def water_dew_point_K(n: dict[str, float], P_bar: float) -> float | None:
    """Dew point of water in a gas (CoolProp saturation curve of water)."""
    import CoolProp.CoolProp as CP

    tot = sum(n.values())
    p_w = n.get("H2O", 0.0) / tot * P_bar * 1e5 if tot > 0 else 0.0
    if p_w < 612.0:  # below the triple-point pressure: no liquid water
        return None
    return float(CP.PropsSI("T", "P", p_w, "Q", 1, "Water"))


def reaction_duty_kW(res: SimulationResult) -> tuple[float, str]:
    b = res.blocks.get("CRACKER")
    if b is not None and b.duty_kW is not None:
        return float(b.duty_kW), "CRACKER block duty (simulation result)"
    if res.kpis.reactor_duty_kW is not None:
        return float(res.kpis.reactor_duty_kW), "KPI reactor_duty_kW (simulation result)"
    s4, s5 = res.streams["S4"], res.streams["S5"]
    q = isothermal_reactor_duty_kW(_flows(s4), _T_K(s4), _flows(s5), _T_K(s5),
                                   P_in_bar=s4.pressure_bar, P_out_bar=s5.pressure_bar, eos="pr")
    return float(q), "independent calculation (amcrax.thermodynamics, PR)"


def extract_streams(res: SimulationResult) -> dict:
    """Return the HI streams and the metadata needed by the analysis."""
    st = res.streams
    for sid in ("S1", "S4", "S5", "S7"):
        if sid not in st or _T_K(st[sid]) is None:
            raise ValueError(f"SimulationResult lacks stream {sid} temperature")
    warnings: list[str] = []
    s1, s4, s5, s7 = st["S1"], st["S4"], st["S5"], st["S7"]
    s2 = st.get("S2")
    P_vap = (s2.pressure_bar if s2 is not None and s2.pressure_bar else None) or s1.pressure_bar \
        or res.inputs.reactor_pressure_bar + 0.8
    feed_n = _flows(s1)
    feed, feed_meta = feed_curve(feed_n, _T_K(s1), _T_K(s4), P_vap, _T_K(s2))

    T_R = _T_K(s5)
    q_rxn, q_rxn_src = reaction_duty_kW(res)
    rxn = make_curve("REACTION", "cold", [T_R, T_R], [0.0, max(q_rxn, 0.0)],
                     f"Cracking reaction heat (isothermal, {T_R - 273.15:.0f} degC)")

    cg_n = _flows(s5)
    P_cg = s5.pressure_bar or res.inputs.reactor_pressure_bar
    cracked = gas_curve("CRACKED", "hot", cg_n, _T_K(s5), _T_K(s7), P_cg, "Cracked gas S5->S7")
    dp = water_dew_point_K(cg_n, s7.pressure_bar or P_cg)
    if dp is not None and dp > _T_K(s7):
        warnings.append(f"Cracked gas water dew point {dp - 273.15:.1f} degC above PSA feed T: condensation neglected.")

    flue = None
    if "FLUE" in st and _T_K(st["FLUE"]) is not None:
        fl = st["FLUE"]
        T_stack = _T_K(st.get("STACK")) or res.inputs.stack_temperature_C + 273.15
        fn = _flows(fl)
        if _T_K(fl) > T_stack:
            flue = gas_curve("FLUE", "hot", fn, _T_K(fl), T_stack, fl.pressure_bar, "Tail-gas flue gas FLUE->STACK")
        dpf = water_dew_point_K(fn, fl.pressure_bar or 1.1)
        if dpf is not None and dpf > T_stack:
            warnings.append(f"Flue-gas water dew point {dpf - 273.15:.1f} degC above stack T: condensation neglected.")
    else:
        warnings.append("No FLUE stream in result: tail-gas firing not analysed.")
    return {
        "feed": feed, "feed_meta": feed_meta, "reaction": rxn, "reaction_source": q_rxn_src,
        "cracked": cracked, "flue": flue, "T_reactor_K": T_R, "warnings": warnings, "P_vap_bar": P_vap,
    }
