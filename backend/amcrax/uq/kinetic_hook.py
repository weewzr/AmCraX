"""Temporary kinetic parameter overrides for the existing PFR (amcrax.reactor.pfr).

amcrax.kinetics.rate_laws.rate_mol_per_kgcat_s has an optional ``param_overrides`` keyword (default None, results
bit-identical). simulate_pfr does not forward it, so this context manager rebinds the name used inside
amcrax.reactor.pfr to a wrapper that adds the overrides, and restores the original in ``finally``.
The kinetics registry (kinetics.yaml) is never modified. Single-threaded use only (one process per worker).
"""
from __future__ import annotations

import contextlib
from typing import Iterator

from amcrax.kinetics import rate_laws
from amcrax.reactor import pfr as _pfr


@contextlib.contextmanager
def kinetic_overrides(catalyst_id: str, overrides: dict[str, float] | None) -> Iterator[None]:
    original = _pfr.rate_mol_per_kgcat_s
    if not overrides:
        yield
        return
    ov = {k: float(v) for k, v in overrides.items()}

    def wrapped(cid, T_K, p_bar, **kw):
        if cid == catalyst_id:
            kw["param_overrides"] = ov
        return rate_laws.rate_mol_per_kgcat_s(cid, T_K, p_bar, **kw)

    _pfr.rate_mol_per_kgcat_s = wrapped
    try:
        yield
    finally:
        _pfr.rate_mol_per_kgcat_s = original


def simulate_with(catalyst_id: str, overrides: dict[str, float] | None, *args, **kw):
    with kinetic_overrides(catalyst_id, overrides):
        return _pfr.simulate_pfr(catalyst_id, *args, **kw)


def mass_with(catalyst_id: str, overrides: dict[str, float] | None, *args, **kw):
    with kinetic_overrides(catalyst_id, overrides):
        return _pfr.catalyst_mass_for_conversion(catalyst_id, *args, **kw)
