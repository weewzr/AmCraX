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


TABLES = {"catalyst": catalyst, "mcmc": mcmc, "optimisation": optimisation}


def main() -> None:
    names = sys.argv[1:] or list(TABLES)
    G4.install_recorder()
    try:
        for n in names:
            TABLES[n]()
    finally:
        G4.remove_recorder()
    prev = OUT / "coolprop_states.json"
    if prev.exists():  # keep the states recorded by tables generated in earlier invocations
        for r in json.loads(prev.read_text(encoding="utf-8"))["states"]:
            k = (r["fluid"], r["out"], r["in"], r["phase"], float(r["a"]), float(r["b"]))
            G4.STATES.setdefault(k, r)
    recs = sorted(G4.STATES.values(), key=lambda r: (r["fluid"], r["out"], r["in"], r["phase"], r["b"], r["a"]))
    write_table("coolprop_states", {
        "columns": "as rust/golden/stage4/coolprop_states.json",
        "recorded_from": "the tables of this generator run: " + ", ".join(names),
        "states": recs}, len(recs))
    save_manifest()


if __name__ == "__main__":
    main()
