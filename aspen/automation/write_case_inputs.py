"""Write the Aspen Plus input file of every stored Aspen case and record it in the result.

Each stored Aspen result contains its complete ``CaseInputs``; the Aspen input file is a pure
function of those inputs (``amcrax.aspen.inp_writer.build_flowsheet_input``). This script writes
``aspen/models/cases/<case_id>.inp`` for every converged Aspen case in ``results/simulations`` and
sets ``model_file`` to that file, so that the file named in a result reproduces exactly that case.
(Cases solved by modifying a loaded model in place used to name the input file of the first case of
their group - found by the independent code review.)

No Aspen run is involved; results are not changed apart from the ``model_file`` field.
The baseline pair keeps pointing at the solved backups in ``aspen/models``.
"""
from __future__ import annotations

import json

from amcrax.aspen.inp_writer import build_flowsheet_input
from amcrax.paths import ASPEN_MODELS, RESULTS_SIMULATIONS, ROOT
from amcrax.schemas import DataSource, SimulationResult

KEEP = {"baseline", "baseline_no_hi"}  # solved .bkp/.apw/.inp already live in aspen/models


def main() -> int:
    out_dir = ASPEN_MODELS / "cases"
    out_dir.mkdir(parents=True, exist_ok=True)
    n = 0
    for path in sorted(RESULTS_SIMULATIONS.glob("*.json")):
        try:
            result = SimulationResult.model_validate_json(path.read_text(encoding="utf-8"))
        except Exception:
            continue  # analysis files of other modules
        if result.source != DataSource.ASPEN or not result.status.converged or result.case_id in KEEP:
            continue
        inp = out_dir / f"{result.case_id}.inp"
        inp.write_text(build_flowsheet_input(result.inputs), encoding="ascii")
        raw = json.loads(path.read_text(encoding="utf-8"))
        raw["model_file"] = inp.resolve().relative_to(ROOT.resolve()).as_posix()
        path.write_text(json.dumps(raw, indent=2), encoding="utf-8")
        n += 1
        print(f"{result.case_id:28s} -> {raw['model_file']}")
    print(f"{n} case input files written to {out_dir.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
