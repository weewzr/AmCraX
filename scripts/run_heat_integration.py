"""Run the AmCraX heat-integration (pinch) analysis on a SimulationResult JSON.

Usage:
    python scripts/run_heat_integration.py results/simulations/baseline.json [--dtmin 20] [--out-dir DIR]

Writes results/simulations/heat_integration_<case_id>.json and
results/figures/hi_composite_<case_id>.png, hi_grand_composite_<case_id>.png,
hi_configuration_comparison_<case_id>.png (300 dpi). With --out-dir both go to DIR instead.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from amcrax import paths
from amcrax.heat_integration import analyse
from amcrax.heat_integration.plots import plot_all
from amcrax.schemas import SimulationResult


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("result_json", type=Path)
    ap.add_argument("--dtmin", type=float, default=20.0, help="Minimum approach temperature, K (default 20)")
    ap.add_argument("--out-dir", type=Path, default=None, help="Write JSON and figures here instead of results/")
    a = ap.parse_args(argv)
    res = SimulationResult.model_validate_json(a.result_json.read_text(encoding="utf-8"))
    h = analyse(res, a.dtmin)
    sim_dir = a.out_dir or paths.RESULTS_SIMULATIONS
    fig_dir = a.out_dir or paths.RESULTS_FIGURES
    sim_dir.mkdir(parents=True, exist_ok=True)
    out_json = sim_dir / f"heat_integration_{h.case_id}.json"
    out_json.write_text(h.model_dump_json(indent=2), encoding="utf-8")
    figs = plot_all(h, fig_dir)
    print(f"case {h.case_id} (input source {h.input_source.value}), dT_min = {h.dT_min_K:g} K")
    for t in (h.targets_process, h.targets_with_flue):
        if t is None:
            continue
        pinch = "threshold (no pinch)" if t.pinch_hot_C is None else f"pinch {t.pinch_hot_C:.1f} / {t.pinch_cold_C:.1f} degC (hot/cold)"
        print(f"  {t.label}: Qh,min = {t.hot_utility_kW:.1f} kW, Qc,min = {t.cold_utility_kW:.1f} kW, {pinch}")
    print(f"  {'configuration':58s} {'heat kW':>9s} {'cool kW':>9s} {'recov kW':>9s} {'tailgas kW':>10s} {'red.':>6s} {'kWh/kgH2':>9s}")
    for r in h.configurations:
        sp = "n/a" if r.specific_heat_demand_kWh_per_kgH2 is None else f"{r.specific_heat_demand_kWh_per_kgH2:.3f}"
        print(f"  {r.label:58s} {r.external_heating_kW:9.1f} {r.external_cooling_kW:9.1f} {r.process_heat_recovered_kW:9.1f} "
              f"{r.tailgas_heat_used_kW:10.1f} {100 * r.reduction_vs_no_recovery:5.1f}% {sp:>9s}")
    if h.fehe:
        f = h.fehe
        print(f"  FEHE ({'simulated' if f.present_in_simulation else 'model estimate'}): Q = {f.duty_kW:.1f} kW, "
              f"min approach {f.min_internal_approach_K:.1f} K, LMTD {f.lmtd_K if f.lmtd_K is None else round(f.lmtd_K, 1)} K, "
              f"UA {f.ua_segmented_kW_K} kW/K, area {f.area_m2 if f.area_m2 is None else round(f.area_m2)} m2 at assumed U "
              f"{f.U_assumed_W_m2K:g} W/m2K (range {[round(x) for x in f.area_range_m2]} m2)")
    for c in h.consistency:
        rd = "n/a" if c.rel_deviation is None else f"{100 * c.rel_deviation:+.2f} %"
        print(f"  check {c.item}: model {c.model_kW:.1f} kW vs simulated {c.simulated_kW} kW ({rd})")
    for w in h.warnings:
        print("  WARNING:", w)
    print("wrote", out_json)
    for p in figs:
        print("wrote", p)
    return 0


if __name__ == "__main__":
    sys.exit(main())
