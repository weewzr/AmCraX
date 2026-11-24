"""Generate the stage 1 golden reference tables (data loading, thermodynamics) for the Rust engine.

The tables are produced ONCE by the Python reference implementation (the ``amcrax`` package of this
repository, imported from ``backend/``) and committed. They are never regenerated from Rust. The Rust
checks (``amcrax_engine::verify``, run by ``cargo test`` and ``amcrax verify thermo``) read them, check
the SHA-256 recorded in MANIFEST.json and compare the Rust results with the gate each table states.

Run from the repository root with the project virtual environment:

    python rust/golden/generate_stage1_golden.py

The script refuses to run unless ``amcrax`` is imported from this repository's ``backend/``.
Floats are written with repr() (shortest round-trip form); non-finite floats as "nan", "inf", "-inf".
Python exceptions raised by the reference are recorded as {"error": <class name>, "message": ...}.

Instrumentation: ``scipy.optimize.brentq`` is wrapped (``full_output=True``) only to RECORD the bracket,
iteration count and function-call count of each call; the wrapper returns the same root, so the
recorded results are those of the unmodified reference. ``peng_robinson.dew_liquid`` is wrapped the
same way to record the dew-point scan (which scan temperature failed, the value of S - 1 at the others).
"""

from __future__ import annotations

import hashlib
import json
import math
import os
import platform
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
RUST_DIR = HERE.parent
REPO = RUST_DIR.parent
os.environ["AMCRAX_ROOT"] = str(REPO)
sys.path.insert(0, str(REPO / "backend"))

import numpy as np  # noqa: E402
import scipy  # noqa: E402
import scipy.optimize  # noqa: E402
import yaml  # noqa: E402

import amcrax  # noqa: E402

if Path(amcrax.__file__).resolve().parents[1] != (REPO / "backend").resolve():
    raise SystemExit(f"amcrax imported from {amcrax.__file__}, not from {REPO / 'backend'}")

from amcrax.economics import reference as ref  # noqa: E402
from amcrax.thermodynamics import equilibrium as eq  # noqa: E402
from amcrax.thermodynamics import nasa7  # noqa: E402
from amcrax.thermodynamics import peng_robinson as pr  # noqa: E402

OUT = HERE / "stage1"
GENERATOR = "rust/golden/generate_stage1_golden.py"
COMPONENTS = ("NH3", "H2", "N2", "H2O", "O2")


def _git_rev() -> str:
    try:
        import subprocess
        return subprocess.run(["git", "rev-parse", "HEAD"], cwd=REPO, capture_output=True, text=True,
                              check=True).stdout.strip()
    except Exception:  # noqa: BLE001
        return "unknown"


META = {
    "generator": GENERATOR,
    "python": platform.python_version(),
    "numpy": np.__version__,
    "scipy": scipy.__version__,
    "pyyaml": yaml.__version__,
    "platform": f"{platform.system()} {platform.machine()}",
    "amcrax_source": "backend/amcrax (this repository)",
    "git_head_at_generation": _git_rev(),
}


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


def write_json(rel: str, body, *, canonical: bool = False) -> str:
    path = OUT / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    if canonical:
        text = json.dumps(body, sort_keys=True, indent=1, ensure_ascii=False, allow_nan=False) + "\n"
    else:
        text = json.dumps(enc(body), separators=(",", ":"), allow_nan=False) + "\n"
    data = text.encode("utf-8")
    path.write_bytes(data)
    h = hashlib.sha256(data).hexdigest()
    MANIFEST["files"][rel] = {"sha256": h, "bytes": len(data)}
    print(f"wrote rust/golden/stage1/{rel} ({len(data)} bytes)")
    return h


def write_table(name: str, body: dict) -> None:
    write_json(f"{name}.json", {"meta": dict(META, table=name), **body})


def err(e: BaseException) -> dict:
    return {"error": type(e).__name__, "message": str(e)}


# ----------------------------------------------------------------------------------- instrumentation
_BRENT_LOG: list[dict] = []
_orig_brentq = scipy.optimize.brentq


def _rec_brentq(f, a, b, *args, **kw):
    kw.pop("full_output", None)
    root, info = _orig_brentq(f, a, b, *args, full_output=True, **kw)
    _BRENT_LOG.append({"a": a, "b": b, "root": root, "iterations": info.iterations,
                       "function_calls": info.function_calls, "converged": bool(info.converged)})
    return root


eq.brentq = _rec_brentq            # module-level import in equilibrium.py
scipy.optimize.brentq = _rec_brentq  # local imports inside peng_robinson functions


def last_brent() -> dict | None:
    return dict(_BRENT_LOG[-1]) if _BRENT_LOG else None


# ----------------------------------------------------------------------------------- 1. data files
CORE = [
    ("null", re.compile(r"^(?:~|null|Null|NULL|)$")),
    ("bool", re.compile(r"^(?:true|True|TRUE|false|False|FALSE)$")),
    ("int", re.compile(r"^(?:[-+]?[0-9]+|0o[0-7]+|0x[0-9a-fA-F]+)$")),
    ("float", re.compile(r"^(?:[-+]?(?:\.[0-9]+|[0-9]+(?:\.[0-9]*)?)(?:[eE][-+]?[0-9]+)?"
                         r"|[-+]?\.(?:inf|Inf|INF)|\.(?:nan|NaN|NAN))$")),
]
T11 = {"tag:yaml.org,2002:null": "null", "tag:yaml.org,2002:bool": "bool", "tag:yaml.org,2002:int": "int",
       "tag:yaml.org,2002:float": "float", "tag:yaml.org,2002:str": "str",
       "tag:yaml.org,2002:timestamp": "timestamp"}


def core_value(s: str):
    """Value of a plain scalar under the YAML 1.2 core schema."""
    for name, rx in CORE:
        if rx.match(s):
            if name == "null":
                return "null", None
            if name == "bool":
                return "bool", s.lower() == "true"
            if name == "int":
                if s.startswith("0o"):
                    return "int", int(s[2:], 8)
                if s.startswith("0x"):
                    return "int", int(s[2:], 16)
                return "int", int(s, 10)
            low = s.lower()
            if low.endswith("inf"):
                return "float", float("-inf") if s.startswith("-") else float("inf")
            if low.endswith("nan"):
                return "float", float("nan")
            return "float", float(s)
    return "str", s


def yaml_differences(text: str) -> list[dict]:
    """Plain scalars whose PyYAML (YAML 1.1) value differs from the YAML 1.2 core-schema value."""
    node = yaml.compose(text, Loader=yaml.SafeLoader)
    out: list[dict] = []
    loader = yaml.SafeLoader("")

    def walk(n, path):
        if isinstance(n, yaml.ScalarNode):
            if n.style is None:
                t11 = T11.get(n.tag, n.tag)
                v11 = loader.construct_object(n, deep=True)
                t12, v12 = core_value(n.value)
                same = t11 == t12 and (v11 == v12 or (isinstance(v11, float) and isinstance(v12, float)
                                                      and math.isnan(v11) and math.isnan(v12)))
                if not same:
                    out.append({"path": path, "line": n.start_mark.line + 1, "text": n.value,
                                "yaml11_type": t11, "yaml11_value": v11 if t11 != "timestamp" else str(v11),
                                "yaml12_core_type": t12, "yaml12_core_value": v12})
            return
        if isinstance(n, yaml.SequenceNode):
            for i, v in enumerate(n.value):
                walk(v, path + [i])
        elif isinstance(n, yaml.MappingNode):
            for k, v in n.value:
                if not (isinstance(k, yaml.ScalarNode) and k.tag == "tag:yaml.org,2002:str"):
                    out.append({"path": path, "line": k.start_mark.line + 1, "text": getattr(k, "value", "?"),
                                "yaml11_type": "non-string key", "yaml12_core_type": "?"})
                walk(v, path + [k.value])

    walk(node, [])
    return out


def gen_data() -> None:
    data_dir = REPO / "backend" / "amcrax" / "data"
    files = []
    for p in sorted(data_dir.iterdir()):
        if p.suffix not in (".yaml", ".json"):
            continue
        raw = p.read_bytes()
        rel = f"backend/amcrax/data/{p.name}"
        if p.suffix == ".yaml":
            value = yaml.safe_load(raw.decode("utf-8"))
            diffs = yaml_differences(raw.decode("utf-8"))
            parser = f"PyYAML {yaml.__version__} yaml.safe_load (YAML 1.1 resolver)"
        else:
            value = json.loads(raw.decode("utf-8"))
            diffs = []
            parser = "json.loads"
        canon_rel = f"data/{p.name}.canonical.json"
        canon_sha = write_json(canon_rel, value, canonical=True)
        files.append({"file": rel, "raw_sha256": hashlib.sha256(raw).hexdigest(), "bytes": len(raw),
                      "python_parser": parser, "canonical": canon_rel, "canonical_sha256": canon_sha,
                      "yaml11_vs_yaml12_differences": diffs})
        print(f"  {rel}: {len(diffs)} YAML 1.1/1.2 difference(s)")
    stamp = ref.provenance_stamp()
    write_table("data_files", {
        "description": "Every YAML and JSON file under backend/amcrax/data as Python loads it. The canonical "
                       "dump is json.dumps(value, sort_keys=True). Rust must parse each file to identical "
                       "values (same type: integer, float, string, bool, null; floats bitwise), except at the "
                       "listed paths where the YAML 1.1 resolver (PyYAML) and the YAML 1.2 core schema "
                       "disagree by definition.",
        "files": files,
        "reference_scenario_provenance_stamp": stamp,
    })


# ----------------------------------------------------------------------------------- 2. NASA-7
def gen_nasa7() -> None:
    temps = [200.0, 210.0, 250.0, 298.15, 300.0, 350.0, 400.0, 500.0, 600.0, 700.0, 773.15, 800.0, 873.15,
             900.0, 999.999999, 1000.0, 1000.0000000001, 1000.001, 1100.0, 1200.0, 1500.0, 2000.0, 2500.0, 3000.0,
             3499.999, 3500.0, 3500.001, 4000.0, 5000.0, 6000.0, 6000.5, 199.99, 150.0, 100.0]
    cases = []
    for s in COMPONENTS:
        for T in temps:
            c = {"species": s, "T_K": T}
            try:
                c.update(cp_J_molK=nasa7.species_cp_J_molK(s, T), h_kJ_mol=nasa7.species_enthalpy_kJ_mol(s, T),
                         s_J_molK=nasa7.species_entropy_J_molK(s, T), g_kJ_mol=nasa7.species_gibbs_kJ_mol(s, T),
                         cp_R=nasa7.cp_R(s, T), h_RT=nasa7.h_RT(s, T), s_R=nasa7.s_R(s, T))
            except Exception as e:  # noqa: BLE001
                c["result"] = err(e)
            cases.append(c)
    rcases = []
    for T in [200.0, 250.0, 298.15, 300.0] + [float(t) for t in np.arange(320.0, 1520.0, 10.0)] + \
             [999.999999, 1000.0, 1000.000001, 2000.0, 3000.0, 3500.0, 3600.0, 150.0]:
        c = {"T_K": T}
        try:
            c.update(dH_kJ_mol=eq.reaction_enthalpy_kJ_mol(T), dG_kJ_mol=eq.reaction_gibbs_kJ_mol(T),
                     dS_J_molK=eq.reaction_entropy_J_molK(T), Kp=eq.equilibrium_constant(T))
        except Exception as e:  # noqa: BLE001
            c["result"] = err(e)
        rcases.append(c)
    write_table("nasa7", {
        "gate": {"rule": "relative", "tol": 1e-12,
                 "why": "same coefficients and the same sequence of IEEE operations; only the libm pow/log/exp "
                        "of the platform differ (<= 1 ulp each), amplified at most by the condition number of "
                        "the polynomial sums (< 1e4 in this range)"},
        "R_J_molK": nasa7.R_J_molK, "species_cases": cases, "reaction_cases": rcases,
    })


# ----------------------------------------------------------------------------------- 3. ideal equilibrium
FEEDS = {
    "pure_nh3": {"NH3": 1.0},
    "baseline_kmol_h": {"NH3": 99.8, "H2O": 0.2},
    "h2_seed": {"NH3": 100.0, "H2": 0.001},
    "full_mix": {"NH3": 50.0, "H2": 30.0, "N2": 10.0, "H2O": 5.0, "O2": 1.0},
    "synthesis_no_nh3": {"H2": 3.0, "N2": 1.0},
    "nh3_n2_rich": {"NH3": 10.0, "N2": 40.0},
    "small_scale": {"NH3": 1e-6, "H2O": 1e-9},
}


def eq_case(T, P, feed, eos, kij=None, alpha="standard") -> dict:
    c = {"T_K": T, "P_bar": P, "feed": feed, "eos": eos, "alpha": alpha,
         "kij": [[a, b, v] for (a, b), v in (kij or {}).items()]}
    n0 = len(_BRENT_LOG)
    try:
        r = eq.solve_equilibrium(T, P, feed, eos, kij=kij, alpha=alpha)
        c["result"] = {"conversion": r.conversion, "extent": r.extent, "n_out": r.n_out, "y": r.y,
                       "K_eq": r.K_eq, "phi": r.phi, "residual": r.residual,
                       "brentq": last_brent() if len(_BRENT_LOG) > n0 else None}
    except Exception as e:  # noqa: BLE001
        c["result"] = err(e)
    return c


def gen_equilibrium_ideal() -> None:
    cases = []
    Ts = [250.0 + 25.0 * i for i in range(31)]
    Ps = [1.0, 1.01325, 2.0, 5.0, 10.0, 20.0, 30.0, 50.0, 75.0, 100.0]
    for name, feed in FEEDS.items():
        for Tc in Ts:
            for P in Ps:
                c = eq_case(Tc + 273.15, P, feed, "ideal")
                c["feed_name"] = name
                cases.append(c)
    # input errors
    for feed in ({"NH3": -1.0}, {"H2": 1.0}, {"N2": 1.0, "H2O": 1.0}):
        c = eq_case(873.15, 20.0, feed, "ideal")
        c["feed_name"] = "invalid"
        cases.append(c)
    write_table("equilibrium_ideal", {
        "gate": {"conversion_abs": 1e-10, "other_rel": 1e-10, "Kp_rel": 1e-12,
                 "why": "brentq on z = ln n_NH3 with xtol 1e-13, rtol 1e-15: identical algorithm; the residual "
                        "differs only by libm ulps, so the root moves by at most a few xtol"},
        "cases": cases})


# ----------------------------------------------------------------------------------- 4. Peng-Robinson
COMPS_PR = {
    "pure_nh3": {"NH3": 1.0},
    "pure_h2o": {"H2O": 1.0},
    "pure_h2": {"H2": 1.0},
    "cracked_x0.5": {"NH3": 0.3322, "H2": 0.4993, "N2": 0.1664, "H2O": 0.0021},
    "cracked_x0.99": {"NH3": 0.00502, "H2": 0.74531, "N2": 0.24844, "H2O": 0.00123},
    "nh3_h2o": {"NH3": 0.6, "H2O": 0.4},
    "with_zero": {"NH3": 0.7, "H2": 0.3, "N2": 0.0, "H2O": 0.0, "O2": 0.0},
    "all_five": {"NH3": 0.2, "H2": 0.3, "N2": 0.2, "H2O": 0.2, "O2": 0.1},
    "trace_h2o": {"H2": 0.75, "N2": 0.25, "H2O": 1e-9},
}
KIJ_SET = {("NH3", "H2O"): -0.25, ("H2", "N2"): 0.103, ("N2", "NH3"): 0.2193, ("H2", "O2"): 0.05}


def pr_props(y, T, P, kij, alpha) -> dict:
    out = {}
    for phase in ("vapour", "liquid"):
        try:
            out[f"phi_{phase}"] = pr.fugacity_coefficients(y, T, P, kij=kij, alpha=alpha, phase=phase)
        except Exception as e:  # noqa: BLE001
            out[f"phi_{phase}"] = err(e)
        try:
            out[f"Z_{phase}"] = pr.compressibility(y, T, P, kij=kij, alpha=alpha, phase=phase)
        except Exception as e:  # noqa: BLE001
            out[f"Z_{phase}"] = err(e)
        try:
            out[f"H_dep_{phase}_J_mol"] = pr.enthalpy_departure_J_mol(y, T, P, kij=kij, alpha=alpha, phase=phase)
        except Exception as e:  # noqa: BLE001
            out[f"H_dep_{phase}_J_mol"] = err(e)
    return out


def numpy_root_info(A, B):
    roots = np.roots([1.0, -(1.0 - B), A - 3 * B**2 - 2 * B, -(A * B - B**2 - B**3)])
    real = roots[np.abs(roots.imag) < 1e-10].real
    return {"roots_re": roots.real.tolist(), "roots_im": roots.imag.tolist(),
            "n_real_numpy_rule": int(real.size), "n_physical": int((real > B).sum())}


def gen_pr() -> None:
    cases = []
    Ts = [200.0, 250.0, 300.0, 350.0, 400.0, 500.0, 700.0, 900.0, 1200.0]
    Ps = [1.0, 10.0, 50.0, 100.0, 200.0]
    for name, y in COMPS_PR.items():
        for T in Ts:
            for P in Ps:
                for alpha in ("standard", "boston-mathias"):
                    for kname, kij in (("none", None), ("set", KIJ_SET)):
                        c = {"comp": name, "y": y, "T_K": T, "P_bar": P, "alpha": alpha,
                             "kij": [[a, b, v] for (a, b), v in (kij or {}).items()], "kij_name": kname}
                        c.update(pr_props(y, T, P, kij, alpha))
                        cases.append(c)
    # input errors
    bad = []
    for y, kij in (({"NH3": -0.1, "H2": 1.1}, None), ({"NH3": float("nan")}, None),
                   ({"NH3": 1.0}, {("NH3", "NH3"): 0.1}), ({"NH3": 1.0}, {("NH3", "H2"): float("inf")}),
                   ({"NH3": 1.0}, {("NH3", "H2"): 0.1, ("H2", "NH3"): 0.2}),
                   ({"NH3": 0.0, "H2": 0.0}, None)):
        c = {"y": y, "T_K": 500.0, "P_bar": 10.0, "alpha": "standard",
             "kij": [[a, b, v] for (a, b), v in (kij or {}).items()]}
        try:
            c["phi_vapour"] = pr.fugacity_coefficients(y, 500.0, 10.0, kij=kij)
        except Exception as e:  # noqa: BLE001
            c["phi_vapour"] = err(e)
        try:
            c["Z_vapour"] = pr.compressibility(y, 500.0, 10.0, kij=kij)
        except Exception as e:  # noqa: BLE001
            c["Z_vapour"] = err(e)
        bad.append(c)

    # cubic root classification near double roots: for fixed B, the boundaries of the three-root region
    # in A (discriminant = 0) are located, and A is perturbed by relative eps on both sides.
    def disc(A, B):
        a, b, c = -(1.0 - B), A - 3 * B**2 - 2 * B, -(A * B - B**2 - B**3)
        return 18 * a * b * c - 4 * a**3 * c + a**2 * b**2 - 4 * b**3 - 27 * c**2

    cubic = []
    for B in (0.005, 0.02, 0.05, 0.1):
        As = np.linspace(B * 1.0001, 0.6, 20001)
        d = [disc(A, B) for A in As]
        zeros = []
        for i in range(len(As) - 1):
            if d[i] == 0 or (d[i] > 0) != (d[i + 1] > 0):
                zeros.append(_orig_brentq(lambda A: disc(A, B), As[i], As[i + 1], xtol=1e-300, rtol=1e-15,
                                          maxiter=400))
        for A0 in zeros:
            for eps in [0.0] + [s * 10.0 ** -k for k in range(2, 16) for s in (1.0, -1.0)]:
                A = A0 * (1.0 + eps)
                c = {"A": A, "B": B, "A_boundary": A0, "rel_offset": eps, "numpy": numpy_root_info(A, B)}
                for phase in ("vapour", "liquid"):
                    try:
                        c[f"Z_{phase}"] = pr._z_root(A, B, phase)
                    except Exception as e:  # noqa: BLE001
                        c[f"Z_{phase}"] = err(e)
                cubic.append(c)
    # plus the realistic range: every (A, B) of the property cases above at the vapour root
    write_table("peng_robinson", {
        "gate": {"rule": "relative", "tol": 1e-10,
                 "why": "same equations; numpy.roots (companion-matrix eigenvalues) versus the analytic cubic "
                        "with Newton polishing differ by ~1e-15 relative for separated roots; BLAS dot products "
                        "in the mixing rules sum in another order (~1e-16)"},
        "critical_properties": pr.critical_properties(), "cases": cases, "invalid_inputs": bad,
        "cubic_near_double_roots": {
            "description": "numpy.roots root classification (|imag| < 1e-10 is real, then > B) near the "
                           "boundaries of the three-real-root region. Near a double root the eigenvalue solver "
                           "has an error of order sqrt(eps) * scale, so the count it reports there is a "
                           "numerical artefact; Rust must agree wherever the root pair is separated by more than "
                           "the stated band.",
            "cases": cubic}})


# ----------------------------------------------------------------------------------- 5. dew point, saturation
_DEW_SCAN: list[dict] = []
_orig_dew_liquid = pr.dew_liquid


def _rec_dew_liquid(y, T_K, P_bar, **kw):
    try:
        x, S = _orig_dew_liquid(y, T_K, P_bar, **kw)
    except RuntimeError as e:
        _DEW_SCAN.append({"T_K": float(T_K), "error": type(e).__name__, "message": str(e)})
        raise
    _DEW_SCAN.append({"T_K": float(T_K), "S": S})
    return x, S


def gen_dew() -> None:
    pr.dew_liquid = _rec_dew_liquid
    mixes = {
        "nh3_h2o_50": {"NH3": 0.5, "H2O": 0.5},
        "nh3_h2_n2": {"NH3": 0.8, "H2": 0.15, "N2": 0.05},
        "h2o_n2": {"H2O": 0.1, "N2": 0.9},
        "h2o_cracked": {"H2": 0.6, "N2": 0.2, "H2O": 0.2},
        "nh3_h2o_cracked": {"NH3": 0.3, "H2": 0.49, "N2": 0.16, "H2O": 0.05},
        "pure_nh3": {"NH3": 1.0},
        "pure_h2o": {"H2O": 1.0},
    }
    cases = []
    for name, y in mixes.items():
        for P in (1.0, 5.0, 10.0, 20.0, 50.0, 100.0):
            for kname, kij in (("none", None), ("set", KIJ_SET)):
                if kname == "set" and name not in ("nh3_h2o_50", "nh3_h2o_cracked"):
                    continue
                c = {"mix": name, "y": y, "P_bar": P, "alpha": "standard",
                     "kij": [[a, b, v] for (a, b), v in (kij or {}).items()]}
                _DEW_SCAN.clear()
                b0 = len(_BRENT_LOG)
                try:
                    Td, x = pr.dew_point_K(P, y, kij=kij)
                    c["result"] = {"T_K": Td, "x": x}
                except Exception as e:  # noqa: BLE001
                    c["result"] = err(e)
                calls = list(_DEW_SCAN)
                brs = _BRENT_LOG[b0:]
                c["brentq"] = brs[-1] if brs else None
                if len(y) > 1:
                    # calls: 351-point scan (until the bracket is found), then the brentq calls, then the final one
                    n_scan = (len(calls) - (brs[-1]["function_calls"] + 1)) if brs else len(calls)
                    c["scan"] = calls[:n_scan]
                    c["bracket"] = [brs[-1]["a"], brs[-1]["b"]] if brs else None
                cases.append(c)
    # direct dew_liquid evaluations (S and x, or the RuntimeError) on a grid
    direct = []
    for name in ("nh3_h2o_50", "nh3_h2o_cracked", "h2o_cracked"):
        y = mixes[name]
        for T in (280.0, 300.0, 320.0, 350.0, 380.0, 400.0, 450.0, 500.0):
            for P in (5.0, 20.0, 50.0):
                c = {"mix": name, "y": y, "T_K": T, "P_bar": P}
                try:
                    x, S = _orig_dew_liquid(y, T, P)
                    c["result"] = {"x": x, "S": S}
                except Exception as e:  # noqa: BLE001
                    c["result"] = err(e)
                direct.append(c)
    sat = []
    for s in ("NH3", "H2O", "N2"):
        for P in (1.0, 5.0, 10.0, 20.0, 30.0):
            for alpha in ("standard", "boston-mathias"):
                c = {"species": s, "P_bar": P, "alpha": alpha}
                try:
                    c["result"] = {"T_K": pr.saturation_temperature_K(s, P, alpha=alpha), "brentq": last_brent()}
                except Exception as e:  # noqa: BLE001
                    c["result"] = err(e)
                sat.append(c)
    pr.dew_liquid = _orig_dew_liquid
    write_table("dew_point", {
        "gate": {"T_rel": 1e-8, "S_rel": 1e-10, "x_abs": 1e-10, "scan": "identical: the same scan "
                 "temperatures fail, the same sign of S - 1 at every other one, the same bracket",
                 "why": "brentq xtol 1e-9 K (dew) / 1e-11 K (saturation); successive substitution converged "
                        "to 1e-14"},
        "cases": cases, "dew_liquid": direct, "saturation": sat})


# ----------------------------------------------------------------------------------- 6. PR equilibrium, enthalpy
def gen_pr_equilibrium() -> None:
    cases = []
    feeds = {k: FEEDS[k] for k in ("pure_nh3", "baseline_kmol_h", "full_mix", "synthesis_no_nh3")}
    for name, feed in feeds.items():
        for Tc in (300.0, 400.0, 500.0, 600.0, 700.0, 800.0, 1000.0):
            for P in (1.0, 10.0, 20.0, 50.0, 100.0):
                for kname, kij in (("none", None), ("set", KIJ_SET)):
                    for alpha in ("standard", "boston-mathias"):
                        c = eq_case(Tc + 273.15, P, feed, "pr", kij=kij, alpha=alpha)
                        c["feed_name"] = name
                        cases.append(c)
    hcases = []
    flows = {"baseline": {"NH3": 99.8, "H2O": 0.2},
             "cracked": {"NH3": 1.2, "H2": 147.0, "N2": 49.0, "H2O": 0.2},
             "with_zero": {"NH3": 10.0, "H2": 0.0, "N2": 0.0},
             "all_zero": {"NH3": 0.0}}
    for name, n in flows.items():
        for T in (300.0, 500.0, 873.15, 1200.0):
            for P in (1.0, 20.0, 80.0):
                for eos in ("ideal", "pr"):
                    c = {"flows": name, "n_kmol_h": n, "T_K": T, "P_bar": P, "eos": eos}
                    try:
                        c["H_kW"] = eq.mixture_enthalpy_kW(n, T, P_bar=P, eos=eos)
                    except Exception as e:  # noqa: BLE001
                        c["H_kW"] = err(e)
                    hcases.append(c)
    write_table("equilibrium_pr", {
        "gate": {"conversion_abs": 1e-10, "phi_rel": 1e-10, "H_rel": 1e-10,
                 "why": "as equilibrium_ideal, plus the Peng-Robinson fugacity coefficients (1e-10)"},
        "cases": cases, "enthalpy_cases": hcases})


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    gen_data()
    gen_nasa7()
    gen_equilibrium_ideal()
    gen_pr()
    gen_dew()
    gen_pr_equilibrium()
    text = json.dumps(enc(MANIFEST), indent=1, sort_keys=True) + "\n"
    (OUT / "MANIFEST.json").write_bytes(text.encode("utf-8"))
    print("wrote rust/golden/stage1/MANIFEST.json")


if __name__ == "__main__":
    main()
