"""1-D pseudo-homogeneous packed-bed plug-flow reactor for NH3 cracking.

Independent variable: catalyst mass W [kg]. State: conversion X of the NH3 fed, T [K], P [bar], residence time.

    dX/dW   = r(T, p_i) / F_NH3,0                                      [r: mol NH3 kg_cat^-1 s^-1]
    dT/dW   = [ -dH_r(T) r + U (4/D_t) (T_wall - T) / rho_bed ] / sum_i F_i cp_i(T)
              (isothermal: 0;  adiabatic: U = 0;  externally heated: wall temperature + overall U)
    dP/dW   = (dP/dz)_Ergun / (rho_bed A_total)
    dtau/dW = eps_b / (rho_bed Q_actual)

Molar flows follow from X (single net reaction NH3 -> 0.5 N2 + 1.5 H2; H2O/Ar inert), so the N and H element
balances hold by construction (checked in tests). Ideal-gas cp and reaction enthalpy come from
:mod:`amcrax.thermodynamics` (NASA7, GRI-Mech 3.0). Gas viscosity for Ergun is Cantera's mixture-averaged
viscosity with GRI-Mech 3.0 transport data (smith_grimech30 / goodwin2018cantera).

Neglected effects (this is NOT a full-fidelity reactor model):
* intraparticle diffusion (effectiveness factor = 1; the Takahashi rates were measured on 22-42 mesh powder
  free of diffusion limits, so pellet-scale rates in a real bed would be lower);
* external (film) heat and mass transfer, i.e. catalyst surface = bulk gas conditions;
* radial temperature/concentration gradients (Kum et al. needed a 2-D model to capture these in fired tubes);
* axial dispersion and conduction;
* catalyst deactivation, non-ideal gas behaviour in the energy balance, and wall/flue-gas dynamics;
* kinetics extrapolated beyond their fitted P/T range (see CatalystModel.validity) - results at 20 bar are
  model extrapolations and are labelled ``python_model``.

Numerical assumption: the Temkin-Pyzhev law is singular at p_H2 = 0, so a pure-NH3 feed starts at X0 = 1e-6
(``x_seed``); the catalyst mass this corresponds to is negligible (checked: result insensitive to x_seed).
"""
from __future__ import annotations

import math
from dataclasses import asdict, dataclass, field
from functools import lru_cache
from typing import Any

import numpy as np
from scipy.integrate import solve_ivp

from amcrax.kinetics import get_catalyst, rate_mol_per_kgcat_s
from amcrax.thermodynamics import (
    R_J_molK,
    equilibrium_constant,
    mixture_enthalpy_kW,
    reaction_enthalpy_kJ_mol,
    solve_equilibrium,
    species_cp_J_molK,
)

KMOLH_TO_MOLS = 1000.0 / 3600.0
MOLAR_MASS_kg_mol = {"NH3": 0.017031, "H2": 0.002016, "N2": 0.028014, "H2O": 0.018015, "Ar": 0.039948}
NORMAL_T_K = 273.15        # GHSV "normal" basis: 0 degC, 1 atm (stated convention, not a sourced value)
NORMAL_P_Pa = 101325.0

# Bed defaults (kum2026heatintegrated Table 1, p. 5; Ru/Al2O3 beads). Used for the Takahashi powders too
# (assumption: no bed data in takahashi2016kinetic) - always pass explicit values for a real design.
DEFAULT_BED = {
    "eps_b": 0.36,
    "rho_particle_kg_m3": 980.0,
    "dp_m": 0.0006,
    "tube_inner_diameter_m": 0.126,
}
DEFAULT_BED_SOURCE = "kum2026heatintegrated p. 5 Table 1 (eps_b, rho_cat, dp, Din); rho_bed = (1-eps_b)*rho_cat as in Kum Table 2"
BASELINE_FEED_kmol_h = {"NH3": 99.8, "H2O": 0.2}   # config/flowsheet.json basis: 100 kmol/h, 99.8/0.2 mol%


@lru_cache(maxsize=1)
def _ct_gas():
    import cantera as ct  # local import: only needed for viscosity
    return ct.Solution("gri30.yaml")


def gas_viscosity_Pa_s(T_K: float, P_bar: float, y: dict[str, float]) -> float:
    gas = _ct_gas()
    X = {k: max(v, 0.0) for k, v in y.items() if k != "Ar"}
    if y.get("Ar", 0.0) > 0:
        X["AR"] = y["Ar"]
    gas.TPX = T_K, P_bar * 1e5, X
    return float(gas.viscosity)


@dataclass
class PFRResult:
    catalyst_id: str
    mode: str
    W_kg: list[float]
    conversion: list[float]
    T_K: list[float]
    P_bar: list[float]
    y: dict[str, list[float]]
    rate_mol_per_kgcat_s: list[float]
    X_eq_local: list[float]
    approach_to_equilibrium: list[float]       # X / X_eq(T, P local)
    Q_over_K: list[float]
    residence_time_s: list[float]
    outlet: dict[str, Any]
    W_over_F_kg_s_per_mol_NH3: float
    GHSV_h_inv: float                          # normal (0 degC, 1 atm) volumetric feed / bed volume
    bed_volume_m3: float
    inputs: dict[str, Any]
    assumptions: list[str] = field(default_factory=list)
    source: str = "python_model"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _flows(X: float, F_feed: dict[str, float]) -> dict[str, float]:
    F0 = F_feed["NH3"]
    F = dict(F_feed)
    F["NH3"] = F0 * (1.0 - X)
    F["N2"] = F_feed.get("N2", 0.0) + 0.5 * F0 * X
    F["H2"] = F_feed.get("H2", 0.0) + 1.5 * F0 * X
    return F


def _cp_species(s: str, T: float) -> float:
    if s == "Ar":
        return 20.786  # monatomic ideal gas 5/2 R (exact for ideal gas)
    return species_cp_J_molK(s, T)


def _eq_conversion(T_K: float, P_bar: float, feed: dict[str, float]) -> float:
    """Ideal-gas equilibrium conversion. Ar (not in the thermo species set) is passed as an equal amount of
    inert O2; exact for the ideal-gas equilibrium, where an inert enters only through the total mole number."""
    f = {k: v for k, v in feed.items() if k != "Ar"}
    if feed.get("Ar", 0.0) > 0:
        f["O2"] = f.get("O2", 0.0) + feed["Ar"]
    return solve_equilibrium(T_K, P_bar, f).conversion


def _enthalpy_kW(n_kmol_h: dict[str, float], T_K: float) -> float:
    h = mixture_enthalpy_kW({k: v for k, v in n_kmol_h.items() if k != "Ar"}, T_K)
    return h + n_kmol_h.get("Ar", 0.0) * 20.786e-3 * (T_K - 298.15) / 3.6  # kmol/h * kJ/mol -> kW


def simulate_pfr(
    catalyst_id: str,
    W_kg: float,
    *,
    T_in_C: float = 600.0,
    P_in_bar: float = 20.0,
    feed_kmol_h: dict[str, float] | None = None,
    mode: str = "isothermal",
    T_wall_C: float | None = None,
    U_W_m2K: float | None = None,
    eps_b: float = DEFAULT_BED["eps_b"],
    rho_particle_kg_m3: float = DEFAULT_BED["rho_particle_kg_m3"],
    dp_m: float = DEFAULT_BED["dp_m"],
    tube_inner_diameter_m: float = DEFAULT_BED["tube_inner_diameter_m"],
    n_tubes: int = 1,
    pressure_drop: bool = True,
    approach_factor: bool | None = None,
    keq_basis: str = "amcrax_thermo",
    x_seed: float = 1e-6,
    n_points: int = 201,
    rtol: float = 1e-8,
    atol: float = 1e-12,
) -> PFRResult:
    """Integrate the packed-bed PFR from W = 0 to W_kg (total catalyst over all n_tubes).

    mode: 'isothermal' | 'adiabatic' | 'external' (needs T_wall_C and U_W_m2K).
    keq_basis (Kum model only): default 'amcrax_thermo' so the rate vanishes exactly at the equilibrium of
    amcrax.thermodynamics used for the approach-to-equilibrium output; 'published' uses Kum Eq. 4.
    """
    if mode not in ("isothermal", "adiabatic", "external"):
        raise ValueError("mode must be isothermal | adiabatic | external")
    if mode == "external" and (T_wall_C is None or U_W_m2K is None):
        raise ValueError("external mode requires T_wall_C and U_W_m2K")
    cat = get_catalyst(catalyst_id)
    feed = dict(feed_kmol_h or BASELINE_FEED_kmol_h)
    F_feed = {k: v * KMOLH_TO_MOLS for k, v in feed.items() if v > 0}
    for s in ("N2", "H2"):
        F_feed.setdefault(s, 0.0)
    F0 = F_feed["NH3"]
    m_dot = sum(F_feed[s] * MOLAR_MASS_kg_mol[s] for s in F_feed)
    rho_bed = (1.0 - eps_b) * rho_particle_kg_m3
    A_tot = n_tubes * math.pi * tube_inner_diameter_m**2 / 4.0
    G = m_dot / A_tot
    T_in = T_in_C + 273.15
    T_w = (T_wall_C + 273.15) if T_wall_C is not None else None
    assumptions: list[str] = []
    X0 = 0.0
    if cat.form == "temkin_pyzhev" and F_feed["H2"] <= 0.0:
        X0 = x_seed
        assumptions.append(f"numerical: H2 seed, integration starts at X0={x_seed:g} (rate singular at p_H2=0)")
    if cat.form == "takahashi_microkinetic":
        on = True if approach_factor is None else approach_factor
        assumptions.append(f"AmCraX extension: equilibrium approach factor (1-Q/K) {'ON' if on else 'OFF'}")
    if cat.form == "lhhw_lucentini":
        on = True if approach_factor is None else approach_factor
        assumptions.append(f"AmCraX extension: equilibrium approach factor (1-Q/K) {'ON' if on else 'OFF'} (Lucentini LHHW)")
    if cat.form == "temkin_pyzhev":
        assumptions.append(f"Kum Keq basis: {keq_basis}")
    assumptions.append("bed: " + DEFAULT_BED_SOURCE + (" (defaults used)" if (eps_b, rho_particle_kg_m3, dp_m) ==
                       (DEFAULT_BED["eps_b"], DEFAULT_BED["rho_particle_kg_m3"], DEFAULT_BED["dp_m"]) else " (user values)"))
    assumptions.append("effectiveness factor = 1; no radial gradients; no axial dispersion (see module docstring)")

    def state(Xv, T, P):
        F = _flows(Xv, F_feed)
        Ft = sum(F.values())
        y = {s: F[s] / Ft for s in F}
        return F, Ft, y

    def rate(Xv, T, P):
        _, _, y = state(Xv, T, P)
        p = {s: y[s] * P for s in y}
        return rate_mol_per_kgcat_s(catalyst_id, T, p, approach_factor=approach_factor, keq_basis=keq_basis)

    def rhs(W, u):
        Xv, T, P, _tau = u
        Xv = min(max(Xv, 0.0), 1.0 - 1e-15)
        F, Ft, y = state(Xv, T, P)
        p = {s: y[s] * P for s in y}
        if cat.form == "temkin_pyzhev" and p["H2"] <= 0:
            p["H2"] = 1e-300
        r = rate_mol_per_kgcat_s(catalyst_id, T, p, approach_factor=approach_factor, keq_basis=keq_basis)
        dX = r / F0
        if mode == "isothermal":
            dT = 0.0
        else:
            Fcp = sum(F[s] * _cp_species(s, T) for s in F)
            q = -reaction_enthalpy_kJ_mol(T) * 1e3 * r
            if mode == "external":
                q += U_W_m2K * (4.0 / tube_inner_diameter_m) * (T_w - T) / rho_bed
            dT = q / Fcp
        if pressure_drop:
            M = sum(y[s] * MOLAR_MASS_kg_mol[s] for s in y)
            rho_g = P * 1e5 * M / (R_J_molK * T)
            mu = gas_viscosity_Pa_s(T, P, y)
            dPdz = -(G / (rho_g * dp_m)) * ((1 - eps_b) / eps_b**3) * (150.0 * (1 - eps_b) * mu / dp_m + 1.75 * G)
            dP = dPdz / (rho_bed * A_tot) / 1e5
        else:
            dP = 0.0
        Q = Ft * R_J_molK * T / (P * 1e5)
        dtau = eps_b / (rho_bed * Q)
        return [dX, dT, dP, dtau]

    def low_p(W, u):
        return u[2] - 0.05 * P_in_bar
    low_p.terminal = True

    W_eval = np.linspace(0.0, W_kg, n_points)
    sol = solve_ivp(rhs, (0.0, W_kg), [X0, T_in, P_in_bar, 0.0], method="LSODA", t_eval=W_eval,
                    rtol=rtol, atol=atol, events=low_p)
    if sol.status < 0:
        raise RuntimeError(f"PFR integration failed: {sol.message}")
    Ws = np.asarray(sol.t, dtype=float)
    Ys = np.asarray(sol.y, dtype=float)
    hydraulic_limit = bool(sol.status == 1 and len(sol.t_events) and len(sol.t_events[0]))
    if hydraulic_limit:
        # The terminal event fires between t_eval points: the integration stops at W_stop, but sol.t/sol.y hold only
        # the t_eval points before it. Append the event state so the profile and the outlet end at the stop.
        W_stop = float(sol.t_events[0][0])
        y_stop = np.asarray(sol.y_events[0][0], dtype=float)
        if Ws.size == 0 or W_stop > Ws[-1]:
            Ws = np.append(Ws, W_stop)
            Ys = np.column_stack([Ys, y_stop]) if Ys.size else y_stop.reshape(-1, 1)
        assumptions.append(f"integration stopped (hydraulic limit): pressure fell to 5 % of inlet at W = {W_stop:.6g} kg "
                           f"of the requested {W_kg:g} kg (bed too long/narrow); outlet = state at the stop")
    Xs, Ts, Ps, taus = Ys
    ys = {s: [] for s in F_feed}
    rates, Xeq, appr, qk = [], [], [], []
    for Xv, T, P in zip(Xs, Ts, Ps):
        Xv = float(min(max(Xv, 0.0), 1.0))
        _, _, y = state(Xv, T, P)
        for s in ys:
            ys[s].append(y[s])
        rates.append(rate(Xv, T, P) if not (cat.form == "temkin_pyzhev" and y["H2"] <= 0) else float("nan"))
        eq = _eq_conversion(float(T), float(P), feed)
        Xeq.append(eq)
        appr.append(Xv / eq if eq > 0 else float("nan"))
        p = {s: y[s] * P for s in y}
        Qv = (p["N2"] ** 0.5 * p["H2"] ** 1.5 / p["NH3"]) if p["NH3"] > 0 else float("inf")
        qk.append(Qv / equilibrium_constant(float(T)))

    V_bed = W_kg / rho_bed
    Fn_tot = sum(F_feed.values())
    Q_normal = Fn_tot * R_J_molK * NORMAL_T_K / NORMAL_P_Pa      # m3/s at 0 degC, 1 atm
    outlet = {
        "conversion": float(Xs[-1]), "T_C": float(Ts[-1] - 273.15), "P_bar": float(Ps[-1]),
        "pressure_drop_bar": float(P_in_bar - Ps[-1]), "X_eq_outlet": Xeq[-1], "approach_to_equilibrium": appr[-1],
        "y": {s: ys[s][-1] for s in ys},
        "flows_kmol_h": {s: v / KMOLH_TO_MOLS for s, v in _flows(float(Xs[-1]), F_feed).items()},
        "H2_kmol_h": _flows(float(Xs[-1]), F_feed)["H2"] / KMOLH_TO_MOLS,
        "heat_input_kW": None, "residence_time_s": float(taus[-1]), "W_reached_kg": float(Ws[-1]),
        "W_requested_kg": float(W_kg), "hydraulic_limit": hydraulic_limit,
    }
    # heat added = outlet minus inlet ideal-gas enthalpy flow (kW, > 0 = heat added; ~0 for adiabatic)
    Fout = {s: v / KMOLH_TO_MOLS for s, v in _flows(float(Xs[-1]), F_feed).items()}
    Fin = {s: v / KMOLH_TO_MOLS for s, v in F_feed.items()}
    outlet["heat_input_kW"] = float(_enthalpy_kW(Fout, float(Ts[-1])) - _enthalpy_kW(Fin, T_in))
    return PFRResult(
        catalyst_id=catalyst_id, mode=mode, W_kg=Ws.tolist(), conversion=Xs.tolist(), T_K=Ts.tolist(),
        P_bar=Ps.tolist(), y=ys, rate_mol_per_kgcat_s=rates, X_eq_local=Xeq, approach_to_equilibrium=appr,
        Q_over_K=qk, residence_time_s=taus.tolist(), outlet=outlet,
        W_over_F_kg_s_per_mol_NH3=W_kg / F0, GHSV_h_inv=Q_normal * 3600.0 / V_bed if V_bed > 0 else float("inf"),
        bed_volume_m3=V_bed,
        inputs={"T_in_C": T_in_C, "P_in_bar": P_in_bar, "feed_kmol_h": feed, "mode": mode, "T_wall_C": T_wall_C,
                "U_W_m2K": U_W_m2K, "eps_b": eps_b, "rho_particle_kg_m3": rho_particle_kg_m3,
                "rho_bed_kg_m3": rho_bed, "dp_m": dp_m, "tube_inner_diameter_m": tube_inner_diameter_m,
                "n_tubes": n_tubes, "pressure_drop": pressure_drop, "approach_factor": approach_factor,
                "keq_basis": keq_basis, "W_kg": W_kg},
        assumptions=assumptions,
    )


def catalyst_mass_for_conversion(
    catalyst_id: str,
    target_conversion: float | None = None,
    *,
    fraction_of_equilibrium: float | None = None,
    W_max_kg: float = 1e6,
    return_details: bool = False,
    **kw,
) -> float | dict[str, Any]:
    """Catalyst mass [kg] at which conversion first reaches the target.

    Give either an absolute ``target_conversion`` or ``fraction_of_equilibrium`` (times X_eq at inlet T, P;
    for isothermal operation). Extra keyword arguments go to :func:`simulate_pfr`.

    The trial mass grows geometrically (x4, last trial clamped to ``W_max_kg``). A trial that hits the hydraulic
    limit (pressure below 5 % of inlet) is evaluated at the stop (``outlet['W_reached_kg']``): the bed beyond it
    does not exist, so if the target is reached before the stop the crossing is refined between the last
    sub-target mass and ``W_reached_kg``; otherwise the target is unreachable.

    Returns ``nan`` if the target is not reached (within ``W_max_kg`` or before the hydraulic stop); a
    ``RuntimeWarning`` states the reason. With ``return_details=True`` a dict is returned instead:
    ``{"W_kg", "reachable", "reason", "target_conversion", "hydraulic_limit", "W_reached_kg", "X_reached"}``.
    """
    if (target_conversion is None) == (fraction_of_equilibrium is None):
        raise ValueError("give exactly one of target_conversion / fraction_of_equilibrium")
    if fraction_of_equilibrium is not None:
        feed = kw.get("feed_kmol_h") or BASELINE_FEED_kmol_h
        Xe = _eq_conversion(kw.get("T_in_C", 600.0) + 273.15, kw.get("P_in_bar", 20.0), feed)
        target_conversion = fraction_of_equilibrium * Xe
    kw.pop("n_points", None)
    from scipy.optimize import brentq

    def out(W, reason=None, hyd=False, W_reached=None, X_reached=None):
        if reason is not None and not return_details:
            import warnings
            warnings.warn(f"catalyst_mass_for_conversion({catalyst_id}): {reason}", RuntimeWarning, stacklevel=3)
        if not return_details:
            return float(W)
        return {"W_kg": float(W), "reachable": reason is None, "reason": reason,
                "target_conversion": float(target_conversion), "hydraulic_limit": hyd,
                "W_reached_kg": W_reached, "X_reached": X_reached}

    def outlet(w):
        return simulate_pfr(catalyst_id, w, n_points=2, **kw).outlet

    # 1) bracket: geometric growth, last trial clamped to W_max_kg
    W = min(1e-3, W_max_kg)
    lo = 0.0
    while True:
        o = outlet(W)
        if o.get("hydraulic_limit"):
            W_r, X_r = float(o["W_reached_kg"]), float(o["conversion"])
            if X_r < target_conversion:
                return out(float("nan"), f"target X = {target_conversion:.6g} not reached before the hydraulic limit "
                           f"(pressure < 5 % of inlet at W = {W_r:.6g} kg, X = {X_r:.6g} there)",
                           hyd=True, W_reached=W_r, X_reached=X_r)
            W = W_r          # the target lies on the existing bed, before the stop
            break
        if o["conversion"] >= target_conversion:
            break
        lo = W
        if W >= W_max_kg:
            return out(float("nan"), f"target X = {target_conversion:.6g} not reached within W_max_kg = {W_max_kg:g} kg "
                       f"(X = {o['conversion']:.6g} there)", W_reached=float(o["W_reached_kg"]),
                       X_reached=float(o["conversion"]))
        W = min(4.0 * W, W_max_kg)

    # 2) refine the crossing with brentq (f is evaluated below the stop, so no event fires inside the bracket)
    def f(w):
        return outlet(w)["conversion"] - target_conversion
    if lo == 0.0:
        lo = 1e-9
        if f(lo) >= 0:
            return out(lo)
    f_hi = f(W)
    if f_hi < 0:
        # target equals the conversion at the hydraulic stop to within integrator tolerance
        return out(W)
    return out(brentq(f, lo, W, xtol=1e-6 * W, rtol=1e-6))
