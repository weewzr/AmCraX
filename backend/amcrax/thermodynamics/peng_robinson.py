"""Peng-Robinson (1976) cubic EOS for gas mixtures: fugacity coefficients, enthalpy departure, dew point.

Source of equations: D.-Y. Peng, D.B. Robinson, Ind. Eng. Chem. Fundam. 15 (1976) 59-64, eqs. 2-6,
fugacity coefficient eq. 15 (van der Waals one-fluid mixing rules,
a_ij = sqrt(a_i a_j) (1 - k_ij), a_m = sum_ij y_i y_j a_ij, b_m = sum_i y_i b_i). Optional Boston-Mathias
alpha extrapolation above Tc (Boston & Mathias, Proc. 2nd Int. Conf. Phase Equilibria and Fluid Properties
in the Chemical Process Industries, 1980), which Aspen Plus PENG-ROB applies to supercritical
components (Aspen Physical Property System - Physical Property Methods documentation, "Peng-Robinson").

Critical constants / acentric factors: ``backend/amcrax/data/critical_properties.json`` (CoolProp).

Binary interaction parameters
-----------------------------
``kij`` is ``None`` (all k_ij = 0, the AmCraX default: ASSUMPTION - no sourced values collected; Aspen
may use non-zero databank PRKBV values, which is a known source of model difference) or a mapping
keyed by species pairs, order-insensitive, e.g. ``{("NH3", "H2"): 0.0, ("H2O", "NH3"): -0.25}``.
Pairs that are not given are 0; a pair given twice with different values is an error. Pairs that
name a known species absent from the mixture are ignored (they cannot contribute).

Species order and zero mole fractions
-------------------------------------
Arrays are always assembled in the fixed order of :data:`amcrax.schemas.COMPONENTS` (never in the
iteration order of a set or of the caller's dict), so results do not depend on ``PYTHONHASHSEED``.
The k_ij matrix is built once over *all* species of the mixture, including those with zero mole
fraction. A species with y_i = 0 contributes exactly zero to the mixing sums a_m, b_m, so the sums
are evaluated over the non-zero entries (bit-for-bit identical to the previous implementation when
``kij is None``); its fugacity coefficient is the infinite-dilution limit of eq. 15, evaluated with
the same mixture and with (1 - k_ij) applied:
    ln phi_i^inf = b_i/b_m (Z-1) - ln(Z-B) - A/(2 sqrt2 B) (2 sum_j y_j sqrt(a_i a_j)(1-k_ij)/a_m - b_i/b_m) ln[...].
"""
from __future__ import annotations

import json
import math
from collections.abc import Mapping
from functools import lru_cache
from pathlib import Path

import numpy as np

from amcrax.schemas import COMPONENTS

from .nasa7 import R_J_molK

DATA_FILE = Path(__file__).resolve().parents[1] / "data" / "critical_properties.json"
SQRT2 = math.sqrt(2.0)


@lru_cache(maxsize=1)
def critical_properties() -> dict[str, dict]:
    return json.loads(DATA_FILE.read_text(encoding="utf-8"))["species"]


def ordered_species(names) -> list[str]:
    """``names`` in the fixed :data:`COMPONENTS` order (KeyError for a species without PR constants)."""
    names = list(dict.fromkeys(names))
    cp = critical_properties()
    for s in names:
        if s not in cp:
            raise KeyError(f"no Peng-Robinson constants for species {s!r}; available: {sorted(cp)}")
    rank = {s: i for i, s in enumerate(COMPONENTS)}
    return sorted(names, key=lambda s: (rank.get(s, len(rank)), s))


def _alpha(T_K: float, Tc: float, omega: float, alpha: str) -> float:
    m = 0.37464 + 1.54226 * omega - 0.26992 * omega**2
    Tr = T_K / Tc
    if alpha == "boston-mathias" and Tr > 1.0:
        d = 1.0 + m / 2.0
        c = 1.0 - 1.0 / d
        return math.exp(2.0 * c * (1.0 - Tr**d))
    return (1.0 + m * (1.0 - math.sqrt(Tr))) ** 2


def _pure_params(species: list[str], T_K: float, alpha: str) -> tuple[np.ndarray, np.ndarray]:
    cp = critical_properties()
    a = np.empty(len(species))
    b = np.empty(len(species))
    for i, s in enumerate(species):
        Tc = cp[s]["Tc_K"]
        Pc = cp[s]["Pc_bar"] * 1e5
        a[i] = 0.45724 * R_J_molK**2 * Tc**2 / Pc * _alpha(T_K, Tc, cp[s]["omega"], alpha)
        b[i] = 0.07780 * R_J_molK * Tc / Pc
    return a, b


def _mix(y: np.ndarray, a: np.ndarray, b: np.ndarray, kij: np.ndarray):
    aij = np.sqrt(np.outer(a, a)) * (1.0 - kij)
    return float(y @ aij @ y), float(y @ b), aij


def _z_root(A: float, B: float, phase: str = "vapour") -> float:
    # Z^3 - (1-B) Z^2 + (A - 3B^2 - 2B) Z - (AB - B^2 - B^3) = 0 ; vapour: largest real root, liquid: smallest
    roots = np.roots([1.0, -(1.0 - B), A - 3 * B**2 - 2 * B, -(A * B - B**2 - B**3)])
    real = roots[np.abs(roots.imag) < 1e-10].real
    real = real[real > B]
    if real.size == 0:
        raise RuntimeError(f"Peng-Robinson: no physical {phase} root")
    if phase == "vapour":
        return float(real.max())
    if phase == "liquid":
        return float(real.min())
    raise ValueError("phase must be 'vapour' or 'liquid'")


def _z_vapour(A: float, B: float) -> float:
    return _z_root(A, B, "vapour")


def _pair(key) -> tuple[str, str]:
    if isinstance(key, str) or not hasattr(key, "__iter__"):
        raise TypeError(f"kij key {key!r} must be a pair of species names, e.g. ('NH3', 'H2')")
    p = tuple(key)
    if len(p) != 2 or not all(isinstance(s, str) for s in p):
        raise TypeError(f"kij key {key!r} must be a pair of species names, e.g. ('NH3', 'H2')")
    if p[0] == p[1]:
        raise ValueError(f"kij key {key!r}: k_ii is not a parameter (must be two different species)")
    return p


def normalise_kij(kij) -> dict[frozenset, float]:
    """Validate ``kij`` (None or {pair: value}) and return {frozenset(pair): value} (order-insensitive)."""
    if kij is None:
        return {}
    if not isinstance(kij, Mapping):
        raise TypeError("kij must be None or a mapping {(species_i, species_j): k_ij}; positional matrices are "
                        "not accepted because their species order would be ambiguous")
    cp = critical_properties()
    out: dict[frozenset, float] = {}
    for key, val in kij.items():
        a, b = _pair(key)
        for s in (a, b):
            if s not in cp:
                raise KeyError(f"kij key {key!r}: unknown species {s!r}")
        v = float(val)
        if not math.isfinite(v):
            raise ValueError(f"kij[{key!r}] = {val!r} is not finite")
        fk = frozenset((a, b))
        if fk in out and out[fk] != v:
            raise ValueError(f"kij pair {a}-{b} given twice with different values ({out[fk]} and {v})")
        out[fk] = v
    return out


def kij_matrix(species: list[str], kij) -> np.ndarray:
    """Symmetric k_ij matrix for ``species`` (in that order) from None or a pair mapping."""
    n = len(species)
    K = np.zeros((n, n))
    pairs = normalise_kij(kij)
    if not pairs:
        return K
    idx = {s: i for i, s in enumerate(species)}
    for fk, v in pairs.items():
        a, b = tuple(fk)
        if a in idx and b in idx:
            K[idx[a], idx[b]] = K[idx[b], idx[a]] = v
    return K


def _prepare(y: dict[str, float], T_K: float, alpha: str, kij):
    sp = ordered_species(y)
    yall = np.array([float(y[s]) for s in sp])
    if np.any(yall < 0) or not np.all(np.isfinite(yall)):
        raise ValueError(f"mole fractions must be finite and >= 0: {y}")
    nz = np.flatnonzero(yall > 0.0)
    if nz.size == 0:
        return sp, None
    K = kij_matrix(sp, kij)
    a_all, b_all = _pure_params(sp, T_K, alpha)
    yv = yall[nz]
    yv = yv / yv.sum()
    return sp, (nz, yv, a_all, b_all, K)


def fugacity_coefficients(y: dict[str, float], T_K: float, P_bar: float, *, kij=None,
                          alpha: str = "standard", phase: str = "vapour") -> dict[str, float]:
    """Fugacity coefficients phi_i of a mixture of mole fractions ``y`` (vapour or liquid root)."""
    sp, prep = _prepare(y, T_K, alpha, kij)
    if prep is None:
        return {s: 1.0 for s in sp}
    nz, yv, a_all, b_all, K = prep
    a, b = a_all[nz], b_all[nz]
    am, bm, aij = _mix(yv, a, b, K[np.ix_(nz, nz)])
    P = P_bar * 1e5
    RT = R_J_molK * T_K
    A = am * P / RT**2
    B = bm * P / RT
    Z = _z_root(A, B, phase)
    lg = math.log((Z + (1 + SQRT2) * B) / (Z + (1 - SQRT2) * B))
    sum_a = aij @ yv
    pos = {int(i): k for k, i in enumerate(nz)}
    out = {}
    for i, s in enumerate(sp):
        if i in pos:
            k = pos[i]
            bi, sa = b[k], sum_a[k]
        else:  # zero mole fraction: infinite-dilution limit in the same mixture, (1 - k_ij) applied
            bi = b_all[i]
            sa = float((np.sqrt(a_all[i] * a) * (1.0 - K[i, nz])) @ yv)
        ln_phi = (bi / bm) * (Z - 1) - math.log(Z - B) - A / (2 * SQRT2 * B) * (2 * sa / am - bi / bm) * lg
        out[s] = math.exp(ln_phi)
    return out


def compressibility(y: dict[str, float], T_K: float, P_bar: float, *, kij=None, alpha: str = "standard",
                    phase: str = "vapour") -> float:
    sp, prep = _prepare(y, T_K, alpha, kij)
    if prep is None:
        raise ValueError("all mole fractions are zero")
    nz, yv, a_all, b_all, K = prep
    am, bm, _ = _mix(yv, a_all[nz], b_all[nz], K[np.ix_(nz, nz)])
    RT = R_J_molK * T_K
    return _z_root(am * P_bar * 1e5 / RT**2, bm * P_bar * 1e5 / RT, phase)


def enthalpy_departure_J_mol(y: dict[str, float], T_K: float, P_bar: float, *, kij=None,
                             alpha: str = "standard", phase: str = "vapour") -> float:
    """H - H_ideal-gas of the mixture (J/mol):  RT(Z-1) + (T da/dT - a)/(2 sqrt2 b) ln[(Z+(1+sqrt2)B)/(Z+(1-sqrt2)B)]."""
    sp, prep = _prepare(y, T_K, alpha, kij)
    if prep is None:
        raise ValueError("all mole fractions are zero")
    nz, yv, _, _, K = prep
    sub = [sp[i] for i in nz]
    k = K[np.ix_(nz, nz)]

    def amix(T):
        a, b = _pure_params(sub, T, alpha)
        return _mix(yv, a, b, k)[:2]

    am, bm = amix(T_K)
    dT = 1e-3 * T_K
    dadT = (amix(T_K + dT)[0] - amix(T_K - dT)[0]) / (2 * dT)
    P = P_bar * 1e5
    RT = R_J_molK * T_K
    A = am * P / RT**2
    B = bm * P / RT
    Z = _z_root(A, B, phase)
    lg = math.log((Z + (1 + SQRT2) * B) / (Z + (1 - SQRT2) * B))
    return RT * (Z - 1) + (T_K * dadT - am) / (2 * SQRT2 * bm) * lg


# ------------------------------------------------------------------ vapour-liquid equilibrium
def _wilson_liquid(y: dict[str, float], T_K: float, P_bar: float) -> dict[str, float]:
    """Initial incipient-liquid estimate x_i ~ y_i / K_i with Wilson K-values (Wilson 1968 correlation)."""
    cp = critical_properties()
    w = {s: v / (cp[s]["Pc_bar"] / P_bar * math.exp(5.373 * (1 + cp[s]["omega"]) * (1 - cp[s]["Tc_K"] / T_K)))
         for s, v in y.items()}
    tot = sum(w.values())
    return {s: v / tot for s, v in w.items()}


def dew_liquid(y: dict[str, float], T_K: float, P_bar: float, *, kij=None, alpha: str = "standard",
               max_iter: int = 2000) -> tuple[dict[str, float], float]:
    """Incipient liquid x in equilibrium with vapour y at T, P, and S = sum_i y_i phi_i^V / phi_i^L(x).

    Successive substitution x_i = y_i phi_i^V / phi_i^L(x) / S from a Wilson estimate. S = 1 at the dew point,
    S > 1 below it (liquid favoured). Raises RuntimeError when the iteration collapses onto the trivial
    solution x = y (no distinct liquid root) or does not converge.
    """
    phiV = fugacity_coefficients(y, T_K, P_bar, kij=kij, alpha=alpha, phase="vapour")
    x = _wilson_liquid(y, T_K, P_bar)
    for _ in range(max_iter):
        phiL = fugacity_coefficients(x, T_K, P_bar, kij=kij, alpha=alpha, phase="liquid")
        w = {s: y[s] * phiV[s] / phiL[s] for s in y}
        S = sum(w.values())
        xn = {s: v / S for s, v in w.items()}
        if max(abs(xn[s] - x[s]) for s in y) < 1e-14:
            if max(abs(xn[s] - y[s]) for s in y) < 1e-8:
                raise RuntimeError("dew-point iteration converged to the trivial solution x = y")
            return xn, S
        x = xn
    raise RuntimeError("dew-point successive substitution did not converge")


def saturation_temperature_K(species: str, P_bar: float, *, alpha: str = "standard") -> float:
    """Pure-component PR saturation temperature at P_bar (phi^L = phi^V)."""
    from scipy.optimize import brentq

    Tc = critical_properties()[species]["Tc_K"]

    def g(T):
        y = {species: 1.0}
        return math.log(fugacity_coefficients(y, T, P_bar, alpha=alpha, phase="liquid")[species]
                        / fugacity_coefficients(y, T, P_bar, alpha=alpha, phase="vapour")[species])

    Ts = np.linspace(0.4 * Tc, Tc - 1e-6, 600)
    prev = None
    for T in Ts:
        v = g(T)
        if prev is not None and prev[1] < 0.0 < v:
            return brentq(g, prev[0], T, xtol=1e-11)
        if v != 0.0:  # v == 0 exactly: single real root (no distinct liquid), skip
            prev = (T, v)
    raise RuntimeError(f"PR saturation temperature of {species} at {P_bar} bar not bracketed")


def dew_point_K(P_bar: float, y: dict[str, float], *, kij=None, alpha: str = "standard",
                T_lo_K: float = 250.0, T_hi_K: float = 600.0) -> tuple[float, dict[str, float]]:
    """Peng-Robinson dew-point temperature of vapour ``y`` at ``P_bar`` and the incipient liquid composition.

    Solves S(T) = sum_i y_i phi_i^V(y) / phi_i^L(x) = 1 (see :func:`dew_liquid`) by a scan for the sign change of
    S - 1 followed by Brent's method. For a single component it returns the PR saturation temperature. Used for
    validation / VLE-model comparison only; the flowsheet uses Raoult's law (see amcrax.process_model.properties).
    """
    from scipy.optimize import brentq

    y = {s: v for s, v in y.items() if v > 0}
    tot = sum(y.values())
    y = {s: v / tot for s, v in y.items()}
    if len(y) == 1:
        (s,) = y
        return saturation_temperature_K(s, P_bar, alpha=alpha), {s: 1.0}

    def f(T):
        return dew_liquid(y, T, P_bar, kij=kij, alpha=alpha)[1] - 1.0

    prev = None
    for T in np.linspace(T_lo_K, T_hi_K, 351):
        try:
            v = f(T)
        except RuntimeError:
            prev = None
            continue
        if prev is not None and prev[1] > 0.0 > v:
            Td = brentq(f, prev[0], T, xtol=1e-9)
            return Td, dew_liquid(y, Td, P_bar, kij=kij, alpha=alpha)[0]
        prev = (T, v)
    raise RuntimeError("PR dew point not bracketed")
