"""Ideal-gas species thermochemistry from NASA 7-coefficient polynomials (numpy only).

Coefficients: ``backend/amcrax/data/nasa7.json``, copied programmatically from Cantera's
``gri30.yaml`` (GRI-Mech 3.0) by :mod:`amcrax.thermodynamics.build_data`. The polynomials give
h including the standard enthalpy of formation at 298.15 K (elements in their reference state
have h(298.15 K) = 0) and the standard entropy s.

Standard-state pressure of the entropy polynomials: Cantera *labels* gri30.yaml with a 1 atm
reference pressure, but the polynomial entropies reproduce the NIST-JANAF **1 bar** values
(4th ed., 1998) for NH3, H2, H2O, O2 to < 0.01 J/(mol K) at 298.15 K and 800 K (N2: 0.1 J/(mol K)),
i.e. the fits were made to 1-bar data. A 1 atm -> 1 bar shift (R ln 1.01325 = 0.109 J/(mol K)) would
break that agreement, so the polynomials are used as **1 bar** data here (POLY_PREF_BAR = 1.0;
evidence checked in tests/test_thermodynamics.py against JANAF tables H-083, N-023, H-050, H-064, O-029).
Consequence: Cantera's own equilibrate() treats the same g as 1 atm values, so Cantera at p atm
corresponds to this model at p bar (used in the solver cross-check).
"""
from __future__ import annotations

import json
import math
from functools import lru_cache
from pathlib import Path

import numpy as np

R_J_molK = 8.314462618  # CODATA 2018 exact (k_B * N_A)
P_STD_BAR = 1.0       # standard state of all public s, g, K values
POLY_PREF_BAR = 1.0   # standard-state pressure the GRI-Mech entropies were fitted at (see module docstring)
DATA_FILE = Path(__file__).resolve().parents[1] / "data" / "nasa7.json"


@lru_cache(maxsize=1)
def _data() -> dict:
    d = json.loads(DATA_FILE.read_text(encoding="utf-8"))
    species = {}
    for name, sp in d["species"].items():
        p = POLY_PREF_BAR * 1e5
        species[name] = {
            "Tmin": sp["T_ranges_K"][0],
            "Tmid": sp["T_ranges_K"][1],
            "Tmax": sp["T_ranges_K"][2],
            "low": np.asarray(sp["coeffs_low"], dtype=float),
            "high": np.asarray(sp["coeffs_high"], dtype=float),
            # correction from polynomial reference pressure to 1 bar standard state, in units of R
            "ds_R": math.log(p / (P_STD_BAR * 1e5)),
            "composition": sp["composition"],
        }
    return species


def species_list() -> list[str]:
    return list(_data().keys())


def composition(species: str) -> dict[str, float]:
    return dict(_data()[species]["composition"])


def _coeffs(species: str, T_K: float) -> np.ndarray:
    try:
        sp = _data()[species]
    except KeyError as exc:
        raise KeyError(f"unknown species {species!r}; available: {species_list()}") from exc
    # GRI-Mech gives N2 from 300 K only; a smooth low-range extrapolation down to Tmin - 100 K is allowed
    # (needed for the 298.15 K reference; deviation at 298.15 K < 0.001 kJ/mol, checked in tests).
    if not (sp["Tmin"] - 100.0 <= T_K <= sp["Tmax"]):
        raise ValueError(f"T = {T_K} K outside NASA7 validity [{sp['Tmin']}, {sp['Tmax']}] K for {species}")
    return sp["low"] if T_K <= sp["Tmid"] else sp["high"]


def cp_R(species: str, T_K: float) -> float:
    a = _coeffs(species, T_K)
    T = T_K
    return float(a[0] + a[1] * T + a[2] * T**2 + a[3] * T**3 + a[4] * T**4)


def h_RT(species: str, T_K: float) -> float:
    a = _coeffs(species, T_K)
    T = T_K
    return float(a[0] + a[1] * T / 2 + a[2] * T**2 / 3 + a[3] * T**3 / 4 + a[4] * T**4 / 5 + a[5] / T)


def s_R(species: str, T_K: float) -> float:
    """Standard entropy / R at 1 bar."""
    a = _coeffs(species, T_K)
    T = T_K
    s = a[0] * math.log(T) + a[1] * T + a[2] * T**2 / 2 + a[3] * T**3 / 3 + a[4] * T**4 / 4 + a[6]
    return float(s + _data()[species]["ds_R"])


def species_cp_J_molK(species: str, T_K: float) -> float:
    return R_J_molK * cp_R(species, T_K)


def species_enthalpy_kJ_mol(species: str, T_K: float) -> float:
    """Ideal-gas molar enthalpy incl. formation enthalpy (elements = 0 at 298.15 K), kJ/mol."""
    return R_J_molK * T_K * h_RT(species, T_K) / 1000.0


def species_entropy_J_molK(species: str, T_K: float) -> float:
    """Standard (1 bar) ideal-gas molar entropy, J/(mol K)."""
    return R_J_molK * s_R(species, T_K)


def species_gibbs_kJ_mol(species: str, T_K: float) -> float:
    """Standard (1 bar) molar Gibbs energy g = h - T s, kJ/mol (same enthalpy reference)."""
    return species_enthalpy_kJ_mol(species, T_K) - T_K * species_entropy_J_molK(species, T_K) / 1000.0
