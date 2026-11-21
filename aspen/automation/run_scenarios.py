"""Solve the named process scenarios of config/scenarios.json in Aspen Plus V15.

Each scenario is written to results/simulations/<id>.json (source = aspen_plus_v15). Scenarios whose
result file already exists and converged are skipped unless --force is given.

Usage:  python aspen/automation/run_scenarios.py [--force] [id ...]
"""
from __future__ import annotations

import json
import logging
import sys

from amcrax.aspen.runner import run_cases, save_result
from amcrax.paths import CONFIG_DIR, RESULTS_SIMULATIONS, ensure_dirs
from amcrax.schemas import CaseInputs, SimulationResult


def main() -> int:
    logging.basicConfig(level=logging.WARNING, format="%(asctime)s %(levelname)s %(message)s")
    ensure_dirs()
    force = "--force" in sys.argv
    wanted = {a for a in sys.argv[1:] if not a.startswith("-")}
    cfg = json.loads((CONFIG_DIR / "scenarios.json").read_text(encoding="utf-8"))
    cases: list[CaseInputs] = []
    for sc in cfg["process_scenarios"]:
        if wanted and sc["id"] not in wanted:
            continue
        path = RESULTS_SIMULATIONS / f"{sc['id']}.json"
        if path.exists() and not force:
            try:
                if SimulationResult.model_validate_json(path.read_text(encoding="utf-8")).status.converged:
                    print(f"{sc['id']:26s} already solved - skipped")
                    continue
            except Exception:
                pass
        cases.append(CaseInputs(case_id=sc["id"], **sc["overrides"]))
    if not cases:
        return 0
    # order by structure so that as few model reloads as possible are needed
    cases.sort(key=lambda c: (c.heat_integration, c.reactor_pressure_bar))
    failed = 0
    for r in run_cases(cases, study="scenarios"):
        save_result(r)
        k = r.kpis
        print(f"{r.case_id:26s} converged={r.status.converged}  X={k.nh3_conversion}  H2={k.h2_product_kg_h} kg/h  "
              f"Qext={k.total_external_heating_kW} kW  eff={k.lhv_efficiency}")
        failed += 0 if r.status.converged else 1
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
