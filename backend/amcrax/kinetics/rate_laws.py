"""Rate-law implementations. See the package docstring and ``amcrax/data/kinetics.yaml``.

Unit handling (explicit, no hidden factors):

* Source rates are mol / (g_cat s); multiplied by ``G_PER_KG`` = 1000 to give mol / (kg_cat s).
* Takahashi uses mole fractions p_i/p_total, so the pressure unit cancels (atm in the paper, bar here).
* Kum uses partial pressures in bar (the unit of ko, mol g^-1 s^-1 bar^0.27, makes the bracket dimensionally
  consistent: (bar^2/bar^3)^0.27 = bar^-0.27).
* Activation energies in kJ/mol (Takahashi) are converted to J/mol (x1000); Kum's Ea is already J/mol.
* R = 8.314 J/(mol K) as used by both sources.
"""
from __future__ import annotations

import copy
import math
from dataclasses import asdict, dataclass, field
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml
from scipy.optimize import brentq

from amcrax.thermodynamics import equilibrium_constant

_DATA = Path(__file__).resolve().parents[1] / "data" / "kinetics.yaml"


@lru_cache(maxsize=1)
def _registry() -> dict[str, Any]:
    with open(_DATA, encoding="utf-8") as fh:
        return yaml.safe_load(fh)


_UC = _registry()["unit_conversions"]
G_PER_KG: float = float(_UC["g_per_kg"])
BAR_PER_ATM: float = float(_UC["bar_per_atm"])
R_KIN_J_molK: float = float(_UC["gas_constant_J_per_mol_K"])
_INERT_KEYS_IGNORED = ("NH3", "H2", "N2")


@dataclass
class CatalystModel:
    """Metadata of one literature kinetic model (provenance: literature)."""
    id: str
    label: str
    metal: str
    composition: str
    form: str
    usable: bool
    rate_law_text: str
    rate_unit_published: str
    pressure_basis: str
    parameters: dict[str, Any]
    validity: dict[str, Any]
    experimental_basis: str
    limitations: list[str]
    source: dict[str, Any]
    irreversible_published: bool
    amcrax_extensions: list[str] = field(default_factory=list)
    extra: dict[str, Any] = field(default_factory=dict)
    rate_unit_amcrax: str = "mol NH3 kg_cat^-1 s^-1"
    provenance: str = "literature"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _build(cid: str, d: dict[str, Any]) -> CatalystModel:
    reg = _registry()
    ext: list[str] = []
    extra: dict[str, Any] = {}
    if d["form"] in reg["equilibrium_approach_factor"]["applies_to_forms"]:
        f = reg["equilibrium_approach_factor"]
        ext.append(f"[{f['label']}] {f['expression']} (default_on={f['default_on']}). {f['rationale'].strip()}")
    if "equilibrium_constant" in d:
        extra["equilibrium_constant"] = d["equilibrium_constant"]
        ext.append("[assumption] " + d["equilibrium_constant"]["assumption_text"].strip())
    if "bed_properties" in d:
        extra["bed_properties"] = d["bed_properties"]
    if "reference_values_773K" in d:
        extra["reference_values_773K"] = d["reference_values_773K"]
    return CatalystModel(
        id=cid, label=d["label"], metal=d["metal"], composition=d["composition"], form=d["form"],
        usable=bool(d["usable"]), rate_law_text=d["rate_law_text"].strip(), rate_unit_published=d["rate_unit"],
        pressure_basis=d["pressure_basis"], parameters=copy.deepcopy(d["parameters"]),
        validity=copy.deepcopy(d["validity"]), experimental_basis=d["experimental_basis"],
        limitations=list(d["limitations"]), source=dict(d["source"]),
        irreversible_published=bool(d["irreversible_published"]), amcrax_extensions=ext, extra=extra,
    )


def list_catalysts() -> list[CatalystModel]:
    """The original registry (section ``catalysts``); research additions are in :func:`list_research_catalysts`."""
    return [_build(cid, d) for cid, d in _registry()["catalysts"].items()]


def _all_cats() -> dict[str, Any]:
    reg = _registry()
    return {**reg["catalysts"], **(reg.get("research_catalysts") or {})}


def list_research_catalysts() -> list[CatalystModel]:
    """Catalysts added by the research expansion (section ``research_catalysts`` of kinetics.yaml)."""
    return [_build(cid, d) for cid, d in (_registry().get("research_catalysts") or {}).items()]


def get_catalyst(catalyst_id: str) -> CatalystModel:
    cats = _all_cats()
    if catalyst_id not in cats:
        raise KeyError(f"unknown catalyst_id {catalyst_id!r}; known: {sorted(cats)}")
    return _build(catalyst_id, cats[catalyst_id])


def _p(cid: str) -> dict[str, float]:
    return {k: float(v["value"]) for k, v in _all_cats()[cid]["parameters"].items()}


def lucentini_rate_mol_per_g_s(catalyst_id: str, T_K: float, p_bar: dict[str, float], *,
                               overrides: dict[str, float] | None = None) -> float:
    """Published (irreversible) LHHW rate of lucentini2021nirukinetic Eq. 17-18 [mol NH3 g_cat^-1 s^-1].

    C_i = p_i / (R T) with p in Pa (ideal gas), C in mol m^-3. ``overrides`` replaces parameters (sensitivity only).
    """
    par = _p(catalyst_id)
    if overrides:
        par.update(overrides)
    RT = R_KIN_J_molK * T_K
    c_nh3 = max(p_bar.get("NH3", 0.0), 0.0) * 1e5 / RT
    c_h2 = max(p_bar.get("H2", 0.0), 0.0) * 1e5 / RT
    k = par["k0"] * math.exp(-par["Ek"] * 1e3 / RT)
    den = 1.0 + par["K1"] * c_nh3 + math.sqrt(c_h2 / par["K4"])
    return k * par["K1"] * c_nh3 / den**2


# ----------------------------------------------------------------------------------------------- helpers
def reaction_quotient(p_bar: dict[str, float]) -> float:
    """Q = p_N2^0.5 p_H2^1.5 / p_NH3 with p in bar (1 bar standard state), per mol NH3."""
    pn = p_bar.get("NH3", 0.0)
    if pn <= 0.0:
        return math.inf
    return max(p_bar.get("N2", 0.0), 0.0) ** 0.5 * max(p_bar.get("H2", 0.0), 0.0) ** 1.5 / pn


def kum_keq(T_K: float, basis: str = "published") -> float:
    """Keq of kum2026heatintegrated Eq. 2, per mol NH3 (bar).

    basis='published': Keq**2 = exp(-dGr/(R T)) with dGr of Eq. 4 read as J per 2 mol NH3 (AmCraX assumption).
    basis='amcrax_thermo': Kp(T) of amcrax.thermodynamics (NASA7 / GRI-Mech 3.0, 1 bar).
    """
    if basis == "published":
        a0, a1, a2, a3 = _registry()["catalysts"]["ru_kum_temkin_pyzhev"]["equilibrium_constant"]["dGr_coefficients_J"]
        dG = a0 + a1 * T_K + a2 * T_K**2 + a3 * T_K**3
        return math.sqrt(math.exp(-dG / (R_KIN_J_molK * T_K)))
    if basis == "amcrax_thermo":
        return equilibrium_constant(T_K)
    raise ValueError("keq_basis must be 'published' or 'amcrax_thermo'")


def takahashi_constants(catalyst_id: str, T_K: float, *, param_overrides: dict[str, float] | None = None) -> dict[str, float]:
    """k1, k_minus1, k2, k3, k4, k_minus4 [mol s^-1 g^-1], K1, K4 [-] (Eqs. 9-10, 20-25; T in K).

    ``param_overrides`` (optional, uncertainty analysis only) replaces registry parameter values by name
    (A1..A6, Ea2..Ea5); None leaves every result unchanged."""
    p = _p(catalyst_id)
    if param_overrides:
        p.update({k: float(v) for k, v in param_overrides.items()})
    RT = R_KIN_J_molK * T_K
    k1 = p["A1"]
    k2 = p["A2"] * math.exp(-p["Ea2"] * 1e3 / RT)
    k3 = p["A3"] * math.exp(-p["Ea3"] * 1e3 / RT)
    k4 = p["A4"] * math.exp(-p["Ea4"] * 1e3 / RT)
    K1 = p["A5"] * math.exp(-p["Ea5"] * 1e3 / RT)
    K4 = p["A6"] * math.exp(-p["Ea4"] * 1e3 / RT)
    return {"k1": k1, "k_minus1": k1 / K1, "k2": k2, "k3": k3, "k4": k4, "k_minus4": k4 / K4, "K1": K1, "K4": K4}


def takahashi_coverages(catalyst_id: str, T_K: float, y_NH3: float, y_H2: float, *,
                        param_overrides: dict[str, float] | None = None) -> dict[str, float]:
    """Quasi-steady-state coverages (Eqs. 11-14) and r_NH3 = r2 [mol s^-1 g^-1].

    For a given vacant fraction th_s the QSS relations give th_NH3 (r1=r2), th_N (r2=2 r3) and
    th_H (3 r2 = 2 r4) explicitly; the site balance (Eq. 11) is then solved for ln(th_s) with brentq.
    ``param_overrides``: see :func:`takahashi_constants` (default None = registry values).
    """
    c = takahashi_constants(catalyst_id, T_K, param_overrides=param_overrides)
    y_NH3 = max(y_NH3, 0.0)
    y_H2 = max(y_H2, 0.0)

    def parts(ths: float):
        th_nh3 = c["k1"] * y_NH3 * ths / (c["k_minus1"] + c["k2"] * ths**3)
        r2 = c["k2"] * th_nh3 * ths**3
        th_n = math.sqrt(r2 / (2.0 * c["k3"]))
        th_h = math.sqrt((1.5 * r2 + c["k_minus4"] * y_H2 * ths**2) / c["k4"])
        return th_nh3, th_n, th_h, r2

    def resid(u: float) -> float:
        ths = math.exp(u)
        a, b, h, _ = parts(ths)
        return ths + a + b + h - 1.0

    if resid(0.0) <= 0.0:  # cannot happen physically (all terms >= 0); guard
        u = 0.0
    else:
        u = brentq(resid, -300.0, 0.0, xtol=1e-14, rtol=1e-13, maxiter=500)
    ths = math.exp(u)
    a, b, h, r2 = parts(ths)
    return {"theta_s": ths, "theta_NH3": a, "theta_N": b, "theta_H": h, "r_mol_per_g_s": r2}


# ----------------------------------------------------------------------------------------------- public
def rate_mol_per_kgcat_s(catalyst_id: str, T_K: float, p_bar: dict[str, float], *,
                         approach_factor: bool | None = None, keq_basis: str = "published",
                         param_overrides: dict[str, float] | None = None) -> float:
    """Net NH3 consumption rate [mol NH3 / (kg_cat s)] at T_K and partial pressures p_bar [bar].

    approach_factor: Takahashi models only; None -> registry default (True, AmCraX extension), False -> published.
    keq_basis: Kum model only; 'published' (Eq. 4, AmCraX reading) or 'amcrax_thermo'.
    param_overrides: optional dict {parameter name: value} replacing registry values for this call only
        (uncertainty analysis; Takahashi and Lucentini forms). None (default) leaves every result bit-identical.
    """
    reg = _registry()
    cats = _all_cats()
    d = cats[catalyst_id] if catalyst_id in cats else None
    if d is None:
        raise KeyError(f"unknown catalyst_id {catalyst_id!r}")
    if not d["usable"]:
        raise ValueError(f"catalyst {catalyst_id} is flagged usable=false")
    P = sum(max(v, 0.0) for v in p_bar.values())
    if P <= 0.0:
        raise ValueError("total pressure must be > 0")
    form = d["form"]
    if form == "takahashi_microkinetic":
        y_nh3 = max(p_bar.get("NH3", 0.0), 0.0) / P
        y_h2 = max(p_bar.get("H2", 0.0), 0.0) / P
        if y_nh3 <= 0.0:
            return 0.0
        r_g = takahashi_coverages(catalyst_id, T_K, y_nh3, y_h2, param_overrides=param_overrides)["r_mol_per_g_s"]
        use = reg["equilibrium_approach_factor"]["default_on"] if approach_factor is None else approach_factor
        if use:
            r_g *= 1.0 - reaction_quotient(p_bar) / equilibrium_constant(T_K)
        return r_g * G_PER_KG
    if form == "temkin_pyzhev":
        par = _p(catalyst_id)
        if param_overrides:
            par.update({k: float(v) for k, v in param_overrides.items()})
        pn, ph, pn2 = p_bar.get("NH3", 0.0), p_bar.get("H2", 0.0), max(p_bar.get("N2", 0.0), 0.0)
        if pn <= 0.0 or ph <= 0.0:
            raise ValueError("Temkin-Pyzhev form is singular for p_NH3 <= 0 or p_H2 <= 0 (seed H2 in the reactor)")
        beta = par["beta"]
        k = par["ko"] * math.exp(-par["Ea"] / (R_KIN_J_molK * T_K))
        keq = kum_keq(T_K, keq_basis)
        ln_ratio = 2.0 * math.log(pn) - 3.0 * math.log(ph)  # ln(pNH3^2/pH2^3)
        fwd = math.exp(beta * ln_ratio)
        rev = (pn2 / keq**2) * math.exp(-(1.0 - beta) * ln_ratio)
        return k * (fwd - rev) * G_PER_KG
    if form == "lhhw_lucentini":
        if max(p_bar.get("NH3", 0.0), 0.0) <= 0.0:
            return 0.0
        r_g = lucentini_rate_mol_per_g_s(catalyst_id, T_K, p_bar, overrides=param_overrides)
        use = reg["equilibrium_approach_factor"]["default_on"] if approach_factor is None else approach_factor
        if use:
            r_g *= 1.0 - reaction_quotient(p_bar) / equilibrium_constant(T_K)
        return r_g * G_PER_KG
    raise ValueError(f"unknown rate-law form {form!r}")
