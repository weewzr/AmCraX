"""Property basis of the AmCraX Python process model.

Enthalpy reference (identical for every stream): elements in their standard state at
298.15 K are zero, so species enthalpies include the enthalpy of formation. This is the
reference of :func:`amcrax.thermodynamics.species_enthalpy_kJ_mol` (NASA-7 polynomials,
GRI-Mech 3.0 data, see ``amcrax/data/nasa7.json``). Aspen Plus also uses a
formation-enthalpy reference (ideal gas elements at 25 degC), so enthalpy flows are
comparable to within the property-model differences.

Gas section (S4 onward, and every stream that contains H2/N2):
    ideal-gas NASA enthalpy (``eos="ideal"``), optionally plus the Peng-Robinson residual
    enthalpy of :mod:`amcrax.thermodynamics.peng_robinson` (``eos="pr"``).

FEHE cold side (S2 -> S3), both eos modes: NASA ideal-gas enthalpy + NH3 residual enthalpy of the
reference EOS (:func:`feed_gas_enthalpy_kW`), so that the FEHE energy balance and its T-Q profile are
on one real-gas basis (see :mod:`amcrax.process_model.flowsheet`).

Ammonia-rich feed section (FEED, S1, S2): ammonia from CoolProp, i.e. the reference
Helmholtz-energy equation of state of Gao et al., J. Phys. Chem. Ref. Data 2020
(CoolProp key ``Gao-JPCRD-2020``), which is needed for the liquid and the vaporisation.

Anchoring (makes CoolProp and NASA enthalpies one consistent scale):
    h_NH3(T, P) = h_CP(T, P) - h_CP(T0, P_low) + h_NASA(T0)
    T0 = 298.15 K, P_low = 1 Pa (1e-5 bar). At 1 Pa ammonia is an ideal gas to < 1e-5 kJ/mol,
    so the anchor matches the two scales at an ideal-gas state; at other low-pressure states
    the two scales then differ only by the (small) difference of their ideal-gas cp
    integrals, which ``tests/test_process_model.py`` checks.

Water (0.2 mol% of the liquid feed) - documented simplification:
    * vapour: ideal-gas NASA H2O (no residual enthalpy; 0.2 mol%).
    * liquid (dissolved in liquid NH3): h_L(T) = h_NASA,ig(T0) - dh_vap(T0) + cp_L(T0) (T - T0),
      with dh_vap and cp_L of pure liquid water at T0 = 298.15 K from CoolProp (IAPWS-95,
      Wagner & Pruss, JPCRD 2002). The linear extrapolation to the feed temperature (-33 degC,
      below the water triple point) treats the water as a sub-cooled liquid component;
      ideal solution, no NH3-H2O heat of mixing (ASSUMPTION: the real heat of solution of
      0.2 mol% water is ~0.2 % of the vaporiser duty).
    * phase equilibrium of the feed section: Raoult's law with CoolProp pure-component vapour
      pressures (ASSUMPTION: ideal liquid; Aspen PENG-ROB computes a non-ideal NH3-H2O VLE, so
      the vaporiser dew point - and hence S2 temperature - can differ by a few kelvin).
      Bubble point: x_NH3 Psat_NH3(T) = P (water volatility at -33 degC is negligible).
      Dew point:   sum_i y_i P / Psat_i(T) = 1.
"""
from __future__ import annotations

import math
import threading
from functools import lru_cache

import CoolProp.CoolProp as CP
from scipy.optimize import brentq

from amcrax.thermodynamics import mixture_enthalpy_kW, species_enthalpy_kJ_mol

T0_K = 298.15
P_LOW_PA = 1.0
NH3_FLUID = "Ammonia"
WATER_FLUID = "Water"


@lru_cache(maxsize=None)
def nh3_anchor_offset_kJ_mol() -> float:
    """Offset added to CoolProp molar enthalpy of NH3 to put it on the NASA formation scale."""
    h_cp = CP.PropsSI("Hmolar", "T", T0_K, "P", P_LOW_PA, NH3_FLUID) / 1000.0
    return species_enthalpy_kJ_mol("NH3", T0_K) - h_cp


_TLS = threading.local()


def _nh3_state(phase: str):
    """Per-thread CoolProp HEOS state for NH3 with an imposed phase (AbstractState is not thread-safe).

    Re-using the state is ~9x faster than creating one per call and gives bit-identical results
    (checked on 2782 random (T, P) gas states, 2026-11-21): with an imposed phase the PT update does not
    depend on the previous state."""
    cache = getattr(_TLS, "states", None)
    if cache is None:
        cache = _TLS.states = {}
    st = cache.get(phase)
    if st is None:
        st = CP.AbstractState("HEOS", NH3_FLUID)
        st.specify_phase(CP.iphase_liquid if phase == "liquid" else CP.iphase_gas)
        cache[phase] = st
    return st


def nh3_enthalpy_kJ_mol(T_K: float, P_bar: float, phase: str) -> float:
    """NH3 molar enthalpy (CoolProp, anchored) in the specified phase ('liquid' | 'gas')."""
    st = _nh3_state("liquid" if phase == "liquid" else "gas")
    st.update(CP.PT_INPUTS, P_bar * 1e5, T_K)
    return st.hmolar() / 1000.0 + nh3_anchor_offset_kJ_mol()


def nh3_liquid_molar_volume_m3_mol(T_K: float, P_bar: float) -> float:
    st = _nh3_state("liquid")
    st.update(CP.PT_INPUTS, P_bar * 1e5, T_K)
    return 1.0 / st.rhomolar()


@lru_cache(maxsize=None)
def _water_liquid_params() -> tuple[float, float]:
    hv = CP.PropsSI("Hmolar", "T", T0_K, "Q", 1, WATER_FLUID)
    hl = CP.PropsSI("Hmolar", "T", T0_K, "Q", 0, WATER_FLUID)
    cpl = CP.PropsSI("Cpmolar", "T", T0_K, "Q", 0, WATER_FLUID)
    return (hv - hl) / 1000.0, cpl / 1000.0


def water_liquid_enthalpy_kJ_mol(T_K: float) -> float:
    dh_vap, cp_l = _water_liquid_params()
    return species_enthalpy_kJ_mol("H2O", T0_K) - dh_vap + cp_l * (T_K - T0_K)


def psat_nh3_bar(T_K: float) -> float:
    return CP.PropsSI("P", "T", T_K, "Q", 0, NH3_FLUID) / 1e5


def psat_water_bar(T_K: float) -> float:
    return CP.PropsSI("P", "T", T_K, "Q", 0, WATER_FLUID) / 1e5


def bubble_point_K(P_bar: float, x_nh3: float) -> float:
    """Raoult bubble point of the NH3/H2O feed (water vapour pressure neglected)."""
    return CP.PropsSI("T", "P", P_bar * 1e5 / x_nh3, "Q", 0, NH3_FLUID)


def dew_point_K(P_bar: float, y: dict[str, float]) -> float:
    """Raoult dew point of an NH3/H2O vapour: sum_i y_i P / Psat_i(T) = 1."""
    y_n, y_w = y.get("NH3", 0.0), y.get("H2O", 0.0)
    t_sat_n = CP.PropsSI("T", "P", P_bar * 1e5, "Q", 1, NH3_FLUID)
    if y_w <= 0:
        return t_sat_n
    t_crit_n = CP.PropsSI("Tcrit", NH3_FLUID)

    def f(T):
        s = y_w * P_bar / psat_water_bar(T)
        if y_n > 0:
            s += y_n * P_bar / psat_nh3_bar(min(T, t_crit_n - 1e-6))
        return s - 1.0

    return brentq(f, t_sat_n - 1e-9, 640.0, xtol=1e-10)


def raoult_dew_sum(T_K: float, P_bar: float, y: dict[str, float]) -> float:
    """sum_i y_i P / Psat_i(T) over the condensables NH3, H2O (< 1: no condensate, ideal VLE)."""
    s = 0.0
    if y.get("H2O", 0.0) > 0 and T_K < 647.0:
        s += y["H2O"] * P_bar / psat_water_bar(T_K)
    if y.get("NH3", 0.0) > 0 and T_K < 405.0:
        s += y["NH3"] * P_bar / psat_nh3_bar(T_K)
    return s


# ------------------------------------------------------------------ stream enthalpy flows (kW)
def feed_section_enthalpy_kW(n_kmol_h: dict[str, float], T_K: float, P_bar: float, phase: str) -> float:
    """Enthalpy flow of an NH3/H2O stream of the feed section ('liquid' or 'gas')."""
    h = 0.0  # kJ/mol * kmol/h = MJ/h
    for s, n in n_kmol_h.items():
        if n == 0:
            continue
        if s == "NH3":
            h += n * nh3_enthalpy_kJ_mol(T_K, P_bar, phase)
        elif s == "H2O":
            h += n * (water_liquid_enthalpy_kJ_mol(T_K) if phase == "liquid" else species_enthalpy_kJ_mol("H2O", T_K))
        else:
            raise ValueError(f"feed-section property basis supports NH3/H2O only, got {s}")
    return h * 1000.0 / 3600.0


def nh3_residual_enthalpy_kJ_mol(T_K: float, P_bar: float) -> float:
    """Residual (real minus ideal-gas) molar enthalpy of NH3 vapour from the reference EOS (CoolProp HEOS).

    The Gao et al. (2020) EOS is valid to 725 K; above that the residual part is extrapolated. The residual
    is small there (-0.09 kJ/mol at 1000 K / 20.5 bar, -0.36 kJ/mol at 1000 K / 80.5 bar) and differs from
    the Peng-Robinson departure by < 0.06 kJ/mol up to 1268 K and 80 bar (checked 2026-11-21).
    """
    st = _nh3_state("gas")
    st.update(CP.PT_INPUTS, P_bar * 1e5, T_K)
    return st.hmolar_residual() / 1000.0


def feed_gas_enthalpy_kW(n_kmol_h: dict[str, float], T_K: float, P_bar: float) -> float:
    """Real-gas enthalpy flow of the ammonia feed vapour (FEHE cold side S2 -> S3), kW.

    NH3: NASA-7 ideal-gas enthalpy (the scale of every gas-section stream) + reference-EOS residual enthalpy
    (:func:`nh3_residual_enthalpy_kJ_mol`). H2O (0.2 mol%): ideal-gas NASA-7, as in
    :func:`feed_section_enthalpy_kW` (documented simplification). Used in both eos modes so that the FEHE
    energy balance and its internal T-Q profile are on one real-gas basis.
    """
    h = 0.0
    for s, n in n_kmol_h.items():
        if n == 0:
            continue
        if s == "NH3":
            h += n * (species_enthalpy_kJ_mol("NH3", T_K) + nh3_residual_enthalpy_kJ_mol(T_K, P_bar))
        elif s == "H2O":
            h += n * species_enthalpy_kJ_mol("H2O", T_K)
        else:
            raise ValueError(f"feed-gas property basis supports NH3/H2O only, got {s}")
    return h * 1000.0 / 3600.0


def gas_enthalpy_kW(n_kmol_h: dict[str, float], T_K: float, P_bar: float, eos: str = "ideal") -> float:
    """Gas-section enthalpy flow: NASA ideal gas (+ PR residual if eos='pr')."""
    n = {s: v for s, v in n_kmol_h.items() if v > 0}
    if not n:
        return 0.0
    return mixture_enthalpy_kW(n, T_K, P_bar=P_bar, eos=eos)


def solve_T_for_enthalpy(h_fun, H_target_kW: float, T_lo: float, T_hi: float) -> float:
    """Temperature at which h_fun(T) = H_target (h_fun increasing in T)."""
    return brentq(lambda T: h_fun(T) - H_target_kW, T_lo, T_hi, xtol=1e-10, rtol=1e-14, maxiter=200)
