"""Variance-based global sensitivity analysis (Sobol indices).

Estimators (A, B: independent N x d base samples; AB_i = A with column i, or a group of columns, taken from B):
    V     = var(concat(f(A), f(B)))
    S_i   = mean((f(B) - mu) * (f(AB_i) - f(A))) / V         Saltelli et al. (2010), Table 2 (b), on centred
            outputs, mu = mean(concat(f(A), f(B))) (fix pass 24 Nov 2026; the uncentred form had the same expectation
            but a larger variance)
    ST_i  = 0.5 * mean((f(A) - f(AB_i))**2) / V              Jansen (1999)
Bootstrap confidence intervals resample the N rows (A, B and every AB_i together).
"""
from __future__ import annotations

import math
from typing import Callable, Sequence

import numpy as np
from scipy.stats import qmc


def sobol_base(n: int, d: int, seed: int) -> tuple[np.ndarray, np.ndarray]:
    """Two N x d matrices in [0, 1) from one scrambled Sobol sequence of dimension 2d (A = first d, B = last d).
    Any prefix of length 2^m is itself a balanced Sobol set, which the convergence check uses."""
    m = int(round(math.log2(n)))
    if 2 ** m != n:
        raise ValueError("n must be a power of 2")
    u = qmc.Sobol(d=2 * d, scramble=True, seed=seed).random_base2(m)
    return u[:, :d], u[:, d:]


def ab_matrix(A: np.ndarray, B: np.ndarray, cols: Sequence[int]) -> np.ndarray:
    M = A.copy()
    M[:, list(cols)] = B[:, list(cols)]
    return M


def indices_from_outputs(fA: np.ndarray, fB: np.ndarray, fAB: np.ndarray) -> tuple[np.ndarray, np.ndarray, float]:
    """fAB: (k, N) outputs for k swap sets. Returns S (k,), ST (k,), V."""
    V = float(np.var(np.concatenate([fA, fB])))
    if V <= 0.0:
        return np.zeros(fAB.shape[0]), np.zeros(fAB.shape[0]), 0.0
    # Centred outputs (review C, finding m1): subtracting the mean leaves the estimator's expectation unchanged
    # (f(AB_i) - f(A) has zero mean) but removes the mean^2 x var term from its variance. ST uses only differences
    # and is unaffected.
    mu = float(np.mean(np.concatenate([fA, fB])))
    S = np.mean((fB[None, :] - mu) * (fAB - fA[None, :]), axis=1) / V
    ST = 0.5 * np.mean((fA[None, :] - fAB) ** 2, axis=1) / V
    return S, ST, V


def bootstrap_ci(fA: np.ndarray, fB: np.ndarray, fAB: np.ndarray, n_boot: int = 1000, seed: int = 20261123,
                 level: float = 0.95) -> tuple[np.ndarray, np.ndarray]:
    """Percentile bootstrap CIs of S and ST; returns arrays (k, 2) for S and ST."""
    rng = np.random.default_rng(seed)
    N = fA.size
    k = fAB.shape[0]
    Sb = np.empty((n_boot, k))
    STb = np.empty((n_boot, k))
    for b in range(n_boot):
        idx = rng.integers(0, N, N)
        Sb[b], STb[b], _ = indices_from_outputs(fA[idx], fB[idx], fAB[:, idx])
    a = (1.0 - level) / 2.0
    return (np.quantile(Sb, [a, 1 - a], axis=0).T, np.quantile(STb, [a, 1 - a], axis=0).T)


def sobol_indices(f: Callable[[np.ndarray], np.ndarray], to_x: Callable[[np.ndarray], np.ndarray], d: int, n: int,
                  seed: int, groups: dict[str, Sequence[int]] | None = None, n_boot: int = 1000) -> dict:
    """Full analysis: f maps an (N, d) array of physical inputs to (N,) or (N, m) outputs; to_x maps U(0,1) -> x."""
    A, B = sobol_base(n, d, seed)
    sets = [[i] for i in range(d)] + [list(g) for g in (groups or {}).values()]
    XA, XB = to_x(A), to_x(B)
    fA, fB = np.asarray(f(XA), float), np.asarray(f(XB), float)
    fAB = np.stack([np.asarray(f(to_x(ab_matrix(A, B, s))), float) for s in sets])
    return {"fA": fA, "fB": fB, "fAB": fAB, "sets": sets, "XA": XA}


# ------------------------------------------------------------------------------------------- test functions
def ishigami(x: np.ndarray, a: float = 7.0, b: float = 0.1) -> np.ndarray:
    """Ishigami and Homma (1990): f = sin x1 + a sin^2 x2 + b x3^4 sin x1, x_i ~ U(-pi, pi)."""
    return np.sin(x[:, 0]) + a * np.sin(x[:, 1]) ** 2 + b * x[:, 2] ** 4 * np.sin(x[:, 0])


def ishigami_analytic(a: float = 7.0, b: float = 0.1) -> dict:
    """Closed-form partial variances of the Ishigami function (e.g. Sobol' and Levitan 1999; Saltelli et al. 2010):
    V1 = 1/2 (1 + b pi^4/5)^2, V2 = a^2/8, V13 = b^2 pi^8 (1/18 - 1/50), V = V1 + V2 + V13."""
    pi = math.pi
    V1 = 0.5 * (1.0 + b * pi**4 / 5.0) ** 2
    V2 = a * a / 8.0
    V13 = b * b * pi**8 * (1.0 / 18.0 - 1.0 / 50.0)
    V = V1 + V2 + V13
    return {"V": V, "S": [V1 / V, V2 / V, 0.0], "ST": [(V1 + V13) / V, V2 / V, V13 / V]}
