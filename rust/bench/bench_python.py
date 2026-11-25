"""Python side of the stage 3 benchmark (the Rust side is `amcrax bench`). Run from the repository root in the same
GitHub Actions job as the Rust benchmark so that the hardware is identical:

    python rust/bench/bench_python.py --items economics,pfr,gsa,kinetic --kinetic-draws 25 --output bench_python.json

Wall-clock timing with time.perf_counter, median of the repetitions stated per item; same inputs as amcrax bench.
Imports the amcrax package of this repository (backend/) and the study scripts' functions; writes nothing to results/.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import platform
import resource
import statistics
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "backend"))
sys.path.insert(0, str(REPO / "scripts" / "research"))


def timed(reps, f):
    v = []
    for _ in range(reps):
        t0 = time.perf_counter()
        f()
        v.append(time.perf_counter() - t0)
    return statistics.median(v), v


def module(name):
    spec = importlib.util.spec_from_file_location(name, REPO / "scripts" / "research" / f"{name}.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--items", default="economics,pfr,gsa,kinetic")
    ap.add_argument("--kinetic-draws", type=int, default=25)
    ap.add_argument("--output", default="bench_python.json")
    a = ap.parse_args()
    items = a.items.split(",")
    import numpy as np
    import scipy

    from amcrax.economics.singapore import evaluate, extract_summary
    from amcrax.reactor.pfr import simulate_pfr

    S = extract_summary(json.loads((REPO / "results/simulations/baseline.json").read_text(encoding="utf-8")))
    out = {"python": platform.python_version(), "numpy": np.__version__, "scipy": scipy.__version__}
    if "economics" in items:
        one, _ = timed(2001, lambda: evaluate(S, "grey"))
        n = 100_000
        batch, reps = timed(3, lambda: [evaluate(S, 300.0 + i * 0.005)["lcoh_USD_per_kg"] for i in range(n)])
        out["economics"] = {"one_evaluate_s": one, "one_evaluate_reps": 2001, "batch_n": n, "batch_evaluate_dict_s": batch,
                            "batch_reps": len(reps)}
    if "pfr" in items:
        cases = {"isothermal": dict(W_kg=50.0, n_tubes=50),
                 "adiabatic": dict(W_kg=50.0, n_tubes=50, mode="adiabatic", T_in_C=650.0),
                 "external": dict(W_kg=50.0, n_tubes=50, mode="external", T_wall_C=700.0, U_W_m2K=100.0)}
        m = {}
        for k, kw in cases.items():
            m[f"one_{k}_s"], _ = timed(21, lambda kw=kw: simulate_pfr("ru_takahashi_microkinetic", **kw))
        n = 200
        m["batch_n"] = n
        m["batch_isothermal_s"], _ = timed(3, lambda: [simulate_pfr("ru_takahashi_microkinetic", W_kg=50.0, n_tubes=50,
                                                                    T_in_C=500.0 + i) for i in range(n)])
        out["pfr"] = m
    if "catalyst" in items:
        try:
            from amcrax.research import catalyst_comparison as cc
        except Exception as e:  # noqa: BLE001
            cc = None
            out["catalyst"] = {"error": str(e)[:200]}
        T_GRID = [float(t) for t in range(470, 761, 5)]

        def curve():
            if cc is None:
                raise RuntimeError("catalyst_comparison not importable")
            cc.required_mass_kg.cache_clear()
            cc._heat_cost_at.cache_clear()
            cc.lcoh_curve("ru_kum_temkin_pyzhev", T_GRID, hi=True)
        try:
            t, _ = timed(1, curve)
            out["catalyst"] = {"lcoh_curve_59T_s": t, "reps": 1, "property_backend": "CoolProp 8.0.0 (Python wheel)"}
        except Exception as e:  # noqa: BLE001  (CoolProp wheel missing on the runner)
            out["catalyst"] = {"error": str(e)[:200]}
    if "mcmc" in items:
        U = module("uq_takahashi_calibration")
        c = json.loads((REPO / "rust/golden/stage5/mcmc.json").read_text(encoding="utf-8"))["calibration"]
        run = next(r for r in c["runs"] if r["grid"] == 0 and r["n_iter"] == 20000)
        sur = U.Surrogate(np.array(c["grids"][0]))
        logp = U.make_logp(sur, run["idx"], np.array(run["y"]), 20.0)
        t, _ = timed(1, lambda: U.run_chains(logp, np.random.default_rng(20261123), 20000, 20.0))
        out["mcmc"] = {"run_chains_4x20000_s": t, "reps": 1}
    if "objective" in items:
        from amcrax.optimisation import evaluate as EV
        from amcrax.optimisation import problems as PB
        from amcrax.schemas import SimulationResult
        res = SimulationResult.model_validate(json.loads((REPO / "results/simulations/baseline.json").read_text(encoding="utf-8")))
        t, _ = timed(2001, lambda: PB.constraint_values(EV.evaluate_result(res), PB.DEFAULT_CONSTRAINTS))
        out["objective"] = {"evaluate_result_and_constraints_s": t, "reps": 2001}
    if "gsa" in items:
        gm = module("uq_gsa_sobol")
        s_hi = extract_summary(json.loads((REPO / "results/simulations/baseline.json").read_text(encoding="utf-8")))
        s_no = extract_summary(json.loads((REPO / "results/simulations/baseline_no_hi.json").read_text(encoding="utf-8")))

        def full():
            for s in (s_hi, s_no):
                for sc in gm.SCEN:
                    gm.analyse(s, sc)
                    gm.analyse(s, sc, "lognormal")
            gm.analyse(s_hi, "grey", dummy=True)

        t, _ = timed(1, full)
        out["gsa"] = {"full_study_s": t, "reps": 1, "note": "cases and dummy run (figures and file writes not timed)"}
    if "kinetic" in items:
        km = module("uq_kinetic_propagation")
        from amcrax.reactor.pfr import _eq_conversion
        skip = _eq_conversion(873.15, 20.0, km.FEED) < 0.99
        n_d = a.kinetic_draws

        def sl():
            for cid in km.CATS:
                for case in ("C1", "C2"):
                    for d in km.draws(cid, case, km.N_DRAWS, km.SEED)[:n_d]:
                        km.run_draw((cid, d, skip))

        t, _ = timed(1, sl)
        out["kinetic_slice"] = {"threads_1": {"seconds": t},
                                "slice": f"first {n_d} draws of C1 and C2 of both catalysts (4 x {n_d} draws)",
                                "note": "single process (the stored study used a multiprocessing pool)"}
    out["peak_rss_kB"] = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    Path(a.output).write_text(json.dumps(out, indent=1), encoding="utf-8")
    print(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
