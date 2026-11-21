"""Pd-Ag membrane H2 separator: Sieverts/Richardson flux integrated along membrane area (reduced-order model).

Flux (richard2024technoeconomic pp. 6-7, Eqs. 1-2):
    J_H2 = m * (Pe/delta) * (p_H2,ret**n - p_H2,perm**n),  Pe = Pe0 exp(-Ea/(R T)),  p in Pa, n = 0.5
    m = flux multiplier (1.0 = ideal Sieverts; concentration-polarisation factor optional, see yaml).
Separator: isothermal, isobaric (no pressure drop - assumption), plug flow on the retentate side.
Permeate is pure H2 (infinite selectivity, richard2024technoeconomic p. 7), so p_H2,perm = P_perm
everywhere and co-current and counter-current arrangements give the same result. NH3, N2, H2O stay
in the retentate (no reaction in the separator). Back-permeation is not allowed (J >= 0).
    d n_H2,ret / dA = -J(A)
Hydrogen recovery factor HRF = H2_perm / (H2_perm + H2_ret) (maccarrone2025comprehensive p. 23, Table 6).
"""
from __future__ import annotations

import math
from typing import Optional

import numpy as np
from pydantic import BaseModel, Field
from scipy.integrate import solve_ivp

from amcrax.schemas import LHV_KJ_PER_MOL, MOLAR_MASS
from amcrax.thermodynamics import R_J_molK

from .params import MODEL_LABEL, cite, params, permeability_set


class MembraneProfilePoint(BaseModel):
    area_m2: float
    h2_retentate_kmol_h: float
    y_h2_retentate: float
    flux_mol_m2_s: float
    recovery: float


class MembraneResult(BaseModel):
    model: str = MODEL_LABEL
    permeability_set: str
    permeability_source: str
    T_K: float
    feed_pressure_bar: float
    permeate_pressure_bar: float
    area_m2: float
    n_exponent: float
    flux_multiplier: float
    permeance_mol_m2_s_Pa_n: float
    feed_kmol_h: dict[str, float]
    permeate_kmol_h: dict[str, float]
    retentate_kmol_h: dict[str, float]
    retentate_mole_frac: dict[str, float]
    h2_recovery: float
    max_recovery_at_pinch: float
    h2_purity_mole_frac: float
    purity_basis: str
    product_h2_kg_h: float
    h2_loss_kmol_h: float
    h2_loss_lhv_kW: float
    in_pd_window: bool
    profile: list[MembraneProfilePoint] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)


def permeance(T_K: float, set_id: str | None = None, thickness_m: float | None = None) -> float:
    """Pe/delta, mol m-2 s-1 Pa-n."""
    s = permeability_set(set_id)
    d = thickness_m if thickness_m is not None else s["thickness_um"] * 1e-6
    Pe = s["Pe0_mol_m_s_Pa05"] * math.exp(-s["Ea_kJ_mol"] * 1000.0 / (R_J_molK * T_K))
    return Pe / d


def sieverts_flux(pH2_ret_Pa: float, pH2_perm_Pa: float, permeance_val: float, n: float = 0.5,
                  multiplier: float = 1.0) -> float:
    """H2 flux, mol m-2 s-1 (no back-permeation)."""
    return max(0.0, multiplier * permeance_val * (max(pH2_ret_Pa, 0.0) ** n - max(pH2_perm_Pa, 0.0) ** n))


def membrane_separator(feed_kmol_h: dict[str, float], area_m2: float, feed_pressure_bar: float,
                       permeate_pressure_bar: float | None = None, T_K: float | None = None, *,
                       permeability: str | None = None, thickness_m: float | None = None,
                       n_exponent: float | None = None, flux_multiplier: float = 1.0,
                       n_profile: int = 41) -> MembraneResult:
    M = params()["membrane"]
    if T_K is None:
        T_K = M["default_temperature_C"]["value"] + 273.15
    if permeate_pressure_bar is None:
        permeate_pressure_bar = M["default_permeate_pressure_bar"]["value"]
    n = M["flux_law"]["n"] if n_exponent is None else n_exponent
    if area_m2 < 0:
        raise ValueError("area must be >= 0")
    pset = permeability_set(permeability)
    k = permeance(T_K, permeability, thickness_m)
    feed = {s: float(v) for s, v in feed_kmol_h.items() if v}
    others = sum(v for s, v in feed.items() if s != "H2")
    h2_in = feed.get("H2", 0.0) / 3.6  # mol/s
    P_ret = feed_pressure_bar * 1e5
    P_perm = permeate_pressure_bar * 1e5
    oth = others / 3.6

    def flux(nh2: float) -> float:
        y = nh2 / (nh2 + oth) if nh2 + oth > 0 else 0.0
        return sieverts_flux(y * P_ret, P_perm, k, n, flux_multiplier)

    def rhs(_A, x):
        return [-flux(max(x[0], 0.0))]

    grid = np.linspace(0.0, area_m2, max(n_profile, 2))
    if area_m2 > 0 and h2_in > 0:
        sol = solve_ivp(rhs, (0.0, area_m2), [h2_in], t_eval=grid, method="LSODA", rtol=1e-10, atol=1e-12)
        nh2 = np.maximum(sol.y[0], 0.0)
    else:
        nh2 = np.full_like(grid, h2_in)
    prof = []
    for A, x in zip(grid, nh2):
        y = x / (x + oth) if x + oth > 0 else 0.0
        prof.append(MembraneProfilePoint(area_m2=float(A), h2_retentate_kmol_h=float(x * 3.6), y_h2_retentate=float(y),
                                         flux_mol_m2_s=flux(float(x)), recovery=float(1 - x / h2_in) if h2_in else 0.0))
    h2_out = float(nh2[-1]) * 3.6
    h2_perm = feed.get("H2", 0.0) - h2_out
    ret = dict(feed)
    ret["H2"] = h2_out
    rtot = sum(ret.values())
    # pinch: y_H2 * P_ret = P_perm  ->  n_H2 = y/(1-y) * others
    y_p = P_perm / P_ret
    if y_p >= 1:
        rmax = 0.0
    else:
        nh2_p = y_p / (1 - y_p) * oth
        rmax = max(0.0, 1 - nh2_p / h2_in) if h2_in else 0.0
    T_C = T_K - 273.15
    win = M["operating_window_C"]
    notes = [f"{MODEL_LABEL}: isothermal, isobaric plug flow, ideal Sieverts flux, pure-H2 permeate",
             f"permeability {pset['id']}: Pe0 {pset['Pe0_mol_m_s_Pa05']:g} mol/(m s Pa^0.5), Ea {pset['Ea_kJ_mol']} kJ/mol, "
             f"{(thickness_m or pset['thickness_um'] * 1e-6) * 1e6:g} um ({cite(pset)})"]
    in_win = win["min"] <= T_C <= win["max"]
    if not in_win:
        notes.append(f"WARNING: {T_C:.0f} degC outside Pd window {win['min']}-{win['max']} degC ({cite(win)})")
    if flux_multiplier != 1.0:
        notes.append(f"flux multiplier {flux_multiplier} applied (concentration-polarisation sensitivity)")
    return MembraneResult(
        permeability_set=pset["id"], permeability_source=cite(pset), T_K=T_K, feed_pressure_bar=feed_pressure_bar,
        permeate_pressure_bar=permeate_pressure_bar, area_m2=area_m2, n_exponent=n, flux_multiplier=flux_multiplier,
        permeance_mol_m2_s_Pa_n=k, feed_kmol_h=feed, permeate_kmol_h={"H2": h2_perm}, retentate_kmol_h=ret,
        retentate_mole_frac={s: v / rtot for s, v in ret.items()} if rtot > 0 else {},
        h2_recovery=h2_perm / feed["H2"] if feed.get("H2") else 0.0, max_recovery_at_pinch=rmax,
        h2_purity_mole_frac=1.0,
        purity_basis="infinite selectivity assumed (richard2024technoeconomic p. 7); measured Pd-Ag in NH3 service "
                     ">99.999 % H2, NH3 < 0.01 ppm (cechetto2023membrane pp. 15, 17, Tables 8, 10)",
        product_h2_kg_h=h2_perm * MOLAR_MASS["H2"], h2_loss_kmol_h=h2_out,
        h2_loss_lhv_kW=h2_out * LHV_KJ_PER_MOL["H2"] / 3.6, in_pd_window=in_win, profile=prof, notes=notes,
    )


def area_for_recovery(feed_kmol_h: dict[str, float], target_recovery: float, feed_pressure_bar: float,
                      permeate_pressure_bar: float | None = None, T_K: float | None = None, **kw) -> Optional[float]:
    """Membrane area (m2) that reaches target_recovery, or None if above the pinch limit."""
    from scipy.optimize import brentq

    r0 = membrane_separator(feed_kmol_h, 0.0, feed_pressure_bar, permeate_pressure_bar, T_K, **kw)
    if target_recovery >= r0.max_recovery_at_pinch:
        return None
    hi = 10.0
    while membrane_separator(feed_kmol_h, hi, feed_pressure_bar, permeate_pressure_bar, T_K, n_profile=2,
                             **kw).h2_recovery < target_recovery:
        hi *= 2
        if hi > 1e7:
            return None
    return brentq(lambda A: membrane_separator(feed_kmol_h, A, feed_pressure_bar, permeate_pressure_bar, T_K,
                                               n_profile=2, **kw).h2_recovery - target_recovery, 0.0, hi, xtol=1e-6)
