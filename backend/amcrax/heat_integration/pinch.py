"""Generic problem-table algorithm (Linnhoff) for piecewise-linear H-T streams.

Every stream is a monotone piecewise-linear curve of cumulative heat content ``H_kW``
versus temperature ``T_K`` (H increasing with T, starting at 0 at the stream's cold end),
so non-constant heat capacities and phase changes are represented exactly by their
breakpoints. Hot streams release heat from their supply (hot end) to their target (cold end);
cold streams absorb heat from supply (cold end) to target (hot end).

The method: shift hot temperatures down and cold temperatures up by dT_min/2, take every
shifted breakpoint as an interval boundary, compute the heat deficit of each interval
(cold demand - hot supply), cascade it from the top, and add the smallest hot utility that
keeps every cascaded heat flow non-negative (Linnhoff et al. 1982 problem-table algorithm).
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

#: Width (K) used to represent an isothermal duty (pure-component phase change, isothermal
#: reactor) as a steep linear segment. Numerical device only; 0.01 K is far below any dT_min.
ISOTHERMAL_WIDTH_K = 0.01


@dataclass
class Curve:
    """Piecewise-linear stream; ``T_K`` strictly increasing, ``H_kW`` non-decreasing from 0."""

    id: str
    kind: str  # "hot" | "cold"
    T_K: np.ndarray
    H_kW: np.ndarray
    name: str = ""
    meta: dict = field(default_factory=dict)

    @property
    def duty_kW(self) -> float:
        return float(self.H_kW[-1] - self.H_kW[0])

    @property
    def T_min_K(self) -> float:
        return float(self.T_K[0])

    @property
    def T_max_K(self) -> float:
        return float(self.T_K[-1])

    def H_at(self, T_K: float) -> float:
        return float(np.interp(T_K, self.T_K, self.H_kW))

    def T_at(self, H_kW: float) -> float:
        return float(np.interp(H_kW, self.H_kW, self.T_K))

    def slice(self, T_lo_K: float, T_hi_K: float, id: str | None = None, kind: str | None = None) -> "Curve":
        lo, hi = max(T_lo_K, self.T_min_K), min(T_hi_K, self.T_max_K)
        if hi <= lo:
            raise ValueError(f"empty slice of {self.id}: [{T_lo_K}, {T_hi_K}]")
        inner = (self.T_K > lo) & (self.T_K < hi)
        T = np.concatenate([[lo], self.T_K[inner], [hi]])
        H = np.array([self.H_at(t) for t in T])
        return Curve(id or self.id, kind or self.kind, T, H - H[0], self.name, dict(self.meta))


def make_curve(id: str, kind: str, T_K, H_kW, name: str = "", meta: dict | None = None) -> Curve:
    """Build a Curve from (T, H) points in any order; equal temperatures are spread by ISOTHERMAL_WIDTH_K."""
    T = np.asarray(T_K, dtype=float)
    H = np.asarray(H_kW, dtype=float)
    order = np.lexsort((H, T))
    T, H = T[order].copy(), H[order].copy()
    for i in range(1, len(T)):
        if T[i] <= T[i - 1]:
            T[i] = T[i - 1] + ISOTHERMAL_WIDTH_K
    if np.any(np.diff(H) < -1e-9):
        raise ValueError(f"stream {id}: enthalpy must increase with temperature")
    return Curve(id, kind, T, H - H[0], name, meta or {})


def linear_curve(id: str, kind: str, T_a_K: float, T_b_K: float, CP_kW_K: float | None = None,
                 duty_kW: float | None = None, name: str = "") -> Curve:
    """Constant-CP stream between two temperatures (or an isothermal duty when T_a == T_b)."""
    lo, hi = sorted((T_a_K, T_b_K))
    Q = duty_kW if duty_kW is not None else CP_kW_K * (hi - lo)
    return make_curve(id, kind, [lo, hi], [0.0, Q], name)


@dataclass
class PinchResult:
    dT_min_K: float
    hot_utility_kW: float
    cold_utility_kW: float
    pinch_shifted_K: float | None
    threshold: bool
    boundaries_shifted_K: np.ndarray        # descending
    interval_deficit_kW: np.ndarray          # per interval (cold - hot)
    cascade_kW: np.ndarray                   # heat flow at each boundary incl. hot utility (GCC)
    hot_composite: tuple[np.ndarray, np.ndarray]   # (H_kW, T_K) ascending
    cold_composite: tuple[np.ndarray, np.ndarray]  # (H_kW, T_K) ascending, shifted by cold utility
    total_hot_kW: float
    total_cold_kW: float

    @property
    def pinch_hot_K(self) -> float | None:
        return None if self.pinch_shifted_K is None else self.pinch_shifted_K + self.dT_min_K / 2

    @property
    def pinch_cold_K(self) -> float | None:
        return None if self.pinch_shifted_K is None else self.pinch_shifted_K - self.dT_min_K / 2


def _heat_in_interval(c: Curve, lo: float, hi: float) -> float:
    a, b = max(lo, c.T_min_K), min(hi, c.T_max_K)
    return 0.0 if b <= a else c.H_at(b) - c.H_at(a)


def _shift(c: Curve, dT: float) -> Curve:
    s = -dT / 2 if c.kind == "hot" else dT / 2
    return Curve(c.id, c.kind, c.T_K + s, c.H_kW, c.name)


def composite(curves: list[Curve]) -> tuple[np.ndarray, np.ndarray]:
    """Composite curve of same-kind streams: (cumulative H_kW, T_K), both ascending."""
    if not curves:
        return np.array([0.0]), np.array([np.nan])
    T = np.unique(np.concatenate([c.T_K for c in curves]))
    H = np.zeros_like(T)
    for i in range(1, len(T)):
        H[i] = H[i - 1] + sum(_heat_in_interval(c, T[i - 1], T[i]) for c in curves)
    return H, T


def problem_table(curves: list[Curve], dT_min_K: float, tol_kW: float = 1e-6) -> PinchResult:
    if dT_min_K < 0:
        raise ValueError("dT_min_K must be >= 0")
    hot = [c for c in curves if c.kind == "hot"]
    cold = [c for c in curves if c.kind == "cold"]
    shifted = [_shift(c, dT_min_K) for c in curves]
    bounds = np.unique(np.concatenate([c.T_K for c in shifted]))[::-1]
    deficit = np.array([
        sum(_heat_in_interval(c, lo, hi) for c in shifted if c.kind == "cold")
        - sum(_heat_in_interval(c, lo, hi) for c in shifted if c.kind == "hot")
        for hi, lo in zip(bounds[:-1], bounds[1:])
    ])
    raw = np.concatenate([[0.0], -np.cumsum(deficit)])
    Qh = max(0.0, -float(raw.min()))
    casc = raw + Qh
    Qc = float(casc[-1])
    total_hot = sum(c.duty_kW for c in hot)
    total_cold = sum(c.duty_kW for c in cold)
    # pinch: boundary where cascaded heat is zero (strictly inside the temperature range)
    zero = np.where(casc <= tol_kW * max(1.0, total_hot + total_cold))[0]
    inner = [i for i in zero if 0 < i < len(casc) - 1]
    threshold = Qh <= tol_kW or Qc <= tol_kW
    pinch = None
    if inner:
        pinch = float(bounds[inner[0]])
    elif zero.size and not threshold:
        pinch = float(bounds[zero[0]])
    Hh, Th = composite(hot)
    Hc, Tc = composite(cold)
    return PinchResult(dT_min_K, Qh, Qc, pinch, bool(threshold and not inner), bounds, deficit, casc,
                       (Hh, Th), (Hc + Qc, Tc), total_hot, total_cold)
