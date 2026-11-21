"""Run the independent Python process model for the baseline (with and without heat integration).

Writes results/simulations/python_baseline.json and python_baseline_no_hi.json
(source = python_model) and prints the KPI table.

    . scripts/env.ps1; python scripts/run_python_baseline.py [--eos ideal|pr]
"""
from __future__ import annotations

import argparse

from amcrax.paths import RESULTS_SIMULATIONS, ensure_dirs
from amcrax.process_model import run_python_case
from amcrax.schemas import CaseInputs, KPIs


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--eos", default="ideal", choices=["ideal", "pr"])
    args = ap.parse_args()
    ensure_dirs()
    suffix = "" if args.eos == "ideal" else "_pr"
    cases = {
        f"python_baseline{suffix}": CaseInputs(case_id=f"python_baseline{suffix}"),
        f"python_baseline_no_hi{suffix}": CaseInputs(case_id=f"python_baseline_no_hi{suffix}", heat_integration=False),
    }
    results = {}
    for name, inp in cases.items():
        r = run_python_case(inp, eos=args.eos)
        path = RESULTS_SIMULATIONS / f"{name}.json"
        path.write_text(r.model_dump_json(indent=2), encoding="utf-8")
        print(f"wrote {path}  (source={r.source.value}, eos={args.eos})")
        results[name] = r
    names = list(results)
    print(f"\n{'KPI':38s}" + "".join(f"{n:>28s}" for n in names))
    for f in KPIs.model_fields:
        vals = [getattr(results[n].kpis, f) for n in names]
        print(f"{f:38s}" + "".join(f"{('-' if v is None else f'{v:.6g}'):>28s}" for v in vals))
    print(f"{'mass_closure_rel':38s}" + "".join(f"{results[n].balances.mass_closure_rel:>28.3e}" for n in names))
    print(f"{'energy_closure_rel':38s}" + "".join(f"{results[n].balances.energy_closure_rel:>28.3e}" for n in names))


if __name__ == "__main__":
    main()
