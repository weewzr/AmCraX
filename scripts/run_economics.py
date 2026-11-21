"""Run the AmCraX LCOH model on a SimulationResult JSON.

Usage:
    python scripts/run_economics.py [results/simulations/baseline.json] [--target-lcoh 5.0] [--out-dir DIR]

Without an argument it uses results/simulations/baseline.json (Aspen); if that is missing it falls back to
results/simulations/python_baseline.json, else to amcrax.process_model.run_python_case(CaseInputs()); the
source is recorded in the output.
Writes results/simulations/economics_<case_id>.json, results/sensitivity/lcoh_tornado_<case_id>.csv,
results/sensitivity/lcoh_vs_ammonia_price_<case_id>.csv and results/figures/lcoh_breakdown_<case_id>.png,
lcoh_tornado_<case_id>.png, lcoh_vs_ammonia_price_<case_id>.png.
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

import numpy as np

from amcrax import paths
from amcrax.economics import (
    EconomicAssumptions,
    breakeven_ammonia_price,
    compute_lcoh,
    lcoh_sensitivity,
    lcoh_vs_ammonia_price,
    literature_benchmarks,
)
from amcrax.schemas import CaseInputs, SimulationResult

LABELS = {"capex": "Annualised CAPEX", "fixed_opex": "Fixed OPEX", "ammonia_feed": "NH3 feed",
          "imported_heat": "Imported heat", "electricity": "Electricity", "cooling_water": "Cooling water",
          "catalyst": "Catalyst replacement"}


def _load(arg: Path | None) -> tuple[SimulationResult, str]:
    if arg is not None:
        return SimulationResult.model_validate_json(arg.read_text(encoding="utf-8")), str(arg)
    for name in ("baseline.json", "python_baseline.json"):
        p = paths.RESULTS_SIMULATIONS / name
        if p.exists():
            return SimulationResult.model_validate_json(p.read_text(encoding="utf-8")), str(p)
    from amcrax.process_model import run_python_case
    return run_python_case(CaseInputs()), "amcrax.process_model.run_python_case(CaseInputs())"


def _plots(res, lc, bars, curve, fig_dir: Path) -> list[Path]:
    from amcrax import plotstyle
    import matplotlib.pyplot as plt

    plotstyle.apply_style()
    prov = (f"Process data: {res.source.value} ({res.case_id}); costs: literature/assumption inputs "
            f"(backend/amcrax/data/economics.yaml); preliminary class 4-5 CAPEX")
    out = []
    cid = res.case_id
    cols = [plotstyle.C_PRIMARY, plotstyle.C_GREY, plotstyle.C_NH3, plotstyle.C_HEAT, plotstyle.C_AMBER,
            plotstyle.C_COLD, plotstyle.C_N2]

    # breakdown
    fig, ax = plt.subplots(figsize=(6.4, 2.4))
    left = 0.0
    for (k, v), c in zip(lc.breakdown_USD_per_kg.items(), cols):
        ax.barh([0], [v], left=left, color=c, label=f"{LABELS[k]} {v:.3f}")
        left += v
    ax.set_yticks([])
    ax.set_xlabel("LCOH contribution, USD/kg H2")
    ax.set_title(f"AmCraX LCOH {lc.lcoh_USD_per_kg:.2f} USD/kg H2 ({cid}, NH3 {lc.assumptions.nh3_price_USD_per_t:g} USD/t)")
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.28), ncol=2, fontsize=7.5)
    fig.text(0.01, -0.02, prov, fontsize=6.5, color=plotstyle.C_GREY)
    out.append(_save(fig, fig_dir, f"lcoh_breakdown_{cid}.png"))

    # tornado
    fig, ax = plt.subplots(figsize=(6.4, 3.8))
    base = bars[0].lcoh_base
    for i, b in enumerate(reversed(bars)):
        lo, hi = b.lcoh_at_low - base, b.lcoh_at_high - base
        ax.barh(i, lo, left=base, color=plotstyle.C_COLD)
        ax.barh(i, hi, left=base, color=plotstyle.C_HEAT)
    ax.set_yticks(range(len(bars)))
    ax.set_yticklabels([f"{b.parameter} [{b.low_value:g} / {b.high_value:g}]" for b in reversed(bars)], fontsize=7)
    ax.axvline(base, color="#33415f", lw=0.8)
    ax.set_xlabel("LCOH, USD/kg H2 (blue = low value, orange = high value)")
    ax.set_title(f"LCOH sensitivity, one at a time ({cid})")
    fig.text(0.01, -0.02, prov + "; ranges: cho2026nickel Table 8 / library min-max", fontsize=6.5, color=plotstyle.C_GREY)
    out.append(_save(fig, fig_dir, f"lcoh_tornado_{cid}.png"))

    # vs NH3 price, with literature points
    fig, ax = plt.subplots(figsize=(6.4, 3.8))
    x, y = zip(*curve)
    ax.plot(x, y, color=plotstyle.C_PRIMARY, label="AmCraX (this model)")
    for b in literature_benchmarks():
        if b.get("nh3_price_USD_per_t") and b["unit"] == "USD/kg":
            ax.scatter(b["nh3_price_USD_per_t"], b["value"], s=18, color=plotstyle.C_HEAT, zorder=3)
            ax.annotate(b["citekey"].split("20")[0], (b["nh3_price_USD_per_t"], b["value"]), fontsize=6,
                        xytext=(3, 3), textcoords="offset points")
    ax.scatter([], [], s=18, color=plotstyle.C_HEAT, label="Literature values (not AmCraX results)")
    ax.set_xlabel("Ammonia price, USD/t")
    ax.set_ylabel("LCOH, USD/kg H2")
    ax.set_title(f"LCOH vs ammonia price ({cid})")
    ax.legend(fontsize=7.5)
    fig.text(0.01, -0.02, prov, fontsize=6.5, color=plotstyle.C_GREY)
    out.append(_save(fig, fig_dir, f"lcoh_vs_ammonia_price_{cid}.png"))
    return out


def _save(fig, d: Path, name: str) -> Path:
    import matplotlib.pyplot as plt
    d.mkdir(parents=True, exist_ok=True)
    p = d / name
    fig.savefig(p, dpi=300, bbox_inches="tight", pad_inches=0.12)
    plt.close(fig)
    return p


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("result_json", type=Path, nargs="?", default=None)
    ap.add_argument("--target-lcoh", type=float, default=None, help="Breakeven target, USD/kg (default: none)")
    ap.add_argument("--out-dir", type=Path, default=None)
    a = ap.parse_args(argv)

    res, src_file = _load(a.result_json)
    assump = EconomicAssumptions()
    lc = compute_lcoh(res, assump)
    lc.input_file = src_file
    bars = lcoh_sensitivity(res, assump)
    prices = np.arange(0.0, 1001.0, 25.0)
    curve = lcoh_vs_ammonia_price(res, assump, prices)

    sim_dir = a.out_dir or paths.RESULTS_SIMULATIONS
    sens_dir = a.out_dir or paths.RESULTS_SENSITIVITY
    fig_dir = a.out_dir or paths.RESULTS_FIGURES
    for d in (sim_dir, sens_dir, fig_dir):
        d.mkdir(parents=True, exist_ok=True)
    cid = res.case_id

    payload = json.loads(lc.model_dump_json())
    payload["tornado"] = [dict(b.model_dump(), swing=b.swing) for b in bars]
    payload["literature_benchmarks"] = literature_benchmarks()
    if a.target_lcoh is not None:
        payload["breakeven"] = {"target_lcoh_USD_per_kg": a.target_lcoh,
                                "nh3_price_USD_per_t": breakeven_ammonia_price(res, assump, a.target_lcoh)}
    (sim_dir / f"economics_{cid}.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")

    with open(sens_dir / f"lcoh_tornado_{cid}.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["parameter", "base_value", "low_value", "high_value", "lcoh_base_USD_per_kg",
                    "lcoh_at_low_USD_per_kg", "lcoh_at_high_USD_per_kg", "swing_USD_per_kg", "range_source",
                    "process_data_source"])
        for b in bars:
            w.writerow([b.parameter, b.base_value, b.low_value, b.high_value, b.lcoh_base, b.lcoh_at_low,
                        b.lcoh_at_high, b.swing, b.source_of_range, res.source.value])
    with open(sens_dir / f"lcoh_vs_ammonia_price_{cid}.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["nh3_price_USD_per_t", "lcoh_USD_per_kg", "process_data_source"])
        for p, l in curve:
            w.writerow([p, l, res.source.value])

    figs = _plots(res, lc, bars, curve, fig_dir)
    print(f"case {cid}: process data {res.source.value} from {src_file}")
    print(f"LCOH {lc.lcoh_USD_per_kg:.3f} USD/kg H2 (reconversion {lc.reconversion_cost_USD_per_kg:.3f}); "
          f"CAPEX {lc.capex.total_capex_USD / 1e6:.2f} MUSD ({lc.capex.method}); CRF {lc.crf:.5f}")
    for k, v in lc.breakdown_USD_per_kg.items():
        print(f"  {k:14s} {v:8.4f}")
    print(f"  NH3 feed {lc.kg_nh3_feed_per_kg_h2:.3f} + fuel {lc.kg_nh3_fuel_per_kg_h2:.3f} kg/kg H2 "
          f"(stoichiometric floor {lc.stoichiometric_floor_kg_nh3_per_kg_h2:.3f})")
    for alt in lc.capex.alternatives:
        print(f"  CAPEX alternative {alt.method}: {alt.scaled_capex_USD / 1e6:.2f} MUSD")
    if a.target_lcoh is not None:
        print(f"  breakeven NH3 price for {a.target_lcoh} USD/kg: {payload['breakeven']['nh3_price_USD_per_t']}")
    for p in figs:
        print(f"  wrote {p}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
