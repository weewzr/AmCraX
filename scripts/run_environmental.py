"""Run the AmCraX simplified carbon-intensity accounting (NOT a life-cycle assessment).

Usage:
    python scripts/run_environmental.py [results/simulations/baseline.json] [--grid singapore_2024]
                                        [--distance-km 5000] [--out-dir DIR]

Without an argument it uses results/simulations/baseline.json (Aspen) if present, otherwise falls back
to results/simulations/python_baseline.json (Python model); the source is printed and stored.
Writes results/simulations/environmental_<case_id>.json and results/figures/ci_scenarios_<case_id>.png,
ci_breakdown_<case_id>.png (300 dpi). With --out-dir both go to DIR instead.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from amcrax import paths
from amcrax.environmental import carbon_intensity, compare_scenarios
from amcrax.environmental.plots import plot_all
from amcrax.schemas import SimulationResult


def _default_input() -> Path:
    for name in ("baseline.json", "python_baseline.json"):
        p = paths.RESULTS_SIMULATIONS / name
        if p.exists():
            return p
    raise SystemExit("no input: pass a SimulationResult JSON (no baseline.json / python_baseline.json found)")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("result_json", type=Path, nargs="?", default=None)
    ap.add_argument("--grid", default="singapore_2024", help="electricity factor key in environmental.yaml")
    ap.add_argument("--distance-km", type=float, default=None, help="NH3 sea distance (default from YAML, assumption)")
    ap.add_argument("--out-dir", type=Path, default=None)
    a = ap.parse_args(argv)
    src = a.result_json or _default_input()
    res = SimulationResult.model_validate_json(src.read_text(encoding="utf-8"))
    kw = {"grid": a.grid}
    if a.distance_km is not None:
        kw["distance_km"] = a.distance_km
    cmp = compare_scenarios(res, **kw)
    detail = {f"{r}/{h}": carbon_intensity(res, f"{r}/{h}", **kw).model_dump(mode="json")
              for r, h in ((x.nh3_route, x.heating_option) for x in cmp.rows)}
    sim_dir = a.out_dir or paths.RESULTS_SIMULATIONS
    fig_dir = a.out_dir or paths.RESULTS_FIGURES
    sim_dir.mkdir(parents=True, exist_ok=True)
    out = sim_dir / f"environmental_{res.case_id}.json"
    payload = {"input_file": src.name, "comparison": cmp.model_dump(mode="json"), "scenarios": detail}
    out.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    figs = plot_all(cmp, fig_dir)
    print(f"case {res.case_id}: flowsheet source {res.source.value} ({src.name}); grid {cmp.grid}; "
          f"ship {cmp.transport_distance_km:g} km")
    print("SIMPLIFIED CARBON-INTENSITY ACCOUNTING - NOT A LIFE-CYCLE ASSESSMENT")
    for n in cmp.notes[2:]:
        print(" ", n)
    print(f"  {'scenario':28s} {'total':>7s} {'NH3':>7s} {'ship':>7s} {'elec':>7s} {'heat':>7s}  kg CO2e/kg H2")
    for r in cmp.rows:
        b = r.breakdown_kgCO2e_per_kgH2
        print(f"  {r.nh3_route + '/' + r.heating_option:28s} {r.total_kgCO2e_per_kgH2:7.3f} {b.upstream_ammonia:7.3f} "
              f"{b.transport:7.3f} {b.electricity:7.3f} {b.external_heat:7.3f}")
    for rl in cmp.reference_lines:
        print(f"  reference: {rl.label} = {rl.value_kgCO2e_per_kgH2:.3f} ({rl.source})")
    print("wrote", out)
    for p in figs:
        print("wrote", p)
    return 0


if __name__ == "__main__":
    sys.exit(main())
