"""Adaptive Metropolis (Haario, Saksman and Tamminen 2001) and convergence diagnostics (Vehtari et al. 2021)."""
from __future__ import annotations

from typing import Callable

import numpy as np
from scipy.stats import norm, rankdata


def adaptive_metropolis(logp: Callable[[np.ndarray], float], x0: np.ndarray, n_iter: int, rng: np.random.Generator,
                        adapt_start: int = 1000, burn_in: int = 5000, cov0: np.ndarray | None = None,
                        eps: float = 1e-8) -> dict:
    """One chain. Proposal N(x, C): C = cov0 until ``adapt_start``; then C = 2.38^2/d * cov(history) + eps I,
    updated every iteration until ``burn_in`` and frozen afterwards (so the retained part is a plain Metropolis
    chain with a fixed proposal). Returns all states, log densities and the acceptance rate after burn-in."""
    x = np.asarray(x0, float).copy()
    d = x.size
    sd = 2.38 ** 2 / d
    C = np.eye(d) * 0.01 if cov0 is None else np.asarray(cov0, float)
    L = np.linalg.cholesky(C)
    lp = logp(x)
    chain = np.empty((n_iter, d))
    lps = np.empty(n_iter)
    acc = np.zeros(n_iter, bool)
    mean = x.copy()
    M2 = np.zeros((d, d))
    for t in range(n_iter):
        y = x + L @ rng.standard_normal(d)
        lq = logp(y)
        if np.log(rng.random()) < lq - lp:
            x, lp = y, lq
            acc[t] = True
        chain[t], lps[t] = x, lp
        # running mean / covariance (Welford)
        k = t + 1
        delta = x - mean
        mean = mean + delta / k
        M2 = M2 + np.outer(delta, x - mean)
        if adapt_start <= t < burn_in and k > 1:
            C = sd * (M2 / (k - 1)) + eps * np.eye(d)
            try:
                L = np.linalg.cholesky(C)
            except np.linalg.LinAlgError:
                pass
    return {"chain": chain, "logp": lps, "accept_rate": float(acc[burn_in:].mean()) if n_iter > burn_in else float(acc.mean())}


# ------------------------------------------------------------------------------------------- diagnostics
def _split(chains: np.ndarray) -> np.ndarray:
    m, n = chains.shape
    h = n // 2
    return np.vstack([chains[:, :h], chains[:, n - h:]])


def _rhat_basic(c: np.ndarray) -> float:
    m, n = c.shape
    W = c.var(axis=1, ddof=1).mean()
    B = n * c.mean(axis=1).var(ddof=1)
    var_plus = (n - 1) / n * W + B / n
    return float(np.sqrt(var_plus / W))


def _rank_normalise(c: np.ndarray) -> np.ndarray:
    r = rankdata(c.ravel()).reshape(c.shape)
    return norm.ppf((r - 3.0 / 8.0) / (c.size + 0.25))


def rhat(chains: np.ndarray) -> float:
    """Rank-normalised split R-hat (max of bulk and folded), chains: (m, n)."""
    s = _split(np.asarray(chains, float))
    bulk = _rhat_basic(_rank_normalise(s))
    tail = _rhat_basic(_rank_normalise(np.abs(s - np.median(s))))
    return max(bulk, tail)


def _ess_basic(c: np.ndarray) -> float:
    m, n = c.shape
    acov = np.empty((m, n))
    for j in range(m):
        x = c[j] - c[j].mean()
        f = np.fft.rfft(x, n=2 * n)
        acov[j] = np.fft.irfft(f * np.conj(f))[:n] / n
    W = c.var(axis=1, ddof=1).mean()
    var_plus = (n - 1) / n * W + n * c.mean(axis=1).var(ddof=1) / n if m > 1 else W
    rho = 1.0 - (W - acov.mean(axis=0)) / var_plus
    rho[0] = 1.0
    # Geyer initial monotone sequence
    tau, prev = -1.0, np.inf
    for t in range(0, n - 1, 2):
        p = rho[t] + rho[t + 1]
        if p < 0:
            break
        p = min(p, prev)
        prev = p
        tau += 2.0 * p
    return float(m * n / max(tau, 1e-12))


def ess_bulk(chains: np.ndarray) -> float:
    return _ess_basic(_rank_normalise(_split(np.asarray(chains, float))))
