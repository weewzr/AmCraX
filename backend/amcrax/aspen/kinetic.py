"""Catalyst-kinetic plug-flow reactor (Aspen Plus RPLUG) for the AmCraX research expansion.

Additive module: nothing in the existing RGibbs flowsheet changes unless the caller asks for it.

Standalone model (``build_kinetic_reactor_input``)::

    KFEED -> RXR (RPLUG, catalyst kinetics) -> KPROD
    EQFEED -> REQ (RGIBBS at the same T, P)  -> EQPROD      (equilibrium reference, same run)

Kinetics are written as a ``REACTIONS ... GENERAL`` block of class POWERLAW on a partial-pressure basis
(bar), rate per kg catalyst (RBASIS=CAT-WT), reversible with Aspen's automatic micro-reversibility
(REV-METH=AUTOMATIC: reverse rate from the Gibbs energy of reaction of the property method). The input
language follows the AspenTech V15 example "Ammonia decomposition datafit" exported through COM.

Kum et al. (2026) Temkin-Pyzhev law (kinetics.yaml ``ru_kum_temkin_pyzhev``), per mol NH3::

    r_NH3 = k [ (pNH3^2/pH2^3)^b - (pN2/Keq^2) (pH2^3/pNH3^2)^(1-b) ]
          = k pNH3^(2b) pH2^(-3b) [ 1 - pN2 pH2^3 / (pNH3^2 Keq^2) ]

Keq^2 (per 2 mol NH3, 1 bar) is the equilibrium constant of 2 NH3 = N2 + 3 H2, so the law is exactly a
forward power law times (1 - Q2/K2), which is Aspen's reversible GENERAL POWERLAW form for the reaction
written per 2 mol NH3. Aspen's rate is per reaction event, so r_rxn = r_NH3 / 2:

    PRE-EXP [kmol kg_cat^-1 s^-1 bar^-(2b-3b)] = ko [mol g^-1 s^-1 bar^0.27] x 1000 g/kg / 1000 mol/kmol / 2
    ACT-ENERGY = Ea / 1000 kJ/mol;   exponents NH3: 2b = 0.54, H2: -3b = -0.81;  no reference temperature.

Keq: Aspen computes it from Gibbs energies (property-method ideal-gas data), not from Kum Eq. 4; the
Python comparison therefore uses ``keq_basis='amcrax_thermo'``. Kum Eq. 4 contains a T^3 term in dGr that
the native ln K = A + B/T + C ln T + D T form cannot represent exactly; this is recorded as a limitation.
"""
from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any, Literal, Optional

from pydantic import BaseModel, Field, model_validator

from amcrax.aspen.inp_writer import _HEADER, _f

MOLAR_MASS = {"NH3": 17.031, "H2": 2.016, "N2": 28.014, "H2O": 18.015, "O2": 31.998}
COMPONENTS = ("NH3", "H2", "N2", "H2O", "O2")


# ----------------------------------------------------------------------------------------- kinetics spec
class AspenPowerLawSpec(BaseModel):
    """Native Aspen GENERAL / POWERLAW reaction (per reaction event as written in ``stoichiometry``)."""
    catalyst_id: str
    label: str = ""
    stoichiometry: dict[str, float] = Field(default_factory=lambda: {"NH3": -2.0, "N2": 1.0, "H2": 3.0})
    pre_exp_kmol_kgcat_s: float          # in kmol kg_cat^-1 s^-1 (pressure unit bar)^-(sum of exponents)
    activation_energy_kJ_mol: float
    temperature_exponent: float = 0.0
    reference_temperature_C: Optional[float] = None
    exponents: dict[str, float]
    reversible: bool = True
    rev_method: Literal["AUTOMATIC"] = "AUTOMATIC"
    cbasis: Literal["PARTIALPRES"] = "PARTIALPRES"
    rbasis: Literal["CAT-WT"] = "CAT-WT"
    pres_unit: Literal["BAR"] = "BAR"
    requires_h2_seed: bool = True
    derivation: list[str] = Field(default_factory=list)
    source: str = ""
    provenance: str = "literature"


def spec_from_registry(catalyst_id: str = "ru_kum_temkin_pyzhev") -> AspenPowerLawSpec:
    """Translate a kinetics.yaml entry into the native Aspen form (only Temkin-Pyzhev is expressible)."""
    from amcrax.kinetics.rate_laws import G_PER_KG, _registry

    d = _registry()["catalysts"][catalyst_id]
    if d["form"] != "temkin_pyzhev":
        raise ValueError(
            f"{catalyst_id}: form {d['form']!r} is not expressible as a native Aspen rate law "
            "(the Takahashi microkinetic model needs a user kinetics subroutine; no Fortran compiler is installed)"
        )
    p = d["parameters"]
    ko, ea, beta = float(p["ko"]["value"]), float(p["Ea"]["value"]), float(p["beta"]["value"])
    pre = ko * G_PER_KG / 1000.0 / 2.0
    return AspenPowerLawSpec(
        catalyst_id=catalyst_id,
        label=d["label"],
        pre_exp_kmol_kgcat_s=pre,
        activation_energy_kJ_mol=ea / 1000.0,
        exponents={"NH3": 2.0 * beta, "H2": -3.0 * beta},
        derivation=[
            f"ko = {ko} {p['ko']['unit']} ({p['ko']['citekey']} p. {p['ko']['page']} {p['ko']['locator']})",
            f"PRE-EXP = ko x {G_PER_KG:g} g/kg / 1000 mol/kmol / 2 (rate per 2 mol NH3) = {pre:.6g} kmol/(kg_cat s bar^0.27)",
            f"ACT-ENERGY = {ea} J/mol / 1000 = {ea/1000:.6g} kJ/mol",
            f"exponents: NH3 2*beta = {2*beta:.6g}, H2 -3*beta = {-3*beta:.6g} (beta = {beta})",
            "reverse: Aspen micro-reversibility, Keq of 2NH3 = N2 + 3H2 from Gibbs energies (not Kum Eq. 4)",
        ],
        source=f"{d['source']['citekey']} {d['source']['locator']}",
    )


def load_spec(catalyst_id: str, spec_path: Optional[Path] = None) -> AspenPowerLawSpec:
    """Kinetic spec for ``catalyst_id``: from the kinetics workstream's aspen_kinetics_spec.json when it holds
    a native entry for the catalyst, otherwise translated from kinetics.yaml by :func:`spec_from_registry`."""
    from amcrax.paths import ROOT

    path = spec_path or ROOT / "results" / "research" / "kinetics" / "aspen_kinetics_spec.json"
    if path.exists():
        data = json.loads(path.read_text(encoding="utf-8"))
        entry = _find_entry(data, catalyst_id)
        if entry is not None:
            spec = _spec_from_external(catalyst_id, entry)
            if spec is not None:
                return spec
    return spec_from_registry(catalyst_id)


def _find_entry(data: Any, catalyst_id: str) -> Optional[dict]:
    if isinstance(data, dict):
        for key in ("catalysts", "reactions", "entries", "specs"):
            if key in data:
                found = _find_entry(data[key], catalyst_id)
                if found is not None:
                    return found
        if catalyst_id in data and isinstance(data[catalyst_id], dict):
            return data[catalyst_id]
    if isinstance(data, list):
        for e in data:
            if isinstance(e, dict) and (e.get("catalyst_id") == catalyst_id or e.get("id") == catalyst_id):
                return e
    return None


def _spec_from_external(catalyst_id: str, e: dict) -> Optional[AspenPowerLawSpec]:
    """Map an external spec entry onto :class:`AspenPowerLawSpec` (tolerant to key names; None if unusable)."""
    a = e.get("aspen", e)
    if a.get("native") is False or a.get("expressible_natively") is False:
        return None
    try:
        return AspenPowerLawSpec(catalyst_id=catalyst_id, **{k: v for k, v in a.items()
                                                              if k in AspenPowerLawSpec.model_fields})
    except Exception:
        return None


class AspenLHHWSpec(BaseModel):
    """Native Aspen GENERAL / LHHW reaction from the kinetics workstream's aspen_kinetics_spec.json (SI units:
    rate kmol kg_cat^-1 s^-1, partial pressures in N/sqm or concentrations in kmol/m3, ln K with T in K)."""
    catalyst_id: str
    label: str = ""
    stoichiometry: dict[str, float]
    k_kmol_kgcat_s: float
    temperature_exponent: float = 0.0
    activation_energy_kJ_mol: float
    cbasis: Literal["PARTIALPRES", "MOLARITY", "MOLEFRAC"] = "PARTIALPRES"
    term1_exponents: dict[str, float]
    term1_lnK: dict[str, float]
    term2_exponents: dict[str, float]
    term2_lnK: dict[str, float]
    adsorption_exponent: float = 1.0
    adsorption_terms: list[dict[str, Any]]      # [{"exponents": {...}, "lnK_coefficients": {A,B,C,D}}]
    requires_h2_seed: bool = True
    source: str = ""
    derivation: list[str] = Field(default_factory=list)
    provenance: str = "literature (converted by the kinetics workstream)"


def lhhw_from_kinetics_spec(e: dict) -> AspenLHHWSpec:
    kf, df, ad = e["kinetic_factor"], e["driving_force"], e["adsorption"]
    cb = str(e.get("concentration_basis", "Partial pressure")).lower()
    src = e.get("source", {})
    return AspenLHHWSpec(
        catalyst_id=e["catalyst_id"], label=e.get("label", ""),
        stoichiometry={k: float(v) for k, v in e["stoichiometry"].items()},
        k_kmol_kgcat_s=float(kf["k"]), temperature_exponent=float(kf.get("n", 0.0)),
        activation_energy_kJ_mol=float(kf["E_kJ_per_mol"]),
        cbasis="PARTIALPRES" if "partial" in cb else "MOLARITY",
        term1_exponents=df["term1"]["exponents"], term1_lnK=df["term1"]["lnK_coefficients"],
        term2_exponents=df["term2"]["exponents"], term2_lnK=df["term2"]["lnK_coefficients"],
        adsorption_exponent=float(ad["exponent"]), adsorption_terms=ad["terms"],
        requires_h2_seed=True,
        source=f"{src.get('citekey', '')} {src.get('locator', '')}".strip(),
        derivation=["taken unchanged from results/research/kinetics/aspen_kinetics_spec.json (kinetics workstream)"],
    )


APPROXIMATION_PRESSURE_BAR = 20.0   # term-2 constant of the fitted approximations is valid at this P only


def lhhw_from_approximation(e: dict) -> AspenLHHWSpec:
    """Fitted LHHW approximation (``best_native_approximation``) of a non-native law, mole-fraction basis.

    Research option only (``kinetic_form='lhhw_approximation'``). The parameters are a Python fit made by the
    kinetics workstream (source_type python, not literature); the reversible term-2 constant includes the total
    pressure and is valid at APPROXIMATION_PRESSURE_BAR only.
    """
    b = e["best_native_approximation"]
    kf, df, ad = b["kinetic_factor"], b["driving_force"], b["adsorption"]
    return AspenLHHWSpec(
        catalyst_id=e["catalyst_id"], label=e.get("label", "") + " (fitted LHHW approximation)",
        stoichiometry={"NH3": -1.0, "N2": 0.5, "H2": 1.5},
        k_kmol_kgcat_s=float(kf["k"]), temperature_exponent=float(kf.get("n", 0.0)),
        activation_energy_kJ_mol=float(kf["E_J_per_mol"]) / 1000.0,
        cbasis="MOLEFRAC",
        term1_exponents=df["term1"]["exponents"], term1_lnK=df["term1"]["lnK_coefficients"],
        term2_exponents=df["term2"]["exponents"], term2_lnK=df["term2"]["lnK_coefficients"],
        adsorption_exponent=float(ad["exponent"]), adsorption_terms=ad["terms"],
        requires_h2_seed=True, source="best_native_approximation in aspen_kinetics_spec.json",
        derivation=["python fit by the kinetics workstream to the microkinetic law; not literature",
                    f"term-2 constant valid only at {APPROXIMATION_PRESSURE_BAR} bar"],
        provenance="python (fitted approximation of a literature law)",
    )


def load_kinetics_spec_file(path: Optional[Path] = None) -> dict[str, dict]:
    from amcrax.paths import ROOT

    p = path or ROOT / "results" / "research" / "kinetics" / "aspen_kinetics_spec.json"
    if not p.exists():
        return {}
    data = json.loads(p.read_text(encoding="utf-8"))
    return {c["catalyst_id"]: c for c in data.get("catalysts", []) if isinstance(c, dict) and "catalyst_id" in c}


R_J_PER_KMOL_K = 8314.0   # = 8.314 J/(mol K) of the kinetics registry (same R as the Python rate law)
P0_PA = 1.0e5             # 1 bar standard state of Kp


def load_equilibrium_fit(path: Optional[Path] = None) -> dict[str, float]:
    """ln Kp = A + B/T + C ln T + D T (1 bar standard state) from aspen_kinetics_spec.json."""
    from amcrax.paths import ROOT

    p = path or ROOT / "results" / "research" / "kinetics" / "aspen_kinetics_spec.json"
    fit = json.loads(p.read_text(encoding="utf-8"))["equilibrium_constant_fit"]
    return {k: float(fit[k]) for k in ("A", "B", "C", "D")}


def lhhw_partialpres_from_molarity(e: dict, kp_fit: dict[str, float]) -> AspenLHHWSpec:
    """Exact partial-pressure (Pa) form of a molarity-basis Lucentini LHHW entry (Phase 2, task K1 item 3).

    The source law uses ideal-gas concentrations C_i = p_i/(R T) (lucentini2021nirukinetic, 1 atm), and the Python
    model does the same. With CBASIS=MOLARITY Aspen instead computes C_i from the PENG-ROB molar volume,
    C_i = y_i P/(Z R T), while the term-2 constant uses the ideal-gas Kc = Kp P0/(R T); the driving force then
    vanishes at Q_y P/P0 = Kp Z instead of Kp (an implementation inconsistency, not physics). On a partial-pressure
    basis (p_i = y_i P, no Z) the same law is, with every constant in Aspen's ln K = A + B/T + C ln T + D T form:

    * K1 C_NH3 = (K1/R T) p_NH3                   -> ln K1' = ln(K1/R) - ln T
    * sqrt(C_H2/K4) = sqrt(p_H2/(R T K4))         -> ln K4' = -0.5 ln(R K4) - 0.5 ln T   (exponent 0.5 on H2)
    * term 2 = K1'/(Kp P0) p_N2^0.5 p_H2^1.5     -> ln K2' = ln K1' - ln Kp - ln P0
    No parameter is refitted; the transformation is algebraic (R = 8314 J/(kmol K), p in N/m2).
    """
    if str(e.get("concentration_basis", "")).lower() != "molarity" or not e.get("aspen_native"):
        raise ValueError(f"{e.get('catalyst_id')}: lhhw_partialpres needs a native molarity-basis LHHW entry")
    base = lhhw_from_kinetics_spec(e)
    lnK1 = float(base.term1_lnK.get("A", 0.0))
    for k in ("B", "C", "D"):
        if abs(float(base.term1_lnK.get(k, 0.0))) > 0:
            raise ValueError("term-1 constant must be temperature independent (Lucentini K1)")
    lnK1p = {"A": lnK1 - math.log(R_J_PER_KMOL_K), "B": 0.0, "C": -1.0, "D": 0.0}
    lnK2p = {"A": lnK1p["A"] - kp_fit["A"] - math.log(P0_PA), "B": -kp_fit["B"], "C": -1.0 - kp_fit["C"],
             "D": -kp_fit["D"]}
    terms = []
    for t in base.adsorption_terms:
        ex = {c: float(v) for c, v in (t.get("exponents") or {}).items() if float(v) != 0.0}
        lk = {k: float((t.get("lnK_coefficients") or {}).get(k, 0.0)) for k in ("A", "B", "C", "D")}
        if not ex:
            terms.append({"exponents": {}, "lnK_coefficients": lk})
            continue
        if len(ex) != 1 or any(abs(lk[k]) > 0 for k in ("B", "C", "D")):
            raise ValueError("unexpected adsorption term for the molarity -> partial-pressure transformation")
        (c, a), = ex.items()
        # K C^a = K (p/(R T))^a  ->  ln K' = ln K - a ln R - a ln T
        terms.append({"exponents": {c: a}, "lnK_coefficients": {"A": lk["A"] - a * math.log(R_J_PER_KMOL_K),
                                                                 "B": 0.0, "C": -a, "D": 0.0}})
    return base.model_copy(update={
        "cbasis": "PARTIALPRES", "term1_lnK": lnK1p, "term2_lnK": lnK2p, "adsorption_terms": terms,
        "label": base.label + " (partial-pressure basis, exact transformation)",
        "derivation": base.derivation + [
            "molarity -> partial pressure (Pa): C_i = p_i/(R T), R = 8314 J/(kmol K); ln K' gains -a ln R - a ln T",
            "term 2 = K1'/(Kp P0), Kp from equilibrium_constant_fit of aspen_kinetics_spec.json (ideal gas, 1 bar)",
            "removes the PENG-ROB compressibility factor from the concentrations (Phase 2 task K1 item 3)"],
    })


def resolve_spec(catalyst_id: str, kinetic_form: str = "auto", spec_path: Optional[Path] = None):
    """Choose the native Aspen form.

    'powerlaw': kinetics.yaml translated to GENERAL POWERLAW with Aspen micro-reversibility (Temkin-Pyzhev only);
    'lhhw': the kinetics workstream's LHHW entry; 'auto': powerlaw where possible, else lhhw.
    """
    if kinetic_form in ("auto", "powerlaw"):
        try:
            return spec_from_registry(catalyst_id)
        except (KeyError, ValueError):
            if kinetic_form == "powerlaw":
                raise
    entries = load_kinetics_spec_file(spec_path)
    e = entries.get(catalyst_id)
    if e is None:
        raise ValueError(f"{catalyst_id}: no entry in aspen_kinetics_spec.json and not expressible from kinetics.yaml")
    if kinetic_form == "lhhw_partialpres":
        return lhhw_partialpres_from_molarity(e, load_equilibrium_fit(spec_path))
    if kinetic_form == "lhhw_approximation":
        if "best_native_approximation" not in e:
            raise ValueError(f"{catalyst_id}: no best_native_approximation in aspen_kinetics_spec.json")
        return lhhw_from_approximation(e)
    if not e.get("aspen_native"):
        raise ValueError(f"{catalyst_id}: the kinetics workstream marks this law as not expressible natively in Aspen "
                         "(a user kinetics subroutine would need a Fortran compiler, which is not installed)")
    return lhhw_from_kinetics_spec(e)


def _lnk(d: dict[str, float]) -> str:
    return " ".join(f"{k}={_f(d.get(k, 0.0))}" for k in ("A", "B", "C", "D"))


def lhhw_reactions_block(spec: AspenLHHWSpec, rxn_id: str = "NH3KIN") -> str:
    terms = spec.adsorption_terms
    comps = sorted({c for t in terms for c in (t.get("exponents") or {})}) or ["NH3"]  # all-zero row = constant 1
    stoic = " / ".join(f"{c} {_f(v)}" for c, v in spec.stoichiometry.items())
    d1 = " / ".join(f"MIXED {c} {_f(v)}" for c, v in spec.term1_exponents.items() if v != 0) or "MIXED NH3 0."
    d2 = " / ".join(f"MIXED {c} {_f(v)}" for c, v in spec.term2_exponents.items() if v != 0) or "MIXED NH3 0."
    pu = '  &\n        PRES-UNIT="N/sqm"' if spec.cbasis == "PARTIALPRES" else ""
    lines = [
        f"REACTIONS {rxn_id} GENERAL",
        f"    PARAM NTERM-ADS={len(terms)}",
        "    REAC-DATA 1 NAME=NH3DEC REAC-CLASS=LHHW PHASE=V  &",
        f"        CBASIS={spec.cbasis} RBASIS=CAT-WT REVERSIBLE=YES  &",
        f"        REV-METH=USER-SPEC{pu}",
        f"    RATE-CON 1 PRE-EXP={_f(spec.k_kmol_kgcat_s)} ACT-ENERGY={_f(spec.activation_energy_kJ_mol)} <kJ/mol>  &",
        f"        TEMP-EXPONEN={_f(spec.temperature_exponent)}",
        f"    STOIC 1 MIXED {stoic}",
        f"    DFORCE-EXP 1 {d1}",
        f"    DFORCE-EXP-2 1 {d2}",
        f"    DFORCE-EQ-1 REACNO=1 {_lnk(spec.term1_lnK)}",
        f"    DFORCE-EQ-2 REACNO=1 {_lnk(spec.term2_lnK)}",
    ]
    parts = [f"REACNO=1 CID={c} SSID=MIXED EXPONENT=" + " ".join(_f((t.get("exponents") or {}).get(c, 0.0)) for t in terms)
             for c in comps]
    lines.append("    ADSORP-EXP " + " /  &\n        ".join(parts))
    eq = [f"REACNO=1 TERM= {n + 1} {_lnk(t.get('lnK_coefficients') or {})}" for n, t in enumerate(terms)]
    lines.append("    ADSORP-EQTER " + " /  &\n        ".join(eq))
    lines.append(f"    ADSORP-POW REACNO=1 EXPONENT={_f(spec.adsorption_exponent)}")
    lines.append("    REAC-ACT 1")
    return "\n".join(lines) + "\n"


def any_reactions_block(spec, rxn_id: str = "NH3KIN") -> str:
    return lhhw_reactions_block(spec, rxn_id) if isinstance(spec, AspenLHHWSpec) else reactions_block(spec, rxn_id)


# ----------------------------------------------------------------------------------------- reactor inputs
class KineticReactorInputs(BaseModel):
    """Typed inputs of the standalone RPLUG model (independent of CaseInputs)."""
    case_id: str = "kinetic_case"
    catalyst_id: str = "ru_kum_temkin_pyzhev"
    kinetic_form: Literal["auto", "powerlaw", "lhhw", "lhhw_approximation", "lhhw_partialpres"] = "auto"   # see resolve_spec
    temperature_C: float = 450.0                 # feed temperature and (isothermal) reactor temperature
    pressure_bar: float = 5.0
    feed_kmol_h: dict[str, float] = Field(default_factory=lambda: {"NH3": 99.8, "H2O": 0.2})
    # Pre-cracked NH3 fraction added to the feed as N2/H2 (rate singular at pH2 = 0). Numerical assumption:
    # 1e-6 gave "BLOCK IS IN MASS IMBALANCE" in adiabatic and coolant RPLUG runs, 1e-4 still in the coolant
    # run; 1e-3 solves all modes, and the Python PFR outlet conversion changes by < 3e-5 between 1e-6 and 1e-3.
    h2_seed_conversion: float = 1e-3
    thermal_mode: Literal["isothermal", "adiabatic", "coolant"] = "isothermal"
    coolant_temperature_C: Optional[float] = None
    U_W_m2K: Optional[float] = None
    catalyst_mass_kg: Optional[float] = None     # total over all tubes; sets the length if length_m is None
    length_m: Optional[float] = None
    tube_diameter_m: float = 0.126               # kum2026heatintegrated Table 1 (Din)
    n_tubes: int = 1
    bed_voidage: float = 0.36                    # kum2026heatintegrated Table 1
    particle_density_kg_m3: float = 980.0        # kum2026heatintegrated Table 1
    particle_diameter_m: float = 0.0006          # kum2026heatintegrated Table 1
    pressure_drop: bool = False
    property_method: str = "PENG-ROB"
    npoint: int = 50
    integration_tolerance: Optional[float] = None  # RPLUG INT-TOL; None = Aspen default (1e-7 made 500 degC fail)
    include_equilibrium_reference: bool = True

    @model_validator(mode="after")
    def _check(self) -> "KineticReactorInputs":
        if (self.catalyst_mass_kg is None) == (self.length_m is None):
            raise ValueError("give exactly one of catalyst_mass_kg or length_m")
        if self.thermal_mode == "coolant" and (self.coolant_temperature_C is None or self.U_W_m2K is None):
            raise ValueError("thermal_mode 'coolant' needs coolant_temperature_C and U_W_m2K")
        if self.feed_kmol_h.get("NH3", 0.0) <= 0:
            raise ValueError("feed must contain NH3")
        if self.kinetic_form == "lhhw_approximation" and abs(self.pressure_bar - APPROXIMATION_PRESSURE_BAR) > 1e-6:
            raise ValueError(f"kinetic_form 'lhhw_approximation' is valid only at {APPROXIMATION_PRESSURE_BAR} bar")
        return self

    @property
    def bed_density_kg_m3(self) -> float:
        return (1.0 - self.bed_voidage) * self.particle_density_kg_m3

    @property
    def cross_section_m2(self) -> float:
        return self.n_tubes * math.pi * self.tube_diameter_m ** 2 / 4.0

    @property
    def reactor_length_m(self) -> float:
        if self.length_m is not None:
            return self.length_m
        return self.catalyst_mass_kg / (self.bed_density_kg_m3 * self.cross_section_m2)

    @property
    def catalyst_mass_total_kg(self) -> float:
        return self.bed_density_kg_m3 * self.cross_section_m2 * self.reactor_length_m

    def seeded_feed(self) -> dict[str, float]:
        """Feed with the H2 seed: a fraction ``h2_seed_conversion`` of the NH3 is pre-cracked (atom balance kept)."""
        f = {k: float(v) for k, v in self.feed_kmol_h.items() if v > 0}
        if self.feed_kmol_h.get("H2", 0.0) <= 0 and self.h2_seed_conversion > 0:
            x = self.h2_seed_conversion * f["NH3"]
            f["NH3"] -= x
            f["N2"] = f.get("N2", 0.0) + 0.5 * x
            f["H2"] = f.get("H2", 0.0) + 1.5 * x
        unknown = set(f) - set(COMPONENTS)
        if unknown:
            raise ValueError(f"unsupported feed components {sorted(unknown)}")
        return f


# ----------------------------------------------------------------------------------------- input writer
def reactions_block(spec: AspenPowerLawSpec, rxn_id: str = "NH3KIN") -> str:
    stoic = " / ".join(f"{c} {_f(v)}" for c, v in spec.stoichiometry.items())
    exps = " / ".join(f"MIXED {c} {_f(v)}" for c, v in spec.exponents.items())
    rev = f"REVERSIBLE=YES REV-METH={spec.rev_method}" if spec.reversible else "REVERSIBLE=NO"
    tref = f" T-REF={_f(spec.reference_temperature_C)}" if spec.reference_temperature_C is not None else ""
    return (
        f"REACTIONS {rxn_id} GENERAL\n"
        f"    REAC-DATA 1 NAME=NH3DEC REAC-CLASS=POWERLAW PHASE=V  &\n"
        f"        CBASIS={spec.cbasis} RBASIS={spec.rbasis} {rev}  &\n"
        f"        PRES-UNIT=\"{spec.pres_unit}\"\n"
        f"    RATE-CON 1 PRE-EXP={_f(spec.pre_exp_kmol_kgcat_s)} ACT-ENERGY={_f(spec.activation_energy_kJ_mol)} <kJ/mol>  &\n"
        f"        TEMP-EXPONEN={_f(spec.temperature_exponent)}{tref}\n"
        f"    STOIC 1 MIXED {stoic}\n"
        f"    DFORCE-EXP 1 {exps}\n"
        f"    REAC-ACT 1\n"
    )


def rplug_block(i: KineticReactorInputs, block_id: str, rxn_id: str = "NH3KIN",
                temperature_C: Optional[float] = None) -> str:
    """RPLUG block text. ``temperature_C`` overrides the isothermal reactor temperature (integrated use)."""
    t = i.temperature_C if temperature_C is None else temperature_C
    if i.thermal_mode == "isothermal":
        head, extra = "TYPE=T-SPEC", f"    T-SPEC 0. {_f(t)}\n"
    elif i.thermal_mode == "adiabatic":
        head, extra = "TYPE=ADIABATIC", ""
    else:
        head = f"TYPE=TCOOL-SPEC U={_f(i.U_W_m2K)} <Watt/sqm-K>"
        extra = f"    COOLANT TEMP={_f(i.coolant_temperature_C)}\n"
    pd = (f"OPT-PDROP=CORRELATION DP-FCOR=ERGUN DIA-PART={_f(i.particle_diameter_m)} <meter>"
          if i.pressure_drop else "PRES=0.")
    return (
        f"BLOCK {block_id} RPLUG\n"
        f"    PARAM {head} NTUBE={int(i.n_tubes)} LENGTH={_f(i.reactor_length_m)} <meter>  &\n"
        f"        DIAM={_f(i.tube_diameter_m)} <meter> NPOINT={int(i.npoint)} NPHASE=1 PHASE=V  &\n"
        + (f"        INT-TOL={_f(i.integration_tolerance)}  &\n" if i.integration_tolerance is not None else "")
        + f"        IGN-CAT-VOL=NO  &\n"
        f"        CAT-PRESENT=YES BED-VOIDAGE={_f(i.bed_voidage)} CAT-RHO={_f(i.particle_density_kg_m3)} <kg/cum>  &\n"
        f"        {pd}\n"
        f"{extra}"
        f"    REACTIONS RXN-IDS={rxn_id}\n"
    )


def build_kinetic_reactor_input(i: KineticReactorInputs, spec: Optional[AspenPowerLawSpec] = None) -> str:
    """Standalone kinetic RPLUG model (+ RGibbs reference at the same T, P when requested)."""
    spec = spec or resolve_spec(i.catalyst_id, i.kinetic_form)
    title = f"AmCraX kinetic RPLUG - {i.case_id}"
    description = (
        f"Standalone packed-bed RPLUG with {spec.catalyst_id} kinetics (GENERAL POWERLAW, partial "
        f"pressures in bar, rate per kg catalyst, Aspen micro-reversibility), thermal mode {i.thermal_mode}. "
        f"Property method: {i.property_method}."
    )
    feed = i.seeded_feed()
    total = sum(feed.values())
    fs = ["FLOWSHEET", "    BLOCK RXR IN=KFEED OUT=KPROD"]
    if i.include_equilibrium_reference:
        fs.append("    BLOCK REQ IN=EQFEED OUT=EQPROD")
    flows = " / ".join(f"{c} {_f(v)}" for c, v in feed.items())
    out = [_HEADER.format(title=title, description=description), "\n".join(fs) + "\n",
           f"PROPERTIES {i.property_method}\n"]
    for sid in (["KFEED", "EQFEED"] if i.include_equilibrium_reference else ["KFEED"]):
        out.append(
            f"STREAM {sid}\n"
            f"    SUBSTREAM MIXED TEMP={_f(i.temperature_C)} PRES={_f(i.pressure_bar)}\n"
            f"    MOLE-FLOW {flows}\n"
        )
    out.append(rplug_block(i, "RXR"))
    if i.include_equilibrium_reference:
        out.append(
            "BLOCK REQ RGIBBS\n"
            f"    PARAM TEMP={_f(i.temperature_C)} PRES={_f(i.pressure_bar)}\n"
            "    PROD NH3 / H2 / N2 / H2O\n"
        )
    out.append(any_reactions_block(spec))
    out.append("STREAM-REPOR MOLEFLOW MOLEFRAC\n")
    _ = total
    return "\n".join(out)


# ----------------------------------------------------------------------------------------- extraction
_B = r"\Data\Blocks"
_S = r"\Data\Streams"


def _num(v: Any) -> Optional[float]:
    try:
        return None if v is None else float(v)
    except (TypeError, ValueError):
        return None


def _series(s, path: str) -> list[Optional[float]]:
    return [_num(s.get(path + "\\" + k)) for k in s.children(path)]


def _stream(s, sid: str) -> dict[str, Any]:
    o = rf"{_S}\{sid}\Output"
    return {
        "T_C": _num(s.get(rf"{o}\TEMP_OUT\MIXED")),
        "P_bar": _num(s.get(rf"{o}\PRES_OUT\MIXED")),
        "flows_kmol_h": {c: _num(s.get(rf"{o}\MOLEFLOW\MIXED\{c}", 0.0)) or 0.0 for c in COMPONENTS},
        "y": {c: _num(s.get(rf"{o}\MOLEFRAC\MIXED\{c}", 0.0)) or 0.0 for c in COMPONENTS},
    }


def extract_rplug(s, block_id: str = "RXR") -> dict[str, Any]:
    """Block results and axial profiles of an RPLUG block (values with the units Aspen reports)."""
    o = rf"{_B}\{block_id}\Output"
    duty, duty_u = s.get_with_unit(rf"{o}\QCALC")
    rt, rt_u = s.get_with_unit(rf"{o}\RES_TIME")
    ln, ln_u = s.get_with_unit(rf"{o}\LEN_REACTOR")
    prof: dict[str, Any] = {"length_m": _series(s, rf"{o}\LENGTH_PY"), "T_C": _series(s, rf"{o}\B_TEMP3")}
    # pressure / composition profiles: B_PRES\MIXED\<pt>, B_MOLEFRAC\MIXED\<comp>\<pt> (or <pt>\<comp>)
    pm = rf"{o}\B_PRES\MIXED"
    prof["P_bar"] = _series(s, pm)
    ym = rf"{o}\B_MOLEFRAC\MIXED"
    kids = s.children(ym)
    y: dict[str, list] = {}
    if kids and kids[0] in COMPONENTS:
        y = {c: _series(s, ym + "\\" + c) for c in kids}
    elif kids:
        for pt in kids:
            for c in s.children(ym + "\\" + pt):
                y.setdefault(c, []).append(_num(s.get(ym + "\\" + pt + "\\" + c)))
    prof["y"] = y
    prof["residence_time"] = _series(s, rf"{o}\TIME")
    return {
        "duty": _num(duty), "duty_unit": duty_u,
        "residence_time": _num(rt), "residence_time_unit": rt_u,
        "reactor_length": _num(ln), "reactor_length_unit": ln_u,
        "n_tubes": _num(s.get(rf"{o}\NTUBE")),
        "inlet_pressure_bar": _num(s.get(rf"{o}\IN_PRES")),
        "block_status_code": s.comp_status(rf"{_B}\{block_id}"),
        "block_messages": s.get(rf"{o}\BLKMSG"),
        "profiles": prof,
        "profile_units": {"length_m": s.get_with_unit(rf"{o}\LENGTH_PY\1")[1] if prof["length_m"] else None,
                          "T_C": s.get_with_unit(rf"{o}\B_TEMP3\1")[1] if prof["T_C"] else None,
                          "P_bar": s.get_with_unit(pm + "\\1")[1] if prof["P_bar"] else None},
    }


def extract_kinetic_case(s, i: KineticReactorInputs) -> dict[str, Any]:
    from amcrax.aspen.session import HAP_RESULTS_ERRORS, HAP_RESULTS_WARNINGS

    feed, prod = _stream(s, "KFEED"), _stream(s, "KPROD")
    n0_seeded = feed["flows_kmol_h"]["NH3"]
    n0_fresh = float(i.feed_kmol_h["NH3"])
    res: dict[str, Any] = {"feed": feed, "product": prod, "rplug": extract_rplug(s, "RXR")}
    nout = prod["flows_kmol_h"]["NH3"]
    res["conversion_of_reactor_inlet_NH3"] = 1.0 - nout / n0_seeded if n0_seeded else None
    res["conversion_of_fresh_NH3"] = 1.0 - nout / n0_fresh
    if i.include_equilibrium_reference:
        eq = _stream(s, "EQPROD")
        res["equilibrium_reference"] = {
            "block": "REQ (RGIBBS, same T, P, feed)", "product": eq,
            "conversion_of_reactor_inlet_NH3": 1.0 - eq["flows_kmol_h"]["NH3"] / n0_seeded,
            "duty_kW": _num(s.get(rf"{_B}\REQ\Output\QCALC")),
        }
    rt = res["rplug"]["residence_time"]
    if rt is not None and res["rplug"]["residence_time_unit"] in ("hr", "sec"):
        res["rplug"]["residence_time_s"] = rt * (3600.0 if res["rplug"]["residence_time_unit"] == "hr" else 1.0)
    code = res["rplug"]["block_status_code"]
    msgs = s.run_messages()
    res["status"] = {
        "rplug_has_errors": bool(code & HAP_RESULTS_ERRORS) or res["rplug"]["profiles"]["T_C"] == [],
        "rplug_has_warnings": bool(code & HAP_RESULTS_WARNINGS),
        "run_messages": msgs,
        "any_warning_text": any("WARNING" in m.upper() for m in msgs),
        "any_error_text": any("ERROR" in m.upper() for m in msgs),
    }
    return res


# ----------------------------------------------------------------------------------------- cases and runs
class KineticCase(BaseModel):
    """One driver case: a standalone RPLUG model or the full flowsheet with the RPLUG cracker."""
    configuration: Literal["standalone", "integrated"] = "standalone"
    reactor: KineticReactorInputs
    flowsheet: dict[str, Any] = Field(default_factory=dict)   # CaseInputs overrides (integrated only)

    @classmethod
    def from_json(cls, d: dict[str, Any]) -> "KineticCase":
        d = dict(d)
        conf = d.pop("configuration", "standalone")
        fs = d.pop("flowsheet", {}) or {}
        if conf == "integrated":
            d.setdefault("include_equilibrium_reference", False)
        return cls(configuration=conf, reactor=KineticReactorInputs(**d), flowsheet=fs)

    def case_inputs(self):
        from amcrax.schemas import CaseInputs

        kw = dict(self.flowsheet)
        kw.update(case_id=self.reactor.case_id, reactor_temperature_C=self.reactor.temperature_C,
                  reactor_pressure_bar=self.reactor.pressure_bar)
        return CaseInputs(**kw)

    def input_text(self, spec: Optional[AspenPowerLawSpec] = None) -> str:
        if self.configuration == "standalone":
            return build_kinetic_reactor_input(self.reactor, spec)
        from amcrax.aspen.inp_writer import build_flowsheet_input

        return build_flowsheet_input(self.case_inputs(), kinetic_cracker=self.reactor)


CRACKER_RPLUG_NOTE = ("kinetic RPLUG cracker: block_type, outlet temperature and pressure corrected from the "
                      "flowsheet-config RGibbs metadata (the generic extractor read RGibbs scalar paths); outlet T and "
                      "P are those of the cracker outlet stream S5 (Phase 2 task K1 item 5)")


def correct_cracker_block_entry(flowsheet_result: dict[str, Any], kinetic_out: dict[str, Any]) -> dict[str, Any]:
    """Label the integrated cracker as the RPLUG it is (the generic extractor uses the RGibbs flowsheet metadata).

    The duty (QCALC) is the RPLUG duty and is kept. B_TEMP / B_PRES are profile arrays in RPLUG, so the generic
    extractor stored 1.0 / 1.0; they are replaced by the outlet stream S5 values. Pure relabelling of stored values:
    no number is recomputed. Idempotent.
    """
    blocks = flowsheet_result.get("blocks") or {}
    cr = blocks.get("CRACKER")
    if cr is None:
        return flowsheet_result
    s5 = kinetic_out.get("cracker_outlet") or {}
    cr["block_type"] = "RPlug"
    cr["outlet_temperature_C"] = s5.get("T_C")
    cr["outlet_pressure_bar"] = s5.get("P_bar")
    det = cr.setdefault("details", {})
    det["model_note"] = CRACKER_RPLUG_NOTE
    rp = kinetic_out.get("rplug") or {}
    if rp.get("duty") is not None:
        det["rplug_duty_kW"] = rp.get("duty")
    return flowsheet_result


def extract_integrated_case(s, case: KineticCase, engine_time_s: float, model_file: str) -> dict[str, Any]:
    from amcrax.aspen.extract import extract_result

    out: dict[str, Any] = {"rplug": extract_rplug(s, "CRACKER")}
    s4, s5 = _stream(s, "S4"), _stream(s, "S5")
    out["cracker_inlet"], out["cracker_outlet"] = s4, s5
    n_in = s4["flows_kmol_h"]["NH3"]
    out["conversion_of_reactor_inlet_NH3"] = 1.0 - s5["flows_kmol_h"]["NH3"] / n_in if n_in else None
    try:
        sim = extract_result(s, case.case_inputs(), engine_time_s=engine_time_s, model_file=model_file)
        out["flowsheet_result"] = correct_cracker_block_entry(json.loads(sim.model_dump_json()), out)
        out["status"] = {"converged": sim.status.converged, "has_errors": sim.status.has_errors,
                         "has_warnings": sim.status.has_warnings, "run_messages": sim.status.messages}
    except Exception as exc:  # keep the kinetic results even if the flowsheet extractor rejects a node
        msgs = s.run_messages()
        out["flowsheet_result_error"] = str(exc)
        out["status"] = {"converged": None, "run_messages": msgs}
    return out


def _sanitise_bkp(path: Path) -> dict[str, Any]:
    """Apply aspen/automation/sanitise_models.py's run-status rewrite and check for identifiers/paths."""
    import getpass
    import re
    import socket

    run_status = re.compile(rb'(DSET RUN-STATUS VERS @VERS \(\s*"[^"]*"\s+"[^"]*"\s+"[^"]*"\s+)"([^"]*)"(\s+)"([^"]*)"')
    data = path.read_bytes()
    data, n = run_status.subn(rb'\1"user"\3"host"', data)
    ids = [v.encode() for v in (getpass.getuser(), socket.gethostname()) if v and len(v) >= 4]
    for ident in ids:
        for form in {ident, ident.lower(), ident.upper()}:
            data = data.replace(form, b"user")
    path.write_bytes(data)
    left = sum(data.count(f) for i in ids for f in {i, i.lower(), i.upper()})
    return {"run_status_records_rewritten": n, "identifiers_remaining": left}


def run_kinetic_cases(
    cases: list[KineticCase],
    *,
    study: str = "research_kinetic",
    timeout_s: float = 300.0,
    save_models: bool = True,
    on_result=None,
    session_hook=None,
) -> list[dict[str, Any]]:
    """Run cases sequentially in one locked Aspen session; one fresh input file per case."""
    import time as _time

    from amcrax.aspen.runner import _rel, aspen_lock
    from amcrax.aspen.session import AspenError, AspenSession
    from amcrax.paths import ASPEN_MODELS, ASPEN_RUNS, ensure_dirs

    ensure_dirs()
    run_dir = ASPEN_RUNS / study
    run_dir.mkdir(parents=True, exist_ok=True)
    model_dir = ASPEN_MODELS / "research"
    model_dir.mkdir(parents=True, exist_ok=True)
    results = []
    with aspen_lock():
        with AspenSession() as s:
            for case in cases:
                cid = case.reactor.case_id
                rec: dict[str, Any] = {"case_id": cid, "configuration": case.configuration}
                try:
                    spec = resolve_spec(case.reactor.catalyst_id, case.reactor.kinetic_form)
                    rec["kinetic_spec"] = spec.model_dump()
                    text = case.input_text(spec)
                    inp = run_dir / f"{cid}.inp"
                    if inp.resolve().parent != run_dir.resolve():
                        raise ValueError(f"case_id {cid!r} does not map to a file inside the run directory")
                    inp.write_text(text, encoding="ascii")
                    (model_dir / f"{cid}.inp").write_text(text, encoding="ascii")
                    s.open(inp)
                    t0 = _time.time()
                    elapsed = s.run(timeout_s=timeout_s, reinit=True)
                    if case.configuration == "standalone":
                        rec["aspen"] = extract_kinetic_case(s, case.reactor)
                    else:
                        rec["aspen"] = extract_integrated_case(s, case, round(elapsed, 3), _rel(inp))
                    rec["engine_time_s"] = round(elapsed, 3)
                    rec["model_inp"] = _rel(model_dir / f"{cid}.inp")
                    if save_models:
                        bkp = s.save_as(model_dir / f"{cid}.bkp")
                        rec["model_bkp"] = _rel(bkp)
                        rec["model_bkp_sanitised"] = _sanitise_bkp(bkp)
                    if session_hook is not None:
                        session_hook(s, case)
                    st = rec["aspen"].get("status", {})
                    bad = st.get("rplug_has_errors") or st.get("has_errors") or not rec["aspen"]["rplug"]["profiles"]["T_C"]
                    rec["run_status"] = "error" if bad else ("ok_with_warnings" if (st.get("rplug_has_warnings") or st.get("has_warnings")) else "ok")
                    _ = t0
                except (AspenError, ValueError, RuntimeError) as exc:
                    rec["run_status"] = "failed"
                    rec["error"] = str(exc)
                results.append(rec)
                if on_result is not None:
                    on_result(rec, case)
    return results
