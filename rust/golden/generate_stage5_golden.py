"""Generate the stage 5 golden reference tables (catalyst studies, end use, LCA, optimisation, MCMC calibration).

Produced ONCE by the Python reference (the ``amcrax`` package of this repository, imported from ``backend/``) with the
project venv and committed; never regenerated from Rust. Run from the repository root, naming the tables to (re)write:

    python rust/golden/generate_stage5_golden.py catalyst

Conventions are those of ``generate_stage4_golden.py`` (repr floats, "nan"/"inf" strings, errors as
{"error": class, "message": ...}); the CoolProp calls made by the new flowsheet and heat-integration states are recorded
the same way and written to ``coolprop_states.json`` (merged over every table generated in the same invocation).
"""

from __future__ import annotations

import csv
import hashlib
import importlib.util
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
_spec = importlib.util.spec_from_file_location("gen4", HERE / "generate_stage4_golden.py")
G4 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(G4)  # imports amcrax from this repository and checks it

REPO = G4.REPO
OUT = HERE / "stage5"
GENERATOR = "rust/golden/generate_stage5_golden.py"
META = dict(G4.META, generator=GENERATOR)
enc, err, call, load = G4.enc, G4.err, G4.call, G4.load


def manifest() -> dict:
    p = OUT / "MANIFEST.json"
    if p.exists():
        m = json.loads(p.read_text(encoding="utf-8"))
        m["meta"] = META
        return m
    return {"meta": META, "files": {}}


MANIFEST = manifest()


def write_table(name: str, body: dict, n_cases: int) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    text = json.dumps(enc({"meta": dict(META, table=name), **body}), separators=(",", ":"), allow_nan=False) + "\n"
    data = text.encode("utf-8")
    (OUT / f"{name}.json").write_bytes(data)
    MANIFEST["files"][f"{name}.json"] = {"sha256": hashlib.sha256(data).hexdigest(), "bytes": len(data),
                                         "cases": n_cases}
    print(f"wrote rust/golden/stage5/{name}.json ({len(data)} bytes, {n_cases} cases)")


def save_manifest() -> None:
    (OUT / "MANIFEST.json").write_bytes((json.dumps(MANIFEST, indent=1, sort_keys=True) + "\n").encode("utf-8"))


def max_rel_flat(stored: dict, new: dict, keys) -> float:
    worst = 0.0
    for k in keys:
        a, b = stored.get(k), new.get(k)
        try:
            a, b = float(a), float(b)
        except (TypeError, ValueError):
            continue
        if a != b:
            worst = max(worst, abs(a - b) / max(abs(a), 1e-300))
    return worst


# ===================================================================================== catalyst studies
def catalyst() -> None:
    from amcrax.research import catalyst_comparison as cc
    from amcrax.schemas import SimulationResult

    T_GRID = [float(t) for t in range(470, 761, 5)]
    BASE = dict(P_bar=20.0, X=0.95, dT=20.0, psa=0.85, feff=cc.FURNACE_EFFICIENCY, scenario="grey")
    ASPEN_CASES = {"ru_kum_temkin_pyzhev": "kum_T499", "nire_ceo2_5ni1ru_lucentini_lhhw": "luc5_T572",
                   "nire_ceo2_2p5ni0p5ru_lucentini_lhhw": "luc25_T576", "ni_takahashi_microkinetic": "tni_T594",
                   "ru_takahashi_microkinetic": "tru_T522"}
    catalysts = {cid: {k: c[k] for k in ("label", "family", "short", "eps_b", "rho_particle", "price", "price_key")}
                 for cid, c in cc.CATALYSTS.items()}
    curves, optima, designs, flows = [], [], [], []
    for hi in (True, False):
        for cid in cc.CATALYSTS:
            c = cc.lcoh_curve(cid, T_GRID, P_bar=20.0, X=0.95, hi=hi, dT=20.0, psa=0.85, feff=BASE["feff"],
                              scenario="grey")
            curves.append({"catalyst_id": cid, "heat_integration": hi, "T_grid": T_GRID, "rows": c})
            oc = cc.optimum(c)
            grid = [oc["T_C"] + k for k in range(-5, 6)]
            loc = cc.lcoh_curve(cid, grid, P_bar=20.0, X=0.95, hi=hi, dT=20.0, psa=0.85, feff=BASE["feff"],
                                scenario="grey")
            o = cc.optimum(loc)
            optima.append({"catalyst_id": cid, "heat_integration": hi, "coarse": oc, "refine_grid": grid,
                           "refined_rows": loc, "refined": o})
            d = cc.design_point(cid, o["T_C"], 20.0, 0.95, heat_integration=hi, W_kg=o["W_kg"])
            designs.append({"kind": "python_optimum", "catalyst_id": cid, "heat_integration": hi, "T_C": o["T_C"],
                            "P_bar": 20.0, "X": 0.95, "W_kg": o["W_kg"], "result_file": None, "out": d})
            flows.append({"T_C": o["T_C"], "P_bar": 20.0, "X": 0.95, "heat_integration": hi,
                          "result": G4.dump_result(cc.kinetic_flowsheet(o["T_C"], 20.0, 0.95, hi))})
    ni_curve = next(c for c in curves if c["catalyst_id"] == cc.REFERENCE_NI and c["heat_integration"])["rows"]
    for Tn in (700.0, 735.0):
        cN = [r for r in ni_curve if abs(r["T_C"] - Tn) < 1e-9][0]
        designs.append({"kind": "fixed_ni", "catalyst_id": cc.REFERENCE_NI, "heat_integration": True, "T_C": Tn,
                        "P_bar": 20.0, "X": 0.95, "W_kg": cN["W_kg"], "result_file": None,
                        "out": cc.design_point(cc.REFERENCE_NI, Tn, 20.0, 0.95, W_kg=cN["W_kg"])})
    pinch = []
    for cid, tag in ASPEN_CASES.items():
        for hi in (True, False):
            fn = f"results/research/aspen_kinetic/ci_{tag}_P20_W100_{'hi' if hi else 'nohi'}.json"
            res = SimulationResult.model_validate(load(fn)["aspen"]["flowsheet_result"])
            T, X = res.inputs.reactor_temperature_C, res.kpis.nh3_conversion
            d = cc.design_point(cid, T, 20.0, round(X, 6), heat_integration=hi, W_kg=100.0, result=res)
            designs.append({"kind": "aspen", "catalyst_id": cid, "heat_integration": hi, "T_C": T, "P_bar": 20.0,
                            "X": round(X, 6), "W_kg": 100.0, "result_file": fn, "out": d})
            py = cc.design_point(cid, T, 20.0, X, heat_integration=hi, W_kg=100.0)
            designs.append({"kind": "python_same_T_X", "catalyst_id": cid, "heat_integration": hi, "T_C": T,
                            "P_bar": 20.0, "X": X, "W_kg": 100.0, "result_file": None, "out": py})
            for dT in (10.0, 20.0, 30.0, 40.0, 50.0):
                pinch.append({"result_file": fn, "dT_min_K": dT, "out": cc.heat_accounting(res, dT)})
    base = SimulationResult.model_validate(load("results/simulations/baseline.json"))
    for dT in (10.0, 20.0, 30.0, 40.0, 50.0):
        pinch.append({"result_file": "results/simulations/baseline.json", "dT_min_K": dT,
                      "out": cc.heat_accounting(base, dT)})
    masses = []
    for cid in cc.CATALYSTS:
        for (T, P, X) in ((480.0, 20.0, 0.95), (600.0, 20.0, 0.95), (650.0, 10.0, 0.9), (700.0, 30.0, 0.99),
                          (450.0, 20.0, 0.95), (550.0, 5.0, 0.97)):
            masses.append({"catalyst_id": cid, "T_C": T, "P_bar": P, "X": X, "W_kg": cc.required_mass_kg(cid, T, P, X),
                           "X_eq": cc.eq_conversion(T, P)})
    # stored-result reproduction flags (the Rust verifier compares with the stored files itself)
    stored = []
    rows_csv = list(csv.DictReader(open(REPO / "results/research/catalyst_comparison/catalyst_design_curves.csv",
                                        encoding="utf-8")))
    new_rows = [dict(catalyst_id=c["catalyst_id"], heat_integration=str(c["heat_integration"]), **r)
                for c in curves for r in c["rows"]]
    keys = [k for k in rows_csv[0] if k not in ("catalyst_id", "heat_integration", "source_type")]
    dev = max((max_rel_flat(a, b, keys) for a, b in zip(rows_csv, new_rows)), default=0.0)
    stored.append({"file": "results/research/catalyst_comparison/catalyst_design_curves.csv", "rows": len(rows_csv),
                   "new_rows": len(new_rows), "python_max_rel_dev": dev,
                   "same_keys": all(a["catalyst_id"] == b["catalyst_id"] and a["heat_integration"] == b["heat_integration"]
                                    for a, b in zip(rows_csv, new_rows))})
    srows = load("results/research/catalyst_comparison/catalyst_comparison.json")["rows"]
    matched, worst = 0, 0.0
    for s in srows:
        for d in designs:
            if d["kind"] in ("python_optimum", "aspen", "fixed_ni") and d["catalyst_id"] == s["catalyst_id"] \
                    and d["heat_integration"] == s["heat_integration"] and d["T_C"] == s["T_C"] \
                    and (s.get("source_type") == "aspen") == (d["kind"] == "aspen"):
                matched += 1
                worst = max(worst, max_rel_flat(s, d["out"], [k for k in s if not isinstance(s[k], (dict, list))]))
    stored.append({"file": "results/research/catalyst_comparison/catalyst_comparison.json", "rows": len(srows),
                   "matched_rows": matched, "python_max_rel_dev": worst})
    body = {"catalysts": catalysts, "T_grid": T_GRID, "curves": curves, "optima": optima, "designs": designs,
            "pinch_dT": pinch, "masses": masses, "flowsheets": flows, "stored": stored,
            "constants": {"FURNACE_EFFICIENCY": cc.FURNACE_EFFICIENCY, "THERMAL_LOSS_FRACTION": cc.THERMAL_LOSS_FRACTION,
                          "CATALYST_LIFETIME_YR": cc.CATALYST_LIFETIME_YR, "FEED_NH3_KMOL_H": cc.FEED_NH3_KMOL_H,
                          "LCA_DISTANCE_KM": cc.LCA_DISTANCE_KM}}
    write_table("catalyst", body, sum(len(c["rows"]) for c in curves) + len(designs) + len(pinch) + len(masses))
    print("stored:", json.dumps(stored))


# ===================================================================================== MCMC calibration
def _ziggurat_tables():
    """NumPy's 256-layer ziggurat tables of random_standard_normal: ki and fi from the Marsaglia-Tsang recurrence in
    double precision, wi recovered exactly from NumPy's own output (x = rabs * wi[idx] on accepted draws; the double
    satisfying every observed product is unique); the whole stream is then checked draw for draw."""
    import math
    import numpy as np
    dn, vn, m1 = 3.6541528853610088, 0.00492867323399, 2.0 ** 52
    tn = dn
    ki, wi, fi = [0] * 256, [0.0] * 256, [0.0] * 256
    q = vn / math.exp(-0.5 * dn * dn)
    ki[0], ki[1], wi[0], wi[255], fi[0], fi[255] = int((dn / q) * m1), 0, q / m1, dn / m1, 1.0, math.exp(-0.5 * dn * dn)
    for i in range(254, 0, -1):
        dn = math.sqrt(-2.0 * math.log(vn / dn + math.exp(-0.5 * dn * dn)))
        ki[i + 1] = int((dn / tn) * m1)
        tn = dn
        fi[i] = math.exp(-0.5 * dn * dn)
        wi[i] = dn / m1
    R, INV_R = 3.6541528853610087963519472518, 0.27366123732975827203338247596
    nd = lambda r: (int(r) >> 11) * (1.0 / 9007199254740992.0)  # noqa: E731

    def walk(raw, n, cons=None, ref=None):
        out, pos = [], 0
        while len(out) < n:
            r = int(raw[pos]); pos += 1
            idx = r & 0xff; r >>= 8; sign = r & 1; rabs = (r >> 1) & 0x000fffffffffffff
            x = rabs * wi[idx]
            x = -x if sign else x
            if rabs < ki[idx]:
                if cons is not None:
                    cons[idx].append((rabs, abs(float(ref[len(out)]))))
                out.append(x); continue
            if idx == 0:
                while True:
                    xx = -INV_R * math.log1p(-nd(raw[pos])); pos += 1
                    yy = -math.log1p(-nd(raw[pos])); pos += 1
                    if yy + yy > xx * xx:
                        out.append(-(R + xx) if ((rabs >> 8) & 1) else R + xx); break
                continue
            u = nd(raw[pos]); pos += 1
            if ((fi[idx - 1] - fi[idx]) * u + fi[idx]) < math.exp(-0.5 * x * x):
                if cons is not None:
                    cons[idx].append((rabs, abs(float(ref[len(out)]))))
                out.append(x)
        return out

    n = 3_000_000
    ref = np.random.Generator(np.random.PCG64(777)).standard_normal(n)
    cons = {i: [] for i in range(256)}
    walk(np.random.PCG64(777).random_raw(2 * n), n, cons, ref)
    for idx in range(256):
        c = cons[idx]
        w = c[0][1] / c[0][0]
        cand = {w}
        lo = hi = w
        for _ in range(40):
            lo, hi = float(np.nextafter(lo, 0)), float(np.nextafter(hi, 1))
            cand |= {lo, hi}
        ok = sorted(v for v in cand if all(float(a * v) == b for a, b in c[:4000]))
        if len(ok) != 1:
            raise SystemExit(f"ziggurat wi[{idx}] not unique: {len(ok)} candidates")
        wi[idx] = ok[0]
    checks = []
    for seed in (20261123, 1, 12345):
        m = 1_000_000
        ref = np.random.Generator(np.random.PCG64(seed)).standard_normal(m)
        got = np.array(walk(np.random.PCG64(seed).random_raw(2 * m), m))
        checks.append({"seed": seed, "n": m, "mismatches": int((got != ref).sum()),
                       "sha256_le_f8": hashlib.sha256(np.ascontiguousarray(ref, "<f8").tobytes()).hexdigest(),
                       "first": ref[:50].tolist()})
    return {"ki": ki, "wi": wi, "fi": fi, "R": R, "INV_R": INV_R, "checks": checks}


def write_ziggurat_rs(z: dict) -> None:
    p = REPO / "rust/crates/amcrax-numerics/src/ziggurat_tables.rs"
    lines = ["//! NumPy's 256-layer ziggurat tables for `random_standard_normal`, written by",
             "//! `rust/golden/generate_stage5_golden.py mcmc` (do not edit): `KI` and `FI` from the Marsaglia-Tsang",
             "//! recurrence in double precision, `WI` recovered exactly from NumPy's output; the generator checks",
             "//! 3 x 10^6 draws of NumPy 2.5.5 draw for draw.", "",
             "pub const KI: [u64; 256] = ["] + [f"    {v}," for v in z["ki"]] + ["];", "", "pub const WI: [f64; 256] = ["] + \
            [f"    {float(v)!r}," for v in z["wi"]] + ["];", "", "pub const FI: [f64; 256] = ["] + [f"    {float(v)!r}," for v in z["fi"]] + \
            ["];", ""]
    p.write_bytes(("\n".join(lines) + "\n").encode("utf-8"))
    print("wrote", p.relative_to(REPO))


def mcmc() -> None:
    import os
    import tempfile
    import numpy as np
    from scipy.interpolate import RectBivariateSpline
    from amcrax.uq import mcmc as M

    z = _ziggurat_tables()
    if any(c["mismatches"] for c in z["checks"]):
        raise SystemExit(f"ziggurat reconstruction differs from NumPy: {z['checks']}")
    write_ziggurat_rs(z)
    # spawn and normal streams of Generator
    g = np.random.default_rng(20261123)
    kids = g.spawn(4)
    spawn = [{"child": i, "normal_0_2": [float(c.normal(0, 2.0)) for _ in range(5)],
              "standard_normal_3": c.standard_normal(3).tolist(), "random": float(c.random())} for i, c in enumerate(kids)]
    kids2 = g.spawn(2)
    spawn2 = [{"child": i, "standard_normal_3": c.standard_normal(3).tolist()} for i, c in enumerate(kids2)]
    # diagnostics on fixed arrays
    rng = np.random.default_rng(5)
    arrays = []
    for shape, ar in (((4, 1500), 0.0), ((4, 2000), 0.9), ((4, 1001), 0.97), ((2, 500), 0.5)):
        e = rng.standard_normal(shape)
        x = np.empty(shape)
        x[:, 0] = e[:, 0]
        for t in range(1, shape[1]):
            x[:, t] = ar * x[:, t - 1] + e[:, t]
        x[1] += 0.3 * (shape[0] > 2)
        arrays.append({"chains": x.tolist(), "rhat": M.rhat(x), "ess_bulk": M.ess_bulk(x)})
    ties = np.round(rng.standard_normal((4, 800)), 1)
    arrays.append({"chains": ties.tolist(), "rhat": M.rhat(ties), "ess_bulk": M.ess_bulk(ties)})
    # adaptive Metropolis on a correlated Gaussian target (chain for chain)
    S = np.array([[1.0, 0.6, -0.2], [0.6, 2.0, 0.3], [-0.2, 0.3, 0.5]])
    Si = np.linalg.inv(S)

    def logp(th):
        th = np.asarray(th)
        return -np.inf if th[0] > 4 else float(-0.5 * th @ Si @ th)

    am = []
    for seed, cov0 in ((11, None), (12, np.diag([0.05, 4.0, 0.1]))):
        r = M.adaptive_metropolis(logp, np.array([0.5, -1.0, 0.2]), 6000, np.random.default_rng(seed), adapt_start=500,
                                  burn_in=3000, cov0=cov0)
        am.append({"seed": seed, "cov0": None if cov0 is None else cov0.tolist(), "n_iter": 6000, "adapt_start": 500,
                   "burn_in": 3000, "x0": [0.5, -1.0, 0.2], "chain": r["chain"].tolist(), "logp": r["logp"].tolist(),
                   "accept_rate": r["accept_rate"], "Sinv": Si.tolist()})
    # the calibration script, run with captures (its outputs go to a scratch directory, never to results/)
    spec = importlib.util.spec_from_file_location("ucal", REPO / "scripts/research/uq_takahashi_calibration.py")
    U = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(U)
    scratch = Path(tempfile.mkdtemp(prefix="amcrax_stage5_"))
    U.OUT, U.FIG = scratch, scratch
    grids, runs = [], []
    real_sur, real_mk, real_run = U.Surrogate.__init__, U.make_logp, U.run_chains

    def sur_init(self, grid):
        self._gid = len(grids)
        grids.append(np.array(grid))
        real_sur(self, grid)

    def mk(sur, idx, y, dE_sd=20.0):
        f = real_mk(sur, idx, y, dE_sd)
        f._meta = {"grid": sur._gid, "idx": list(map(int, idx)), "y": list(map(float, y)), "dE_sd": float(dE_sd)}
        return f

    def run(logp, rng, n_iter, dE_sd=20.0):
        ss = rng.bit_generator.seed_seq
        pre = {"entropy": int(ss.entropy), "spawn_key": list(ss.spawn_key), "n_children_spawned": int(ss.n_children_spawned)}
        C, diag, acc = real_run(logp, rng, n_iter, dE_sd)
        runs.append({**logp._meta, "rng": pre, "n_iter": n_iter, "dE_sd_init": dE_sd, "diag": diag, "acc": acc,
                     "summary": U.summarise(C), "sha256_le_f8": hashlib.sha256(np.ascontiguousarray(C, "<f8").tobytes()).hexdigest(),
                     "head": C[:, :5, :].tolist(), "tail": C[:, -5:, :].tolist(), "shape": list(C.shape)})
        return C, diag, acc

    class SeqPool:  # in-process stand-in for multiprocessing.Pool (same tasks, same results; the order of
        def __init__(self, *a, **k):  # completion does not matter because each task writes its own (i, j) cell)
            pass

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

        def imap_unordered(self, f, tasks, chunksize=1):
            return map(f, tasks)

    U.Surrogate.__init__, U.make_logp, U.run_chains, U.Pool = sur_init, mk, run, SeqPool
    os.environ.setdefault("AMCRAX_UQ_NPROC", str(max(1, (os.cpu_count() or 2) - 1)))
    U.main()
    stored = []
    for key in ("ni", "ru"):
        new = json.loads((scratch / f"takahashi_calibration_{key}.json").read_text(encoding="utf-8"))
        old = load(f"results/research/uq/takahashi_calibration_{key}.json")
        dev, where = G4.max_rel({k: v for k, v in old.items() if k != "provenance"}, {k: v for k, v in new.items() if k != "provenance"})
        csv_same = (scratch / f"takahashi_posterior_{key}.csv").read_bytes().replace(b"\r\n", b"\n") == \
            (REPO / f"results/research/uq/takahashi_posterior_{key}.csv").read_bytes().replace(b"\r\n", b"\n")
        stored.append({"file": f"results/research/uq/takahashi_calibration_{key}.json", "python_max_rel_dev": dev,
                       "worst_path": where, "posterior_csv_identical": csv_same})
    # spline: dense evaluation of the first grids against SciPy
    spl = []
    for gi in range(len(grids)):
        gr = grids[gi]
        zl = U.logit(gr[:, :, 0])
        sp = RectBivariateSpline(U.LNS_GRID, U.DE_GRID, zl, kx=3, ky=3)
        prng = np.random.default_rng(100 + gi)
        pts = np.column_stack([prng.uniform(U.LNS_GRID[0], U.LNS_GRID[-1], 400), prng.uniform(U.DE_GRID[0], U.DE_GRID[-1], 400)])
        pts = np.vstack([pts, [[U.LNS_GRID[0], U.DE_GRID[0]], [U.LNS_GRID[-1], U.DE_GRID[-1]], [U.LNS_GRID[3], U.DE_GRID[7]]]])
        spl.append({"grid": gi, "point_index": 0, "x": pts[:, 0].tolist(), "y": pts[:, 1].tolist(),
                    "ev": [float(sp.ev(a, b)) for a, b in pts]})
    body = {"ziggurat": {k: z[k] for k in ("R", "INV_R", "checks")}, "spawn": spawn, "spawn_second": spawn2,
            "diagnostics": arrays, "adaptive_metropolis": am,
            "calibration": {"LNS_GRID": U.LNS_GRID.tolist(), "DE_GRID": U.DE_GRID.tolist(), "SEED": U.SEED,
                            "N_ITER": U.N_ITER, "N_ITER_SYN": U.N_ITER_SYN, "BURN": U.BURN, "ADAPT": U.ADAPT,
                            "SIGMA_R": U.SIGMA_R, "points": U.digitised(),
                            "grids": [g_.tolist() for g_ in grids], "runs": runs},
            "spline": spl, "stored": stored}
    write_table("mcmc", body, len(arrays) + len(am) + len(runs) + sum(len(s["ev"]) for s in spl))
    print("stored:", json.dumps(stored))

# ===================================================================================== optimisation objectives
def optimisation() -> None:
    from amcrax.optimisation import evaluate as EV
    from amcrax.optimisation import problems as PB
    from amcrax.optimisation.pareto import nh3_price_for_route
    from amcrax.schemas import SimulationResult

    calls = []
    files = sorted(p.name for p in (REPO / "results/simulations").glob("*.json")
                   if isinstance(load(f"results/simulations/{p.name}").get("streams"), dict))
    for name in files:
        res = SimulationResult.model_validate(load(f"results/simulations/{name}"))
        for hs in ("ammonia", "natural_gas", "electric"):
            for route in ("grey", "green", "blue"):
                for price in (None, nh3_price_for_route(route)):
                    kw = {"heat_source": hs, "nh3_route": route, "nh3_price_USD_per_t": price}
                    m = call(EV.evaluate_result, res, **kw)
                    g = PB.constraint_values(m, PB.DEFAULT_CONSTRAINTS) if isinstance(m, dict) and "error" not in m else None
                    calls.append({"file": f"results/simulations/{name}", "args": kw, "out": m, "constraints": g})
        calls.append({"file": f"results/simulations/{name}", "args": {"include_compression": False},
                      "out": call(EV.evaluate_result, res, include_compression=False), "constraints": None})
    write_table("optimisation", {"calls": calls, "green_price": nh3_price_for_route("green"),
                                 "grey_price": nh3_price_for_route("grey")}, len(calls))


# ===================================================================================== end use and LCA
def tree_diff(stored, new, path=""):
    """Compare a stored result file with the rerun output: (numbers compared, max relative deviation, worst path,
    differing non-number leaves, paths only in one of the two). Provenance blocks are skipped."""
    st = {"n": 0, "max": 0.0, "worst": "", "other": [], "only": []}

    def walk(a, b, p):
        if isinstance(a, dict) and isinstance(b, dict):
            for k in a:
                if k == "provenance" or k == "generated_utc":
                    continue
                if k not in b:
                    st["only"].append(f"{p}/{k} (stored only)")
                else:
                    walk(a[k], b[k], f"{p}/{k}")
            for k in b:
                if k not in a and k != "provenance":
                    st["only"].append(f"{p}/{k} (rerun only)")
        elif isinstance(a, list) and isinstance(b, list):
            if len(a) != len(b):
                st["only"].append(f"{p} (lengths {len(a)} {len(b)})")
            for i, (x, y) in enumerate(zip(a, b)):
                walk(x, y, f"{p}[{i}]")
        elif isinstance(a, (int, float)) and isinstance(b, (int, float)) and not isinstance(a, bool) and not isinstance(b, bool):
            st["n"] += 1
            if a != b:
                d = abs(a - b) / max(abs(a), 1e-300)
                if d > st["max"]:
                    st["max"], st["worst"] = d, p
        elif a != b:
            st["other"].append(p)

    walk(stored, new, path)
    st["other"] = st["other"][:50]
    st["only"] = st["only"][:50]
    return st


def _jsonable(o):
    return json.loads(json.dumps(o, default=float))


def enduse() -> None:
    import tempfile
    import numpy as np
    from amcrax.enduse import pathways as pw
    from amcrax.enduse import params as P

    calls = []

    def rec(fn, args, out):
        calls.append({"fn": fn, "args": args, "out": out})

    def act_dict(a):
        return {k: getattr(a, k) for k in ("id", "label", "product", "functional_unit", "nh3_kg", "aux_kWh", "efficiency",
                                           "n2o_kgCO2e", "no_kg", "cracker_h2_kg_h", "capex_kind", "h2_fraction_vol",
                                           "cracked_share", "purity_note", "heat_mode", "cracker_nh3_kg_h")}

    def act_call(**kw):
        try:
            return act_dict(pw.power_activity(**kw))
        except Exception as e:  # noqa: BLE001
            return err(e)

    # ---- direct calls: stoichiometry
    for y in (0.0, 0.1, 0.3, 0.4, 0.6, 0.74, 0.75, 0.8, -0.1):
        for X in (1.0, 0.97, 0.9936, 0.5):
            rec("cracked_share_for_h2_fraction", {"y_h2": y, "conversion": X}, call(pw.cracked_share_for_h2_fraction, y, X))
    for f_ in (0.0, 0.25, 0.5, 1.0):
        for X in (1.0, 0.97):
            rec("h2_fraction_of_blend", {"f": f_, "conversion": X}, pw.h2_fraction_of_blend(f_, X))
            rec("alpha_of_cracked_share", {"f": f_, "conversion": X}, pw.alpha_of_cracked_share(f_, X))
            rec("fuel_lhv_mj_per_kg_nh3_fed", {"f": f_, "conversion": X}, pw.fuel_lhv_mj_per_kg_nh3_fed(f_, X))
    # ---- crackers of the stored cases
    cases = ("baseline", "baseline_no_hi", "scn_fuel_cell_grade", "scn_low_temperature", "scn_high_temperature")
    for c in cases:
        cr = call(pw.load_cracker, c)
        rec("load_cracker", {"case": c}, cr if isinstance(cr, dict) else {**cr.__dict__, "crack_heat_MJ_per_kg_nh3": cr.crack_heat_MJ_per_kg_nh3,
                                                                       "deficit_MJ_per_kg_nh3": cr.deficit_MJ_per_kg_nh3,
                                                                       "h2_product_per_kg_nh3": cr.h2_product_per_kg_nh3,
                                                                       "pump_kWh_per_kg_nh3": cr.pump_kWh_per_kg_nh3})
    # ---- power activities over kinds, H2 fractions, cases, gain, eta and heat-fuel efficiency
    kinds = [("direct", None), ("full_exhaust", None), ("full_fired", None), ("full_purified", None)]
    kinds += [(k, y) for k in ("partial_exhaust", "partial_fired", "blend_purified") for y in (0.2, 0.3, 0.4, 0.6, 0.7)]
    kinds += [("partial_fired", 0.76), ("bogus", None)]
    for c in cases:
        for k, y in kinds:
            rec("power_activity", {"kind": k, "y_h2": y, "case": c}, act_call(kind=k, y_h2=y, case=c))
    for k, y in kinds[:-2]:
        for g in (0.0, 0.5, 1.7, -1.0):
            rec("power_activity", {"kind": k, "y_h2": y, "gain_scale": g}, act_call(kind=k, y_h2=y, gain_scale=g))
        for e in (0.45, 0.55, 0.62):
            rec("power_activity", {"kind": k, "y_h2": y, "eta_h2_fuel": e}, act_call(kind=k, y_h2=y, eta_h2_fuel=e))
        for h in (0.85, 0.9225, 1.2):
            rec("power_activity", {"kind": k, "y_h2": y, "heat_fuel_efficiency": h}, act_call(kind=k, y_h2=y, heat_fuel_efficiency=h))
    # ---- power cost
    for k, y in kinds[:-2]:
        a = pw.power_activity(k, y)
        for kw in ({}, {"hours": 5000.0}, {"discount": 0.07, "life": 30.0}, {"mass_basis_kg_s": 2.0},
                   {"electricity_price": 0.2}, {"unpurified_full_correlation": True}, {"cracker_capex_factor": 2.0},
                   {"plant_capex_factor": 1.12}, {"extra_capex_USD_per_kW": 40.0}):
            for price in (450.0, 1000.0):
                rec("power_cost", {"kind": k, "y_h2": y, "nh3_price": price, **kw}, call(pw.power_cost, a, price, **kw))
    # ---- hydrogen
    for c in cases:
        a = call(pw.hydrogen_activity, c, "h", "lab", "note")
        rec("hydrogen_activity", {"case": c}, a if isinstance(a, dict) else act_dict(a))
        for price in (300.0, 450.0, 1000.0):
            for kw in ({}, {"hours": 5000.0}, {"electricity": 0.2}, {"capex_mode": "legacy"}):
                rec("hydrogen_cost", {"case": c, "nh3_price": price, **kw}, call(pw.hydrogen_cost, c, price, **kw))
    for cfg, gk in (("PSA_AMCRAX", "industrial_99.9"), ("PSA_D_MB", "fuel_cell_grade_D")):
        a, cost = pw.hydrogen_activity_purification(cfg, gk, "i", "l")
        rec("hydrogen_activity_purification", {"config_id": cfg, "grade_key": gk}, {"activity": act_dict(a), "cost": cost})
    # ---- carbon intensity and break-even factor
    for k, y in (("direct", None), ("full_purified", None), ("partial_fired", 0.4)):
        a = pw.power_activity(k, y)
        for ef, d, kw in ((1.16, 5000.0, {}), (2.6, 12000.0, {"grid": 0.5}), (0.0, 0.0, {"boil_off": 0.02, "ship_ef": 0.02})):
            rec("carbon_intensity", {"kind": k, "y_h2": y, "route_ef": ef, "distance_km": d, **kw}, pw.carbon_intensity(a, ef, d, **kw))
        for alt, d in ((367.2, 5000.0), (402.0, 2000.0)):
            rec("breakeven_ef", {"kind": k, "y_h2": y, "alt_ci": alt, "distance_km": d}, pw.breakeven_ef(a, alt, d))

    # ---- the three drivers, run with their outputs redirected to a scratch directory
    scratch = Path(tempfile.mkdtemp(prefix="amcrax_stage5_enduse_"))
    (scratch / "validation").mkdir()
    (scratch / "fig").mkdir()
    csv_rows: dict[str, list] = {}
    runs = {}
    for script in ("lca_run", "enduse_run", "enduse_threshold"):
        spec = importlib.util.spec_from_file_location(f"eu_{script}", REPO / f"scripts/research/{script}.py")
        m = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(m)
        m.OUT, m.FIG = scratch, scratch / "fig"
        m.VAL = scratch / "validation" / "enduse.json" if script == "enduse_threshold" else scratch / "validation"
        real_csv = m.write_csv

        def wcsv(path, rows, _real=real_csv, _s=script):
            csv_rows[f"{_s}/{Path(path).name}"] = _jsonable(rows)
            _real(path, rows)
        m.write_csv = wcsv
        m.main()
    for rel in ("lca_results.json", "assumptions.json", "enduse_results.json", "turbine_threshold.json", "nox_n2o_blends.json",
                "validation/lca.json", "validation/enduse.json"):
        runs[rel] = json.loads((scratch / rel).read_text(encoding="utf-8"))
    # lca_run and enduse_run both write assumptions.json in their OUT; the second overwrites the first in the scratch
    # directory, so the LCA register is re-read from the module call below
    from amcrax.environmental import lca as L
    runs["lca_assumptions_factors"] = {k: v["value"] for k, v in L.FACTORS.items()}
    stored = []
    for rel, srel in (("lca_results.json", "results/research/lca/lca_results.json"),
                      ("enduse_results.json", "results/research/enduse/enduse_results.json"),
                      ("turbine_threshold.json", "results/research/enduse/turbine_threshold.json"),
                      ("nox_n2o_blends.json", "results/research/enduse/nox_n2o_blends.json"),
                      ("validation/lca.json", "results/research/validation/lca.json"),
                      ("validation/enduse.json", "results/research/validation/enduse.json")):
        d = tree_diff(load(srel), runs[rel])
        stored.append({"file": srel, "rerun": rel, **d})
    body = {"calls": calls, "runs": runs, "csv_rows": csv_rows, "stored": stored,
            "params": {k: getattr(P, k) for k in dir(P) if k.isupper() and isinstance(getattr(P, k), (int, float))}}
    write_table("enduse", _jsonable(body), len(calls) + len(runs) + len(csv_rows))
    print("stored:", json.dumps([{k: s[k] for k in ("file", "n", "max", "worst")} | {"n_other": len(s["other"]), "n_only": len(s["only"])} for s in stored], indent=1))


# ===================================================================================== ziggurat experiment
def ziggurat() -> None:
    """The libm values used by NumPy's ziggurat on this (Windows) machine, for the platform experiment of stage 5:
    every exp() of a wedge test and every log1p() of a tail attempt in the first 10^6 draws of each seed, with the
    draw index and layer, so that the Rust generator can (a) compare its own exp/log1p with them and (b) replay the
    stream with these values substituted (which must give NumPy's Windows stream bit for bit)."""
    import math
    import struct
    import numpy as np

    z = _ziggurat_tables()
    ki, wi, fi, R, INV_R = z["ki"], z["wi"], z["fi"], z["R"], z["INV_R"]
    bits = lambda v: struct.unpack("<Q", struct.pack("<d", v))[0]  # noqa: E731
    nd = lambda r: (int(r) >> 11) * (1.0 / 9007199254740992.0)  # noqa: E731
    seeds = []
    for seed in (20261123, 1, 12345):
        n = 1_000_000
        raw = np.random.PCG64(seed).random_raw(2 * n)
        out, pos, wedge, tail = [], 0, [], []
        while len(out) < n:
            r = int(raw[pos]); pos += 1
            idx = r & 0xff; r >>= 8; sign = r & 1; rabs = (r >> 1) & 0x000fffffffffffff
            x = rabs * wi[idx]
            x = -x if sign else x
            if rabs < ki[idx]:
                out.append(x); continue
            if idx == 0:
                while True:
                    l1 = math.log1p(-nd(raw[pos])); pos += 1
                    l2 = math.log1p(-nd(raw[pos])); pos += 1
                    tail.append([len(out), f"{bits(l1):016x}", f"{bits(l2):016x}"])
                    xx, yy = -INV_R * l1, -l2
                    if yy + yy > xx * xx:
                        out.append(-(R + xx) if ((rabs >> 8) & 1) else R + xx); break
                continue
            u = nd(raw[pos]); pos += 1
            e = math.exp(-0.5 * x * x)
            wedge.append([len(out), idx, f"{bits(e):016x}"])
            if ((fi[idx - 1] - fi[idx]) * u + fi[idx]) < e:
                out.append(x)
        ref = np.random.Generator(np.random.PCG64(seed)).standard_normal(n)
        got = np.array(out)
        seeds.append({"seed": seed, "n": n, "emulation_mismatches": int((got != ref).sum()),
                      "sha256_le_f8": hashlib.sha256(np.ascontiguousarray(ref, "<f8").tobytes()).hexdigest(),
                      "wedge": wedge, "tail": tail})
        print(f"seed {seed}: {len(wedge)} wedge tests, {len(tail)} tail attempts, emulation mismatches "
              f"{seeds[-1]['emulation_mismatches']}")
    import platform
    write_table("ziggurat", {"platform": platform.platform(), "python": platform.python_version(),
                             "numpy": np.__version__, "seeds": seeds},
                sum(len(s["wedge"]) + len(s["tail"]) for s in seeds))


# ===================================================================================== catalyst economics
def catalyst_economics() -> None:
    """research/catalyst_economics.py: direct calls of every function, and sections 2 (catalyst cost table) and 4
    (break-even prices and lifetimes, fixed and re-optimised designs) of scripts/research/catalyst_economics.py,
    recomputed with the module functions exactly as the script does (the script itself also draws figures and writes
    results/, so its calculation is repeated here, not run)."""
    import math
    from scipy.optimize import brentq
    from amcrax.research import catalyst_comparison as cc
    from amcrax.research import catalyst_economics as ce
    from amcrax.schemas import SimulationResult

    calls = []

    def rec(fn, args, out):
        calls.append({"fn": fn, "args": args, "out": out})

    CIDS = list(cc.CATALYSTS)
    NI = cc.REFERENCE_NI
    rec("price_table", {}, ce.price_table())
    rec("published_tea_prices", {}, ce.published_tea_prices())
    for name in list(ce.MODELLED.values()) + list(ce.UNMODELLED):
        for sc in cc.PRICE_SCENARIOS:
            rec("price", {"name": name, "scenario": sc}, ce.price(name, sc))
    for w in (0.0, 1.5, 4.0):
        rec("ru_metal_floor", {"wt_pct_ru": w}, ce.ru_metal_floor(w))
    for W, p, L, H in ((100.0, 61.3, 2.0, 6.5e5), (37.2, 900.0, 4.0, 7.1e5)):
        rec("catalyst_cost", {"W_kg": W, "price": p, "lifetime_yr": L, "annual_h2_kg": H}, ce.catalyst_cost(W, p, L, H))
    for T in (520.0, 600.0, 680.0):
        for hi in (True, False):
            rec("state", {"T_C": T, "hi": hi}, call(ce.state, T, 20.0, 0.95, hi))
    for fehe, nh3 in ((0.0, 99.8), (25000.0, 99.8), (80000.0, 60.0)):
        rec("hx_size_ratio", {"fehe_tci_USD": fehe, "nh3_feed_kmol_h": nh3}, ce.hx_size_ratio(fehe, nh3))
    pcen = {c: ce.price(cc.CATALYSTS[c]["price_key"], "central") for c in CIDS}
    for cid in CIDS:
        for T in (480.0, 560.0, 640.0, 735.0):
            for kw in ({}, {"mode": "reference"}, {"mode": "exchanger_reactor_mass"}, {"U_case": "low"}, {"U_case": 75.0},
                       {"hi": False}, {"scenario": 610.0}, {"econ_overrides": {"heat_fuel": "natural_gas"}},
                       {"econ_overrides": {"discount_rate": 0.085}}, {"kinetic_factor": 0.2}, {"W_kg": 100.0}):
                rec("design", {"cid": cid, "T_C": T, "price": pcen[cid], "lifetime_yr": 2.0, **kw},
                    call(ce.design, cid, T, pcen[cid], 2.0, **kw))
    opts = {}
    for cid in CIDS:
        for kw in ({"mode": "exchanger"}, {"mode": "reference"}, {"mode": "exchanger", "U_case": "high"},
                   {"mode": "exchanger", "refine": False}):
            o = ce.optimise(cid, pcen[cid], 2.0, **kw)
            opts[(cid, json.dumps(kw, sort_keys=True))] = o
            rec("optimise", {"cid": cid, "price": pcen[cid], "lifetime_yr": 2.0, **kw}, o)
    for cid in ce.LOW_T:
        for kw in ({"mode": "exchanger"}, {"mode": "reference"}):
            k = json.dumps(kw, sort_keys=True)
            rec("compare", {"low": cid, "ref": NI, **kw}, ce.compare(opts[(cid, k)], opts[(NI, k)]))
    rec("kinetics_label", {"cids": CIDS}, ce.kinetics_label(*CIDS))
    for cid in CIDS:
        rec("kinetics_label", {"cids": [cid, NI]}, ce.kinetics_label(cid, NI))

    # ---- section 2 of the script: catalyst cost table (cost-optimal and fixed 100 kg on the stored Aspen states)
    ASPEN_CASES = {"ru_kum_temkin_pyzhev": "kum_T499", "nire_ceo2_5ni1ru_lucentini_lhhw": "luc5_T572",
                   "nire_ceo2_2p5ni0p5ru_lucentini_lhhw": "luc25_T576", "ni_takahashi_microkinetic": "tni_T594",
                   "ru_takahashi_microkinetic": "tru_T522"}

    def load_aspen(cid, hi):
        fn = f"results/research/aspen_kinetic/ci_{ASPEN_CASES[cid]}_P20_W100_{'hi' if hi else 'nohi'}.json"
        return SimulationResult.model_validate(load(fn)["aspen"]["flowsheet_result"])

    def pc(cid, case):
        return cc.PUBLISHED_TEA_PRICE[cid] if case == "published_TEA" else ce.price(cc.CATALYSTS[cid]["price_key"], case)

    asp_state = {(c, hi): ce.state_from_result(load_aspen(c, hi)) for c in CIDS for hi in (True, False)}
    cost = []
    for cid in CIDS:
        for case in ("low", "central", "high", "published_TEA"):
            p = pc(cid, case)
            for L in sorted(ce.LIFETIMES_YR):
                o = ce.optimise(cid, p, L, mode="reference")
                fx = ce.design(cid, asp_state[(cid, True)]["T_C"], p, L, W_kg=100.0, mode="reference", st=asp_state[(cid, True)])
                cost.append({"catalyst_id": cid, "price_case": case, "price_USD_per_kg": p, "lifetime_yr": L,
                             "costopt": o, "fixed100kg": fx})
    # ---- section 4: break-even prices and lifetimes of the cost-optimal designs (fixed design and re-optimised)
    be = []
    for mode in ("reference", "exchanger", "exchanger_reactor_mass"):
        rf = ce.optimise(NI, pcen[NI], 2.0, mode=mode)
        for cid in ce.LOW_T:
            lo = ce.optimise(cid, pcen[cid], 2.0, mode=mode)
            c = ce.compare(lo, rf)

            def f(p, cid=cid, mode=mode, l_ref=rf["lcoh_USD_per_kg"]):
                return ce.optimise(cid, p, 2.0, mode=mode)["lcoh_USD_per_kg"] - l_ref
            f0 = f(0.0)
            p_re = brentq(f, 0.0, 2e5, xtol=0.05) if f0 < 0 < f(2e5) else None

            def g(L, cid=cid, mode=mode, l_ref=rf["lcoh_USD_per_kg"]):
                return ce.optimise(cid, pcen[cid], L, mode=mode)["lcoh_USD_per_kg"] - l_ref
            L_re = brentq(g, 0.05, 200.0, xtol=1e-3) if g(200.0) < 0 < g(0.05) else None
            be.append({"mode": mode, "catalyst_id": cid, "low": lo, "ref": rf, "compare": c,
                       "lcoh_low_at_zero_price_minus_ref_USD_per_kg": f0, "breakeven_price_reoptimised_USD_per_kg": p_re,
                       "T_at_reoptimised_breakeven_C": ce.optimise(cid, p_re, 2.0, mode=mode)["T_C"] if p_re else None,
                       "breakeven_lifetime_reoptimised_yr": L_re})
    body = {"calls": calls, "cost_table": cost, "breakeven": be,
            "constants": {"FX": ce.FX, "USD_PER_EUR": ce.USD_PER_EUR, "T_GRID": ce.T_GRID, "P_BAR": ce.P_BAR,
                          "X_TARGET": ce.X_TARGET, "BASE_LIFETIME": ce.BASE_LIFETIME, "LOW_T": ce.LOW_T,
                          "MODES": list(ce.MODES), "LIFETIMES_YR": sorted(ce.LIFETIMES_YR),
                          "PUBLISHED_TEA_PRICE": cc.PUBLISHED_TEA_PRICE}}
    write_table("catalyst_economics", _jsonable(enc(body)), len(calls) + len(cost) + len(be))


TABLES = {"catalyst": catalyst, "mcmc": mcmc, "optimisation": optimisation, "enduse": enduse, "ziggurat": ziggurat,
          "catalyst_economics": catalyst_economics}


def main() -> None:
    names = sys.argv[1:] or list(TABLES)
    G4.install_recorder()
    try:
        for n in names:
            TABLES[n]()
    finally:
        G4.remove_recorder()
    prev = OUT / "coolprop_states.json"
    recorded = list(names)
    if prev.exists():  # keep the states recorded by tables generated in earlier invocations
        old = json.loads(prev.read_text(encoding="utf-8"))
        before = old.get("recorded_from", "").split(": ", 1)[-1]
        recorded = [x for x in before.split(", ") if x] + [n for n in names if n not in before.split(", ")]
        for r in old["states"]:
            k = (r["fluid"], r["out"], r["in"], r["phase"], float(r["a"]), float(r["b"]))
            G4.STATES.setdefault(k, r)
    if prev.exists() and len(G4.STATES) == len(old["states"]):
        print("no new CoolProp states: coolprop_states.json unchanged")
        save_manifest()
        return
    recs = sorted(G4.STATES.values(), key=lambda r: (r["fluid"], r["out"], r["in"], r["phase"], r["b"], r["a"]))
    write_table("coolprop_states", {
        "columns": "as rust/golden/stage4/coolprop_states.json",
        "recorded_from": "the tables of this generator run: " + ", ".join(recorded),
        "states": recs}, len(recs))
    save_manifest()


if __name__ == "__main__":
    main()
