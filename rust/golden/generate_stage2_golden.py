"""Generate the stage 2 golden reference tables (rate laws, viscosity, plug-flow reactor) for the Rust engine.

Produced ONCE by the Python reference (the ``amcrax`` package of this repository, imported from ``backend/``)
and committed; never regenerated from Rust. Run from the repository root with the project venv:

    python rust/golden/generate_stage2_golden.py

Writes rust/golden/stage2/*.json (+ MANIFEST.json) and the transport data file the Rust engine embeds,
rust/data/transport_gri30.json (Cantera's pure-species viscosity polynomials and molar masses for the
species of the reactor model, exported programmatically from Cantera's gri30.yaml; no manual typing).

Instrumentation (recording only, results unchanged): ``scipy.optimize.brentq`` (iterations, calls) in the
rate laws, and ``solve_ivp`` in the reactor (nfev, njev, nlu, status: LSODA's Jacobian evaluations show
where it switched to its stiff BDF method).
"""

from __future__ import annotations

import hashlib
import json
import math
import os
import platform
import sys
import warnings
from pathlib import Path

HERE = Path(__file__).resolve().parent
RUST_DIR = HERE.parent
REPO = RUST_DIR.parent
os.environ["AMCRAX_ROOT"] = str(REPO)
sys.path.insert(0, str(REPO / "backend"))

import cantera as ct  # noqa: E402
import numpy as np  # noqa: E402
import scipy  # noqa: E402
import scipy.optimize  # noqa: E402
import yaml  # noqa: E402

import amcrax  # noqa: E402

if Path(amcrax.__file__).resolve().parents[1] != (REPO / "backend").resolve():
    raise SystemExit(f"amcrax imported from {amcrax.__file__}, not from {REPO / 'backend'}")

from amcrax.kinetics import rate_laws as rl  # noqa: E402
from amcrax.reactor import pfr  # noqa: E402
from amcrax.thermodynamics import equilibrium as eq  # noqa: E402

OUT = HERE / "stage2"
TRANSPORT = RUST_DIR / "data" / "transport_gri30.json"
GENERATOR = "rust/golden/generate_stage2_golden.py"
CATS = ["ni_takahashi_microkinetic", "ru_takahashi_microkinetic", "ru_kum_temkin_pyzhev",
        "nire_ceo2_5ni1ru_lucentini_lhhw", "nire_ceo2_2p5ni0p5ru_lucentini_lhhw"]


def _git_rev() -> str:
    try:
        import subprocess
        return subprocess.run(["git", "rev-parse", "HEAD"], cwd=REPO, capture_output=True, text=True,
                              check=True).stdout.strip()
    except Exception:  # noqa: BLE001
        return "unknown"


META = {"generator": GENERATOR, "python": platform.python_version(), "numpy": np.__version__,
        "scipy": scipy.__version__, "cantera": ct.__version__, "pyyaml": yaml.__version__,
        "platform": f"{platform.system()} {platform.machine()}", "amcrax_source": "backend/amcrax (this repository)",
        "git_head_at_generation": _git_rev()}


def enc(o):
    if isinstance(o, dict):
        return {str(k): enc(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [enc(v) for v in o]
    if isinstance(o, np.ndarray):
        return enc(o.tolist())
    if isinstance(o, (bool, np.bool_)):
        return bool(o)
    if isinstance(o, (int, np.integer)):
        return int(o)
    if isinstance(o, (float, np.floating)):
        f = float(o)
        if math.isnan(f):
            return "nan"
        if math.isinf(f):
            return "inf" if f > 0 else "-inf"
        return f
    return o


MANIFEST = {"meta": META, "files": {}}


def write_table(name: str, body: dict) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    text = json.dumps(enc({"meta": dict(META, table=name), **body}), separators=(",", ":"), allow_nan=False) + "\n"
    data = text.encode("utf-8")
    (OUT / f"{name}.json").write_bytes(data)
    MANIFEST["files"][f"{name}.json"] = {"sha256": hashlib.sha256(data).hexdigest(), "bytes": len(data)}
    print(f"wrote rust/golden/stage2/{name}.json ({len(data)} bytes)")


def err(e: BaseException) -> dict:
    return {"error": type(e).__name__, "message": str(e)}


_BRENT: list[dict] = []
_orig_brentq = scipy.optimize.brentq


def _rec_brentq(f, a, b, *args, **kw):
    kw.pop("full_output", None)
    root, info = _orig_brentq(f, a, b, *args, full_output=True, **kw)
    _BRENT.append({"a": a, "b": b, "iterations": info.iterations, "function_calls": info.function_calls})
    return root


rl.brentq = _rec_brentq

_IVP: list[dict] = []
_orig_ivp = pfr.solve_ivp


def _rec_ivp(*args, **kw):
    sol = _orig_ivp(*args, **kw)
    _IVP.append({"nfev": int(sol.nfev), "njev": int(sol.njev), "nlu": int(sol.nlu), "status": int(sol.status),
                 "n_t": len(sol.t)})
    return sol


pfr.solve_ivp = _rec_ivp


# ------------------------------------------------------------------------------------------ 1. rate laws
def partial_pressures(feed: dict, X: float, P: float) -> dict:
    F = dict(feed)
    F0 = feed["NH3"]
    F["NH3"] = F0 * (1.0 - X)
    F["N2"] = feed.get("N2", 0.0) + 0.5 * F0 * X
    F["H2"] = feed.get("H2", 0.0) + 1.5 * F0 * X
    tot = sum(F.values())
    return {s: v / tot * P for s, v in F.items()}


def rate_case(cid, T, p, **kw) -> dict:
    c = {"catalyst_id": cid, "T_K": T, "p_bar": p,
         "approach_factor": kw.get("approach_factor"), "keq_basis": kw.get("keq_basis", "published"),
         "param_overrides": kw.get("param_overrides")}
    n0 = len(_BRENT)
    try:
        c["rate"] = rl.rate_mol_per_kgcat_s(cid, T, p, **kw)
        c["brentq"] = _BRENT[-1] if len(_BRENT) > n0 else None
    except Exception as e:  # noqa: BLE001
        c["rate"] = err(e)
    return c


OVERRIDES = {
    "takahashi_microkinetic": [{"A2": 5.0e15, "Ea2": 140.0}, {"Ea4": 100.0, "A6": 1e6}],
    "lhhw_lucentini": [{"k0": 4.5e6, "Ek": 120.0}, {"K1": 0.9, "K4": 0.05}],
    "temkin_pyzhev": [{"beta": 0.3}, {"ko": 60000.0, "Ea": 110000.0}],
}


def gen_kinetics() -> None:
    feeds = {"pure_nh3": {"NH3": 1.0}, "wet_nh3": {"NH3": 0.998, "H2O": 0.002},
             "h2_cofeed": {"NH3": 0.6, "H2": 0.3, "N2": 0.1}, "argon_diluted": {"NH3": 0.1, "Ar": 0.9}}
    Ts = [573.15, 623.15, 673.15, 723.15, 773.15, 823.15, 873.15, 923.15, 973.15, 1073.15]
    Ps = [1.0, 1.01325, 5.0, 20.0, 50.0]
    Xs = [0.0, 1e-9, 1e-6, 0.01, 0.1, 0.5, 0.9, 0.99, 0.999]
    cases = []
    for cid in CATS:
        form = rl.get_catalyst(cid).form
        if form == "temkin_pyzhev":
            opts = [{"keq_basis": "published"}, {"keq_basis": "amcrax_thermo"}]
        else:
            opts = [{}, {"approach_factor": False}, {"approach_factor": True}]
        for fname, feed in feeds.items():
            for T in Ts:
                for P in Ps:
                    Xe = eq.solve_equilibrium(T, P, {k: v for k, v in feed.items() if k != "Ar"}
                                              | ({"O2": feed["Ar"]} if "Ar" in feed else {})).conversion
                    for X in Xs + [Xe * (1 - 1e-6), Xe, min(Xe * (1 + 1e-6), 1.0)]:
                        p = partial_pressures(feed, X, P)
                        for o in opts:
                            c = rate_case(cid, T, p, **o)
                            c.update(feed_name=fname, X=X, X_eq=Xe)
                            cases.append(c)
        # overrides (None leaves results bit-identical; given values replace registry values)
        for ov in OVERRIDES[form]:
            for T in (673.15, 873.15):
                p = partial_pressures(feeds["h2_cofeed"], 0.3, 20.0)
                cases.append(rate_case(cid, T, p, param_overrides=ov) | {"feed_name": "h2_cofeed", "X": 0.3})
    # edge cases
    edge = []
    for cid in CATS:
        for p in ({"NH3": 1.0}, {"NH3": 0.0, "H2": 0.75, "N2": 0.25}, {"NH3": 1.0, "H2": 0.0, "N2": 0.0},
                  {"NH3": -0.1, "H2": 0.5, "N2": 0.2}, {"NH3": 0.0}, {"NH3": 0.5, "H2": 0.3, "N2": 0.1, "Ar": 2.0},
                  {"NH3": 1e-300, "H2": 1e-300, "N2": 1e-300}, {"H2": 1.0}):
            for o in ({}, {"approach_factor": False}, {"keq_basis": "amcrax_thermo"}):
                edge.append(rate_case(cid, 773.15, p, **o))
    edge.append(rate_case("no_such_catalyst", 773.15, {"NH3": 1.0}))
    # helper functions
    helpers = {"kum_keq": [], "reaction_quotient": [], "takahashi": [], "lucentini_g": []}
    for T in Ts:
        helpers["kum_keq"].append({"T_K": T, "published": rl.kum_keq(T, "published"),
                                   "amcrax_thermo": rl.kum_keq(T, "amcrax_thermo")})
        for cid in CATS[:2]:
            k = rl.takahashi_constants(cid, T)
            for yn, yh in ((1.0, 0.0), (0.5, 0.3), (0.01, 0.7), (1e-8, 0.75)):
                cov = rl.takahashi_coverages(cid, T, yn, yh)
                helpers["takahashi"].append({"catalyst_id": cid, "T_K": T, "y_NH3": yn, "y_H2": yh,
                                             "constants": k, "coverages": cov, "brentq": _BRENT[-1]})
        for cid in CATS[3:]:
            p = {"NH3": 0.4, "H2": 0.45, "N2": 0.15}
            helpers["lucentini_g"].append({"catalyst_id": cid, "T_K": T, "p_bar": p,
                                           "rate_mol_per_g_s": rl.lucentini_rate_mol_per_g_s(cid, T, p)})
    for p in ({"NH3": 1.0, "H2": 3.0, "N2": 1.0}, {"NH3": 0.0, "H2": 1.0}, {"NH3": 2.0, "N2": -1.0, "H2": 1.0}):
        helpers["reaction_quotient"].append({"p_bar": p, "Q": rl.reaction_quotient(p)})
    write_table("kinetics", {
        "gate": {"rule": "relative", "tol": 1e-12,
                 "why": "closed forms in the same operation order; Takahashi coverages by the same brentq (xtol "
                        "1e-14, rtol 1e-13) on ln theta_s; libm exp/log/pow ulps only"},
        "unit_conversions": rl._registry()["unit_conversions"], "cases": cases, "edge_cases": edge,
        "helpers": helpers})


# ------------------------------------------------------------------------------------------ 2. viscosity
VISC_SPECIES = ["NH3", "H2", "N2", "H2O", "O2", "AR"]


def gen_viscosity() -> None:
    gas = ct.Solution("gri30.yaml")
    sp = {}
    for s in VISC_SPECIES:
        k = gas.species_index(s)
        sp[s] = {"index": k, "molecular_weight_kg_kmol": float(gas.molecular_weights[k]),
                 "viscosity_polynomial": [float(c) for c in gas.get_viscosity_polynomial(k)]}
    transport = {
        "provenance": {"source": "Cantera gri30.yaml (GRI-Mech 3.0 transport data), mixture-averaged model",
                       "cantera_version": ct.__version__, "transport_model": gas.transport_model,
                       "extracted_by": GENERATOR + " (programmatic export, no manual typing)",
                       "form": "sqrt(mu_k) = T^(1/4) * sum_{n=0..4} c_n (ln T)^n, mu in Pa s (Cantera "
                               "GasTransport::updateSpeciesViscosities); mixture: Wilke rule as Cantera "
                               "MixTransport::viscosity, phi_kj = (1 + sqrt(mu_k/mu_j) (M_j/M_k)^(1/4))^2 / "
                               "sqrt(8 (1 + M_k/M_j))"},
        "species": sp}
    TRANSPORT.parent.mkdir(parents=True, exist_ok=True)
    tdata = (json.dumps(transport, indent=1) + "\n").encode("utf-8")
    TRANSPORT.write_bytes(tdata)
    print(f"wrote rust/data/transport_gri30.json ({len(tdata)} bytes)")
    pure, mix = [], []
    Ts = [300.0 + 25.0 * i for i in range(49)]  # 300 .. 1500 K
    for T in Ts:
        gas.TPX = T, 1e5, "N2:1"
        sv = gas.species_viscosities
        pure.append({"T_K": T, "mu_Pa_s": {s: float(sv[gas.species_index(s)]) for s in VISC_SPECIES}})
    comps = []
    for feed in ({"NH3": 99.8, "H2O": 0.2}, {"NH3": 100.0}, {"NH3": 60.0, "H2": 30.0, "N2": 10.0},
                 {"NH3": 10.0, "Ar": 90.0}):
        for X in (0.0, 0.3, 0.7, 0.99, 1.0):
            F = dict(feed)
            F["NH3"] = feed["NH3"] * (1 - X)
            F["N2"] = feed.get("N2", 0.0) + 0.5 * feed["NH3"] * X
            F["H2"] = feed.get("H2", 0.0) + 1.5 * feed["NH3"] * X
            tot = sum(F.values())
            comps.append({s: v / tot for s, v in F.items()})
    comps += [{"H2": 1.0}, {"NH3": 1.0}, {"H2O": 1.0}, {"O2": 0.21, "N2": 0.79}, {"NH3": 0.5, "H2": 0.0, "N2": 0.5}]
    for T in Ts[::2]:
        for P in (1.0, 20.0, 100.0):
            for y in comps:
                mix.append({"T_K": T, "P_bar": P, "y": y, "mu_Pa_s": pfr.gas_viscosity_Pa_s(T, P, y)})
    write_table("viscosity", {
        "gate": {"rule": "relative", "tol": 1e-10,
                 "why": "the same polynomials and the same Wilke formula; Cantera evaluates the polynomial and "
                        "the mole-fraction normalisation in a different order (~1e-14) and adds 1e-20 to every "
                        "mole fraction of its 53 species (relative effect < 1e-18)"},
        "transport_file": "rust/data/transport_gri30.json",
        "transport_sha256": hashlib.sha256(tdata).hexdigest(), "pure": pure, "mixture": mix})


# ------------------------------------------------------------------------------------------ 3. PFR
def pfr_record(r) -> dict:
    d = r.to_dict()
    d.pop("assumptions", None)
    return d


def pfr_case(cid, W, name, **kw) -> dict:
    c = {"id": name, "catalyst_id": cid, "W_kg": W, "kwargs": kw}
    n0 = len(_IVP)
    try:
        r = pfr.simulate_pfr(cid, W, **kw)
        c["result"] = pfr_record(r)
        c["assumptions"] = r.assumptions
        c["ivp"] = _IVP[n0:]
    except Exception as e:  # noqa: BLE001
        c["result"] = err(e)
    return c


def parity_cases() -> list[dict]:
    tv = json.loads((REPO / "results" / "research" / "simulator" / "test_vectors.json").read_text(encoding="utf-8"))
    out = []
    for v in tv["vectors"]:
        if v["kind"] != "pfr":
            continue
        i = v["inputs"]
        kw = {"T_in_C": i["T_in_C"], "P_in_bar": i["P_in_bar"], "mode": i["mode"], "n_points": 11,
              "pressure_drop": i["pressure_drop"]}
        if i["T_wall_C"] is not None:
            kw["T_wall_C"] = i["T_wall_C"]
            kw["U_W_m2K"] = i["U_W_m2K"]
        if "_nt" in v["id"]:
            kw["n_tubes"] = i["n_tubes"]
        c = pfr_case(i["catalyst_id"], i["W_kg"], v["id"], **kw)
        c["stored_browser_vector"] = {"conversion": v["python"]["conversion"], "outlet": v["python"]["outlet"]}
        tight = pfr.simulate_pfr(i["catalyst_id"], i["W_kg"], rtol=1e-11, atol=1e-14, **kw)
        c["tight_reference"] = {"rtol": 1e-11, "atol": 1e-14, "conversion": tight.conversion, "T_K": tight.T_K,
                                "P_bar": tight.P_bar}
        out.append(c)
    return out


def wider_cases() -> list[dict]:
    out = []
    for cid in CATS:
        for mode, extra in (("isothermal", {}), ("adiabatic", {}), ("external", {"T_wall_C": 700.0, "U_W_m2K": 150.0})):
            for dp in (False, True):
                for (T, P, W) in ((550.0, 5.0, 30.0), (650.0, 30.0, 300.0)):
                    kw = {"T_in_C": T, "P_in_bar": P, "mode": mode, "pressure_drop": dp, "n_points": 21,
                          "n_tubes": 40, **extra}
                    name = f"{cid}_{mode}_T{T:g}_P{P:g}_W{W:g}{'_dp' if dp else ''}"
                    out.append(pfr_case(cid, W, name, **kw))
    special = [
        ("ru_kum_temkin_pyzhev", 50.0, "kum_published_keq", {"keq_basis": "published", "T_in_C": 550.0, "P_in_bar": 10.0}),
        ("ru_kum_temkin_pyzhev", 50.0, "kum_h2_cofeed_no_seed", {"feed_kmol_h": {"NH3": 90.0, "H2": 10.0}, "T_in_C": 550.0}),
        ("ru_kum_temkin_pyzhev", 50.0, "kum_xseed_1e-4", {"x_seed": 1e-4, "T_in_C": 550.0, "P_in_bar": 10.0}),
        ("ni_takahashi_microkinetic", 100.0, "tni_no_approach", {"approach_factor": False, "P_in_bar": 20.0}),
        ("nire_ceo2_5ni1ru_lucentini_lhhw", 100.0, "luc5_no_approach", {"approach_factor": False}),
        ("ru_takahashi_microkinetic", 80.0, "tru_mixed_feed_ar",
         {"feed_kmol_h": {"NH3": 70.0, "H2": 5.0, "N2": 5.0, "H2O": 1.0, "Ar": 19.0}, "mode": "adiabatic",
          "T_in_C": 620.0, "n_tubes": 20}),
        ("ru_takahashi_microkinetic", 80.0, "tru_user_bed",
         {"eps_b": 0.4, "rho_particle_kg_m3": 1200.0, "dp_m": 0.003, "tube_inner_diameter_m": 0.05, "n_tubes": 30}),
        # hydraulic limit (narrow single tube, long bed): stop before W, also with a terminal state appended
        ("ni_takahashi_microkinetic", 2000.0, "tni_hydraulic_limit", {"n_tubes": 1, "P_in_bar": 5.0, "n_points": 41}),
        ("ru_kum_temkin_pyzhev", 3000.0, "kum_hydraulic_limit", {"n_tubes": 1, "P_in_bar": 3.0, "n_points": 41}),
        ("nire_ceo2_2p5ni0p5ru_lucentini_lhhw", 1500.0, "luc25_hydraulic_limit_adiabatic",
         {"n_tubes": 1, "P_in_bar": 4.0, "mode": "adiabatic", "T_in_C": 650.0, "n_points": 41}),
        ("ru_takahashi_microkinetic", 50.0, "tru_201_points_default", {}),
        # input errors and limits
        ("ru_takahashi_microkinetic", 10.0, "err_mode", {"mode": "fired"}),
        ("ru_takahashi_microkinetic", 10.0, "err_external_no_wall", {"mode": "external"}),
        ("ru_takahashi_microkinetic", 10.0, "err_negative_pressure", {"P_in_bar": -1.0}),
        ("ru_takahashi_microkinetic", 10.0, "err_T_outside_nasa", {"T_in_C": 6000.0, "pressure_drop": False}),
        ("ru_takahashi_microkinetic", 0.0, "zero_catalyst_mass", {"n_points": 3}),
        ("no_such_catalyst", 10.0, "err_unknown_catalyst", {}),
    ]
    for cid, W, name, kw in special:
        kw = {"n_points": 21, **kw}
        out.append(pfr_case(cid, W, name, **kw))
    return out


def gen_pfr() -> None:
    write_table("pfr", {
        "gate": {"outlet_conversion_abs": 1e-7, "outlet_T_K_abs": 1e-4, "outlet_P_bar_abs": 1e-6,
                 "profile_conversion_abs": 1e-6,
                 "why": "Python integrates with LSODA (rtol 1e-8, atol 1e-12); Rust with DOPRI5 at tighter "
                        "tolerances; the gates bound the global error of both. tight_reference (LSODA at rtol "
                        "1e-11) separates the LSODA error from the port's error."},
        "parity_cases": parity_cases(), "cases": wider_cases()})


# ------------------------------------------------------------------------------------------ 4. derived searches
BED = {"ru_kum_temkin_pyzhev": (0.36, 980.0), "nire_ceo2_5ni1ru_lucentini_lhhw": (0.36, 1651.8),
       "nire_ceo2_2p5ni0p5ru_lucentini_lhhw": (0.36, 1651.8), "ni_takahashi_microkinetic": (0.36, 980.0),
       "ru_takahashi_microkinetic": (0.36, 980.0)}


def temperature_for_conversion(cid, W, P, X_t):
    """scripts/research/kinetics_studies.py lines 163-174 (run, g, bracket check, brentq xtol 0.05)."""
    eps, rho = BED[cid]

    def g(T):
        return pfr.simulate_pfr(cid, W, T_in_C=T, P_in_bar=P, feed_kmol_h={"NH3": 100.0}, mode="isothermal",
                                pressure_drop=False, eps_b=eps, rho_particle_kg_m3=rho,
                                n_points=2).outlet["conversion"] - X_t
    T_lo, T_hi = 300.0, 900.0
    try:
        ok = g(T_lo) < 0 < g(T_hi)
    except Exception:  # noqa: BLE001
        ok = False
    if not ok:
        return {"ok": False, "T_required_C": float("nan")}
    root, info = _orig_brentq(g, T_lo, T_hi, xtol=0.05, full_output=True)
    return {"ok": True, "T_required_C": root, "iterations": info.iterations}


def gen_searches() -> None:
    mass = []
    for cid in CATS:
        eps, rho = BED[cid]
        base = {"T_in_C": 600.0, "P_in_bar": 20.0, "feed_kmol_h": {"NH3": 100.0}, "mode": "isothermal",
                "pressure_drop": False, "eps_b": eps, "rho_particle_kg_m3": rho}
        specs = [("frac0.9", {"fraction_of_equilibrium": 0.9}, base),
                 ("frac0.99", {"fraction_of_equilibrium": 0.99}, base),
                 ("abs0.5_T500", {"target_conversion": 0.5}, {**base, "T_in_C": 500.0}),
                 ("unreachable_Wmax", {"target_conversion": 0.95, "W_max_kg": 1.0}, base),
                 ("above_equilibrium", {"target_conversion": 0.9999}, {**base, "T_in_C": 450.0}),
                 ("hydraulic_unreachable", {"target_conversion": 0.99},
                  {**base, "pressure_drop": True, "n_tubes": 1, "P_in_bar": 5.0}),
                 ("hydraulic_reachable", {"target_conversion": 0.3},
                  {**base, "pressure_drop": True, "n_tubes": 1, "P_in_bar": 5.0}),
                 ("adiabatic_dp", {"target_conversion": 0.4},
                  {**base, "mode": "adiabatic", "pressure_drop": True, "n_tubes": 50, "T_in_C": 650.0})]
        for name, tgt, kw in specs:
            c = {"catalyst_id": cid, "name": name, "target": tgt, "kwargs": kw}
            try:
                with warnings.catch_warnings():
                    warnings.simplefilter("ignore")
                    c["result"] = pfr.catalyst_mass_for_conversion(cid, return_details=True, **tgt, **kw)
            except Exception as e:  # noqa: BLE001
                c["result"] = err(e)
            mass.append(c)
            print(f"  mass {cid} {name}: {c['result'].get('W_kg', c['result'])}")
    temps = []
    for P in (1.01325, 20.0):
        for W in (100.0, 1000.0):
            for cid in CATS:
                for X in (0.95, 0.99):
                    r = temperature_for_conversion(cid, W, P, X)
                    temps.append({"catalyst_id": cid, "P_bar": P, "W_kg": W, "X_target": X, "bed": BED[cid], **r})
                    print(f"  T {cid} P={P} W={W} X={X}: {r['T_required_C']}")
    write_table("searches", {
        "gate": {"catalyst_mass_rel": 1e-5, "temperature_abs_K": 0.05, "flags": "identical",
                 "why": "catalyst mass: brentq xtol 1e-6 W, rtol 1e-6 on the outlet conversion; temperature: "
                        "brentq xtol 0.05 K (scripts/research/kinetics_studies.py)"},
        "catalyst_mass": mass, "temperature_for_conversion": temps})


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    gen_kinetics()
    gen_viscosity()
    gen_pfr()
    gen_searches()
    text = json.dumps(enc(MANIFEST), indent=1, sort_keys=True) + "\n"
    (OUT / "MANIFEST.json").write_bytes(text.encode("utf-8"))
    print("wrote rust/golden/stage2/MANIFEST.json")


if __name__ == "__main__":
    main()
