"""Independent-physics recalculations of selected Aspen Plus block results (used by the validation matrix).

Each function takes a stored Aspen :class:`SimulationResult` and recomputes one block output from the
Aspen *inlet* states with an independent property source:

* :func:`flame_temperature_cantera`   adiabatic complete-combustion temperature of TAILGAS + AIR
  (Cantera ideal-gas mixture with GRI-Mech 3.0 thermo, fixed product composition H2O/N2/O2), and for
  information the HP chemical-equilibrium temperature with dissociation (full GRI-Mech 3.0 species set,
  incl. OH, H, O, NO).
* :func:`fluehx_duty_cantera`         FLUEHX duty = n (h(T_stack) - h(T_flue)) of the Aspen flue composition.
* :func:`pump_power_hand`             brake power n v_L dP / eta with the CoolProp reference-EOS liquid volume.
* :func:`fehe_ua_lmtd`                Aspen HeatX UA against Q / LMTD from the four terminal temperatures.
* :func:`feed_section_analysis`       decomposition of the feed-section (vaporiser / FEHE) differences between
  Aspen PENG-ROB and the Python property basis at identical states (no tuning; reported only).

Cantera and CoolProp are imported lazily. Nothing here feeds back into a model.
"""
from __future__ import annotations

import math

from amcrax.schemas import SimulationResult

K0 = 273.15
#: Aspen Plus reports UA in cal/sec-K; the International Table calorie is used for the conversion.
CAL_IT_J = 4.1868
CAL_TH_J = 4.184


def _kmolh(st) -> dict[str, float]:
    return {k: float(v) for k, v in st.component_mole_flow_kmol_h.items() if v and v > 0}


def _cantera_gas(full: bool = False):
    import cantera as ct

    if full:
        return ct.Solution("gri30.yaml")
    allsp = {s.name: s for s in ct.Species.list_from_file("gri30.yaml")}
    return ct.Solution(thermo="ideal-gas", species=[allsp[n] for n in ("NH3", "H2", "N2", "H2O", "O2")])


def _H_W(gas, n_kmol_h: dict[str, float], T_K: float, P_bar: float) -> float:
    """Enthalpy flow (formation-enthalpy reference) of a stream, W."""
    tot = sum(n_kmol_h.values())
    if tot <= 0:
        return 0.0
    gas.TPX = T_K, P_bar * 1e5, n_kmol_h
    return gas.enthalpy_mole * tot / 3600.0  # J/kmol * kmol/h / (s/h)


def complete_combustion_products(tail: dict[str, float], air: dict[str, float]) -> dict[str, float]:
    nh3, h2 = tail.get("NH3", 0.0), tail.get("H2", 0.0)
    o2_stoich = 0.5 * h2 + 0.75 * nh3
    return {"N2": tail.get("N2", 0.0) + air.get("N2", 0.0) + 0.5 * nh3,
            "H2O": tail.get("H2O", 0.0) + air.get("H2O", 0.0) + h2 + 1.5 * nh3,
            "O2": tail.get("O2", 0.0) + air.get("O2", 0.0) - o2_stoich}


def flame_temperature_cantera(r: SimulationResult) -> dict:
    """Adiabatic flame temperature from the Aspen TAILGAS and AIR streams (complete combustion, and HP equilibrium)."""
    st = r.streams
    tail, air, flue = st["TAILGAS"], st["AIR"], st["FLUE"]
    gas = _cantera_gas()
    n_t, n_a = _kmolh(tail), _kmolh(air)
    H_in = _H_W(gas, n_t, tail.temperature_C + K0, tail.pressure_bar) + _H_W(gas, n_a, air.temperature_C + K0,
                                                                            air.pressure_bar)
    prod = complete_combustion_products(n_t, n_a)
    if prod["O2"] < 0:
        raise ValueError("sub-stoichiometric air: complete combustion not defined")
    n_p = sum(prod.values())
    P = flue.pressure_bar * 1e5
    gas.TPX = 1500.0, P, prod
    h_mole = H_in * 3600.0 / n_p                     # J/kmol of products
    gas.HP = h_mole / gas.mean_molecular_weight, P    # composition held fixed
    T_complete = gas.T
    full = _cantera_gas(full=True)
    full.TPX = T_complete, P, prod
    full.HP = h_mole / full.mean_molecular_weight, P
    full.equilibrate("HP")
    T_eq = full.T
    x = dict(zip(full.species_names, full.X))
    minor = {k: float(v) for k, v in sorted(x.items(), key=lambda t: -t[1]) if k not in ("N2", "H2O", "O2") and v > 1e-5}
    flue_n = _kmolh(flue)
    comp_dev = max(abs(prod.get(k, 0.0) - flue_n.get(k, 0.0)) for k in set(prod) | set(flue_n))
    return {"T_complete_C": T_complete - K0, "T_equilibrium_C": T_eq - K0, "T_aspen_C": flue.temperature_C,
            "dT_complete_minus_aspen_K": T_complete - K0 - flue.temperature_C,
            "dT_equilibrium_minus_complete_K": T_eq - T_complete,
            "equilibrium_minor_species_mole_frac": minor,
            "max_abs_product_flow_dev_vs_aspen_flue_kmol_h": comp_dev}


def fluehx_duty_cantera(r: SimulationResult) -> dict:
    st = r.streams
    flue, stack = st["FLUE"], st["STACK"]
    gas = _cantera_gas()
    n = _kmolh(flue)
    q = (_H_W(gas, n, stack.temperature_C + K0, stack.pressure_bar)
         - _H_W(gas, n, flue.temperature_C + K0, flue.pressure_bar)) / 1000.0
    qa = r.blocks["FLUEHX"].duty_kW
    return {"Q_cantera_kW": q, "Q_aspen_kW": qa, "rel_dev": (q - qa) / abs(qa)}


def pump_power_hand(r: SimulationResult, efficiency: float | None = None) -> dict:
    """Brake power = n v_L(T_feed, P_feed) (P_out - P_in) / eta; v_L of NH3 from CoolProp (incompressible liquid)."""
    import CoolProp.CoolProp as CP

    feed, s1 = r.streams["FEED"], r.streams["S1"]
    pump = r.blocks["PUMP"]
    eta = efficiency if efficiency is not None else float(pump.details.get("efficiency") or 0.75)
    stt = CP.AbstractState("HEOS", "Ammonia")
    stt.specify_phase(CP.iphase_liquid)
    stt.update(CP.PT_INPUTS, feed.pressure_bar * 1e5, feed.temperature_C + K0)
    v = 1.0 / stt.rhomolar()
    n_mol_s = feed.mole_flow_kmol_h * 1000.0 / 3600.0
    w = n_mol_s * v * (s1.pressure_bar - feed.pressure_bar) * 1e5 / eta / 1000.0
    return {"W_hand_kW": w, "W_aspen_kW": pump.power_kW, "rel_dev": (w - pump.power_kW) / abs(pump.power_kW),
            "efficiency": eta, "v_L_m3_mol": v}


def fehe_ua_lmtd(r: SimulationResult) -> dict | None:
    fe = r.blocks.get("FEHE")
    if fe is None or fe.details.get("UA") is None:
        return None
    d = fe.details
    th_in, th_out = float(d["hot_inlet_temperature_C"]), float(d["hot_outlet_temperature_C"])
    tc_in, tc_out = float(d["cold_inlet_temperature_C"]), float(d["cold_outlet_temperature_C"])
    d1, d2 = th_in - tc_out, th_out - tc_in
    lmtd = d1 if abs(d1 - d2) < 1e-12 else (d1 - d2) / math.log(d1 / d2)
    if str(d.get("UA_unit")).lower() != "cal/sec-k":
        raise ValueError(f"unexpected UA unit {d.get('UA_unit')!r}")
    ua_it = float(d["UA"]) * CAL_IT_J / 1000.0
    ua_th = float(d["UA"]) * CAL_TH_J / 1000.0
    ua_lm = fe.duty_kW / lmtd
    return {"UA_aspen_kW_K": ua_it, "UA_Q_over_LMTD_kW_K": ua_lm, "LMTD_K": lmtd,
            "lmtd_aspen_K": d.get("lmtd_K"), "rel_dev": (ua_it - ua_lm) / ua_lm,
            "rel_dev_if_thermochemical_cal": (ua_th - ua_lm) / ua_lm}


def feed_section_analysis(aspen: SimulationResult, python_pr: SimulationResult | None = None,
                          python_ideal_old_fehe_kW: float | None = None) -> dict:
    """Feed-section property-model comparison at identical states (Aspen baseline states).

    Returns the vaporiser duty on the reference basis at Aspen's S1/S2 states, the NH3 residual enthalpy at S2
    (PR k_ij = 0 vs reference EOS), the dew points of the feed vapour at the vaporiser pressure (PR with two
    NH3-H2O k_ij values, Raoult, Aspen, pure-NH3 saturation) and an additive split of the FEHE duty gap
    (Python - Aspen) into: (a) inlet temperature (dew-point model), (b) PR vs reference residual at S2,
    (c) residual at S3, (d) remainder (ideal-gas cp sources, PR constants).
    """
    import CoolProp.CoolProp as CP

    from amcrax.process_model import properties as pp
    from amcrax.process_model import run_python_case
    from amcrax.thermodynamics import mixture_enthalpy_kW
    from amcrax.thermodynamics import peng_robinson as pr

    S = aspen.streams
    nf = _kmolh(S["S2"])
    tot = sum(nf.values())
    y = {k: v / tot for k, v in nf.items()}
    T1, P1 = S["S1"].temperature_C + K0, S["S1"].pressure_bar
    T2, P2 = S["S2"].temperature_C + K0, S["S2"].pressure_bar
    out: dict = {"case_id": aspen.case_id, "S2_aspen_C": T2 - K0, "P2_bar": P2}
    q_ref = pp.feed_section_enthalpy_kW(nf, T2, P2, "gas") - pp.feed_section_enthalpy_kW(nf, T1, P1, "liquid")
    q_a = aspen.blocks["VAPORIZR"].duty_kW
    out["vaporiser_at_aspen_states"] = {"reference_eos_kW": q_ref, "aspen_peng_rob_kW": q_a,
                                        "aspen_minus_reference_rel": (q_a - q_ref) / q_ref}
    out["nh3_residual_enthalpy_S2_kJ_mol"] = {"peng_robinson_kij0": pr.enthalpy_departure_J_mol({"NH3": 1.0}, T2, P2) / 1000,
                                              "reference_eos": pp.nh3_residual_enthalpy_kJ_mol(T2, P2)}
    sup = 10.0
    dew = {"pure_NH3_saturation_reference_C": CP.PropsSI("T", "P", P2 * 1e5, "Q", 1, "Ammonia") - K0,
           "raoult_ideal_liquid_C": pp.dew_point_K(P2, y) - K0,
           "aspen_peng_rob_C (S2 - 10 K superheat)": T2 - K0 - sup}
    for k in (0.0, -0.25):
        dew[f"peng_robinson_kij_NH3_H2O_{k:+.2f}_C"] = pr.dew_point_K(P2, y, kij={("NH3", "H2O"): k})[0] - K0
    out["dew_point"] = dew
    if aspen.inputs.heat_integration and "FEHE" in aspen.blocks:
        p = python_pr or run_python_case(aspen.inputs, eos="pr")
        T3, P3 = S["S3"].temperature_C + K0, S["S3"].pressure_bar
        T2p = p.streams["S2"].temperature_C + K0
        nN = nf.get("NH3", 0.0) / 3.6
        qa, qp = aspen.blocks["FEHE"].duty_kW, p.blocks["FEHE"].duty_kW
        a = pp.feed_section_enthalpy_kW(nf, T2, P2, "gas") - pp.feed_section_enthalpy_kW(nf, T2p, P2, "gas")
        b = nN * (pr.enthalpy_departure_J_mol({"NH3": 1.0}, T2, P2) / 1000 - pp.nh3_residual_enthalpy_kJ_mol(T2, P2))
        c = nN * (pp.nh3_residual_enthalpy_kJ_mol(T3, P3) - pr.enthalpy_departure_J_mol({"NH3": 1.0}, T3, P3) / 1000)
        gap = qp - qa
        out["fehe_gap_split_kW"] = {
            "python_kW": qp, "aspen_kW": qa, "gap_python_minus_aspen_kW": gap,
            "a_inlet_temperature_dew_point": a, "b_PR_vs_reference_residual_at_S2": b,
            "c_reference_vs_PR_residual_at_S3": c, "d_remainder_ideal_gas_cp_and_PR_constants": gap - a - b - c,
            "NASA_PR_kij0_between_aspen_S2_S3_kW": mixture_enthalpy_kW(nf, T3, P_bar=P3, eos="pr")
            - mixture_enthalpy_kW(nf, T2, P_bar=P2, eos="pr")}
        if python_ideal_old_fehe_kW is not None:
            out["fehe_gap_split_kW"]["former_python_ideal_kW (mixed basis, before the fix)"] = python_ideal_old_fehe_kW
    return out
