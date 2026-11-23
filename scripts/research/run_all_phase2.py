"""Regenerate every Phase 2 research result that depends on the unified reference scenario, in dependency order.

Usage (from the repository root, virtual environment active):

    python scripts/research/run_all_phase2.py            # everything (about 15 minutes plus the kinetic propagation: 10 to 45 minutes)
    python scripts/research/run_all_phase2.py --from uq  # resume at the first script whose name contains "uq"

Nothing here runs Aspen Plus. The Aspen kinetic cases are stored results (results/research/aspen_kinetic) and are
re-run only through aspen/automation on a machine with Aspen Plus V15. After this script, rebuild the evidence
matrix, the report and the website snapshot as described in docs/reproducing.md.
"""
from __future__ import annotations

import argparse
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

# Order matters: each script reads results written by the ones above it.
STEPS = [
    "scripts/research/economics_reference_scenario.py",  # unified baseline, CAPEX audit, supersession table
    "scripts/research/economics_singapore.py",           # scenarios, tornado, Monte Carlo, break-even prices
    "scripts/research/lca_run.py",                       # life-cycle carbon intensity
    "scripts/research/enduse_run.py",                    # power and hydrogen pathways (H1)
    "scripts/research/enduse_threshold.py",              # turbine-efficiency thresholds and sensitivities (H1)
    "scripts/research/purification_study.py",            # purification configurations (H4)
    "scripts/research/purification_phase2.py",           # PSA against Pd-Ag membrane on sourced ranges (H4)
    "scripts/research/catalyst_comparison.py",           # catalyst design cases (H3)
    "scripts/research/heat_exchanger_study.py",          # exchanger sizing, cost, net benefit (H3)
    "scripts/research/catalyst_economics.py",            # catalyst economics, break-even, crossover (H3)
    "scripts/research/carbon_pricing_run.py",            # carbon pricing modes A and B (H2)
    "scripts/research/uq_gsa_sobol.py",                  # global sensitivity analysis
    "scripts/research/uq_kinetic_propagation.py",        # kinetic parameter propagation
    "scripts/research/uq_takahashi_calibration.py",      # Bayesian model-form diagnostic
    "scripts/research/uq_build_validation.py",           # UQ acceptance checks
    "scripts/research/export_simulator_data.py",         # data for the browser simulator
    "scripts/research/build_research_validation.py",     # validation summary across all areas
]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--from", dest="start", default=None, help="start at the first step whose path contains this text")
    args = ap.parse_args()
    steps = STEPS
    if args.start:
        idx = next((i for i, s in enumerate(STEPS) if args.start in s), None)
        if idx is None:
            print(f"no step matches {args.start!r}")
            return 2
        steps = STEPS[idx:]
    failed = []
    for rel in steps:
        t0 = time.time()
        print(f"== {rel}", flush=True)
        proc = subprocess.run([sys.executable, str(ROOT / rel)], cwd=ROOT, capture_output=True, text=True)
        dt = time.time() - t0
        tail = (proc.stdout or "").strip().splitlines()[-2:]
        for line in tail:
            print("   " + line)
        if proc.returncode != 0:
            failed.append(rel)
            print(f"   FAILED (exit {proc.returncode}) after {dt:.0f} s")
            for line in (proc.stderr or "").strip().splitlines()[-8:]:
                print("   ! " + line)
            break
        print(f"   ok in {dt:.0f} s", flush=True)
    if failed:
        print("stopped at: " + failed[0])
        return 1
    print("all steps finished")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
