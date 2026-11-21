"""AmCraX P2.5 / P3.5: single-objective optimisation, design grid, objective conflicts, Pareto fronts,
Aspen verification candidates and figures. Engine: Python process model (python_model).

Usage:  python scripts/run_optimisation.py
Writes results/optimisation/{single_objective.json, design_grid.csv, pareto.json, pareto.csv,
objective_conflicts.json, candidates_for_aspen.json} and results/figures/opt_*.png.
"""
from __future__ import annotations

import csv
import json
import sys
import time
from datetime import datetime, timezone

import numpy as np

from amcrax import paths
from amcrax.optimisation import OBJECTIVES, conflicts, design_grid, evaluate_result, pareto, run
from amcrax.optimisation.problems import CONSTRAINT_DOCS, DEFAULT_CONSTRAINTS, VARIABLES
from amcrax.schemas import CaseInputs, SimulationResult

OUT = paths.RESULTS_OPTIMISATION
SEED = 12345


def _json(obj, name):
    p = OUT / name
    p.write_text(json.dumps(obj, indent=1, default=lambda o: o.item() if hasattr(o, "item") else str(o)), encoding="utf-8")
    print("wrote", p)


def single_objectives() -> list[dict]:
    runs = []
    kw = dict(seed=SEED, popsize=10, maxiter=30, flatness_points=41)
    for obj in OBJECTIVES:
        t = time.time()
        r = run(obj, **kw)
        r["variant"] = "all four decision variables free"
        r["id"] = obj
        runs.append(r)
        print(f"{obj:22s} {r['metric']}={r['optimum_metrics'][r['metric']]:.5g}  {r['driver']}  ({time.time()-t:.1f}s)")
        t = time.time()
        r2 = run(obj, variables=["reactor_temperature_C", "reactor_pressure_bar"], **kw)
        r2["variant"] = ("T and P only; psa_h2_recovery (0.85) and fehe_hot_end_approach_K (50 K) fixed at baseline because "
                         "the model does not cost PSA size or FEHE area (their optimum would be bound-driven)")
        r2["id"] = obj + "_TP"
        runs.append(r2)
        print(f"{obj+'_TP':22s} {r2['metric']}={r2['optimum_metrics'][r2['metric']]:.5g}  {r2['driver']}  ({time.time()-t:.1f}s)")
    for extra_id, cons, variant in [
        ("min_lcoh_TP_X99", {"min_nh3_conversion": 0.99},
         "T,P only with min_nh3_conversion = 0.99 (literature-informed variant: hansen2024hysys p. 4-5 Tables 3-4)"),
        ("min_lcoh_TP_selfsuff", {"thermal_self_sufficiency": True},
         "T,P only with thermal self-sufficiency (net_fuel_heat_deficit_kW <= 0)"),
    ]:
        r = run("min_lcoh", constraints=cons, variables=["reactor_temperature_C", "reactor_pressure_bar"], **kw)
        r["variant"], r["id"] = variant, extra_id
        runs.append(r)
        print(f"{extra_id:22s} lcoh={r['optimum_metrics']['lcoh_USD_per_kg']:.5g} {r['driver']}")
    # selfsufficiency with recovery free (recovery is the main lever on tail-gas heat)
    r = run("min_lcoh", constraints={"thermal_self_sufficiency": True},
            variables=["reactor_temperature_C", "reactor_pressure_bar", "psa_h2_recovery"], **kw)
    r["variant"], r["id"] = "T,P,recovery with thermal self-sufficiency (approach fixed 50 K)", "min_lcoh_selfsuff"
    runs.append(r)
    print(f"min_lcoh_selfsuff      lcoh={r['optimum_metrics']['lcoh_USD_per_kg']:.5g} {r['driver']}")
    return runs


def aspen_baseline_metrics() -> dict | None:
    p = paths.RESULTS_SIMULATIONS / "baseline.json"
    if not p.exists():
        return None
    return evaluate_result(SimulationResult.model_validate_json(p.read_text(encoding="utf-8")))


def write_grid(rows):
    keys = []
    for r in rows:
        for k in r:
            if k not in keys:
                keys.append(k)
    p = OUT / "design_grid.csv"
    with open(p, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=keys)
        w.writeheader()
        w.writerows(rows)
    print("wrote", p, len(rows), "rows")


def _round_inputs(d: dict) -> dict:
    d = dict(d)
    d["reactor_temperature_C"] = round(d["reactor_temperature_C"], 1)
    d["reactor_pressure_bar"] = max(3.0, round(d["reactor_pressure_bar"], 2))
    d["psa_h2_recovery"] = round(d["psa_h2_recovery"], 3)
    d["fehe_hot_end_approach_K"] = round(d["fehe_hot_end_approach_K"], 1)
    return d


def candidates(single: list[dict], par: dict) -> list[dict]:
    out, seen = [], set()

    def add(cid, label, why, inputs):
        inp = _round_inputs(inputs)
        key = tuple(inp[k] for k in VARIABLES)
        if key in seen or len(out) >= 10:
            return
        seen.add(key)
        inp["case_id"] = cid
        CaseInputs(**inp)  # validate
        out.append({"id": cid, "label": label, "why": why, "inputs": inp})

    short = {"min_lcoh": "opt_lcoh", "max_lhv_efficiency": "opt_eff", "min_specific_heat": "opt_heat",
             "max_h2_production": "opt_h2", "max_conversion": "opt_conv"}
    base = CaseInputs().model_dump()
    for r in single:
        if r["id"] in short and r.get("feasible", False):
            # The candidate sent to Aspen Plus is the reported optimum itself. (An earlier version
            # replaced variables with a flat 1-D objective scan by their baseline values, so the point
            # verified in Aspen was not the reported optimum - found by the independent code review.)
            inp = dict(r["optimum_inputs"])
            flat = [n for n, f in r["flatness"].items() if (f.get("fraction_of_bound_range") or 0) >= 0.999]
            why = f"single-objective optimum (exact reported optimum_inputs); driver: {r['driver']}"
            if flat:
                why += f"; note: 1-D objective scan is flat in {', '.join(flat)} (value not uniquely determined)"
            add(short[r["id"]], f"{r['label']} (4 variables)", why, inp)
    for r in single:
        if r["id"] == "min_lcoh_TP":
            add("opt_lcoh_tp", "Min LCOH, T and P only", f"recovery/approach fixed at baseline; driver: {r['driver']}",
                r["optimum_inputs"])
    # well-spread Pareto points from the LCOH-vs-efficiency default front (or first conflicting front)
    fr = next((f for f in par["fronts"] if f["objectives"] == ["lcoh_USD_per_kg", "carbon_intensity_kgCO2e_per_kgH2"]
               and f.get("heat_source") == "ammonia"), None)
    cands = [f for f in par["fronts"] if len(f["objectives"]) == 2 and f["n_points"] >= 3 and "heat_source" not in f]
    pref = [f for f in cands if f["objectives"] == ["lcoh_USD_per_kg", "h2_yield_overall"]]
    if pref or cands:
        fr = (pref or cands)[0]
    if fr and fr["n_points"]:
        pts = fr["points"]
        m0 = fr["objectives"][0]
        idx = sorted(set(np.linspace(0, len(pts) - 1, min(4, len(pts))).round().astype(int).tolist()))
        for j, i in enumerate(idx):
            p = pts[i]
            inp = CaseInputs().model_dump()
            inp.update({k: p[k] for k in VARIABLES})
            add(f"par_{j+1}", f"Pareto point {j+1} ({fr['objectives'][0]} vs {fr['objectives'][1]})",
                f"non-dominated grid point, {m0}={p[m0]:.4g}, {fr['objectives'][1]}={p[fr['objectives'][1]]:.4g}", inp)
    return out


# ------------------------------------------------------------------------------------------------- figures
def figures(rows, single, par):
    import matplotlib.pyplot as plt
    from amcrax.plotstyle import C_GREY, C_HEAT, C_PRIMARY, PALETTE, apply_style, save

    apply_style()
    prov = "Source: AmCraX Python process model (python_model); LCOH amcrax.economics; CI simplified accounting (not an LCA)"
    # landscape at baseline recovery / approach
    sel = [r for r in rows if r["psa_h2_recovery"] == 0.85 and r["fehe_hot_end_approach_K"] == 50.0]
    Ts = sorted({r["reactor_temperature_C"] for r in sel})
    Ps = sorted({r["reactor_pressure_bar"] for r in sel})
    Z = np.full((len(Ps), len(Ts)), np.nan)
    F = np.zeros_like(Z, bool)
    for r in sel:
        i, j = Ps.index(r["reactor_pressure_bar"]), Ts.index(r["reactor_temperature_C"])
        if r.get("model_ok"):
            Z[i, j] = r["lcoh_USD_per_kg"]
            F[i, j] = r["feasible"]
    fig, ax = plt.subplots(figsize=(6.4, 4.4))
    cs = ax.contourf(Ts, Ps, Z, levels=20, cmap="viridis_r")
    ax.contour(Ts, Ps, Z, levels=10, colors="white", linewidths=0.4)
    fig.colorbar(cs, ax=ax, label="LCOH (USD/kg H2)")
    ii, jj = np.where(~F)
    ax.scatter([Ts[j] for j in jj], [Ps[i] for i in ii], marker="x", color="#b91c1c", s=14,
               label="infeasible (X < 0.95 or FEHE)")
    tp = next(r for r in single if r["id"] == "min_lcoh_TP")
    ax.plot(tp["optimum_inputs"]["reactor_temperature_C"], tp["optimum_inputs"]["reactor_pressure_bar"], "*", color=C_HEAT,
            ms=13, mec="k", label="min LCOH (T,P; rec 0.85, 50 K)")
    ax.plot(600, 20, "o", color="white", mec="k", label="baseline 600 degC / 20 bar")
    ax.set_xlabel("Reactor temperature (degC)")
    ax.set_ylabel("Reactor pressure (bar)")
    ax.set_title("LCOH landscape, PSA recovery 0.85, FEHE approach 50 K (grid points)")
    ax.legend(loc="upper left", fontsize=7)
    fig.text(0.01, -0.02, prov, fontsize=6.5, color=C_GREY)
    save(fig, "opt_lcoh_landscape.png")

    # flatness: min_lcoh (free) 1-D scans
    r = next(x for x in single if x["id"] == "min_lcoh")
    fl = r["flatness"]
    fig, axs = plt.subplots(1, 4, figsize=(11, 3.0), sharey=True)
    f0 = r["optimum_metrics"]["lcoh_USD_per_kg"]
    for ax, (n, d) in zip(axs, fl.items()):
        xs = [s["x"] for s in d["scan"] if s["value"] is not None]
        ys = [100 * (s["value"] / f0 - 1) for s in d["scan"] if s["value"] is not None]
        ax.plot(xs, ys, "-", color=C_PRIMARY)
        bad = [(s["x"], 100 * (s["value"] / f0 - 1)) for s in d["scan"] if s["value"] is not None and not s["feasible"]]
        if bad:
            ax.plot(*zip(*bad), "x", color="#b91c1c", label="infeasible")
            ax.legend(fontsize=7)
        ax.axhline(1.0, color=C_GREY, ls="--", lw=0.8)
        ax.axvline(r["decision_variables"][n]["optimum"], color=C_HEAT, lw=0.8)
        ax.set_xlabel(n)
    axs[0].set_ylabel("LCOH vs optimum (%)")
    axs[0].set_ylim(-0.5, 10)
    fig.suptitle("Flatness of min-LCOH optimum: 1-D scans through the optimum (dashed = +1 %)", fontsize=10)
    fig.text(0.01, -0.06, prov, fontsize=6.5, color=C_GREY)
    save(fig, "opt_objective_flatness.png")

    # pareto plots
    labels = {"lcoh_USD_per_kg": "LCOH (USD/kg H2)", "lhv_efficiency": "LHV efficiency (-)",
              "h2_yield_overall": "H2 yield (-)", "carbon_intensity_kgCO2e_per_kgH2": "CI (kg CO2e/kg H2)",
              "nh3_conversion": "NH3 conversion (-)"}
    feas = [x for x in rows if x.get("feasible")]
    for fr in par["fronts"]:
        if len(fr["objectives"]) != 2 or "heat_source" in fr:
            continue
        a, b = fr["objectives"]
        fig, ax = plt.subplots(figsize=(5.6, 4.0))
        ax.scatter([x[a] for x in feas], [x[b] for x in feas], s=4, color="#cbd5e1", label="feasible grid points")
        ax.plot([p[a] for p in fr["points"]], [p[b] for p in fr["points"]], "o-", color=C_HEAT, ms=4,
                label=f"non-dominated ({fr['n_points']})")
        inf = fr["unconstrained_front_infeasible_points"]
        if inf:
            ax.plot([p[a] for p in inf], [p[b] for p in inf], "x", color="#b91c1c", label="infeasible, would dominate")
        ax.set_xlabel(labels[a]); ax.set_ylabel(labels[b])
        ax.set_title(f"Pareto: {labels[a]} vs {labels[b]}", fontsize=9.5)
        ax.legend(fontsize=7)
        fig.text(0.01, -0.03, prov, fontsize=6, color=C_GREY)
        save(fig, f"opt_pareto_{a.split('_')[0]}_{b.split('_')[0]}.png")
    # heat source / origin overlay
    fig, ax = plt.subplots(figsize=(6.2, 4.2))
    for k, fr in enumerate([f for f in par["fronts"] if "heat_source" in f]):
        a, b = fr["objectives"]
        ax.plot([p[a] for p in fr["points"]], [p[b] for p in fr["points"]], "o-", ms=3.5, color=PALETTE[k],
                label=f"{fr['overlay']} ({fr['n_points']} pts)")
    ax.set_xlabel("LCOH (USD/kg H2)"); ax.set_ylabel("CI (kg CO2e/kg H2)")
    ax.set_title("LCOH vs carbon intensity non-dominated sets by heat source / NH3 origin", fontsize=9.5)
    ax.legend(fontsize=7)
    fig.text(0.01, -0.03, prov + "; NH3 price: 450 USD/t (grey, base) and the sourced 1000 USD/t for green NH3",
             fontsize=6, color=C_GREY)
    save(fig, "opt_pareto_lcoh_ci_overlays.png")


def main():
    paths.ensure_dirs()
    t0 = time.time()
    if "--candidates-only" in sys.argv:
        # rebuild candidates_for_aspen.json from the stored optimisation results (no re-optimisation)
        single = json.loads((OUT / "single_objective.json").read_text(encoding="utf-8"))["results"]
        par = json.loads((OUT / "pareto.json").read_text(encoding="utf-8"))
        cands = candidates(single, par)
        _json(cands, "candidates_for_aspen.json")
        for c in cands:
            print(c["id"], {k: c["inputs"][k] for k in VARIABLES})
        return 0
    single = single_objectives()
    asp = aspen_baseline_metrics()
    created = datetime.now(timezone.utc).isoformat(timespec="seconds")
    _json({"created_utc": created, "engine": "python_model", "source": "python_model", "seed": SEED,
           "assumptions": {"evaluator": "amcrax.optimisation.evaluate_result defaults: heat deficit by burning grey NH3 "
                           "(economics heat_import_mode ammonia_fuel; CI grey/self_firing), grid singapore_2024, NH3 450 USD/t, "
                           "cracked-gas compression electricity when PSA feed < 7 bar",
                           "variables": VARIABLES, "default_constraints": DEFAULT_CONSTRAINTS,
                           "constraint_definitions": CONSTRAINT_DOCS},
           "aspen_baseline_metrics_same_evaluator": asp,
           "aspen_baseline_note": "evaluate_result applied to results/simulations/baseline.json (aspen_plus_v15) for reference",
           "results": single}, "single_objective.json")
    print("single objectives done", round(time.time() - t0), "s")
    rows = design_grid()
    write_grid(rows)
    print("grid done", round(time.time() - t0), "s")
    par = pareto(rows)
    _json({k: v for k, v in par.items() if k != "conflicts"} | {"assumptions": "see single_objective.json"}, "pareto.json")
    _json({"created_utc": par["created_utc"], "engine": "python_model", **par["conflicts"],
           "constraints": par["constraints"], "n_feasible": par["n_feasible"]}, "objective_conflicts.json")
    with open(OUT / "pareto.csv", "w", newline="", encoding="utf-8") as fh:
        w = None
        for fi, fr in enumerate(par["fronts"]):
            for p in fr["points"]:
                d = {"front": fi, "objectives": "|".join(fr["objectives"]), "overlay": fr["overlay"], **p}
                if w is None:
                    w = csv.DictWriter(fh, fieldnames=list(d), extrasaction="ignore")
                    w.writeheader()
                w.writerow(d)
    print("wrote pareto.csv")
    cands = candidates(single, par)
    _json(cands, "candidates_for_aspen.json")
    figures(rows, single, par)
    print("done", round(time.time() - t0), "s")


if __name__ == "__main__":
    sys.exit(main())
