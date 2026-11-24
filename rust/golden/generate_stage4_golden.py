"""Generate the stage 4 golden reference tables (fluid properties, process flowsheet, heat integration, separation).

Produced ONCE by the Python reference (the ``amcrax`` package of this repository, imported from ``backend/``) with the
project venv (CoolProp 8.0.0) and committed; never regenerated from Rust. Run from the repository root:

    python rust/golden/generate_stage4_golden.py

Tables (rust/golden/stage4/):

* ``coolprop_grid``   dense grid of every CoolProp call the Python model makes (fluid, output, input pair, imposed
                      phase), evaluated the way the Python code evaluates it (PropsSI, or one reused AbstractState per
                      imposed phase). Gate of the C++ back end (feature ``coolprop``).
* ``coolprop_states`` every CoolProp call made while the flowsheet and heat-integration cases below were run (recorded
                      by wrapping CoolProp's PropsSI and AbstractState; values unchanged), each with the derivative of
                      the output with respect to the input that iterations vary (dh/dT|P = cp, dh_res/dT|P = cp - cp0,
                      drho/dT|P, dPsat/dT, dTsat/dP, dh_sat/dP, dh_sat/dT from CoolProp). Back end "tables" of the Rust
                      engine: exact at the recorded states, first-order Taylor within 1e-7 relative of one.
* ``flowsheet``       run_python_case on the stored cases (results/simulations), on the inputs of every stored Aspen
                      case (both eos), on the FEHE approach sweep of scripts/research/heat_exchanger_study.py, on
                      branch-covering variations and on infeasible specifications.
* ``heat``            heat_integration.analyse on the Python cases and on the stored Aspen results; exchanger sizing,
                      costing and break-even solves (the argument sets of heat_exchanger_study.py and grids).
* ``separation``      compression, PSA, membrane (ODE and area search), purification helpers, compare_purification on
                      the stored baseline results.

Floats are written with repr() (shortest round trip); non-finite values as "nan", "inf", "-inf". Python exceptions are
recorded as {"error": <class>, "message": ...}; FlowsheetSpecError keeps its own name (it is a ValueError).
"""

from __future__ import annotations

import hashlib
import json
import math
import os
import platform
import subprocess
import sys
import types
from pathlib import Path

HERE = Path(__file__).resolve().parent
RUST_DIR = HERE.parent
REPO = RUST_DIR.parent
os.environ["AMCRAX_ROOT"] = str(REPO)
sys.path.insert(0, str(REPO / "backend"))

import CoolProp  # noqa: E402
import CoolProp.CoolProp as CP  # noqa: E402
import numpy as np  # noqa: E402
import pydantic  # noqa: E402
import scipy  # noqa: E402
import yaml  # noqa: E402

import amcrax  # noqa: E402

if Path(amcrax.__file__).resolve().parents[1] != (REPO / "backend").resolve():
    raise SystemExit(f"amcrax imported from {amcrax.__file__}, not from {REPO / 'backend'}")

from amcrax.heat_integration import analyse  # noqa: E402
from amcrax.heat_integration import exchanger as HX  # noqa: E402
from amcrax.process_model import flowsheet as FS  # noqa: E402
from amcrax.process_model import properties as PP  # noqa: E402
from amcrax.schemas import CaseInputs, SimulationResult  # noqa: E402
from amcrax.separation import compare as SC  # noqa: E402
from amcrax.separation import compression as CO  # noqa: E402
from amcrax.separation import membrane as ME  # noqa: E402
from amcrax.separation import psa as PS  # noqa: E402
from amcrax.separation import purification as PU  # noqa: E402

OUT = HERE / "stage4"
GENERATOR = "rust/golden/generate_stage4_golden.py"
REFERENCE_TAG = "amcrax-phase2-reviewed-2026-11-24"


def _git(*args: str) -> str:
    try:
        return subprocess.run(["git", *args], cwd=REPO, capture_output=True, text=True, check=True).stdout.strip()
    except Exception:  # noqa: BLE001
        return "unknown"


META = {"generator": GENERATOR, "python": platform.python_version(), "numpy": np.__version__,
        "scipy": scipy.__version__, "pydantic": pydantic.VERSION, "pyyaml": yaml.__version__,
        "coolprop": CoolProp.__version__, "coolprop_gitrevision": CoolProp.__gitrevision__,
        "coolprop_ammonia_eos": CP.get_fluid_param_string("Ammonia", "BibTeX-EOS"),
        "coolprop_water_eos": CP.get_fluid_param_string("Water", "BibTeX-EOS"),
        "coolprop_reference_state": "CoolProp default reference state of each fluid file (the Python code never calls "
                                    "set_reference_state; the NH3 scale is anchored to NASA-7 by the Python model)",
        "platform": f"{platform.system()} {platform.machine()}", "amcrax_source": "backend/amcrax (this repository)",
        "git_head_at_generation": _git("rev-parse", "HEAD"),
        "python_reference_tag": REFERENCE_TAG,
        "science_diff_vs_tag": _git("diff", "--stat", REFERENCE_TAG, "--", "backend/amcrax", ":!backend/amcrax/api")
        or "none"}


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
    if o is None or isinstance(o, str):
        return o
    if hasattr(o, "model_dump"):
        return enc(o.model_dump(mode="python"))
    if hasattr(o, "value") and hasattr(o, "name"):  # Enum
        return enc(o.value)
    return str(o)


def err(e: BaseException) -> dict:
    if isinstance(e, FS.FlowsheetSpecError):
        cls = "FlowsheetSpecError"
    elif isinstance(e, KeyError):
        cls = "KeyError"
    elif isinstance(e, ZeroDivisionError):
        cls = "ZeroDivisionError"
    elif isinstance(e, ValueError):
        cls = "ValueError"
    elif isinstance(e, TypeError):
        cls = "TypeError"
    else:
        cls = type(e).__name__
    return {"error": cls, "message": str(e)[:300]}


def call(f, *a, **k):
    try:
        return f(*a, **k)
    except Exception as e:  # noqa: BLE001
        return err(e)


MANIFEST = {"meta": META, "files": {}}


def write_table(name: str, body: dict, n_cases: int) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    text = json.dumps(enc({"meta": dict(META, table=name), **body}), separators=(",", ":"), allow_nan=False) + "\n"
    data = text.encode("utf-8")
    (OUT / f"{name}.json").write_bytes(data)
    MANIFEST["files"][f"{name}.json"] = {"sha256": hashlib.sha256(data).hexdigest(), "bytes": len(data),
                                         "cases": n_cases}
    print(f"wrote rust/golden/stage4/{name}.json ({len(data)} bytes, {n_cases} cases)")


def save_manifest() -> None:
    (OUT / "MANIFEST.json").write_bytes((json.dumps(MANIFEST, indent=1, sort_keys=True) + "\n").encode("utf-8"))


def load(rel: str):
    return json.loads((REPO / rel).read_text(encoding="utf-8"))


# ===================================================================================== CoolProp recording
REAL_PROPSSI = CP.PropsSI
REAL_AS = CP.AbstractState
PHASE_NAME = {CP.iphase_liquid: "liquid", CP.iphase_gas: "gas"}
PHASE_CODE = {"liquid": CP.iphase_liquid, "gas": CP.iphase_gas}
STATES: dict[tuple, dict] = {}


def derivative(fluid: str, out: str, pair: str, phase: str, a: float, b: float):
    """d(out)/d(varying input) at the state (TP: d/dT at constant P; TQ: d/dT along saturation; PQ: d/dP)."""
    try:
        st = REAL_AS("HEOS", fluid)
        if pair == "TP":
            if phase != "none":
                st.specify_phase(PHASE_CODE[phase])
            st.update(CP.PT_INPUTS, b, a)
            if out == "Hmolar":
                return st.first_partial_deriv(CP.iHmolar, CP.iT, CP.iP)
            if out == "Dmolar":
                return st.first_partial_deriv(CP.iDmolar, CP.iT, CP.iP)
            if out == "Hmolar_residual":
                return st.cpmolar() - st.cp0molar()
            return None
        if pair == "TQ":
            if out not in ("P", "Hmolar"):
                return None
            st.update(CP.QT_INPUTS, b, a)
            return st.first_saturation_deriv(CP.iP if out == "P" else CP.iHmolar, CP.iT)
        if pair == "PQ":
            if out not in ("T", "Hmolar"):
                return None
            st.update(CP.PQ_INPUTS, a, b)
            return st.first_saturation_deriv(CP.iT if out == "T" else CP.iHmolar, CP.iP)
    except Exception:  # noqa: BLE001
        return None
    return None


def record(fluid, out, pair, phase, a, b, value=None, error=None):
    k = (fluid, out, pair, phase, float(a), float(b))
    if k in STATES:
        old = STATES[k]
        if error is None and old.get("v") != value:
            raise SystemExit(f"CoolProp returned two values for {k}: {old.get('v')!r} and {value!r}")
        return
    STATES[k] = {"fluid": fluid, "out": out, "in": pair, "phase": phase, "a": float(a), "b": float(b),
                 "v": value, "error": error,
                 "d": None if error is not None else derivative(fluid, out, pair, phase, float(a), float(b))}


def canon(n1, v1, n2, v2):
    d = {n1: v1, n2: v2}
    if set(d) == {"T", "P"}:
        return "TP", d["T"], d["P"]
    if set(d) == {"T", "Q"}:
        return "TQ", d["T"], d["Q"]
    if set(d) == {"P", "Q"}:
        return "PQ", d["P"], d["Q"]
    raise SystemExit(f"unexpected CoolProp input pair {n1}, {n2}")


def rec_propssi(*args):
    if len(args) == 2:
        out, fluid = args
        v = REAL_PROPSSI(*args)
        record(fluid, out, "none", "none", 0.0, 0.0, v)
        return v
    out, n1, v1, n2, v2, fluid = args
    pair, a, b = canon(n1, v1, n2, v2)
    try:
        v = REAL_PROPSSI(*args)
    except Exception as e:  # noqa: BLE001
        record(fluid, out, pair, "none", a, b, error=str(e)[:200])
        raise
    record(fluid, out, pair, "none", a, b, v)
    return v


class RecState:
    """Recording proxy of CoolProp.AbstractState for the calls of process_model/properties.py."""

    def __init__(self, backend, fluid):
        self._s = REAL_AS(backend, fluid)
        self.fluid = fluid
        self.phase = "none"
        self.T = self.P = math.nan
        self.failed = None

    def specify_phase(self, ph):
        self._s.specify_phase(ph)
        self.phase = PHASE_NAME[ph]

    def update(self, pair, x1, x2):
        if pair != CP.PT_INPUTS:
            raise SystemExit("unexpected AbstractState input pair")
        self.P, self.T = float(x1), float(x2)
        try:
            self._s.update(pair, x1, x2)
            self.failed = None
        except Exception as e:  # noqa: BLE001
            self.failed = str(e)[:200]
            for out in ("Hmolar", "Dmolar", "Hmolar_residual"):
                record(self.fluid, out, "TP", self.phase, self.T, self.P, error=self.failed)
            raise

    def _out(self, name, f):
        v = f()
        record(self.fluid, name, "TP", self.phase, self.T, self.P, v)
        return v

    def hmolar(self):
        return self._out("Hmolar", self._s.hmolar)

    def rhomolar(self):
        return self._out("Dmolar", self._s.rhomolar)

    def hmolar_residual(self):
        return self._out("Hmolar_residual", self._s.hmolar_residual)


def install_recorder() -> None:
    shim = types.SimpleNamespace(PropsSI=rec_propssi, AbstractState=RecState, PT_INPUTS=CP.PT_INPUTS,
                                 iphase_liquid=CP.iphase_liquid, iphase_gas=CP.iphase_gas)
    PP.CP = shim
    CP.PropsSI = rec_propssi  # heat_integration/streams.py imports CoolProp.CoolProp inside its functions
    PP.nh3_anchor_offset_kJ_mol.cache_clear()
    PP._water_liquid_params.cache_clear()
    PP._TLS.states = {}


def remove_recorder() -> None:
    PP.CP = CP
    CP.PropsSI = REAL_PROPSSI
    PP._TLS.states = {}


# ===================================================================================== dense CoolProp grid
def coolprop_grid() -> None:
    rows = []
    pl = {"liquid": REAL_AS("HEOS", "Ammonia"), "gas": REAL_AS("HEOS", "Ammonia")}
    pl["liquid"].specify_phase(CP.iphase_liquid)
    pl["gas"].specify_phase(CP.iphase_gas)

    def add(fluid, out, pair, phase, a, b, f):
        try:
            v = f()
            rows.append([fluid, out, pair, phase, float(a), float(b), float(v)])
        except Exception as e:  # noqa: BLE001
            rows.append([fluid, out, pair, phase, float(a), float(b), {"error": str(e)[:160]}])

    def tsat(p):
        return REAL_PROPSSI("T", "P", p, "Q", 0, "Ammonia")

    p_liq = [1.013, 2.013, 4.0, 6.0, 9.513, 11.0, 21.0, 31.0, 41.0, 61.0, 81.0, 101.0]
    for pb in p_liq:
        P = pb * 1e5
        ts = tsat(P)
        for T in np.linspace(196.0, ts - 0.5, 41):
            T = float(T)
            for out, getter in (("Hmolar", "hmolar"), ("Dmolar", "rhomolar")):
                def f(T=T, P=P, getter=getter):
                    pl["liquid"].update(CP.PT_INPUTS, P, T)
                    return getattr(pl["liquid"], getter)()
                add("Ammonia", out, "TP", "liquid", T, P, f)
    p_gas = [0.5, 1.013, 1.8, 3.8, 5.8, 10.8, 20.5, 20.8, 25.0, 40.8, 60.0, 80.5, 100.8]
    for pb in p_gas:
        P = pb * 1e5
        ts = tsat(P) if P < 112e5 else 300.0
        for T in np.concatenate([np.linspace(ts + 0.5, 725.0, 40), np.linspace(730.0, 1300.0, 20)]):
            T = float(T)
            for out, getter in (("Hmolar", "hmolar"), ("Hmolar_residual", "hmolar_residual")):
                def f(T=T, P=P, getter=getter):
                    pl["gas"].update(CP.PT_INPUTS, P, T)
                    return getattr(pl["gas"], getter)()
                add("Ammonia", out, "TP", "gas", T, P, f)
    for pb in [1e-5, 1.013, 2.013, 10.8, 20.8, 40.8, 80.8, 100.8]:
        P = pb * 1e5
        ts = tsat(P) if pb > 0.06 else 150.0
        temps = list(np.linspace(196.0, 1300.0, 70)) + ([ts - 1e-3, ts + 1e-3, ts - 0.3, ts + 0.3] if pb > 0.06 else [298.15])
        for T in temps:
            T = float(T)
            add("Ammonia", "Hmolar", "TP", "none", T, P, lambda T=T, P=P: REAL_PROPSSI("Hmolar", "T", T, "P", P, "Ammonia"))
    for T in np.linspace(196.0, 405.0, 120):
        T = float(T)
        add("Ammonia", "P", "TQ", "none", T, 0.0, lambda T=T: REAL_PROPSSI("P", "T", T, "Q", 0, "Ammonia"))
    for P in np.geomspace(1.0e4, 112.0e5, 120):
        P = float(P)
        for q in (0.0, 1.0):
            add("Ammonia", "T", "PQ", "none", P, q, lambda P=P, q=q: REAL_PROPSSI("T", "P", P, "Q", q, "Ammonia"))
            add("Ammonia", "Hmolar", "PQ", "none", P, q, lambda P=P, q=q: REAL_PROPSSI("Hmolar", "P", P, "Q", q, "Ammonia"))
    for T in np.linspace(274.0, 646.0, 120):
        T = float(T)
        add("Water", "P", "TQ", "none", T, 0.0, lambda T=T: REAL_PROPSSI("P", "T", T, "Q", 0, "Water"))
        for q in (0.0, 1.0):
            add("Water", "Hmolar", "TQ", "none", T, q, lambda T=T, q=q: REAL_PROPSSI("Hmolar", "T", T, "Q", q, "Water"))
        add("Water", "Cpmolar", "TQ", "none", T, 0.0, lambda T=T: REAL_PROPSSI("Cpmolar", "T", T, "Q", 0, "Water"))
    for P in np.geomspace(612.0, 200.0e5, 120):
        P = float(P)
        add("Water", "T", "PQ", "none", P, 1.0, lambda P=P: REAL_PROPSSI("T", "P", P, "Q", 1, "Water"))
    for fl in ("Ammonia", "Water"):
        add(fl, "Tcrit", "none", "none", 0.0, 0.0, lambda fl=fl: REAL_PROPSSI("Tcrit", fl))
    body = {"columns": ["fluid", "out", "in", "phase", "a", "b", "value"],
            "inputs": "TP: a = T [K], b = P [Pa]; TQ: a = T, b = Q; PQ: a = P [Pa], b = Q; none: Tcrit",
            "evaluation": "phase 'none': CoolProp.PropsSI; phase 'liquid'/'gas': one AbstractState('HEOS') per "
                          "imposed phase, reused (as process_model/properties.py does)",
            "rows": rows}
    write_table("coolprop_grid", body, len(rows))


# ===================================================================================== flowsheet
SIM = "results/simulations"
STORED_PY = [("python_baseline.json", "ideal"), ("python_baseline_pr.json", "pr"),
             ("python_baseline_no_hi.json", "ideal"), ("python_baseline_no_hi_pr.json", "pr")]
ASPEN_FILES = sorted(p.name for p in (REPO / SIM).glob("*.json")
                     if p.name.startswith(("baseline", "opt_", "scn_")) and load(f"{SIM}/{p.name}").get("source") == "aspen_plus_v15")
VOLATILE = ("created_utc",)


def dump_result(r: SimulationResult) -> dict:
    d = r.model_dump(mode="python")
    for k in VOLATILE:
        d.pop(k, None)
    d["status"].pop("engine_time_s", None)
    return enc(d)


def leaves(a, b, path=""):
    """(path, stored, new) numeric leaf pairs of two JSON trees."""
    if isinstance(a, dict) and isinstance(b, dict):
        for k in a:
            if k in b:
                yield from leaves(a[k], b[k], f"{path}/{k}")
    elif isinstance(a, (int, float)) and isinstance(b, (int, float)) and not isinstance(a, bool):
        yield path, float(a), float(b)


def max_rel(a, b) -> tuple[float, str]:
    worst, wp = 0.0, ""
    for p, x, y in leaves(a, b):
        if "engine_time" in p:
            continue
        d = abs(x - y) / max(abs(x), 1e-300) if x != y else 0.0
        if d > worst:
            worst, wp = d, p
    return worst, wp


FLOWSHEET_RESULTS: dict[str, SimulationResult] = {}


def flowsheet() -> None:
    cases = []

    def run(cid, inputs: dict, eos: str):
        try:
            inp = CaseInputs.model_validate(inputs)
        except Exception as e:  # noqa: BLE001
            cases.append({"id": cid, "inputs": inputs, "eos": eos, "result": err(e), "note": "CaseInputs validation"})
            return
        try:
            r = FS.run_python_case(inp, eos=eos)
            FLOWSHEET_RESULTS[cid] = r
            cases.append({"id": cid, "inputs": inp.model_dump(mode="python"), "eos": eos, "result": dump_result(r)})
        except Exception as e:  # noqa: BLE001
            cases.append({"id": cid, "inputs": inp.model_dump(mode="python"), "eos": eos, "result": err(e)})

    stored = []
    for name, eos in STORED_PY:
        j = load(f"{SIM}/{name}")
        cid = "stored/" + name[:-5]
        run(cid, j["inputs"], eos)
        new = next(c for c in cases if c["id"] == cid)["result"]
        dev, where = max_rel({k: j[k] for k in ("streams", "blocks", "kpis", "balances")},
                             {k: new[k] for k in ("streams", "blocks", "kpis", "balances")})
        stored.append({"file": f"{SIM}/{name}", "case": cid, "eos": eos, "python_max_rel_dev": dev, "worst_path": where,
                       "reproduced_1e12": dev <= 1e-12})
    for name in ASPEN_FILES:
        inp = load(f"{SIM}/{name}")["inputs"]
        for eos in ("ideal", "pr"):
            run(f"aspen_inputs/{name[:-5]}/{eos}", inp, eos)
    base = load(f"{SIM}/baseline.json")["inputs"]
    for dT in (20.0, 30.0, 40.0, 50.0, 75.0, 100.0, 150.0, 200.0):
        run(f"approach/{dT:g}", dict(base, fehe_hot_end_approach_K=dT), "ideal")
    variations = {
        "dry_feed": {"feed_h2o_mole_frac": 0.0},
        "wet_feed": {"feed_h2o_mole_frac": 0.01},
        "very_wet_feed": {"feed_h2o_mole_frac": 0.15},
        "T250_P3": {"reactor_temperature_C": 250.0, "reactor_pressure_bar": 3.0, "fehe_hot_end_approach_K": 20.0},
        "T400_P10": {"reactor_temperature_C": 400.0, "reactor_pressure_bar": 10.0},
        "T1000_P100": {"reactor_temperature_C": 1000.0, "reactor_pressure_bar": 100.0, "fehe_hot_end_approach_K": 100.0},
        "T900_P60": {"reactor_temperature_C": 900.0, "reactor_pressure_bar": 60.0},
        "T700_P80": {"reactor_temperature_C": 700.0, "reactor_pressure_bar": 80.0},
        "psa_cold": {"psa_feed_temperature_C": 5.0},
        "psa_hot": {"psa_feed_temperature_C": 80.0},
        "full_recovery": {"psa_h2_recovery": 1.0, "psa_n2_slip": 0.05},
        "no_excess_air": {"burner_excess_air": 0.0},
        "excess_air_2": {"burner_excess_air": 2.0, "stack_temperature_C": 400.0},
        "stack_60": {"stack_temperature_C": 60.0},
        "feed_10": {"feed_total_kmol_h": 10.0},
        "feed_1000": {"feed_total_kmol_h": 1000.0, "reactor_pressure_bar": 30.0},
        "no_hi_T800_P5": {"heat_integration": False, "reactor_temperature_C": 800.0, "reactor_pressure_bar": 5.0},
        "approach_5": {"fehe_hot_end_approach_K": 5.0},
        "approach_300_T800": {"fehe_hot_end_approach_K": 300.0, "reactor_temperature_C": 800.0},
    }
    for vid, upd in variations.items():
        for eos in ("ideal", "pr"):
            run(f"variation/{vid}/{eos}", dict(base, **upd, case_id="v_" + vid), eos)
    errors = {
        "low_pressure": {"reactor_pressure_bar": 2.0},
        "approach_too_large": {"fehe_hot_end_approach_K": 300.0, "reactor_temperature_C": 300.0},
        "cross_high_pressure": {"reactor_pressure_bar": 100.0, "fehe_hot_end_approach_K": 5.0, "reactor_temperature_C": 300.0},
    }
    for vid, upd in errors.items():
        for eos in ("ideal", "pr"):
            run(f"error/{vid}/{eos}", dict(base, **upd, case_id="e_" + vid), eos)
    body = {"cases": cases, "stored": stored,
            "note": "result = SimulationResult.model_dump() without created_utc and status.engine_time_s, or the error"}
    write_table("flowsheet", body, len(cases))


# ===================================================================================== heat integration
def heat() -> None:
    cases = []

    def run(cid, src: dict, res: SimulationResult, dT: float):
        try:
            h = analyse(res, dT)
            cases.append({"id": cid, "input": src, "dT_min_K": dT, "result": enc(h)})
        except Exception as e:  # noqa: BLE001
            cases.append({"id": cid, "input": src, "dT_min_K": dT, "result": err(e)})

    for cid, r in FLOWSHEET_RESULTS.items():
        run(f"python/{cid}", {"flowsheet_case": cid}, r, 20.0)
    for cid in ("stored/python_baseline", "aspen_inputs/baseline/ideal", "approach/100"):
        if cid in FLOWSHEET_RESULTS:
            for dT in (5.0, 10.0, 40.0):
                run(f"python/{cid}/dT{dT:g}", {"flowsheet_case": cid}, FLOWSHEET_RESULTS[cid], dT)
    for name in ASPEN_FILES:
        res = SimulationResult.model_validate(load(f"{SIM}/{name}"))
        run(f"aspen/{name[:-5]}", {"file": f"{SIM}/{name}"}, res, 20.0)
    res = SimulationResult.model_validate(load(f"{SIM}/baseline.json"))
    run("aspen/baseline/dT0", {"file": f"{SIM}/baseline.json"}, res, 0.0)
    stored = []
    for name in ("heat_integration_baseline.json", "heat_integration_baseline_no_hi.json"):
        j = load(f"{SIM}/{name}")
        src = f"{SIM}/{'baseline' if name == 'heat_integration_baseline.json' else 'baseline_no_hi'}.json"
        new = enc(analyse(SimulationResult.model_validate(load(src)), j["dT_min_K"]))
        dev, where = max_rel(j, new)
        stored.append({"file": f"{SIM}/{name}", "input_file": src, "dT_min_K": j["dT_min_K"], "python_max_rel_dev": dev,
                       "worst_path": where, "reproduced_1e12": dev <= 1e-12})

    # ------------------------------------------------------------------ exchanger.py
    ex = []

    def xc(fn, args: dict, f):
        ex.append({"fn": fn, "args": args, "out": enc(call(f))})

    for d1, d2 in ((10.0, 20.0), (50.0, 50.0), (50.0, 50.0 + 1e-10), (100.0, 3.0), (0.0, 5.0), (5.0, -1.0)):
        xc("lmtd", {"dT1": d1, "dT2": d2}, lambda d1=d1, d2=d2: HX.lmtd(d1, d2))
    for P in (0.0, 0.05, 0.2, 1 / 3, 0.5, 0.7, 0.9, 0.99, 1.0, 1.2):
        for R in (0.2, 0.5, 1.0, 1.0 + 1e-10, 1.5, 2.0, 4.0):
            xc("f_12", {"P": P, "R": R}, lambda P=P, R=R: HX._f_12(P, R))
    temps = [(600.0, 228.4, 75.9, 550.0), (200.0, 100.0, 50.0, 100.0), (500.0, 300.0, 100.0, 400.0),
             (600.0, 150.0, 60.0, 580.0), (400.0, 390.0, 20.0, 30.0), (300.0, 200.0, 100.0, 200.0),
             (527.2, 151.0, 30.8, 477.2), (800.0, 300.0, 60.0, 700.0), (450.0, 400.0, 50.0, 449.0)]
    for th_in, th_out, tc_in, tc_out in temps:
        for n in range(1, 13):
            xc("f_correction", {"T_hot_in": th_in, "T_hot_out": th_out, "T_cold_in": tc_in, "T_cold_out": tc_out, "n_shells": n},
               lambda a=(th_in, th_out, tc_in, tc_out), n=n: HX.f_correction(*a, n))
        xc("shells_needed", {"T_hot_in": th_in, "T_hot_out": th_out, "T_cold_in": tc_in, "T_cold_out": tc_out},
           lambda a=(th_in, th_out, tc_in, tc_out): HX.shells_needed(*a))
    for area in (0.5, 5.0, 10.0, 47.3, 100.0, 999.9, 1000.0, 1500.0, 4321.0):
        for P in (0.0, 4.9, 5.0, 19.5, 60.0, 140.0):
            for mat in ("SS/SS", "CS/CS", "CS/SS"):
                for kind in ("fixed_tube_sheet", "floating_head", "u_tube"):
                    for mu in (1, 3):
                        xc("turton_cost", {"area_m2": area, "P_barg": P, "material": mat, "kind": kind, "min_units": mu},
                           lambda a=(area, P, mat, kind, mu): HX.turton_cost(a[0], a[1], a[2], a[3], min_units=a[4]))
        for mat in ("SS304", "CS", "SS316"):
            for kind in ("u_tube", "floating_head"):
                for mu in (1, 4):
                    for cep in (797.9, 720.2):
                        xc("towler_cost", {"area_m2": area, "material": mat, "kind": kind, "min_units": mu, "cepci_target": cep},
                           lambda a=(area, mat, kind, mu, cep): HX.towler_cost(a[0], a[1], a[2], cepci_target=a[4], min_units=a[3]))
    xc("indirect_factor", {}, HX.indirect_factor)
    for crf in (None, 0.0, 0.1, 0.2):
        xc("annual_charge_factor", {"crf": crf}, lambda crf=crf: HX.annual_charge_factor(crf))
        xc("capital_for_annual", {"annual_USD_per_yr": 123456.0, "crf": crf}, lambda crf=crf: HX.capital_for_annual(123456.0, crf))
        xc("annualised_cost", {"capital_USD": 2.5e6, "crf": crf}, lambda crf=crf: HX.annualised_cost(2.5e6, crf))
    for sav, cap in ((1e5, 1e6), (2.5e4, 3e5), (1.0, 0.0)):
        xc("breakeven_crf", {"annual_saving_USD_per_yr": sav, "capital_USD": cap}, lambda s=sav, c=cap: HX.breakeven_crf(s, c))
    # argument sets of scripts/research/heat_exchanger_study.py: the FEHE states of the stored Aspen HI results
    states = []
    for name in ASPEN_FILES:
        res = SimulationResult.model_validate(load(f"{SIM}/{name}"))
        if not (res.inputs.heat_integration and "FEHE" in res.blocks and "S3" in res.streams):
            continue
        s = res.streams
        st = {"duty_kW": abs(res.blocks["FEHE"].duty_kW), "T_hot_in": s["S5"].temperature_C,
              "T_hot_out": s["S6"].temperature_C, "T_cold_in": s["S2"].temperature_C,
              "T_cold_out": s["S3"].temperature_C, "ua_seg_kW_K": analyse(res).fehe.ua_segmented_kW_K}
        states.append((name[:-5], st))
    for sid, st in states:
        a = (st["duty_kW"], st["T_hot_in"], st["T_hot_out"], st["T_cold_in"], st["T_cold_out"])
        variants = [{"U_case": u} for u in ("low", "central", "high", "phase1_assumption")]
        variants += [{"U_case": u, "ua_kW_K": st["ua_seg_kW_K"]} for u in ("low", "central", "high")]
        variants += [{"U_case": u, "ua_kW_K": st["ua_seg_kW_K"], "correlation": "towler"} for u in ("low", "central", "high")]
        variants += [{"U_case": u, "ua_kW_K": st["ua_seg_kW_K"], "counter_current": True} for u in ("low", "central", "high")]
        variants += [{"U_case": float(U), "ua_kW_K": st["ua_seg_kW_K"]} for U in (10, 15, 20, 25, 35, 50, 72.5, 100, 150, 250, 500)]
        variants += [{"U_case": "low", "ua_kW_K": st["ua_seg_kW_K"], **kw} for kw in
                     ({"cepci_target": 720.2}, {"cepci_target": 800.3}, {"material": "CS/SS"}, {"material": "CS/CS"},
                      {"correlation": "towler", "material": "CS/CS"}, {"P_barg": 3.0}, {"correlation": "nope"})]
        for v in variants:
            kw = {k: x for k, x in v.items() if k != "U_case"}
            xc("size_and_cost", {"state": sid, "duty_kW": a[0], "T_hot_in": a[1], "T_hot_out": a[2], "T_cold_in": a[3],
                                 "T_cold_out": a[4], **v}, lambda a=a, v=v, kw=kw: HX.size_and_cost(*a, v["U_case"], **kw))
        for tci in (1e4, 2e5, 1e6, 1e9):
            for corr in ("turton", "towler"):
                xc("breakeven_U", {"state": sid, "duty_kW": a[0], "T_hot_in": a[1], "T_hot_out": a[2], "T_cold_in": a[3],
                                   "T_cold_out": a[4], "tci_breakeven_USD": tci, "ua_kW_K": st["ua_seg_kW_K"], "correlation": corr},
                   lambda a=a, tci=tci, corr=corr, ua=st["ua_seg_kW_K"]: HX.breakeven_U(*a, tci, ua_kW_K=ua, correlation=corr))
    xc("size_and_cost", {"duty_kW": 0.0, "T_hot_in": 600.0, "T_hot_out": 228.4, "T_cold_in": 75.9, "T_cold_out": 550.0,
                         "U_case": "central"}, lambda: HX.size_and_cost(0.0, 600.0, 228.4, 75.9, 550.0, "central"))
    body = {"cases": cases, "stored": stored, "exchanger": ex}
    write_table("heat", body, len(cases) + len(ex))


# ===================================================================================== separation
def separation() -> None:
    out = []

    def sc(fn, args: dict, f):
        out.append({"fn": fn, "args": args, "out": enc(call(f))})

    def feed_of(rel):
        res = SimulationResult.model_validate(load(rel))
        sid, feed, P, T = SC.cracked_gas(res)
        return feed, P, T

    f_py, P_py, T_py = feed_of(f"{SIM}/python_baseline.json")
    f_as, P_as, T_as = feed_of(f"{SIM}/baseline.json")
    f_lp, P_lp, _ = feed_of(f"{SIM}/scn_low_pressure.json")
    feeds = {"python_baseline": f_py, "aspen_baseline": f_as, "aspen_low_pressure": f_lp}

    for fid, fd in feeds.items():
        for (pin, pout) in ((19.5, 30.0), (1.0, 30.0), (5.0, 20.0), (20.0, 19.0), (1.2, 700.0), (4.5, 7.0)):
            for stages in (None, 1, 3):
                for eta in (None, 0.7):
                    sc("compression_power_kW", {"feed": fid, "n_kmol_h": sum(fd.values()), "composition": fd, "T_in_K": 313.15,
                                                "P_in_bar": pin, "P_out_bar": pout, "stages": stages, "eta": eta},
                       lambda fd=fd, pin=pin, pout=pout, st=stages, eta=eta: CO.compression_power_kW(sum(fd.values()), fd, 313.15, pin, pout, st, eta))
    for comp in ({"H2": 1.0}, {"H2": 0.75, "N2": 0.25}):
        for (pin, pout) in ((1.0, 30.0), (1.0, 700.0), (19.0, 350.0)):
            sc("compression_power_kW", {"n_kmol_h": 1.0, "composition": comp, "T_in_K": 313.15, "P_in_bar": pin,
                                        "P_out_bar": pout, "stages": None, "eta": None},
               lambda comp=comp, pin=pin, pout=pout: CO.compression_power_kW(1.0, comp, 313.15, pin, pout))
            sc("compression_power_kW", {"n_kmol_h": 1.0, "composition": comp, "T_in_K": 300.0, "P_in_bar": pin,
                                        "P_out_bar": pout, "stages": 2, "eta": 0.8, "cp_J_molK": 29.1},
               lambda comp=comp, pin=pin, pout=pout: CO.compression_power_kW(1.0, comp, 300.0, pin, pout, 2, 0.8, cp_J_molK=29.1))
    for eta, st in ((0.0, None), (1.2, None), (0.75, 0)):
        sc("compression_power_kW", {"n_kmol_h": 1.0, "composition": {"H2": 1.0}, "T_in_K": 313.15, "P_in_bar": 1.0,
                                    "P_out_bar": 10.0, "stages": st, "eta": eta},
           lambda eta=eta, st=st: CO.compression_power_kW(1.0, {"H2": 1.0}, 313.15, 1.0, 10.0, st, eta))
    sc("compression_power_kW", {"n_kmol_h": 0.0, "composition": {"H2": 1.0}, "T_in_K": 313.15, "P_in_bar": 1.0,
                                "P_out_bar": 10.0, "stages": None, "eta": None},
       lambda: CO.compression_power_kW(0.0, {"H2": 1.0}, 313.15, 1.0, 10.0))
    for pin, pout in ((1.0, 1.0), (1.0, 3.5), (1.0, 3.5000001), (1.0, 12.25), (1.0, 700.0), (19.5, 7.0)):
        sc("default_stages", {"P_in_bar": pin, "P_out_bar": pout}, lambda pin=pin, pout=pout: CO.default_stages(pin, pout))

    for fid, fd in feeds.items():
        for P in (19.5, 5.0, 2.0):
            for b in ("cho2026_5A", "hansen2024_cha_AC", "kum2026_lumped", "hansen2024_lee", "amcrax_baseline"):
                sc("psa_performance", {"feed": fid, "feed_kmol_h": fd, "feed_pressure_bar": P, "basis": b, "feed_temperature_K": 313.15},
                   lambda fd=fd, P=P, b=b: PS.psa_performance(fd, P, basis=b, feed_temperature_K=313.15))
    for kw in ({"h2_recovery": 0.9}, {"target_purity": 0.9999}, {"target_purity": 0.999, "basis": "hansen2024_cha_AC"},
               {"required_feed_pressure_bar": 25.0}, {"tailgas_pressure_bar": 1.5}, {"compressor_eta": 0.8, "compressor_stages": 2},
               {"h2_recovery": 1.5}, {"basis": "unknown_point"}, {"target_purity": 0.9999999, "h2_recovery": 0.99}):
        sc("psa_performance", {"feed": "python_baseline", "feed_kmol_h": f_py, "feed_pressure_bar": 5.0,
                               "feed_temperature_K": 313.15, **kw},
           lambda kw=kw: PS.psa_performance(f_py, 5.0, feed_temperature_K=313.15, **kw))

    for fid, fd in feeds.items():
        for P, pp in ((19.5, 1.0), (5.0, 1.0), (10.0, 1.0), (30.0, 1.0), (19.5, 0.5), (19.5, 2.0), (19.5, 4.0), (19.5, None)):
            for A in (0.0, 5.0, 20.0, 80.0):
                sc("membrane_separator", {"feed": fid, "feed_kmol_h": fd, "area_m2": A, "feed_pressure_bar": P,
                                          "permeate_pressure_bar": pp, "n_profile": 41},
                   lambda fd=fd, A=A, P=P, pp=pp: ME.membrane_separator(fd, A, P, pp, n_profile=41))
    for kw in ({"T_K": 623.15}, {"T_K": 823.15}, {"permeability": "richard_ref54"}, {"permeability": "richard_ref52"},
               {"permeability": "nope"}, {"thickness_m": 2e-6}, {"n_exponent": 0.6}, {"n_exponent": 1.0},
               {"flux_multiplier": 0.85}, {"n_profile": 2}):
        sc("membrane_separator", {"feed": "python_baseline", "feed_kmol_h": f_py, "area_m2": 30.0, "feed_pressure_bar": 19.5,
                                  "permeate_pressure_bar": 1.0, **kw},
           lambda kw=kw: ME.membrane_separator(f_py, 30.0, 19.5, 1.0, **kw))
    sc("membrane_separator", {"feed_kmol_h": f_py, "area_m2": -1.0, "feed_pressure_bar": 19.5},
       lambda: ME.membrane_separator(f_py, -1.0, 19.5))
    for fid, fd in feeds.items():
        for R in (0.5, 0.756, 0.9, 0.95, 0.999):
            for P in (19.5, 5.0):
                sc("area_for_recovery", {"feed": fid, "feed_kmol_h": fd, "target_recovery": R, "feed_pressure_bar": P},
                   lambda fd=fd, R=R, P=P: ME.area_for_recovery(fd, R, P))
    sc("area_for_recovery", {"feed_kmol_h": f_py, "target_recovery": 0.9, "feed_pressure_bar": 19.5, "T_K": 623.15,
                             "permeate_pressure_bar": 2.0},
       lambda: ME.area_for_recovery(f_py, 0.9, 19.5, 2.0, 623.15))

    # purification.py
    for g in ("D", "E3", "B", "A"):
        for y in ({"N2": 100.0, "NH3": 0.05, "H2O": 1.0}, {"N2": 900.0, "NH3": 0.0}, {"N2": 250.0, "NH3": 0.2, "H2O": 6.0}, {}):
            for h2f in (None, 0.9995):
                sc("evaluate_product", {"y_ppm": y, "grade": g, "h2_frac": h2f},
                   lambda y=y, g=g, h2f=h2f: PU.evaluate_product(y, g, h2_frac=h2f, nh3_basis="computed"))
    for fid, fd in feeds.items():
        for rec, pur in ((0.756, 0.9911), (0.71, 0.99), (0.85, 0.999), (0.95, 0.9999)):
            sc("psa_tail_h2_fraction_from_point", {"feed": fid, "feed_kmol_h": fd, "recovery": rec, "purity": pur},
               lambda fd=fd, rec=rec, pur=pur: PU.psa_tail_h2_fraction_from_point(fd, rec, pur))
            sc("psa_split", {"feed": fid, "feed_kmol_h": fd, "recovery": rec, "purity": pur},
               lambda fd=fd, rec=rec, pur=pur: PU.psa_split(fd, rec, pur))
        yt = PU.psa_tail_h2_fraction_from_point(fd, 0.756, 0.9911)
        for pur in (0.99, 0.9911, 0.999, 0.9991, 0.9997, 0.99975, 0.9999, 0.99999):
            for y in (yt, 0.3, 0.6):
                sc("psa_recovery_at_purity", {"feed": fid, "feed_kmol_h": fd, "purity": pur, "y_tail_h2": y},
                   lambda fd=fd, pur=pur, y=y: PU.psa_recovery_at_purity(fd, pur, y))
        for P, pp in ((19.5, 1.0), (5.0, 1.0), (1.3, 1.0), (19.5, 4.0)):
            sc("pinch_recovery", {"feed": fid, "feed_kmol_h": fd, "P_feed_bar": P, "P_perm_bar": pp},
               lambda fd=fd, P=P, pp=pp: PU.pinch_recovery(fd, P, pp))
        for A in (0.0, 10.0, 50.0, 1e6):
            for alpha in (math.inf, 1e3, 1e5):
                sc("membrane_with_leakage", {"feed": fid, "feed_kmol_h": fd, "area_m2": A, "P_feed_bar": 19.5, "P_perm_bar": 1.0,
                                             "T_K": 673.15, "alpha_H2_N2": alpha},
                   lambda fd=fd, A=A, alpha=alpha: PU.membrane_with_leakage(fd, A, 19.5, 1.0, 673.15, alpha_H2_N2=alpha))
        for R in (0.7, 0.9, 0.99):
            for alpha in (math.inf, 1e4):
                sc("membrane_area_for_recovery", {"feed": fid, "feed_kmol_h": fd, "R": R, "P_feed_bar": 19.5, "P_perm_bar": 1.0,
                                                  "T_K": 673.15, "alpha_H2_N2": alpha},
                   lambda fd=fd, R=R, alpha=alpha: PU.membrane_area_for_recovery(fd, R, 19.5, 1.0, 673.15, alpha_H2_N2=alpha))
        for A, lim in ((20.0, 300.0), (20.0, 1000.0), (60.0, 300.0), (60.0, 0.001)):
            sc("required_selectivity", {"feed": fid, "feed_kmol_h": fd, "area": A, "P_feed_bar": 19.5, "P_perm_bar": 1.0,
                                        "T_K": 673.15, "n2_limit_ppm": lim},
               lambda fd=fd, A=A, lim=lim: PU.required_selectivity(fd, A, 19.5, 1.0, 673.15, lim))
        sc("lhv_kW", {"flows_kmol_h": fd}, lambda fd=fd: PU.lhv_kW(fd))
        sc("mass_kg_h", {"flows_kmol_h": fd}, lambda fd=fd: PU.mass_kg_h(fd))
        prod, tail = PU.psa_split(fd, 0.85, 0.999)
        sc("closure", {"feed": fd, "outs": [prod, tail]}, lambda fd=fd, prod=prod, tail=tail: PU.closure(fd, [prod, tail]))
        sc("gas_compression_kWh_per_kg_h2", {"flows": fd, "T_K": 313.15, "P_in_bar": 1.3, "P_out_bar": 19.5, "h2_kg_h": 150.0},
           lambda fd=fd: PU.gas_compression_kWh_per_kg_h2(fd, 313.15, 1.3, 19.5, 150.0))
    sc("closure", {"feed": {"H2": 1.0, "N2": 0.5}, "outs": [{"H2": 0.6}, {"H2": 0.4, "N2": 0.5, "NH3": 1e-13}]},
       lambda: PU.closure({"H2": 1.0, "N2": 0.5}, [{"H2": 0.6}, {"H2": 0.4, "N2": 0.5, "NH3": 1e-13}]))
    for pin, pout in ((1.0, 30.0), (1.0, 350.0), (20.0, 700.0)):
        sc("h2_compression_kWh_per_kg", {"P_in_bar": pin, "P_out_bar": pout}, lambda pin=pin, pout=pout: PU.h2_compression_kWh_per_kg(pin, pout))
    for fid, fd in feeds.items():
        sc("ammonia_slip", {"feed": fid, "cracked_gas_kmol_h": fd}, lambda fd=fd: SC.ammonia_slip(fd))

    stored = []
    for res_file, sep_file in ((f"{SIM}/python_baseline.json", f"{SIM}/separation_python_baseline.json"),
                               (f"{SIM}/baseline.json", f"{SIM}/separation_baseline.json")):
        res = SimulationResult.model_validate(load(res_file))
        cmp = enc(SC.compare_purification(res))
        sc("compare_purification", {"file": res_file}, lambda res=res: SC.compare_purification(res))
        dev, where = max_rel({k: v for k, v in load(sep_file).items() if k != "metadata"}, cmp)
        stored.append({"file": sep_file, "input_file": res_file, "python_max_rel_dev": dev, "worst_path": where,
                       "reproduced_1e12": dev <= 1e-12})
    write_table("separation", {"calls": out, "stored": stored}, len(out))


def main() -> None:
    coolprop_grid()
    install_recorder()
    try:
        flowsheet()
        heat()
    finally:
        remove_recorder()
    recs = sorted(STATES.values(), key=lambda r: (r["fluid"], r["out"], r["in"], r["phase"], r["b"], r["a"]))
    write_table("coolprop_states", {
        "columns": "fluid, out, in, phase, a, b (as coolprop_grid), v = value (or error), d = derivative of the output "
                   "with respect to the varying input (TP: d/dT at constant P; TQ: d/dT along saturation; PQ: d/dP along "
                   "saturation; null: exact lookup only)",
        "recorded_from": "flowsheet and heat tables of this generator (every CoolProp call they made)",
        "states": recs}, len(recs))
    separation()
    save_manifest()


if __name__ == "__main__":
    main()
