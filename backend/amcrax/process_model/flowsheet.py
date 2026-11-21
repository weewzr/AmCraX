"""Independent Python mirror of the AmCraX Aspen Plus flowsheet (``config/flowsheet.json``).

Every result produced here carries ``source = DataSource.PYTHON`` ("python_model"). It is used
(i) to cross-check the Aspen mass/energy balances, (ii) to serve labelled results when Aspen is
unavailable and (iii) as a fast surrogate for optimisation.

Block sequence (IDs = Aspen IDs)::

    FEED -> PUMP -S1-> VAPORIZR -S2-> FEHE(cold) -S3-> HEATER -S4-> CRACKER -S5-> FEHE(hot) -S6->
    COOLER -S7-> PSA -> H2PROD / TAILGAS -> BURNER (+AIR) -FLUE-> FLUEHX -> STACK
    heat_integration=False: no FEHE, S2 -> HEATER, S5 -> COOLER (S3, S6 absent).

Property basis: see :mod:`amcrax.process_model.properties` (NASA ideal gas with formation-enthalpy
reference for the gas section; CoolProp reference EOS for liquid / vaporising ammonia, anchored to
the NASA scale at 298.15 K, 1 Pa; 0.2 mol% water handled as an ideal-solution component).

Block models
------------
* PUMP: incompressible liquid, W = v_L(T_feed) dP / eta, eta = 0.75 (ASSUMPTION, typical
  centrifugal-pump efficiency; same value as the Aspen input ``PUMP_EFFICIENCY``). The brake
  power is added to the fluid enthalpy (as Aspen Pump does).
* VAPORIZR: outlet = Raoult dew point at the outlet pressure + 10 K.
* FEHE: cold outlet T = hot inlet T - ``fehe_hot_end_approach_K``; hot outlet from the energy
  balance. A counter-current T-Q profile (41 points) is checked for a temperature cross; an
  infeasible approach raises :class:`FlowsheetSpecError`.
  Property basis of the FEHE (the same in both ``eos`` modes, so that the energy balance and the
  internal profile are on ONE real-gas basis):
    - cold side S2 -> S3: NASA-7 ideal-gas enthalpy + residual enthalpy of NH3 from the reference
      EOS (CoolProp, Gao et al. 2020; :func:`properties.feed_gas_enthalpy_kW`), water ideal gas.
      Chosen over the PR departure because the reference EOS is the more accurate model for pure
      ammonia (at S2 the PR residual is -1.0 kJ/mol against -1.4 kJ/mol), and over the full
      CoolProp enthalpy because its ideal-gas part is 0.04-0.10 kJ/mol below NIST-JANAF at
      600-1000 K whereas NASA-7 (the scale of every other gas stream) is within 0.012 kJ/mol.
      Above 725 K the reference EOS is extrapolated; the residual is < 0.4 kJ/mol there.
    - hot side S5 -> S6: NASA-7 + Peng-Robinson residual. In eos="ideal" the stream table keeps
      H6 = H5 - Q (ideal basis, exact bookkeeping) while T6 and the profile use the PR hot side:
      an ideal-gas hot side mis-places T6 by up to 7 K at 100 bar and turned feasible 80-100 bar
      specifications into crosses, so it is not negligible. The ideal-basis offset of S6 is
      reported as ``s6_enthalpy_minus_eos_basis_at_T6_kW``.
  The former implementation took S3 on the gas-section basis of ``eos`` (ideal gas for "ideal")
  against a real-gas S2: Q was ~4 kW too high at the baseline and feasible 60-80 bar
  specifications were rejected as temperature crosses.
* HEATER: to the reactor temperature. Its inlet (S3, or S2 without FEHE) is on the real-gas
  basis and its outlet S4 on the eos gas basis; the duty therefore carries the basis difference at
  S4 (detail ``s4_basis_minus_reference_real_gas_kW``: +3.6 kW at the baseline for eos="ideal",
  -0.6 kW for eos="pr"). CRACKER: isothermal equilibrium
  (:func:`amcrax.thermodynamics.solve_equilibrium`, ``eos`` selectable, default "ideal"),
  duty = H_out - H_in.
* COOLER: to ``psa_feed_temperature_C``; a Raoult dew-point check flags (does not model)
  condensation.
* PSA: component splitter (H2 recovery, N2 slip, NH3/H2O/O2 to tail gas); both outlets at the
  feed temperature; duty = H_out - H_in (0 for ideal gas).
* BURNER: adiabatic complete combustion (H2 + 0.5 O2 -> H2O; NH3 + 0.75 O2 -> 0.5 N2 + 1.5 H2O),
  air (79/21 N2/O2, 25 degC) = (1 + excess) x stoichiometric; flame temperature solved.
  Dissociation and NOx are not modelled (same as the Aspen RStoic block).
* FLUEHX: flue gas cooled to the stack temperature.

KPIs and balances: :func:`amcrax.kpis.compute_kpis` / :func:`amcrax.kpis.compute_balances`, i.e. the
same definitions as for Aspen results (including the case of a flame temperature below the stack
temperature, when the positive FLUEHX duty is external heating and the combustion credit is 0).
``lhv_efficiency`` and ``net_fuel_heat_deficit_kW`` are first-law, upper-bound metrics: external heat
is counted 1:1 against LHV (a 100 %-efficient fired heater), flue heat is credited regardless of its
temperature level (also below the reactor temperature), and a surplus earns no credit. The
temperature-level assessment is in :mod:`amcrax.heat_integration`.
"""
from __future__ import annotations

import json
import math
import time
from functools import lru_cache

import numpy as np
from scipy.interpolate import PchipInterpolator

from amcrax.kpis import compute_balances, compute_kpis
from amcrax.paths import CONFIG_DIR
from amcrax.schemas import (
    COMPONENTS,
    MOLAR_MASS,
    BlockResult,
    CaseInputs,
    DataSource,
    RunStatus,
    SimulationResult,
    StreamResult,
)
from amcrax.thermodynamics import solve_equilibrium

from . import properties as pp

FEED_PRESSURE_BAR = 1.013
VAPORIZER_SUPERHEAT_K = 10.0
PUMP_EFFICIENCY = 0.75          # ASSUMPTION (typical centrifugal pump; identical to the Aspen input)
AIR_T_C = 25.0
AIR_O2 = 0.21
AIR_N2 = 0.79
MIN_FLOWSHEET_PRESSURE_BAR = 3.0
FEHE_PROFILE_POINTS = 41
HOT_SIDE_GRID_POINTS = 61       # exact PR evaluations of the FEHE hot side, inverted by PCHIP interpolation
K0 = 273.15


class FlowsheetSpecError(ValueError):
    """Raised when a CaseInputs specification is infeasible for the fixed flowsheet."""


@lru_cache(maxsize=1)
def pressure_profile() -> dict[str, tuple[str, float]]:
    """Parse ``pressure_profile_bar_relative_to_reactor`` of config/flowsheet.json.

    Returns {key: ("rel"|"abs", value_bar)}.
    """
    cfg = json.loads((CONFIG_DIR / "flowsheet.json").read_text(encoding="utf-8"))
    out = {}
    for k, v in cfg["pressure_profile_bar_relative_to_reactor"].items():
        if k == "comment":
            continue
        v = str(v).strip()
        if "absolute" in v:
            out[k] = ("abs", float(v.split()[0]))
        else:
            out[k] = ("rel", float(v))
    return out


def _p(key: str, p_reactor: float) -> float:
    kind, val = pressure_profile()[key]
    return val if kind == "abs" else p_reactor + val


def _clean(n: dict[str, float]) -> dict[str, float]:
    return {c: float(max(n.get(c, 0.0), 0.0)) for c in COMPONENTS}


def _stream(sid, name, src, dst, n, T_K, P_bar, H_kW, phase, vf) -> StreamResult:
    n = _clean(n)
    tot = sum(n.values())
    mass = {c: n[c] * MOLAR_MASS[c] for c in COMPONENTS}
    mtot = sum(mass.values())
    return StreamResult(
        id=sid, name=name, source_block=src, dest_block=dst, phase=phase,
        temperature_C=T_K - K0, pressure_bar=P_bar, vapor_fraction=vf,
        mole_flow_kmol_h=tot, mass_flow_kg_h=mtot, enthalpy_flow_kW=H_kW,
        mole_frac={c: (n[c] / tot if tot > 0 else 0.0) for c in COMPONENTS},
        mass_frac={c: (mass[c] / mtot if mtot > 0 else 0.0) for c in COMPONENTS},
        component_mole_flow_kmol_h=n,
    )


def validate_inputs(inputs: CaseInputs) -> None:
    if inputs.reactor_pressure_bar < MIN_FLOWSHEET_PRESSURE_BAR:
        raise FlowsheetSpecError(
            f"reactor_pressure_bar={inputs.reactor_pressure_bar} below {MIN_FLOWSHEET_PRESSURE_BAR} bar: "
            "the fixed pressure profile (H2 product at P-1.0 bar, tail gas at 1.3 bar) is not physical")
    if inputs.stack_temperature_C <= -100:
        raise FlowsheetSpecError("stack temperature unphysical")


def run_python_case(inputs: CaseInputs, eos: str = "ideal") -> SimulationResult:
    """Simulate one case with the independent Python model (source = python_model).

    ``eos``: "ideal" (default) or "pr" - used for the CRACKER equilibrium and the gas-section
    enthalpies. Raises :class:`FlowsheetSpecError` for infeasible specifications.
    """
    t_start = time.perf_counter()
    eos = eos.lower()
    validate_inputs(inputs)
    P = inputs.reactor_pressure_bar
    T_R = inputs.reactor_temperature_C + K0
    hi = inputs.heat_integration
    msgs: list[str] = []
    warn = False
    streams: dict[str, StreamResult] = {}
    blocks: dict[str, BlockResult] = {}

    def gasH(n, T, Pb):
        return pp.gas_enthalpy_kW(n, T, Pb, eos)

    # ------------------------------------------------------------ FEED
    x_w = inputs.feed_h2o_mole_frac
    n_feed = {"NH3": inputs.feed_total_kmol_h * (1 - x_w), "H2O": inputs.feed_total_kmol_h * x_w}
    T_feed = pp.bubble_point_K(FEED_PRESSURE_BAR, 1 - x_w)
    H_feed = pp.feed_section_enthalpy_kW(n_feed, T_feed, FEED_PRESSURE_BAR, "liquid")
    streams["FEED"] = _stream("FEED", "Liquid ammonia feed", None, "PUMP", n_feed, T_feed, FEED_PRESSURE_BAR,
                              H_feed, "liquid", 0.0)

    # ------------------------------------------------------------ PUMP
    P1 = _p("PUMP_discharge", P)
    v_L = pp.nh3_liquid_molar_volume_m3_mol(T_feed, FEED_PRESSURE_BAR)  # m3/mol (NH3 basis for the mixture)
    n_tot_mol_s = inputs.feed_total_kmol_h * 1000.0 / 3600.0
    fluid_power_kW = n_tot_mol_s * v_L * (P1 - FEED_PRESSURE_BAR) * 1e5 / 1000.0
    W_pump = fluid_power_kW / PUMP_EFFICIENCY
    H1 = H_feed + W_pump
    T1 = pp.solve_T_for_enthalpy(lambda T: pp.feed_section_enthalpy_kW(n_feed, T, P1, "liquid"),
                                 H1, T_feed - 5.0, T_feed + 20.0)
    streams["S1"] = _stream("S1", "Pressurised liquid ammonia", "PUMP", "VAPORIZR", n_feed, T1, P1, H1, "liquid", 0.0)
    blocks["PUMP"] = BlockResult(id="PUMP", name="Ammonia feed pump", block_type="Pump", duty_kW=0.0,
                                 power_kW=W_pump, outlet_temperature_C=T1 - K0, outlet_pressure_bar=P1,
                                 details={"efficiency": PUMP_EFFICIENCY, "fluid_power_kW": fluid_power_kW,
                                          "efficiency_source": "assumption"})

    # ------------------------------------------------------------ VAPORIZR
    P2 = _p("VAPORIZR_out", P)
    y_feed = {k: v / inputs.feed_total_kmol_h for k, v in n_feed.items()}
    T_dew = pp.dew_point_K(P2, y_feed)
    T2 = T_dew + VAPORIZER_SUPERHEAT_K
    H2 = pp.feed_section_enthalpy_kW(n_feed, T2, P2, "gas")
    Q_vap = H2 - H1
    streams["S2"] = _stream("S2", "Ammonia vapour", "VAPORIZR", "FEHE" if hi else "HEATER", n_feed, T2, P2, H2,
                            "vapor", 1.0)
    blocks["VAPORIZR"] = BlockResult(id="VAPORIZR", name="Ammonia vaporiser", block_type="Heater", duty_kW=Q_vap,
                                     outlet_temperature_C=T2 - K0, outlet_pressure_bar=P2,
                                     details={"dew_point_C": T_dew - K0, "superheat_K": VAPORIZER_SUPERHEAT_K,
                                              "vle_model": "Raoult (ideal liquid), CoolProp Psat"})

    # ------------------------------------------------------------ HEATER / CRACKER (T5 is fixed = T_R)
    P4 = _p("HEATER_out", P)
    H4 = gasH(n_feed, T_R, P4)
    eq = solve_equilibrium(T_R, P, n_feed, eos=eos)
    n5 = _clean(eq.n_out)
    H5 = gasH(n5, T_R, P)
    Q_crk = H5 - H4

    # ------------------------------------------------------------ FEHE
    if hi:
        P3 = _p("FEHE_cold_out", P)
        P6 = _p("FEHE_hot_out", P)
        T3 = T_R - inputs.fehe_hot_end_approach_K
        if T3 <= T2:
            raise FlowsheetSpecError(
                f"FEHE infeasible: cold outlet {T3 - K0:.1f} degC not above cold inlet {T2 - K0:.1f} degC; "
                "reduce fehe_hot_end_approach_K or raise reactor_temperature_C")
        def coldH(T, Pb=P3):  # cold side on the real-gas basis in both eos modes (see module docstring)
            return pp.feed_gas_enthalpy_kW(n_feed, T, Pb)

        def hotH(T, Pb=P6):  # hot side on the real-gas (PR) basis in both eos modes
            return pp.gas_enthalpy_kW(n5, T, Pb, "pr")

        H3 = coldH(T3)
        Q_fehe = H3 - H2
        H6 = H5 - Q_fehe                 # S6 enthalpy on the eos basis of the stream table (exact bookkeeping)
        H6r = hotH(T_R, P) - Q_fehe      # real-gas hot-side energy balance (identical to H6 for eos="pr")
        T6 = pp.solve_T_for_enthalpy(hotH, H6r, 250.0, T_R + 1.0)
        s6_offset = H6 - gasH(n5, T6, P6)  # 0 for eos="pr"; ideal-basis H6 vs ideal-gas H at the real-gas T6
        # counter-current T-Q profile check (cold inlet end f=0 <-> hot outlet end). delta_c is the small
        # difference at the cold inlet between S2 (CoolProp anchored, at P2) and the cold-side function at P3
        # (P2 -> P3 pressure drop and NASA vs CoolProp ideal-gas cp between 298.15 K and T2); it is blended out
        # linearly along the exchanger, as a distributed pressure drop would be.
        delta_c = H2 - coldH(T2)
        # Hot side: the PR enthalpy is evaluated exactly on a fine temperature grid and inverted by monotone cubic
        # (PCHIP) interpolation instead of one root solve per profile point (about 5x fewer PR evaluations; the
        # interpolation error is < 1e-3 K, tests/test_process_model.py). The cold side is solved exactly.
        Tg = np.linspace(T6, T_R + 2.0, HOT_SIDE_GRID_POINTS)
        Hg = np.array([hotH(t) for t in Tg])
        Th_of_H = PchipInterpolator(Hg, Tg, extrapolate=False)
        dT_min = math.inf
        for i in range(FEHE_PROFILE_POINTS):
            f = i / (FEHE_PROFILE_POINTS - 1)
            Hc = H2 + f * Q_fehe
            Hh = H6r + f * Q_fehe
            Tc = T2 if i == 0 else (T3 if i == FEHE_PROFILE_POINTS - 1 else pp.solve_T_for_enthalpy(
                lambda T: coldH(T) + (1 - f) * delta_c, Hc, T2 - 5.0, T3 + 5.0))
            if i == 0 or i == FEHE_PROFILE_POINTS - 1:
                Th = T6 if i == 0 else T_R
            else:
                Th = float(Th_of_H(Hh))
                if not math.isfinite(Th):  # outside the grid (cannot happen for a monotone H(T)); exact solve
                    Th = pp.solve_T_for_enthalpy(hotH, Hh, T6 - 5.0, T_R + 5.0)
            dT_min = min(dT_min, Th - Tc)
        if dT_min <= 0.0:
            raise FlowsheetSpecError(
                f"FEHE temperature cross (minimum hot-cold difference {dT_min:.2f} K) with approach "
                f"{inputs.fehe_hot_end_approach_K} K: specification infeasible")
        streams["S3"] = _stream("S3", "Preheated ammonia", "FEHE", "HEATER", n_feed, T3, P3, H3, "vapor", 1.0)
        streams["S6"] = _stream("S6", "Partly cooled cracked gas", "FEHE", "COOLER", n5, T6, P6, H6, "vapor", 1.0)
        blocks["FEHE"] = BlockResult(id="FEHE", name="Feed/effluent heat exchanger", block_type="HeatX",
                                     duty_kW=Q_fehe, outlet_temperature_C=T3 - K0, outlet_pressure_bar=P3,
                                     details={"cold_outlet_C": T3 - K0, "hot_outlet_C": T6 - K0,
                                              "hot_end_approach_K": inputs.fehe_hot_end_approach_K,
                                              "cold_end_approach_K": T6 - T2, "min_internal_dT_K": dT_min,
                                              "cold_side_basis": "NASA-7 ideal gas + reference-EOS NH3 residual "
                                                                 "enthalpy (both eos modes)",
                                              "hot_side_basis": "NASA-7 ideal gas + PR residual (both eos modes)",
                                              "s6_enthalpy_minus_eos_basis_at_T6_kW": s6_offset})
        H_heater_in = H3
    else:
        Q_fehe = 0.0
        H_heater_in = H2
        T6, H6, P6 = T_R, H5, P

    Q_heat = H4 - H_heater_in
    # The HEATER inlet (S3, or S2 without FEHE) is on the real-gas reference basis, its outlet S4 on the gas-section
    # basis of the selected eos; the difference of the two bases at S4 is carried by the HEATER duty (diagnostic).
    s4_offset = H4 - pp.feed_gas_enthalpy_kW(n_feed, T_R, P4)
    streams["S4"] = _stream("S4", "Reactor feed", "HEATER", "CRACKER", n_feed, T_R, P4, H4, "vapor", 1.0)
    blocks["HEATER"] = BlockResult(id="HEATER", name="Fired trim preheater", block_type="Heater", duty_kW=Q_heat,
                                   outlet_temperature_C=T_R - K0, outlet_pressure_bar=P4,
                                   details={"s4_basis_minus_reference_real_gas_kW": s4_offset,
                                            "basis_note": "inlet on the real-gas reference basis, outlet on the "
                                                          f"eos={eos} gas basis; the duty includes the basis "
                                                          "difference at S4 (s4_basis_minus_reference_real_gas_kW)"})
    streams["S5"] = _stream("S5", "Hot cracked gas", "CRACKER", "FEHE" if hi else "COOLER", n5, T_R, P, H5,
                            "vapor", 1.0)
    blocks["CRACKER"] = BlockResult(id="CRACKER", name="Ammonia cracking reactor", block_type="RGibbs",
                                    duty_kW=Q_crk, outlet_temperature_C=T_R - K0, outlet_pressure_bar=P,
                                    details={"conversion": eq.conversion, "K_eq": eq.K_eq, "eos": eos,
                                             "extent_kmol_h": eq.extent})

    # ------------------------------------------------------------ COOLER
    P7 = _p("COOLER_out", P)
    T7 = inputs.psa_feed_temperature_C + K0
    H7 = gasH(n5, T7, P7)
    Q_cool = H7 - H6
    tot5 = sum(n5.values())
    dew_sum = pp.raoult_dew_sum(T7, P7, {k: v / tot5 for k, v in n5.items()})
    if dew_sum >= 1.0:
        warn = True
        msgs.append(f"COOLER outlet below the (Raoult) dew point of NH3/H2O (sum={dew_sum:.3f}); condensation "
                    "is not modelled - stream treated as vapour")
    streams["S7"] = _stream("S7", "PSA feed", "COOLER", "PSA", n5, T7, P7, H7, "vapor", 1.0)
    blocks["COOLER"] = BlockResult(id="COOLER", name="Cracked-gas cooler", block_type="Heater", duty_kW=Q_cool,
                                   outlet_temperature_C=T7 - K0, outlet_pressure_bar=P7,
                                   details={"raoult_dew_sum": dew_sum})

    # ------------------------------------------------------------ PSA
    frac = {"NH3": 0.0, "H2": inputs.psa_h2_recovery, "N2": inputs.psa_n2_slip, "H2O": 0.0, "O2": 0.0}
    n_prod = {c: n5[c] * frac[c] for c in COMPONENTS}
    n_tail = {c: n5[c] - n_prod[c] for c in COMPONENTS}
    P_prod = _p("H2PROD", P)
    P_tail = _p("TAILGAS", P)
    H_prod = gasH(n_prod, T7, P_prod)
    H_tail = gasH(n_tail, T7, P_tail)
    Q_psa = H_prod + H_tail - H7
    streams["H2PROD"] = _stream("H2PROD", "Hydrogen product", "PSA", None, n_prod, T7, P_prod, H_prod, "vapor", 1.0)
    streams["TAILGAS"] = _stream("TAILGAS", "PSA tail gas (N2-rich off-gas)", "PSA", "BURNER", n_tail, T7, P_tail,
                                 H_tail, "vapor", 1.0)
    blocks["PSA"] = BlockResult(id="PSA", name="Hydrogen purification (reduced-order PSA)", block_type="Sep",
                                duty_kW=Q_psa, outlet_temperature_C=T7 - K0, outlet_pressure_bar=P_prod,
                                details={"h2_recovery": inputs.psa_h2_recovery, "n2_slip": inputs.psa_n2_slip})

    # ------------------------------------------------------------ BURNER
    lam = 1.0 + inputs.burner_excess_air
    o2_stoich = 0.5 * n_tail["H2"] + 0.75 * n_tail["NH3"]
    n_air_tot = o2_stoich * lam / AIR_O2
    n_air = {"N2": n_air_tot * AIR_N2, "O2": n_air_tot * AIR_O2}
    T_air = AIR_T_C + K0
    P_air = _p("AIR", P)
    H_air = gasH(n_air, T_air, P_air)
    streams["AIR"] = _stream("AIR", "Combustion air", None, "BURNER", n_air, T_air, P_air, H_air, "vapor", 1.0)
    n_flue = {
        "NH3": 0.0, "H2": 0.0,
        "N2": n_tail["N2"] + n_air["N2"] + 0.5 * n_tail["NH3"],
        "H2O": n_tail["H2O"] + n_tail["H2"] + 1.5 * n_tail["NH3"],
        "O2": n_tail["O2"] + n_air["O2"] - o2_stoich,
    }
    P_b = _p("BURNER", P)
    H_flue = H_tail + H_air  # adiabatic
    T_ad = pp.solve_T_for_enthalpy(lambda T: gasH(n_flue, T, P_b), H_flue, 250.0, 3500.0)
    streams["FLUE"] = _stream("FLUE", "Hot flue gas", "BURNER", "FLUEHX", n_flue, T_ad, P_b, H_flue, "vapor", 1.0)
    blocks["BURNER"] = BlockResult(id="BURNER", name="Tail-gas burner", block_type="RStoic", duty_kW=0.0,
                                   outlet_temperature_C=T_ad - K0, outlet_pressure_bar=P_b,
                                   details={"adiabatic_flame_temperature_C": T_ad - K0,
                                            "air_kmol_h": n_air_tot, "excess_air": inputs.burner_excess_air})

    # ------------------------------------------------------------ FLUEHX
    P_s = _p("FLUEHX_out", P)
    T_s = inputs.stack_temperature_C + K0
    H_stack = gasH(n_flue, T_s, P_s)
    Q_flue = H_stack - H_flue
    flue_heated = T_ad <= T_s
    if flue_heated:
        warn = True
        msgs.append("adiabatic flame temperature below the stack temperature: FLUEHX heats the flue gas "
                    "(no combustion credit; the positive FLUEHX duty counts as external heating, amcrax.kpis)")
    streams["STACK"] = _stream("STACK", "Stack gas", "FLUEHX", None, n_flue, T_s, P_s, H_stack, "vapor", 1.0)
    blocks["FLUEHX"] = BlockResult(id="FLUEHX", name="Flue-gas heat recovery", block_type="Heater", duty_kW=Q_flue,
                                   outlet_temperature_C=T_s - K0, outlet_pressure_bar=P_s,
                                   details={"flame_below_stack_temperature": "yes" if flue_heated else "no",
                                            "signed_heat_released_kW": -Q_flue})

    # ------------------------------------------------------------ KPIs and balances
    # One definition for every result source: amcrax.kpis (also applied to the Aspen results). The previous
    # Python-only KPI block differed when the flame temperature is below the stack temperature.
    kpis = compute_kpis(streams, blocks)
    # overall balances FEED+AIR -> H2PROD+STACK; every block except the internal FEHE exchanges heat/work with the
    # surroundings. For this model the energy closure is zero by construction (each block duty is H_out - H_in);
    # it checks the bookkeeping (stream/block mapping, signs), not physics.
    bal = compute_balances(streams, blocks)

    notes = [
        "Independent AmCraX Python process model (amcrax.process_model); NOT an Aspen Plus result.",
        f"Cracker equilibrium eos={eos}; gas enthalpies NASA-7 ideal gas"
        + (" + Peng-Robinson residual" if eos == "pr" else "") + " (formation-enthalpy reference, 298.15 K).",
        "Liquid/vaporising NH3 from CoolProp (Gao et al. JPCRD 2020 EOS) anchored to NASA ideal gas at 298.15 K, 1 Pa.",
        "Feed-section VLE by Raoult's law (ideal NH3-H2O liquid): ASSUMPTION; Aspen PENG-ROB dew point may differ.",
        f"Pump efficiency {PUMP_EFFICIENCY} (ASSUMPTION). PSA is a reduced-order component splitter.",
    ]
    status = RunStatus(converged=True, has_errors=False, has_warnings=warn, messages=msgs,
                       engine_time_s=time.perf_counter() - t_start)
    return SimulationResult(case_id=inputs.case_id, source=DataSource.PYTHON, model_file="amcrax.process_model",
                            inputs=inputs, status=status, streams=streams, blocks=blocks, kpis=kpis,
                            balances=bal, notes=notes)
