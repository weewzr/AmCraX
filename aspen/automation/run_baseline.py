"""Build and run the AmCraX baseline models in Aspen Plus V15.

Outputs
-------
aspen/models/baseline.{inp,bkp,apw}           heat-integrated baseline (600 degC, 20 bar) incl. native Sensitivity STEMP
aspen/models/baseline_no_hi.{inp,bkp,apw}     same specification without the feed/effluent exchanger
results/simulations/baseline.json             SimulationResult (source = aspen_plus_v15)
results/simulations/baseline_no_hi.json
results/sensitivity/aspen_native_STEMP.csv    table of the Aspen-native Sensitivity block

Usage:  python aspen/automation/run_baseline.py [--visible]
"""
from __future__ import annotations

import csv
import logging
import shutil
import sys

from amcrax.aspen.runner import run_cases, save_result
from amcrax.aspen.session import AspenSession
from amcrax.paths import ASPEN_MODELS, ASPEN_RUNS, RESULTS_SENSITIVITY, ensure_dirs
from amcrax.schemas import CaseInputs

SENS = r"\Data\Model Analysis Tools\Sensitivity\STEMP\Output"
SENS_COLUMNS = ["reactor_temperature_C", "nh3_conversion", "h2_product_kmol_h", "cracker_duty_kW", "heater_duty_kW"]


def export_native_sensitivity(s: AspenSession, inputs: CaseInputs) -> None:
    """Read the result table of the Aspen-native Sensitivity block STEMP (if present)."""
    rows = []
    for r in s.children(SENS + r"\SENSVAR"):
        vals = [s.get(SENS + rf"\SENSVAR\{r}\{c}") for c in range(1, len(SENS_COLUMNS) + 1)]
        if all(v is not None for v in vals):
            rows.append(vals)
    if not rows:
        return
    out = RESULTS_SENSITIVITY / f"aspen_native_STEMP_{inputs.case_id}.csv"
    with open(out, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(SENS_COLUMNS + ["source"])
        for vals in rows:
            w.writerow(list(vals) + ["aspen_plus_v15 (native Sensitivity block STEMP)"])
    print(f"native sensitivity table: {out}  ({len(rows)} rows)")


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    ensure_dirs()
    visible = "--visible" in sys.argv
    cases = [
        CaseInputs(case_id="baseline"),
        CaseInputs(case_id="baseline_no_hi", heat_integration=False),
    ]
    results = run_cases(
        cases, study="baseline", visible=visible, save_models_to=ASPEN_MODELS,
        native_sensitivity=True, session_hook=export_native_sensitivity,
    )
    ok = True
    for r in results:
        path = save_result(r)
        src = ASPEN_RUNS / "baseline" / f"{r.case_id}.inp"
        if src.exists():
            shutil.copy2(src, ASPEN_MODELS / f"{r.case_id}.inp")
        k, b = r.kpis, r.balances
        print(f"\n=== {r.case_id}  converged={r.status.converged} errors={r.status.has_errors} "
              f"warnings={r.status.has_warnings} engine={r.status.engine_time_s}s -> {path}")
        for m in r.status.messages:
            print("   msg:", m)
        for name, val in k.model_dump().items():
            print(f"   {name:36s} {val}")
        print(f"   mass closure rel   {b.mass_closure_rel}")
        print(f"   N atoms in/out     {b.n_atoms_in_kmol_h} / {b.n_atoms_out_kmol_h}")
        print(f"   H atoms in/out     {b.h_atoms_in_kmol_h} / {b.h_atoms_out_kmol_h}")
        print(f"   energy closure rel {b.energy_closure_rel}")
        ok = ok and r.status.converged
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
