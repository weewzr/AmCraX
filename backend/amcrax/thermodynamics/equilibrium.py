"""Single-reaction gas-phase equilibrium of ammonia decomposition.

Reaction basis (per mol NH3):   NH3 <-> 0.5 N2 + 1.5 H2
Equilibrium condition:  K(T) = prod_i (y_i phi_i P / P0)^nu_i,  P0 = 1 bar.
H2O (and O2, if present) are inert. Gas phase only (valid for the AmCraX range T >= 250 degC,
P <= 100 bar, where NH3 is supercritical: Tc = 405.6 K).

The unknown is z = ln(n_NH3,out); the residual is strictly monotone in z for an ideal gas, and
the bracket covers n_NH3 -> 0 (conversion -> 1) and the reverse limit (H2 or N2 exhausted),
so ``scipy.optimize.brentq`` always converges. Working in ln(n_NH3) keeps full relative precision
when conversion approaches 1 (e.g. 1 - X ~ 1e-6 at 900 degC, 1 bar).
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field

from scipy.optimize import brentq

from amcrax.schemas import COMPONENTS

from . import peng_robinson as pr
from .nasa7 import (
    R_J_molK,
    composition,
    species_enthalpy_kJ_mol,
    species_gibbs_kJ_mol,
    species_list,
)

NU: dict[str, float] = {"NH3": -1.0, "N2": 0.5, "H2": 1.5}
DN_GAS = sum(NU.values())  # +1


def reaction_enthalpy_kJ_mol(T_K: float) -> float:
    """Standard reaction enthalpy per mol NH3 decomposed (> 0, endothermic)."""
    return sum(nu * species_enthalpy_kJ_mol(s, T_K) for s, nu in NU.items())


def reaction_gibbs_kJ_mol(T_K: float) -> float:
    """Standard (1 bar) reaction Gibbs energy per mol NH3."""
    return sum(nu * species_gibbs_kJ_mol(s, T_K) for s, nu in NU.items())


def reaction_entropy_J_molK(T_K: float) -> float:
    return (reaction_enthalpy_kJ_mol(T_K) - reaction_gibbs_kJ_mol(T_K)) * 1000.0 / T_K


def equilibrium_constant(T_K: float) -> float:
    """Kp (standard state 1 bar) for NH3 <-> 0.5 N2 + 1.5 H2."""
    return math.exp(-reaction_gibbs_kJ_mol(T_K) * 1000.0 / (R_J_molK * T_K))


@dataclass
class EquilibriumResult:
    T_K: float
    P_bar: float
    eos: str
    conversion: float               # 1 - n_NH3,out / n_NH3,in  (nan if no NH3 in feed)
    extent: float                   # mol NH3 decomposed (same unit as n_feed); < 0 means net synthesis
    n_out: dict[str, float]
    y: dict[str, float]
    K_eq: float
    phi: dict[str, float] = field(default_factory=dict)
    residual: float = 0.0


def _ordered(names) -> list[str]:
    """Species in the fixed COMPONENTS order (others after them, alphabetically)."""
    rank = {s: i for i, s in enumerate(COMPONENTS)}
    return sorted(dict.fromkeys(names), key=lambda s: (rank.get(s, len(rank)), s))


def _state(z: float, n_feed: dict[str, float]):
    n_nh3_in = n_feed.get("NH3", 0.0)
    n_nh3 = math.exp(z)
    xi = n_nh3_in - n_nh3
    n = dict(n_feed)
    n["NH3"] = n_nh3
    n["N2"] = n_feed.get("N2", 0.0) + 0.5 * xi
    n["H2"] = n_feed.get("H2", 0.0) + 1.5 * xi
    return n, xi


def solve_equilibrium(T_K: float, P_bar: float, n_feed: dict[str, float], eos: str = "ideal",
                      *, kij=None, alpha: str = "standard") -> EquilibriumResult:
    """Equilibrium composition at T_K, P_bar for a feed of NH3/H2/N2 (+ inert H2O, O2).

    ``n_feed`` may be in any molar unit (mol, kmol/h ...); ``n_out`` is returned in the same unit.
    ``eos``: "ideal" (phi = 1) or "pr" (Peng-Robinson fugacity coefficients).
    ``kij``: None (all k_ij = 0, default) or {(species_i, species_j): k_ij}, order-insensitive (see
    :mod:`amcrax.thermodynamics.peng_robinson`); used only with eos="pr" but validated in both modes.
    Species are always processed in the fixed :data:`amcrax.schemas.COMPONENTS` order, so the result does not
    depend on PYTHONHASHSEED (the previous set-ordered implementation differed in the last bit between seeds).
    """
    eos = eos.lower()
    if eos not in ("ideal", "pr"):
        raise ValueError("eos must be 'ideal' or 'pr'")
    pr.normalise_kij(kij)  # raises for a malformed kij
    order = _ordered(species_list())
    known = set(order)
    for s, v in n_feed.items():
        if s not in known:
            raise KeyError(f"unknown species {s!r}")
        if v < 0:
            raise ValueError("negative feed flow")
    feed = {s: float(n_feed.get(s, 0.0)) for s in order if n_feed.get(s, 0.0) > 0 or s in NU}
    n_nh3_in = feed["NH3"]
    # maximum NH3 that can exist (all N2 or H2 consumed by synthesis)
    n_nh3_max = n_nh3_in + min(feed["N2"] / 0.5, feed["H2"] / 1.5)
    if n_nh3_max <= 0:
        raise ValueError("feed contains no NH3 and cannot form any (needs both H2 and N2)")
    lnK = -reaction_gibbs_kJ_mol(T_K) * 1000.0 / (R_J_molK * T_K)
    lnP = math.log(P_bar / 1.0)

    def phis(n):
        if eos == "ideal":
            return {s: 1.0 for s in n}
        tot = sum(n.values())
        return pr.fugacity_coefficients({s: v / tot for s, v in n.items()}, T_K, P_bar, kij=kij, alpha=alpha)

    def resid(z):
        n, _ = _state(z, feed)
        tot = sum(n.values())
        ph = phis(n)
        val = DN_GAS * lnP - lnK
        for s, nu in NU.items():
            val += nu * (math.log(max(n[s], 1e-300) / tot) + math.log(ph[s]))
        return val

    # Bracket: upper end = limiting product (H2 or N2) exhausted -> residual -> -inf (clipped at ln 1e-300);
    # lower end = n_NH3 ~ 1e-300 x scale -> residual ~ +690 > any |ln K - ln P| in the valid range.
    z_hi = math.log(n_nh3_max)
    z_lo = z_hi - 690.0
    f_lo, f_hi = resid(z_lo), resid(z_hi)
    if not (f_lo > 0 > f_hi):
        raise RuntimeError(f"equilibrium bracket failed: f({z_lo})={f_lo}, f({z_hi})={f_hi}")
    z = brentq(resid, z_lo, z_hi, xtol=1e-13, rtol=1e-15, maxiter=500)
    n, xi = _state(z, feed)
    tot = sum(n.values())
    y = {s: v / tot for s, v in n.items()}
    ph = phis(n)
    conv = (1.0 - n["NH3"] / n_nh3_in) if n_nh3_in > 0 else float("nan")
    # element balance check (N and H)
    for el in ("N", "H"):
        e_in = sum(v * composition(s).get(el, 0) for s, v in feed.items())
        e_out = sum(v * composition(s).get(el, 0) for s, v in n.items())
        if abs(e_in - e_out) > 1e-9 * max(e_in, 1e-30):
            raise RuntimeError(f"{el} balance violated: {e_in} vs {e_out}")
    return EquilibriumResult(T_K=T_K, P_bar=P_bar, eos=eos, conversion=conv, extent=xi, n_out=n, y=y,
                             K_eq=math.exp(lnK), phi=ph, residual=resid(z))


# ---------------------------------------------------------------- energy helpers
def mixture_enthalpy_kW(n_kmol_h: dict[str, float], T_K: float, *, P_bar: float | None = None,
                        eos: str = "ideal", kij=None, alpha: str = "standard") -> float:
    """Total enthalpy flow (formation-enthalpy reference: elements at 298.15 K = 0), kW.

    eos="ideal": ideal-gas enthalpy. eos="pr": adds the Peng-Robinson residual enthalpy (needs P_bar).
    """
    H = sum(v * species_enthalpy_kJ_mol(s, T_K) for s, v in n_kmol_h.items() if v)  # kJ/mol * kmol/h = MJ/h
    tot = sum(n_kmol_h.values())
    if eos.lower() == "pr" and tot > 0:
        if P_bar is None:
            raise ValueError("P_bar required for eos='pr'")
        y = {s: v / tot for s, v in n_kmol_h.items() if v > 0}
        H += tot * pr.enthalpy_departure_J_mol(y, T_K, P_bar, kij=kij, alpha=alpha) / 1000.0
    return H * 1000.0 / 3600.0  # MJ/h -> kW


def isothermal_reactor_duty_kW(n_in: dict[str, float], T_in_K: float, n_out: dict[str, float], T_out_K: float,
                               *, P_in_bar: float | None = None, P_out_bar: float | None = None,
                               eos: str = "ideal") -> float:
    """Reactor heat duty Q = H_out - H_in (kW, > 0 = heat added); flows in kmol/h."""
    return (mixture_enthalpy_kW(n_out, T_out_K, P_bar=P_out_bar, eos=eos)
            - mixture_enthalpy_kW(n_in, T_in_K, P_bar=P_in_bar, eos=eos))
